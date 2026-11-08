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
    snap=reloaded.export_snapshot();payload=excel.export_xlsx([snap],'Europe/Amsterdam')
    with ZipFile(BytesIO(payload)) as z:
        check('Excel container ZIP CRC',z.testzip() is None)
        files=['xl/workbook.xml','xl/styles.xml']+[f'xl/worksheets/sheet{i}.xml' for i in range(1,8)]
        check('Seven Excel worksheets present',all(k in z.namelist() for k in files))
        for f in files:ET.fromstring(z.read(f))
        check('Seven worksheets valid XML',True)
        ws=z.read('xl/worksheets/sheet2.xml').decode()
        check('Deleted old drinks absent from Excel',ids[1] not in ws and ids[2] not in ws)
        check('Updated type and volume exported', 'soup' in ws and '<v>180' in ws)
        breakdown=z.read('xl/worksheets/sheet7.xml').decode()
        check('Liquid type breakdown exported with unknown legacy', 'Unknown legacy mL' in breakdown)
        check('Excel dates native with DD-MM-YYYY number format', 's="4"' in breakdown and 'formatCode="dd-mm-yyyy"' in z.read('xl/styles.xml').decode())
    await reloaded.async_shutdown()

asyncio.run(test_coordinator())
print(f'QA PASS COUNT: {sum(ok for _,ok in RESULTS)}/{len(RESULTS)}')
if not all(ok for _,ok in RESULTS):sys.exit(1)
