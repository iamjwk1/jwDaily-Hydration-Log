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
    try: await c.async_add_drink(99,'mL','dashboard','water',day='09-11-2026',clock='12:00')
    except ValueError:check('Future drink timestamp rejected',True)
    else:check('Future drink timestamp rejected',False)
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
    snap=reloaded.export_snapshot();payload=excel.export_xlsx([snap],'Europe/Amsterdam')
    with ZipFile(BytesIO(payload)) as z:
        check('Excel container ZIP CRC',z.testzip() is None)
        files=['xl/workbook.xml','xl/styles.xml']+[f'xl/worksheets/sheet{i}.xml' for i in range(1,10)]
        check('Nine Excel worksheets present',all(k in z.namelist() for k in files))
        for f in files:ET.fromstring(z.read(f))
        check('Nine worksheets valid XML',True)
        ws=z.read('xl/worksheets/sheet2.xml').decode()
        check('Deleted old drinks absent from Excel',ids[1] not in ws and ids[2] not in ws)
        check('Updated type and volume exported', 'soup' in ws and '<v>180' in ws)
        breakdown=z.read('xl/worksheets/sheet7.xml').decode()
        check('Liquid type breakdown exported with wine and unknown legacy', 'Unknown legacy mL' in breakdown and 'Wine mL' in breakdown)
        catalog_sheet=z.read('xl/worksheets/sheet8.xml').decode()
        check('Custom liquid catalog exported with SVG and default volume',
              'Citroenwater XL' in catalog_sheet and 'circle' in catalog_sheet and '<v>275' in catalog_sheet)
        pref_sheet=z.read('xl/worksheets/sheet9.xml').decode()
        check('Saved volume button order exported to ninth sheet',
              'Volume mL' in pref_sheet and '<v>333' in pref_sheet and '<v>120' in pref_sheet)
        check('Visibility status included in Excel liquid catalog',
              'Visible in picker' in catalog_sheet and 'Spring water' in catalog_sheet)
        check('Edited built-in name, icon and order exported',
              'Spring water' in catalog_sheet and 'mdi:water-plus' in catalog_sheet and 'Button order' in catalog_sheet)
        workbook_rels=z.read('xl/_rels/workbook.xml.rels').decode()
        check('Styles relationship distinct from all nine worksheet IDs',
              'Id="rId10"' in workbook_rels)
        check('Excel dates native with DD-MM-YYYY number format' , 's="4"' in breakdown and 'formatCode="dd-mm-yyyy"' in z.read('xl/styles.xml').decode())
    restored=await reloaded.async_set_builtin_liquid_visibility('water',True)
    check('Restore re-enables built-in selection without losing custom display data',
          restored['hidden'] is False and restored['name']=='Spring water' and
          len(reloaded.get_history())>0)
    await reloaded.async_delete_drink(custom_drink['id'])
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
