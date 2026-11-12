"""Offline integration checks (no Home Assistant instance is modified)."""
from __future__ import annotations
import asyncio
import copy
from datetime import datetime, timedelta, timezone
from io import BytesIO
import importlib.util
from pathlib import Path
import re
import sys
import types
import xml.etree.ElementTree as ET
from zipfile import ZipFile

BASE=Path(__file__).resolve().parents[1]/'custom_components/jw_daily_hydration_log'
RESULTS=[]
def check(label, truth):
    RESULTS.append((label,bool(truth)))
    print(('PASS' if truth else 'FAIL'),label)


def module(name, **props):
    m=types.ModuleType(name)
    for k,v in props.items():setattr(m,k,v)
    sys.modules[name]=m
    return m

package=module('jw_daily_hydration_log')
package.__path__=[str(BASE)]

def load(name):
    spec=importlib.util.spec_from_file_location('jw_daily_hydration_log.'+name,BASE/(name+'.py'))
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    return mod
const=load('const');excel=load('excel')

class FakeStore:
    slots={}
    def __init__(self,hass,version,key):self.key=key
    async def async_load(self):return copy.deepcopy(self.slots.get(self.key))
    async def async_save(self,v):self.slots[self.key]=copy.deepcopy(v)

class FakeTime:
    now_value=datetime(2026,11,8,8,30,tzinfo=timezone(timedelta(hours=1)))
    @staticmethod
    def now():return FakeTime.now_value

class FakeConfigEntry:
    entry_id='test-entry-123'
    data={'name':'Jan-Willem','age':30,'gender':'male','pregnancy':False,'lactation':False,
          'source_mode':'sum','source_sensor':None,'unit':'mL','day_start':'07:00:00','day_end':'22:00:00'}
    options={}

class FakeHass:
    def __init__(self):
        self.bus=types.SimpleNamespace(async_listen=lambda *a:lambda:None)
        self.config=types.SimpleNamespace(time_zone='Europe/Amsterdam')
    def async_create_task(self,coro):return asyncio.create_task(coro)

module('homeassistant')
module('homeassistant.config_entries',ConfigEntry=FakeConfigEntry)
module('homeassistant.const',EVENT_STATE_CHANGED='state_changed')
module('homeassistant.core',HomeAssistant=FakeHass,callback=lambda x:x)
module('homeassistant.helpers')
module('homeassistant.helpers.dispatcher',async_dispatcher_send=lambda *a:None)
module('homeassistant.helpers.event',async_track_time_change=lambda *a,**k:lambda:None)
module('homeassistant.helpers.storage',Store=FakeStore)
module('homeassistant.util',dt=FakeTime,slugify=lambda name:re.sub(r'_+','_',re.sub('[^a-z0-9]+','_',name.lower())).strip('_'))

coordinator=load('coordinator')

async def test_coordinator():
    h=FakeHass()
    c=coordinator.HydrationCoordinator(h,FakeConfigEntry())
    await c.async_initialize()
    check('Hyphenated name normalized', c.slug=='jan_willem')
    try:
        await c.async_add_drink(120,'mL','dashboard')
    except ValueError:
        check('Drink without liquid type rejected',True)
    else:check('Drink without liquid type rejected',False)
    data=[(120,'water'),(150,'coffee'),(300,'tea'),(500,'milk')]
    drinks=await asyncio.gather(*(c.async_add_drink(x,'mL','dashboard',t) for x,t in data))
    ids=[r['id'] for r in drinks]
    check('Four independent records, types explicitly recorded',len(c.get_history())==4 and len(set(ids))==4
          and {r['liquid_type'] for r in c.get_history()}=={'water','coffee','tea','milk'})
    check('Four drinks total 1070 mL',round(c.consumed_ml,1)==1070 and c.manual_consumed_ml==1070)
    try:
        await c.async_edit_drink(ids[0],125,'other','08-11-2026','25:00')
    except ValueError:check('Time validates strict 24h',True)
    else:check('Time validates strict 24h',False)
    await c.async_edit_drink(ids[0],180,'soup','08-11-2026','08:28:10')
    row=next(r for r in c.records if r['id']==ids[0])
    check('Edit in place retains record ID, replaces type and time',row['liquid_type']=='soup' and row['volume_ml']==180
          and row['timestamp'].endswith('08:28:10+01:00') and len(c.get_history())==4)
    check('Edit corrects today total',c.manual_consumed_ml==1130 and c.consumed_ml==1130)
    await c.async_delete_drink(ids[1])
    check('Delete permanently removes old entry',not any(r.get('id')==ids[1] for r in c.records)
          and len(c.get_history())==3)
    check('Delete corrects today total',c.consumed_ml==980 and c.manual_consumed_ml==980)
    await c.async_edit_drink(ids[2],300,'water','07-11-2026','18:00')
    check('Moving an entry to yesterday updates current daily volume',c.manual_consumed_ml==680
          and c.daily_archive['2026-11-07']['consumed_ml']==300)
    check('Moving an entry to yesterday updates daily event counts',len(c.get_history())==2
          and len(c.get_history('2026-11-07'))==1 and c.daily_archive['2026-11-07']['drink_count']==1)
    await c.async_edit_drink(ids[2],350,'tea','07-11-2026','18:30')
    check('Editing previous day updates archived daily totals',c.daily_archive['2026-11-07']['manual_ml']==350
          and c.daily_archive['2026-11-07']['drink_count']==1)
    await c.async_delete_drink(ids[2])
    check('Deleting previous day removes record and subtracts archived total',c.daily_archive['2026-11-07']['manual_ml']==0
          and c.daily_archive['2026-11-07']['drink_count']==0)
    # HA local time in test is 08:30; 23:59 today is a valid intentional entry.
    timestamp = coordinator._local_timestamp(h,'08-11-2026','23:59:59')
    check('Later time today is allowed', timestamp.startswith('2026-11-08T23:59:59+01:00'))
    try: await c.async_add_drink(99,'mL','dashboard','water',day='09-11-2026',clock='00:00')
    except ValueError as exc:check('Future calendar date rejected', 'date' in str(exc).lower())
    else:check('Future calendar date rejected',False)
    try: await c.async_add_drink(99,'mL','dashboard','water',day='29-03-2026',clock='02:30')
    except ValueError:check('Nonexistent Dutch DST wall time rejected',True)
    else:check('Nonexistent Dutch DST wall time rejected',False)
    await c.async_shutdown()
    reloaded=coordinator.HydrationCoordinator(h,FakeConfigEntry())
    await reloaded.async_initialize()
    check('Edited history and hard deletions survive restart',len(reloaded.get_history())==2
          and round(reloaded.consumed_ml)==680 and len(reloaded.get_history('2026-11-07'))==0)
    # Load a v1.0.2-style historic record and make sure its category is unknown, not water.
    legacy=await reloaded.async_add_drink(80,'mL','dashboard','other')
    legacy.pop('liquid_type')
    legacy.pop('liquid_type_id',None)  # A real v1.0.2 record predates both fields.
    await reloaded._save();await reloaded.async_shutdown()
    reloaded=coordinator.HydrationCoordinator(h,FakeConfigEntry());await reloaded.async_initialize()
    check('Legacy v1.0.2 drinks treated as unknown',any(r['liquid_type']=='unknown' for r in reloaded.get_history()))
    FakeTime.now_value=datetime(2026,11,9,0,0,tzinfo=timezone(timedelta(hours=1)))
    await reloaded.async_maybe_reset()
    check('Midnight reset archives the correct 760 mL and keeps dated entries',reloaded.consumed_ml==0
          and reloaded.daily_archive['2026-11-08']['manual_ml']==760 and len(reloaded.get_history('2026-11-08'))==3)
    await reloaded.async_add_drink(200,'mL','dashboard','milk')
    check('New day starts at 200 mL',reloaded.consumed_ml==200 and len(reloaded.get_history())==1)
    await reloaded.async_add_drink(225,'mL','manual_backdate','water',day='06-11-2026',clock='10:30:25')
    check('Backdated registration never changes current day total',reloaded.consumed_ml==200
          and reloaded.daily_archive['2026-11-06']['manual_ml']==225)
    check('Today breakdown derives from current day only',
          reloaded.today_breakdown()==[{'liquid_type':'milk','volume_ml':200.0}])
    historical=reloaded.day_summary('2026-11-08')
    check('Historical day summary uses saved snapshot and its own drink count',
          historical['consumed_ml']==760 and historical['drink_count']==3
          and historical['target_ml']>0 and historical['date']=='2026-11-08')
    check('Historical day bars exclude drinks from other dates',
          sum(x['volume_ml'] for x in historical['liquid_breakdown'])==760
          and any(x['liquid_type']=='milk' and x['volume_ml']==500 for x in historical['liquid_breakdown']))
    current=reloaded.day_summary('2026-11-09')
    check('Current day summary uses live sensor total and its own liquid breakdown',
          current['consumed_ml']==200 and current['drink_count']==1
          and current['liquid_breakdown']==[{'liquid_type':'milk','volume_ml':200.0}])
    older=reloaded.day_summary('2026-11-06')
    check('Backdated day without original snapshot uses stored drink record',
          older['consumed_ml']==225 and older['drink_count']==1
          and older['liquid_breakdown']==[{'liquid_type':'water','volume_ml':225.0}])
    before=reloaded.daily_archive['2026-11-08'].copy()
    reloaded.daily_archive['2026-11-08']['consumed_ml']=985
    reloaded.daily_archive['2026-11-08']['target_ml']=2750
    check('Historical day preserves sensor-inclusive totals and historical target',
          reloaded.day_summary('2026-11-08')['consumed_ml']==985
          and reloaded.day_summary('2026-11-08')['target_ml']==2750)
    reloaded.daily_archive['2026-11-08']=before
    try:
        reloaded.day_summary('2026-11-10')
    except ValueError: check('Future day history summary blocked', True)
    else: check('Future day history summary blocked', False)
    wine=await reloaded.async_add_drink(75,'mL','dashboard','wine')
    check('Wine recorded as distinct type and appears in today breakdown',
          any(x['liquid_type']=='wine' and x['volume_ml']==75 for x in reloaded.today_breakdown()))
    await reloaded.async_delete_drink(wine['id'])
    check('Wine removal correctly updates today breakdown',
          not any(x['liquid_type']=='wine' for x in reloaded.today_breakdown()))
    kinds=reloaded.get_liquid_definitions()
    check('Built-in catalog has seven types including wine and no automatic volumes',len(kinds)==7 and any(x['id']=='wine' and x['icon_mdi']=='mdi:glass-wine' for x in kinds)
          and all(x['default_volume_ml'] is None for x in kinds))
    testsvg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#48aaff"/></svg>'
    custom=await reloaded.async_add_liquid_type('Citroenwater','',testsvg,250)
    check('Custom SVG liquid stores own name, icon and default volume',custom['name']=='Citroenwater'
          and custom['icon_svg']==testsvg and custom['default_volume_ml']==250 and custom['id'].startswith('custom_'))
    try: await reloaded.async_add_liquid_type('Bad SVG','', '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',100)
    except ValueError: check('Reject scripts in SVG uploads',True)
    else:check('Reject scripts in SVG uploads',False)
    try: await reloaded.async_add_liquid_type('External SVG','', '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.com/a"/></svg>',100)
    except ValueError: check('Reject external SVG resources',True)
    else:check('Reject external SVG resources',False)
    try: await reloaded.async_add_liquid_type('Citroenwater','mdi:cup', '',200)
    except ValueError:check('Reject duplicate custom liquid names',True)
    else:check('Reject duplicate custom liquid names',False)
    try: await reloaded.async_add_drink(100,'mL','dashboard','custom_unknown')
    except ValueError: check('Reject non-existent custom liquid',True)
    else:check('Reject non-existent custom liquid',False)
    custom_drink=await reloaded.async_add_drink(250,'mL','dashboard',custom['id'])
    check('Custom liquid drink saved in normal ledger',any(r['liquid_type']==custom['id'] for r in reloaded.get_history()))
    try: await reloaded.async_delete_liquid_type(custom['id'])
    except ValueError:check('Used liquid type cannot be removed',True)
    else:check('Used liquid type cannot be removed',False)
    check('Default quick-add buttons unset for beta3 migration',reloaded.volume_buttons is None)
    builtin=await reloaded.async_update_liquid_type('water','Spring water','mdi:water-plus','',330)
    check('Built-in liquid renamed and default volume added without replacing its ID',
          builtin['id']=='water' and builtin['name']=='Spring water' and builtin['default_volume_ml']==330)
    before_hidden_ids=[item['id'] for item in reloaded.get_history()]
    hidden=await reloaded.async_set_builtin_liquid_visibility('water',False)
    check('Delete built-in hides picker button without deleting definition',hidden['hidden'] is True
          and next(x for x in reloaded.get_liquid_definitions() if x['id']=='water')['hidden'] is True)
    check('Deleting builtin does not delete or retype drink history',
          [item['id'] for item in reloaded.get_history()]==before_hidden_ids)
    try: await reloaded.async_set_builtin_liquid_visibility(custom['id'],False)
    except ValueError:check('Cannot soft-hide custom type using built-in API',True)
    else:check('Cannot soft-hide custom type using built-in API',False)
    try: await reloaded.async_set_builtin_liquid_visibility('water','false')
    except ValueError:check('Visibility requires actual boolean',True)
    else:check('Visibility requires actual boolean',False)
    custom_changed=await reloaded.async_update_liquid_type(custom['id'],'Citroenwater XL','',testsvg,275)
    check('Custom SVG liquid can be renamed with new default and stable ID',
          custom_changed['id']==custom['id'] and custom_changed['default_volume_ml']==275 and
          custom_changed['icon_svg']==testsvg)
    check('Existing drink remains associated with same custom liquid ID after rename',
          any(item['liquid_type']==custom['id'] for item in reloaded.get_history()))
    first=[item['id'] for item in reloaded.get_liquid_definitions()]
    changed=[custom['id']]+[item for item in first if item!=custom['id']]
    stored=await reloaded.async_set_liquid_order(changed)
    check('Reordered liquid buttons retain stable IDs',stored==changed and
          reloaded.get_liquid_definitions()[0]['id']==custom['id'])
    try: await reloaded.async_set_liquid_order(['water','water'])
    except ValueError:check('Invalid/duplicate liquid order rejected',True)
    else:check('Invalid/duplicate liquid order rejected',False)
    volumes=await reloaded.async_set_volume_buttons([333,120,250])
    check('Volume buttons editable and reorderable',volumes==[333,120,250])
    try: await reloaded.async_set_volume_buttons([120,120])
    except ValueError:check('Duplicate volume button rejected without saving',True)
    else:check('Duplicate volume button rejected without saving',False)
    check('Volume settings do not change drink records',
          reloaded.volume_buttons==[333,120,250] and any(x['liquid_type']==custom['id'] for x in reloaded.get_history()))
    await reloaded.async_shutdown()
    reloaded=coordinator.HydrationCoordinator(h,FakeConfigEntry());await reloaded.async_initialize()
    check('Restart persists built-in customizations, type order and volume buttons',
          reloaded.get_liquid_definitions()[0]['id']==custom['id'] and
          next(x for x in reloaded.get_liquid_definitions() if x['id']=='water')['name']=='Spring water' and
          reloaded.volume_buttons==[333,120,250])
    check('Hidden built-in choice persists after HA restart',
          'water' in reloaded.hidden_builtin_liquids and
          next(x for x in reloaded.get_liquid_definitions() if x['id']=='water')['hidden'])
    check('Custom SVG icon, volume and drink survive HA restart',any(x['id']==custom['id'] and x['icon_svg']==testsvg
          and x['default_volume_ml']==275 for x in reloaded.custom_liquid_types) and
          any(x['liquid_type']==custom['id'] for x in reloaded.get_history()))
    hourly=reloaded.chart_hourly_today()
    weekly=reloaded.chart_last_7_days()
    check('Hourly charts expose 24 local clock bins and total registered drinks',
          len(hourly['buckets'])==24 and abs(hourly['total_logged_ml']-sum(b['total_ml'] for b in hourly['buckets']))<0.001)
    check('Hourly charts preserve stable custom liquid IDs',
          any(custom['id'] in b['liquids'] for b in hourly['buckets']))
    check('Seven-day charts include all calendar days and current type breakdown',
          len(weekly['days'])==7 and weekly['days'][-1]['date']==reloaded._today()
          and any(custom['id'] in d['liquids'] for d in weekly['days']))
    check('Chart totals represent recorded drinks, not unattributed external sensor volume',
          hourly['coverage']=='typed_logged_drinks_only' and
          weekly['coverage']=='typed_logged_drinks_only')
    check('Excel filename uses HA-local DD timestamp and literal spaces',
          excel.export_filename('Europe/Amsterdam',datetime(2026,11,9,13,28,tzinfo=timezone.utc))
          == '20261109-1428 jwDaily Hydration Log - All Data.xlsx')
    check('Excel filename handles summer DST correctly',
          excel.export_filename('Europe/Amsterdam',datetime(2026,7,19,13,28,tzinfo=timezone.utc))
          == '20260719-1528 jwDaily Hydration Log - All Data.xlsx')
    snap=reloaded.export_snapshot();payload=excel.export_xlsx([snap],'Europe/Amsterdam')
    with ZipFile(BytesIO(payload)) as z:
        check('Excel four-sheet ZIP CRC',z.testzip() is None)
        names=z.namelist()
        files=['xl/workbook.xml','xl/styles.xml','xl/theme/theme1.xml'] + [
            f'xl/worksheets/sheet{i}.xml' for i in range(1,5)] + [
            'xl/tables/table1.xml','xl/tables/table2.xml']
        check('Reference Excel four sheets and two Excel tables',all(k in names for k in files) and
              'xl/worksheets/sheet5.xml' not in names)
        for f in files:ET.fromstring(z.read(f))
        check('All reference Excel components valid XML',True)
        wb=z.read('xl/workbook.xml').decode()
        check('Excel sheet names and order match reference',
              all(f'name="{n}"' in wb for n in ('Hydration log','Daily intake',
              'Settings - Liquid Types','Settings - Volume Buttons')))
        log=z.read('xl/worksheets/sheet1.xml').decode()
        totals=z.read('xl/worksheets/sheet2.xml').decode()
        catalog_sheet=z.read('xl/worksheets/sheet3.xml').decode()
        pref_sheet=z.read('xl/worksheets/sheet4.xml').decode()
        check('Hydration log follows B2 metadata and B11 table',
              'Home Assistant jwDaily Hydration log - Hydration log' in log
              and 'Drink log rows' in log and 'Liquid name' in log
              and 'Citroenwater XL' in log)
        check('Daily totals follow B2 metadata, B11 table and 7 types',
              'Home Assistant jwDaily Hydration Log  - Daily totals' in totals
              and 'Coffee' in totals and 'Wine' in totals
              and 'Full day' in totals and '<f>I12/G12*100</f>' in totals)
        check('Liquid settings exported in reference sheet 3',
              'Citroenwater XL' in catalog_sheet and 'circle' in catalog_sheet
              and '<v>275' in catalog_sheet and 'Visible in picker' in catalog_sheet
              and 'Spring water' in catalog_sheet and 'mdi:water-plus' in catalog_sheet)
        check('Volume settings exported in reference sheet 4',
              'Original volume mL' in pref_sheet and '<v>333' in pref_sheet
              and '<v>120' in pref_sheet)
        check('Both reference Excel tables have dynamic ranges',
              'tblHydrationLog' in z.read('xl/tables/table1.xml').decode()
              and 'tblDailyIntake' in z.read('xl/tables/table2.xml').decode())
        check('Reference Excel date/time and date-only formats',
              'dd\\-mmm\\-yyyy' in z.read('xl/styles.xml').decode())
        check('Excel row 11 frozen in both detailed sheets',
              'ySplit="11"' in log and 'ySplit="11"' in totals)
    restored=await reloaded.async_set_builtin_liquid_visibility('water',True)
    check('Restore re-enables built-in selection without losing custom display data',
          restored['hidden'] is False and restored['name']=='Spring water' and
          len(reloaded.get_history())>0)
    await reloaded.async_delete_drink(custom_drink['id'])
    check('Deleting drink updates hourly chart bins immediately',
          not any(custom['id'] in b['liquids'] for b in reloaded.chart_hourly_today()['buckets']))
    check('Deleting drink updates rolling seven-day chart immediately',
          not any(custom['id'] in d['liquids'] for d in reloaded.chart_last_7_days()['days']))
    await reloaded.async_delete_liquid_type(custom['id'])
    check('Unused custom type can be permanently removed',not any(x['id']==custom['id'] for x in reloaded.custom_liquid_types))
    await reloaded.async_set_volume_buttons([])
    check('All quick buttons can be intentionally removed',reloaded.volume_buttons==[])
    await reloaded.async_shutdown()
    last=coordinator.HydrationCoordinator(h,FakeConfigEntry());await last.async_initialize()
    check('Empty quick-button configuration survives restart without fallback',last.volume_buttons==[])
    reloaded=last

    await reloaded.async_shutdown()

asyncio.run(test_coordinator())
print(f'QA PASS COUNT: {sum(ok for _,ok in RESULTS)}/{len(RESULTS)}')
if not all(ok for _,ok in RESULTS):sys.exit(1)
