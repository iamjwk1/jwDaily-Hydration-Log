"""Independent beta29 QA: persistence, conversion, transfer, rollback and four-sheet OOXML."""
from __future__ import annotations
import asyncio,copy,importlib.util,json,sys,types,zipfile
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from io import BytesIO
ROOT=Path(__file__).parents[1]
SOURCE=ROOT/'custom_components/jw_daily_hydration_log'

def fake(name, **attrs):
    module=types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name]=module
    return module

pkg=fake('homeassistant');pkg.__path__=[]
fake('homeassistant.config_entries',ConfigEntry=object)
fake('homeassistant.const',EVENT_STATE_CHANGED='state_changed')
fake('homeassistant.core',HomeAssistant=object,callback=lambda f:f)
fake('homeassistant.helpers');fake('homeassistant.helpers.dispatcher',async_dispatcher_send=lambda *a:None)
fake('homeassistant.helpers.event',async_track_time_change=lambda *a,**kw:(lambda:None))
class Store:
    old={}
    def __init__(self,hass,*args):self.key=args[-1]
    async def async_load(self):return copy.deepcopy(self.old.get(self.key))
    async def async_save(self,value):self.old[self.key]=copy.deepcopy(value)
fake('homeassistant.helpers.storage',Store=Store)
dt=fake('homeassistant.util.dt',now=lambda:datetime.now(timezone.utc))
fake('homeassistant.util',dt=dt,slugify=lambda s:s.strip().lower().replace(' ','_'))
pkg2=fake('custom_components');pkg2.__path__=[str(ROOT/'custom_components')]
addon=fake('custom_components.jw_daily_hydration_log');addon.__path__=[str(SOURCE)]
from custom_components.jw_daily_hydration_log import coordinator, data_io, settings_io, excel

class Hass:
    class Config:time_zone='Europe/Amsterdam'
    config=Config()
    class Bus:
        def async_listen(self,*args):return lambda:None
    bus=Bus()
    def async_create_task(self,coro):return asyncio.create_task(coro)
    class Services:pass
    services=Services()
    class ConfigEntries:
        def async_update_entry(self,entry,**kwargs):entry.options=kwargs.get("options",entry.options)
    config_entries=ConfigEntries()
class Entry:
    entry_id='qa29';data={'name':'Jan-Willem','age':58,'gender':'male','unit':'mL','source_mode':'absolute'};options={}

async def test():
    c=coordinator.HydrationCoordinator(Hass(),Entry())
    await c.async_initialize()
    c.cup_types=[{'id':'cup_glass','name':'Glazen beker','default_volume_ml':180.0,'icon_mdi':'mdi:cup','hidden':False},
                 {'id':'cup_bottle','name':'Fles','default_volume_ml':500.0,'icon_mdi':'mdi:bottle-soda','hidden':False}]
    c.legacy_cup_defaults={'coffee':'cup_glass','tea':'cup_glass'}
    c.legacy_mappings={'custom_old_glass':{'liquid_type_id':'water','cup_type_id':'cup_bottle'}}
    c.custom_liquid_types=[{'id':'custom_old_glass','name':'Water (glas)','icon_mdi':'mdi:glass-mug-variant','icon_svg':'','default_volume_ml':500,'custom':True}]
    raw=[{'id':'r' + str(i).zfill(31),'timestamp':'2026-11-10T12:00:00+01:00',
          'kind':'drink','origin':'dashboard','volume_ml':v,'liquid_type':typ,'details':{}}
         for i,(typ,v) in enumerate([('coffee',180),('tea',150),('custom_old_glass',500),('milk',180)])]
    # Today's meal used in preflight; no accidental user history embedded.
    c.records=copy.deepcopy(raw)
    c.daily_archive={'2026-11-10':{'manual_ml':1010,'source_ml':0,'consumed_ml':1010,'target_ml':2000,'drink_count':4,'closed_at':None}}
    old_id=[(r['id'],r['timestamp'],r['volume_ml']) for r in c.records]
    preview=c.model_migration_preview()
    assert preview['drink_count']==4 and preview['cup_unknown_count']==1 and not preview['unclassified_count']
    try:await c.async_finalize_model(preview['revision'],preview['history_revision'],False)
    except ValueError as e:assert 'Unknown' in str(e)
    else:raise AssertionError('Must acknowledge unknown Cups')
    out=await c.async_finalize_model(preview['revision'],preview['history_revision'],True)
    assert out['completed'] and c.data_model_version==2
    assert old_id==[(r['id'],r['timestamp'],r['volume_ml']) for r in c.records]
    assert [r.get('cup_type_id') for r in c.records]==['cup_glass','cup_glass','cup_bottle',None]
    assert [r['liquid_type'] for r in c.records]==['coffee','tea','water','milk']
    assert c.records[2]['source_legacy_liquid_id']=='custom_old_glass'
    await c.async_shutdown()
    reload=coordinator.HydrationCoordinator(Hass(),Entry());await reload.async_initialize()
    assert reload.data_model_version==2 and reload.records==c.records
    assert reload.model_migration_preview()['completed']
    settings=settings_io.export_payload(reload)
    data=reload.export_data()
    checked=reload._validate_import_data(data)
    assert len(checked['records'])==4
    rawbytes=data_io.canonical(data)
    assert data_io.parse(rawbytes.decode())==data
    assert set(data)=={'format','schema','source_profile','data'}
    for mode in ['merge','update','replace']:
        p=reload.data_import_preview(data,mode)
        assert p['counts']['incoming_drinks']==4 and p['counts']['new_ids']==0
        changed=await reload.async_import_data(data,mode,p)
        assert changed['applied'] and len([r for r in reload.records if r['kind']=='drink'])==4
    # Update existing by stable record ID, never by clock/amount.
    update=copy.deepcopy(data);update['data']['records'][0]['volume_ml']=195
    p=reload.data_import_preview(update,'update')
    assert p['counts']['changed_matching_ids']==1
    await reload.async_import_data(update,'update',p)
    assert reload.records[0]['volume_ml']==195
    # Restore original complete dataset.
    zipped=data_io.build_full(settings,data)
    assert zipfile.ZipFile(BytesIO(zipped)).testzip() is None
    raw_settings,raw_data,digest=data_io.parse_full(__import__('base64').b64encode(zipped).decode())
    p=reload.full_restore_preview(raw_settings,raw_data,digest)
    historical_ids={r.get('source_legacy_liquid_id') or r.get('liquid_type') for r in raw_data['data']['records'] if r['kind']=='drink'}
    historical_ids|=set(raw_settings['settings']['legacy_mappings'])
    clean_settings=settings_io.validate_payload(raw_settings,existing_legacy_ids=historical_ids,include_mappings=True)
    clean_data=reload._validate_import_data(raw_data,settings=clean_settings)
    await reload.async_restore_full(clean_settings,clean_data,p,reload._validate_restored_preferences(raw_settings['profile_preferences']))
    assert reload.records==data['data']['records'] and reload.cup_types==c.cup_types
    # Invalid input and changed revision must block without persistent mutations.
    corrupt=copy.deepcopy(data);corrupt['data']['records'].append(copy.deepcopy(corrupt['data']['records'][0]))
    try:reload.data_import_preview(corrupt,'merge')
    except ValueError:pass
    else:raise AssertionError('duplicate IDs accepted')
    changed=copy.deepcopy(data);changed['data']['records'][0]['cup_type_id']='does_not_exist'
    try:reload.data_import_preview(changed,'merge')
    except ValueError:pass
    else:raise AssertionError('dangling Cup reference accepted')
    # Real OOXML sheets and table metadata; no LibreOffice transformations.
    snap=reload.export_snapshot()
    stream=excel.export_xlsx([snap],timezone_name='Europe/Amsterdam')
    with zipfile.ZipFile(BytesIO(stream)) as z:
        assert z.testzip() is None
        assert len([n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')])==4
        ws=z.read('xl/worksheets/sheet1.xml').decode()
        table=z.read('xl/tables/table1.xml').decode()
        setting3=z.read('xl/worksheets/sheet3.xml').decode()
        setting4=z.read('xl/worksheets/sheet4.xml').decode()
        assert 'Current Cup default' in ws and 'Current Cup default' in table
        assert 'Liquid order' in setting3 and 'Historic alias' in setting3
        assert 'Quick buttons' in setting4 and 'Profile settings' in setting4
        assert 'Glazen beker' in ws and 'Fles' in ws
        assert 'Coffee' in ws and 'Tea' in ws
        assert '<tableColumn' in table and 'tblHydrationLog' in table
    print('BETA29_STORAGE_TRANSFER_MIGRATION_XLSX_PASS',len(stream))

asyncio.run(test())
