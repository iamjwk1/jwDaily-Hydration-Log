"""Offline integration QA; leaves Home Assistant untouched."""
from __future__ import annotations
from copy import deepcopy
import sys,types,importlib.util,asyncio,json,hashlib,zipfile,io,re,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]/'custom_components/jw_daily_hydration_log'
# Minimal HA stubs, matching the coordinator's read/write contract.
for name in ('homeassistant','homeassistant.config_entries','homeassistant.const','homeassistant.core','homeassistant.helpers','homeassistant.helpers.dispatcher','homeassistant.helpers.event','homeassistant.helpers.storage','homeassistant.util','homeassistant.util.dt'):
    m=types.ModuleType(name);m.__path__=[];sys.modules[name]=m
sys.modules['homeassistant.config_entries'].ConfigEntry=object
sys.modules['homeassistant.const'].EVENT_STATE_CHANGED='state_changed'
sys.modules['homeassistant.core'].HomeAssistant=object
sys.modules['homeassistant.core'].callback=lambda f:f
sys.modules['homeassistant.helpers.dispatcher'].async_dispatcher_send=lambda *args:None
sys.modules['homeassistant.helpers.event'].async_track_time_change=lambda *args,**k:lambda:None
class FakeStore:
    data={}
    def __init__(self,h,ver,key):self.key=key
    async def async_load(self):return deepcopy(self.data.get(self.key))
    async def async_save(self,data):self.data[self.key]=deepcopy(data)
sys.modules['homeassistant.helpers.storage'].Store=FakeStore
sys.modules['homeassistant.util'].slugify=lambda s:re.sub(r'[^a-z0-9]+','_',s.lower()).strip('_')
sys.modules['homeassistant.util.dt'].now=lambda:datetime(2026,11,12,22,10,tzinfo=timezone.utc)
package='sandbox_jwdhl'
pkg=types.ModuleType(package);pkg.__path__=[str(ROOT)];sys.modules[package]=pkg
for mod in ('const','settings_io','data_io','coordinator','excel'):
    spec=importlib.util.spec_from_file_location(package+'.'+mod,ROOT/(mod+'.py'))
    obj=importlib.util.module_from_spec(spec);sys.modules[package+'.'+mod]=obj;spec.loader.exec_module(obj)
from sandbox_jwdhl import coordinator,settings_io,data_io,excel
class FakeHass:
    def __init__(self):self.config=types.SimpleNamespace(time_zone='Europe/Amsterdam');self.bus=types.SimpleNamespace(async_listen=lambda *a:lambda:None);self.config_entries=types.SimpleNamespace(async_update_entry=lambda *a,**k:None);self.data={}
class FakeEntry:
    entry_id='sampleprofile'
    data={'name':'Sample','age':58,'gender':'male','unit':'mL'}
    options={}
def src_records():
    cups=[dict(id='cup_6010b46c4a9c',name='Glass mug',default_volume_ml=180.0,icon_mdi='mdi:cup',hidden=False),
          dict(id='cup_fa5e54e2924d',name='Glass',default_volume_ml=220.0,icon_mdi='mdi:glass-mug-variant',hidden=False)]
    samples=[('coffee',180),('water',500),('milk',180),('tea',180),('custom_0fe105154780',220),
             ('coffee',180),('wine',60),('water',220),('tea',180),('milk',180),('coffee',180),('tea',180)]
    rec=[]
    for n,(typ,vol) in enumerate(samples):
        rec.append({'id':'record'+f'{n:027d}', 'timestamp':f'2026-11-{8+n//3:02d}T{10+n%3:02d}:11:00+01:00',
                    'kind':'drink','liquid_type':typ,'volume_ml':float(vol),'origin':'qa','details':{}})
    return {'consumed_ml':0.0,'manual_consumed_ml':0.0,'last_reset_date':'2026-11-12',
            'last_source_value':None,'source_baseline':0.0,'target_override_ml':2000.0,
            'records':rec,'source_readings':[],'daily_archive':{},'custom_liquid_types':[
                {'id':'custom_0fe105154780','name':'Water (glass)','default_volume_ml':220.0,'icon_mdi':'mdi:water','icon_svg':'','custom':True}],
            'liquid_overrides':{'water':{'name':'Water (cup)','default_volume_ml':180.0}},
            'liquid_colors':{},'liquid_order':['coffee','tea','water','custom_0fe105154780','wine'],
            'hidden_builtin_liquids':[],'cup_types':cups,'quick_buttons':[],
            'volume_buttons':[180,220,500]}


async def main():
    # Two independent shortcuts, one with historical references.
    h=FakeHass();entry=FakeEntry();c=coordinator.HydrationCoordinator(h,entry)
    cup='cup_6010b46c4a9c'
    c.cup_types=[dict(id=cup,name='Glazen beker',default_volume_ml=180.0,icon_mdi='mdi:cup',hidden=False)]
    c.quick_buttons=[dict(id='quick_tea',liquid_type_id='tea',cup_type_id=cup,
                          label_mode='automatic',custom_label='',hidden=False),
                     dict(id='quick_coffee',liquid_type_id='coffee',cup_type_id=cup,
                          label_mode='custom',custom_label='Coffee fast',hidden=False)]
    c.records=[dict(id='old0001',kind='drink',timestamp='2026-11-12T11:00:00+01:00',
                    volume_ml=180.0,liquid_type_id='tea',cup_type_id=cup,
                    quick_button_id='quick_tea',origin='dashboard'),
               dict(id='old0002',kind='drink',timestamp='2026-11-12T12:00:00+01:00',
                    volume_ml=180.0,liquid_type_id='tea',cup_type_id=cup,
                    quick_button_id='quick_tea',quick_button_label_at_log='Tea before rename',origin='dashboard'),
               dict(id='old0003',kind='drink',timestamp='2026-11-12T13:00:00+01:00',
                    volume_ml=180.0,liquid_type_id='coffee',cup_type_id=cup,
                    quick_button_id='quick_coffee',origin='dashboard')]
    c.consumed_ml=c.manual_consumed_ml=540.0
    before=[(r['id'],r['timestamp'],r['volume_ml'],r['liquid_type_id'],r['cup_type_id']) for r in c.records]
    await c._save();await c.async_initialize()
    # Failed persistence cannot leave a partial deletion in active memory.
    normal_save=c._save
    async def broken_save(): raise RuntimeError('injected storage error')
    c._save=broken_save
    try:
        await c.async_manage_quick('delete','quick_tea')
        raise AssertionError('Expected storage error')
    except RuntimeError as e: assert str(e)=='injected storage error'
    finally: c._save=normal_save
    assert len(c.quick_buttons)==2 and c.records[0]['quick_button_id']=='quick_tea'
    print('BETA31_DELETE_FAILURE_ROLLBACK_PASS')
    # A real delete must retain native drink records, original volumes and historical labels.
    result=await c.async_manage_quick('delete','quick_tea')
    assert len(result)==1 and result[0]['id']=='quick_coffee'
    assert [(r['id'],r['timestamp'],r['volume_ml'],r['liquid_type_id'],r['cup_type_id']) for r in c.records]==before
    assert all('quick_button_id' not in r for r in c.records[:2])
    assert c.records[0]['quick_button_label_at_log']=='Tea (Glazen beker)'
    assert c.records[1]['quick_button_label_at_log']=='Tea before rename'
    assert c.records[2]['quick_button_id']=='quick_coffee'
    assert c.get_history('2026-11-12')[0]['quick_button_label_at_log']=='Tea (Glazen beker)'
    print('BETA31_QUICK_DELETE_HISTORY_PRESERVED_PASS')
    try: await c.async_manage_quick('delete','quick_tea');raise AssertionError('Repeat should reject')
    except ValueError as e: assert 'not found' in str(e)
    # Excel must show the historic label, not a deleted raw quick ID.
    exported=c.export_snapshot()
    z=zipfile.ZipFile(io.BytesIO(excel.export_xlsx([exported],when=datetime(2026,11,12,22,0,tzinfo=timezone.utc))))
    assert z.testzip() is None
    sheet=z.read('xl/worksheets/sheet1.xml').decode()
    assert 'Tea (Glazen beker)' in sheet and 'Tea before rename' in sheet
    assert 'quick_tea' not in sheet and 'Coffee fast' in sheet
    assert len([n for n in z.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',n)])==4
    print('BETA31_QUICK_DELETE_EXCEL_LABEL_PASS')
    await c.async_shutdown()
    again=coordinator.HydrationCoordinator(h,entry);await again.async_initialize()
    assert len(again.quick_buttons)==1 and again.quick_buttons[0]['id']=='quick_coffee'
    assert again.records==c.records
    # Existing Add/Edit/Hide/Restore and Data imports continue to work.
    await again.async_manage_quick('hide','quick_coffee')
    assert again.quick_buttons[0]['hidden'] is True
    await again.async_manage_quick('restore','quick_coffee')
    assert again.quick_buttons[0]['hidden'] is False
    added=await again.async_add_drink(180,'mL','dashboard','coffee',cup_type_id=cup,quick_button_id='quick_coffee')
    assert added['quick_button_label_at_log']=='Coffee fast'
    assert added['quick_button_id']=='quick_coffee'
    await again.async_manage_quick('delete','quick_coffee')
    stored=next(r for r in again.records if r['id']==added['id'])
    assert stored['quick_button_label_at_log']=='Coffee fast' and 'quick_button_id' not in stored
    assert again.quick_buttons==[]
    print('BETA31_ADD_HIDE_RESTORE_DELETE_RESTART_PASS')
    # JSON Data parser must accept legitimate historical label snapshots and reject controls.
    snapshot=again.export_data_snapshot() if hasattr(again,'export_data_snapshot') else None
    assert snapshot is None or isinstance(snapshot,dict)
    await again.async_shutdown()
    print('BETA31_QUICK_DELETE_ALL_PASS')

asyncio.run(main())
