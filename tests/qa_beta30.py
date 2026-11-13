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
    old=src_records();records=deepcopy(old['records']);alias='custom_0fe105154780';
    for r in records:
        if r.get('kind')!='drink':continue
        lid=r.get('liquid_type') or 'other';r['liquid_type_id']='water' if lid==alias else lid;r['liquid_type']=r['liquid_type_id']
        r['cup_type_id']=r.get('cup_type_id') or ('cup_6010b46c4a9c' if lid in ('tea','milk','coffee') else None)
        r['cup_default_volume_ml_at_log']=None
    before=[(r['id'],r['timestamp'],r['volume_ml'],r.get('kind')) for r in records]
    raw=deepcopy(old)
    raw['records']=records;raw['data_model_version']=2
    raw['legacy_mappings']={alias:{'liquid_type_id':'water','cup_type_id':'cup_fa5e54e2924d'}}
    raw['legacy_cup_defaults']={'coffee':'cup_6010b46c4a9c'}
    raw['conversion_state']={'applied':True,'model_finalized':True}
    key='jw_daily_hydration_log.sampleprofile';FakeStore.data[key]=raw
    h=FakeHass();c=coordinator.HydrationCoordinator(h,FakeEntry());await c.async_initialize()
    assert c.data_model_version==2
    store=FakeStore.data[key]
    assert all(k not in store for k in ('volume_buttons','legacy_mappings','legacy_cup_defaults','conversion_state'))
    assert all('liquid_type' not in r and 'source_legacy_liquid_id' not in r for r in store['records'] if r.get('kind')=='drink')
    after=[(r['id'],r['timestamp'],r['volume_ml'],r.get('kind')) for r in store['records']]
    assert before==after and len(after)==len(before)
    assert c.records==store['records']
    assert c.records[0]['liquid_type_id']=='coffee'
    backup=FakeStore.data[key+'.pre_beta30'];assert backup['payload']==raw
    assert hashlib.sha256(settings_io.canonical(backup['payload'])).hexdigest()==backup['sha256']
    await c.async_shutdown();copy=deepcopy(FakeStore.data[key]);c2=coordinator.HydrationCoordinator(h,FakeEntry());await c2.async_initialize()
    assert FakeStore.data[key]==copy and c2.records==c.records
    assert 'liquid_type' not in data_io.export_payload(c2)['data']['records'][0]
    # 1:1 history / backend native aggregate / XLSX
    hist=[r for r in c2.records if r['kind']=='drink']
    assert sum(float(r['volume_ml']) for r in hist)==sum(float(r['volume_ml']) for r in records if r['kind']=='drink')
    day='2026-11-11';history=c2.get_history(day)
    assert all(r['liquid_type'] in ('water','coffee','tea','milk','wine','other') for r in history)
    assert sum(r['volume_ml'] for r in history)==sum(r['volume_ml'] for r in hist if r['timestamp'][:10]==day)
    total=sum(x['volume_ml'] for x in c2.liquid_breakdown(day));assert total==sum(x['volume_ml'] for x in history)
    xlsx=excel.export_xlsx([c2.export_snapshot()], when=datetime(2026,11,12,22,0,tzinfo=timezone.utc))
    with zipfile.ZipFile(io.BytesIO(xlsx)) as z:
        assert z.testzip() is None
        wb=z.read('xl/workbook.xml').decode();assert wb.count('<sheet name=')==4
        assert b'Legacy liquid ID' in z.read('xl/worksheets/sheet1.xml') or b'Legacy' not in z.read('xl/worksheets/sheet1.xml')
        assert b'Original volume buttons' not in z.read('xl/worksheets/sheet4.xml')
        assert b'Legacy default' not in z.read('xl/worksheets/sheet3.xml')
        assert b'Glass mug' in z.read('xl/worksheets/sheet1.xml')
        assert b'Cup used' in z.read('xl/worksheets/sheet1.xml')
        assert b'Current Cup default' not in z.read('xl/worksheets/sheet1.xml')
        assert b'Quick button' not in z.read('xl/worksheets/sheet1.xml')
        assert b'tblDailyIntake' in z.read('xl/tables/table2.xml')
        for name in z.namelist():
            if name.endswith(('.xml','.rels')): ET.fromstring(z.read(name))
    exported=settings_io.export_payload(c2)
    assert exported['schema']==2 and not any('legacy' in k for k in exported['settings'])
    assert settings_io.validate_payload(exported)==settings_io.extract(c2)
    full=c2.full_backup()
    settings,data,dig=data_io.parse_full(__import__('base64').b64encode(full).decode());assert settings['schema']==2 and data['schema']==2
    # The three import modes remain operational under the native storage contract.
    exported_data=c2.export_data()
    for mode in ('merge','update'):
        preview=c2.data_import_preview(exported_data,mode)
        result=await c2.async_import_data(exported_data,mode,preview)
        assert result['applied'] and len(c2.records)==len(after)
        assert sum(r['volume_ml'] for r in c2.records if r.get('kind')=='drink')==sum(r['volume_ml'] for r in hist)
    # Replace all is explicitly scoped to the same profile; an incoming mismatch fails.
    mismatched=deepcopy(exported_data)
    mismatched['source_profile']['slug']='another_profile'
    try:c2.data_import_preview(mismatched,'replace')
    except ValueError:pass
    else:raise AssertionError('Cross-profile Replace all allowed')
    preview=c2.data_import_preview(exported_data,'replace')
    result=await c2.async_import_data(exported_data,'replace',preview)
    assert result['applied'] and len(c2.records)==len(after)
    print('BETA30_DATA_IMPORT_MERGE_UPDATE_REPLACE_PASS')
    # Old full profile settings schema v1 remains readable by recovery API, with old keys pruned.
    oldset=deepcopy(exported);oldset['schema']=1;oldset['settings'].update({k:raw.get(k) for k in ('volume_buttons','legacy_mappings','legacy_cup_defaults','conversion_state')})
    assert settings_io.validate_payload(oldset)==settings_io.extract(c2)
    # Reject data v1 or bad Cup refs; never silently guess Cup by volume.
    corrupt=deepcopy(FakeStore.data[key]);corrupt['records'][0]['cup_type_id']='missing'
    FakeStore.data[key]=corrupt
    try:
        c_bad=coordinator.HydrationCoordinator(h,FakeEntry());await c_bad.async_initialize()
    except ValueError as e: assert 'Cup' in str(e)
    else:raise AssertionError('Orphaned Cup accepted')
    assert FakeStore.data[key]==corrupt
    FakeStore.data[key]=raw;FakeStore.data[key]['data_model_version']=1
    try:
        c_bad=coordinator.HydrationCoordinator(h,FakeEntry());await c_bad.async_initialize()
    except ValueError as e:assert 'beta.29' in str(e)
    else:raise AssertionError('Unmigrated v1 silently accepted')
    print('BETA30_NATIVE_STORAGE_MIGRATION_AUDIT_PASS')
    print('BETA30_XLSX_HISTORY_BACKUP_COMPAT_PASS')
    print('BETA30_FAIL_CLOSED_NONDESTRUCTIVE_PASS')
asyncio.run(main())
