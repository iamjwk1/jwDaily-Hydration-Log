"""Offline v1.1.0-beta.25 regression: durable settings + conversion + XLSX."""
from __future__ import annotations
import asyncio
import copy
import importlib.util
import json
import re
import sys
import types
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parents[1]/'custom_components/jw_daily_hydration_log'

def module(name,**props):
    obj=types.ModuleType(name)
    for key,value in props.items():setattr(obj,key,value)
    sys.modules[name]=obj
    return obj

class Store:
    data={}
    def __init__(self,hass,version,key):self.key=key
    async def async_load(self):return copy.deepcopy(self.data.get(self.key))
    async def async_save(self,value):self.data[self.key]=copy.deepcopy(value)

fake_now=datetime(2026,11,11,20,45,28,tzinfo=ZoneInfo('Europe/Amsterdam'))
module('homeassistant')
module('homeassistant.config_entries',ConfigEntry=object)
module('homeassistant.const',EVENT_STATE_CHANGED='state_changed')
module('homeassistant.core',HomeAssistant=object,callback=lambda f:f)
module('homeassistant.helpers')
module('homeassistant.helpers.dispatcher',async_dispatcher_send=lambda *args:None)
module('homeassistant.helpers.event',async_track_time_change=lambda *a,**kw:lambda:None)
module('homeassistant.helpers.storage',Store=Store)
module('homeassistant.util',slugify=lambda s:re.sub(r'[^a-z0-9]+','_',s.lower()).strip('_'))
module('homeassistant.util.dt',now=lambda:fake_now)
# Avoid package __init__ execution: load only pure const, settings and coordinator.
module('custom_components').__path__=[str(BASE.parent)]
module('custom_components.jw_daily_hydration_log').__path__=[str(BASE)]
def load(name):
    fullname='custom_components.jw_daily_hydration_log.'+name
    spec=importlib.util.spec_from_file_location(fullname,BASE/(name+'.py'))
    m=importlib.util.module_from_spec(spec);sys.modules[fullname]=m;spec.loader.exec_module(m)
    return m
const=load('const');mod=load('settings_io');co=load('coordinator');excel=load('excel')
assert const.VERSION=='1.1.0-beta.25'

class Hass:
    def __init__(self):
        self.config=types.SimpleNamespace(time_zone='Europe/Amsterdam')
        self.bus=types.SimpleNamespace(async_listen=lambda *a,**k:lambda:None)
class Entry:
    def __init__(self,ident,name):
        self.entry_id=ident
        self.data={'name':name,'age':30,'gender':'male','unit':'mL','source_mode':'absolute'}
        self.options={}

def check(condition,label):
    if not condition:raise AssertionError(label)
    print('PASS',label)

def types_for(c):return {x['id']:x for x in c.get_liquid_definitions()}

async def main():
    h=Hass();c=co.HydrationCoordinator(h,Entry('alpha','Jan-Willem'))
    await c.async_initialize()
    # Legacy 2026-11-11 data, including two distinct Water names/IDs.
    c.liquid_overrides['water']={'name':'Water (beker)','default_volume_ml':180,'icon_mdi':'mdi:water'}
    c.custom_liquid_types.append(dict(id='custom_water_glas',name='Water (glas)',icon_mdi='mdi:water',icon_svg='',default_volume_ml=220,custom=True))
    c.liquid_overrides['coffee']={'name':'Coffee','default_volume_ml':180,'icon_mdi':'mdi:coffee'}
    c.liquid_overrides['tea']={'name':'Tea','default_volume_ml':180,'icon_mdi':'mdi:tea'}
    c.liquid_overrides['milk']={'name':'Milk','default_volume_ml':180,'icon_mdi':'mdi:cow'}
    c.volume_buttons=[120,180,220,300,500]
    vals=[('water',500),('custom_water_glas',220),('coffee',180),('coffee',180),('coffee',180),('tea',180),('milk',180)]
    for i,(kind,amount) in enumerate(vals):
        c.records.append(dict(id='r'+str(i),kind='drink',timestamp=f'2026-11-11T{12+i:02d}:19:30+01:00',liquid_type=kind,volume_ml=amount,origin='user'))
    c.consumed_ml=c.manual_consumed_ml=sum(v for _,v in vals)
    await c._save()
    saved_original=copy.deepcopy(c.records)
    original_totals=c.today_breakdown()
    check(len(saved_original)==7 and sum(x['volume_ml'] for x in saved_original)==1620,'legacy drink record and volume baseline')
    plan=c.conversion_preview()
    check(plan['record_count']==7 and len(plan['cups'])==5,'read-only conversion inventories legacy volumes')
    check(any(s['legacy_id']=='custom_water_glas' and s['liquid_type_id']=='water' for s in plan['sources']),'suggest Water (glas) canonical merge')
    check(any(x['name']=='Beker' for x in plan['cups']) and any(x['name']=='Glas' for x in plan['cups']),'Cup names inferred only from explicit old label hints')
    check(c.records==saved_original and not c.cup_types,'conversion preview leaves storage untouched')
    new_cups={x['default_volume_ml']:x['id'] for x in plan['cups']}
    for source in plan['sources']:
        if source['legacy_id'] in ('water','coffee','tea','milk'):
            source['cup_type_id']=new_cups[180]
        if source['legacy_id']=='custom_water_glas':
            source['cup_type_id']=new_cups[220]
        source['include']=source['record_count']>0
    revision=plan['revision']
    # Bad reference must not leave behind partially applied cups.
    invalid=copy.deepcopy(plan)
    invalid['sources'][0]['cup_type_id']='not_a_cup'
    try:await c.async_apply_conversion(invalid,revision);raise AssertionError('Bad cup accepted')
    except ValueError:pass
    check(c.cup_types==[] and c.records==saved_original,'invalid conversion is fully rejected')
    applied=await c.async_apply_conversion(plan,revision)
    check(applied['applied'] and applied['records_unchanged']==7,'conversion applied with untouched ledger')
    check(c.records==saved_original and c.consumed_ml==1620,'record IDs timestamps and volumes exactly preserved')
    check(c.get_liquid_definitions()[0]['name'] in ('Water','Coffee','Tea','Milk'),'legacy canonical names remain readable')
    check(types_for(c)['water']['name']=='Water','Water (beker) renamed to canonical Water')
    water=next(x for x in c.today_breakdown() if x['liquid_type']=='water')
    check(water['volume_ml']==720 and not any(x['liquid_type']=='custom_water_glas' for x in c.today_breakdown()),'both Water labels aggregate to one 720 mL Liquid')
    check(next(x for x in c.get_history('2026-11-11') if x['id']=='r0')['cup_type_id']==new_cups[180],'confirmed cup metadata resolved for old Water (beker)')
    check(next(x for x in c.get_history('2026-11-11') if x['id']=='r1')['cup_type_id']==new_cups[220],'confirmed cup metadata resolved for old Water (glas)')
    check(len(c.quick_buttons)>=4 and all(x['label_mode']=='automatic' for x in c.quick_buttons),'Quick buttons generated per confirmed Liquid/Cup')
    try:await c.async_apply_conversion(plan,revision);raise AssertionError('Second conversion accepted')
    except ValueError:pass
    check(c.records==saved_original,'repeated conversion is blocked without duplicating history')
    chart=c.chart_hourly_today()
    check(chart['total_logged_ml']==1620 and sum(b['liquids'].get('water',0) for b in chart['buckets'])==720,'hourly charts aggregate canonical Liquid only')
    weekly=c.chart_last_7_days()
    check(weekly['days'][-1]['liquids']['water']==720,'weekly chart aggregates canonical Water')
    snapshot=c.export_snapshot()
    book=excel.export_xlsx([snapshot],'Europe/Amsterdam')
    with ZipFile(BytesIO(book)) as z:
        check(z.testzip() is None,'XLSX ZIP CRC integrity')
        files=z.namelist()
        for name in files:
            if name.endswith('.xml') or name.endswith('.rels'):ET.fromstring(z.read(name))
        check(len([n for n in files if re.fullmatch(r'xl/worksheets/sheet\d.xml',n)])==4,'Excel retains exactly four sheets')
        sheet2=z.read('xl/worksheets/sheet2.xml').decode()
        check('ht="44"' in sheet2.split('<row r="11"')[1].split('>')[0],'Daily intake row 11 preserved at 44 pt')
        check('width="19"' in z.read('xl/worksheets/sheet1.xml').decode(),'Hydration Date+time width 19')
        check(len([n for n in files if '/tables/table' in n])==2,'XLSX structured tables retained')
        check('<f>I12/G12*100</f>' in sheet2,'Daily intake formulas retained')
    # Export only settings, strictly no history.
    exported=mod.export_payload(c)
    data=mod.canonical(exported)
    check('records' not in exported and 'records' not in exported['settings'] and b'2026-11-11T' not in data,'Settings JSON excludes history, sensors and timestamps')
    check('legacy_cup_defaults' in exported['settings'] and exported['settings']['legacy_cup_defaults'],'Settings export preserves historical cup metadata')
    parsed=mod.parse_settings_json(data.decode())
    history_ids={r['liquid_type'] for r in c.records}
    imported=mod.validate_payload(parsed,existing_legacy_ids=history_ids,include_mappings=True)
    check(imported['legacy_mappings']==c.legacy_mappings,'Same-profile settings JSON roundtrip preserves explicit alias mapping')
    # Importing into another profile must not transfer history-specific mappings.
    second=co.HydrationCoordinator(h,Entry('beta','Other Person'));await second.async_initialize()
    raw=mod.validate_payload(parsed,include_mappings=False)
    check(not raw['legacy_mappings'] and not raw['legacy_cup_defaults'],'Cross-profile import discards historical mappings')
    preview=mod.settings_preview(second,raw)
    check(preview['history_unchanged'] and 'cup_types' in preview['changes'],'Import preview identifies settings without changing history')
    before_records=copy.deepcopy(second.records)
    await second.async_import_settings(raw,preview['old_revision'])
    check(second.records==before_records and len(second.cup_types)==5,'Settings imported without creating history')
    await second.async_shutdown()
    reopened=co.HydrationCoordinator(h,Entry('beta','Other Person'));await reopened.async_initialize()
    check(len(reopened.cup_types)==5 and len(reopened.quick_buttons)>=4,'Imported settings survive restart')
    old=mod.extract(reopened)
    try:await reopened.async_import_settings(old,'invalid_revision');raise AssertionError('Stale import accepted')
    except ValueError:pass
    check(old==mod.extract(reopened),'Stale revision blocks writes')
    bad=copy.deepcopy(parsed);bad['settings']['liquid_colors']['water']='#GGGGGG'
    try:mod.validate_payload(bad);raise AssertionError('Invalid color accepted')
    except ValueError:pass
    bad=copy.deepcopy(parsed);bad['settings']['cup_types'][0]['default_volume_ml']=-1
    try:mod.validate_payload(bad);raise AssertionError('Negative cup accepted')
    except ValueError:pass
    bad=copy.deepcopy(parsed);bad['settings']['quick_buttons'][0]['cup_type_id']='missing'
    try:mod.validate_payload(bad);raise AssertionError('Broken reference accepted')
    except ValueError:pass
    check(True,'Malformed settings / broken Quick IDs / negative volumes rejected')
    old_name=c.slug
    await c.async_set_display_name('New display name')
    check(c.name=='New display name' and c.slug==old_name,'Profile name editable without changing entity ID/slug')
    await c.async_shutdown()
    restart=co.HydrationCoordinator(h,Entry('alpha','Jan-Willem'));await restart.async_initialize()
    check(restart.name=='New display name' and restart.slug==old_name and restart.records==saved_original,'Profile and history survive Home Assistant restart')
    check(restart.canonical_liquid('custom_water_glas')=='water' and restart.mapped_cup('water')==new_cups[180],'Conversions and Cup metadata survive restart')
    print('BETA25_BACKEND_STORAGE_EXCEL_PASS')

asyncio.run(main())
