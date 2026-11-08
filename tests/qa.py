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
    def __init__(self):self.bus=types.SimpleNamespace(async_listen=lambda *a:lambda:None)
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
    check('Hyphenated name normalizes to jan_willem',c.slug=='jan_willem')
    data=[120,150,300,500]
    await asyncio.gather(*(c.async_add_drink(x,'mL','dashboard') for x in data))
    check('Four concurrent clicks become four separate records',len(c.get_history())==4 and len({x['id'] for x in c.get_history()})==4)
    check('Four clicks add exact 1070 mL',c.manual_consumed_ml==1070 and c.consumed_ml==1070)
    await c.async_add_drink(10,'fl_oz','dashboard')
    check('Fluid ounces converted to mL',abs(c.manual_consumed_ml-(1070+295.735))<1e-5)
    try:await c.async_add_drink(0,'mL')
    except ValueError:pass
    else:raise AssertionError('Zero drink accepted')
    check('Invalid zero amount produces no ledger event',len(c.get_history())==5)
    # Reload from Store and verify no loss of timestamped records.
    await c.async_shutdown()
    c2=coordinator.HydrationCoordinator(h,FakeConfigEntry())
    await c2.async_initialize()
    check('Drink history survives integration restart',len(c2.get_history())==5 and c2.consumed_ml==c.consumed_ml)
    FakeTime.now_value=datetime(2026,11,9,0,0,tzinfo=timezone(timedelta(hours=1)))
    await c2.async_maybe_reset()
    check('Midnight resets current total, not ledger',c2.consumed_ml==0 and len(c2.records)>=6 and '2026-11-08' in c2.daily_archive)
    check('New day starts with empty drink history',c2.get_history()==[])
    await c2.async_add_drink(200,'mL')
    check('New day still logs with correct date',len(c2.get_history())==1)
    snap=c2.export_snapshot()
    data=excel.export_xlsx([snap],'Europe/Amsterdam')
    with ZipFile(BytesIO(data)) as z:
        check('Excel ZIP CRC',z.testzip() is None)
        required=['xl/workbook.xml','xl/styles.xml']+[f'xl/worksheets/sheet{i}.xml' for i in range(1,7)]
        check('Excel six complete worksheets',all(x in z.namelist() for x in required))
        for key in required:
            ET.fromstring(z.read(key))
        check('Excel XML well-formed',True)
        sheet=z.read('xl/worksheets/sheet2.xml').decode()
        check('Five old and one new drink exported',sheet.count('<row r=')==7)
        check('Excel numeric values (not strings)', '<v>120' in sheet and '<v>500' in sheet)
        check('Excel dates use datetime style', 's="2"' in sheet)
    await c2.async_set_consumed(700,'mL')
    check('Manual correction recorded separately from drink history',
          c2.records[-1]['kind']=='set_consumed' and len(c2.get_history())==1)
    await c2.async_reset_today()
    check('Manual reset retained as correction record', c2.records[-1]['kind']=='reset')
    check('Manual reset no artificial drink event',len(c2.get_history())==1)
    await c2.async_shutdown()

asyncio.run(test_coordinator())
print(f'QA PASS COUNT: {sum(ok for _,ok in RESULTS)}/{len(RESULTS)}')
if not all(ok for _,ok in RESULTS):sys.exit(1)
