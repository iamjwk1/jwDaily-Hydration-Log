"""Stubbed Home Assistant WebSocket integration-contract QA for beta.26."""
from __future__ import annotations
import asyncio,copy,importlib.util,json,re,sys,types
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
BASE=Path(__file__).resolve().parents[1]/'custom_components/jw_daily_hydration_log'

def m(name,**attrs):
    o=types.ModuleType(name)
    for k,v in attrs.items():setattr(o,k,v)
    sys.modules[name]=o;return o

def rule(k,*a,**kw):return k
class V:
    Schema=staticmethod(lambda x:x)
    Required=staticmethod(rule);Optional=staticmethod(rule)
    In=staticmethod(lambda x:x)
    Coerce=staticmethod(lambda x:float)
class Store:
    data={}
    def __init__(self,h,v,key):self.key=key
    async def async_load(self):return copy.deepcopy(self.data.get(self.key))
    async def async_save(self,value):self.data[self.key]=copy.deepcopy(value)
class Err(Exception):pass
class Entry:
    def __init__(self,ident,name='Jan-Willem'):
        self.entry_id=ident;self.data={'name':name,'age':30,'gender':'male','unit':'mL','source_mode':'absolute'}
        self.options={};self.title=name
m('homeassistant')
m('homeassistant.config_entries',ConfigEntry=Entry)
m('homeassistant.const',EVENT_STATE_CHANGED='state_changed')
m('homeassistant.core',HomeAssistant=object,callback=lambda f:f)
m('homeassistant.helpers')
m('homeassistant.helpers.dispatcher',async_dispatcher_send=lambda *a:None)
m('homeassistant.helpers.event',async_track_time_change=lambda *a,**kw:lambda:None)
m('homeassistant.helpers.storage',Store=Store)
m('homeassistant.util',slugify=lambda x:re.sub(r'[^a-z0-9]+','_',x.lower()).strip('_'))
m('homeassistant.util.dt',now=lambda:datetime(2026,11,11,20,10,tzinfo=ZoneInfo('Europe/Amsterdam')))
m('homeassistant.components')
m('homeassistant.components.websocket_api',websocket_command=lambda schema:lambda f:f,
  require_admin=lambda f:f,async_response=lambda f:f)
m('homeassistant.exceptions',HomeAssistantError=Err,ServiceValidationError=Err)
m('homeassistant.helpers.config_validation',config_entry_only_config_schema=lambda d:dict,string=str)
m('voluptuous',Schema=V.Schema,Required=V.Required,Optional=V.Optional,In=V.In,Coerce=V.Coerce)
m('probatio',Required=V.Required,Optional=V.Optional)
m('custom_components').__path__=[str(BASE.parent)]
pkg=m('custom_components.jw_daily_hydration_log');pkg.__path__=[str(BASE)]
async def noop(*a,**k):return None
m('custom_components.jw_daily_hydration_log.frontend',async_register_frontend=noop)

def load(name,path=None):
    fullname='custom_components.jw_daily_hydration_log'+('.'+name if name else '')
    spec=importlib.util.spec_from_file_location(fullname,path or BASE/(name+'.py'),submodule_search_locations=([str(BASE)] if not name else None))
    target=importlib.util.module_from_spec(spec);sys.modules[fullname]=target;spec.loader.exec_module(target)
    return target
const=load('const');settings=load('settings_io');co=load('coordinator');excel=load('excel')
api=load('',BASE/'__init__.py')
class Connection:
    def __init__(self):self.responses=[];self.errors=[]
    def send_result(self,id,value):self.responses.append((id,value))
    def send_error(self,id,code,message):self.errors.append((id,code,message))
    @property
    def last(self):return self.responses[-1][1]
class Hass:
    def __init__(self):
        self.data={const.DOMAIN:{'profiles':{}}};self.config=types.SimpleNamespace(time_zone='Europe/Amsterdam')
        self.bus=types.SimpleNamespace(async_listen=lambda *a,**kw:lambda:None)
        self.entries=[];self.config_entries=types.SimpleNamespace(flow=types.SimpleNamespace(async_init=self.flow_init),
             async_update_entry=self.update,async_reload=self.reload)
        self.reloaded=[]
    async def flow_init(self,domain,context,data):
        entry=Entry('new'+str(len(self.entries)+1),data['name']);entry.data=dict(data);self.entries.append(entry)
        return {'type':'create_entry','result':entry}
    def update(self,entry,**kwargs):
        if 'options' in kwargs:entry.options=kwargs['options']
        if 'title' in kwargs:entry.title=kwargs['title']
    async def reload(self,entry_id):
        self.reloaded.append(entry_id)
        entry=next(e for e in self.entries if e.entry_id==entry_id)
        c=co.HydrationCoordinator(self,entry);await c.async_initialize();self.data[const.DOMAIN]['profiles'][entry_id]=c

async def check():
    h=Hass();entry=Entry('alpha');h.entries.append(entry)
    c=co.HydrationCoordinator(h,entry);await c.async_initialize();h.data[const.DOMAIN]['profiles'][entry.entry_id]=c
    c.cup_types=[dict(id='cup_custom',name='Mug',default_volume_ml=180,icon_mdi='mdi:cup',hidden=False)]
    c.quick_buttons=[dict(id='quick_custom',liquid_type_id='water',cup_type_id='cup_custom',label_mode='automatic',custom_label='',hidden=False)]
    await c._save()
    conn=Connection()
    api.ws_profiles_list(h,conn,{'id':1,'type':const.DOMAIN+'/profiles_list'})
    assert conn.last['profiles'][0]['slug']=='jan_willem'
    await api.ws_profile_create(h,conn,dict(id=2,type=const.DOMAIN+'/profile_create',name='Another Person',age=25,gender='female',unit='mL',copy_from='jan_willem'))
    assert not conn.errors,conn.errors
    created=conn.last;assert created['copied_settings'] and not created['history_copied']
    assert len(h.entries)==2
    entry2=h.entries[-1]
    restored=co.HydrationCoordinator(h,entry2);await restored.async_initialize()
    assert len(restored.cup_types)==1 and len(restored.quick_buttons)==1 and len(restored.records)==0
    print('PASS new profile created via HA flow, settings copied; no history or personal targets')
    await api.ws_profile_edit(h,conn,dict(id=3,type=const.DOMAIN+'/profile_edit',profile='jan_willem',name='Updated Display',age=31,gender='male',unit='mL',pregnancy=False,lactation=False,source_sensor='',source_mode='absolute'))
    assert not conn.errors,conn.errors
    assert c.slug=='jan_willem' and c.name=='Updated Display' and entry.options['age']==31
    print('PASS profile editing retains stable slug and updates native HA config options')
    await api.ws_settings_export(h,conn,dict(id=4,type=const.DOMAIN+'/settings_export',profile='jan_willem'))
    assert conn.last['size']>50 and conn.last['filename'].endswith('.json')
    from base64 import b64decode
    jsontext=b64decode(conn.last['base64']).decode('utf-8')
    assert 'records' not in json.loads(jsontext)['settings']
    print('PASS WS JSON settings export does not disclose drink ledger')
    api.ws_settings_preview(h,conn,dict(id=5,type=const.DOMAIN+'/settings_import_preview',profile='jan_willem',content=jsontext))
    assert not conn.errors,conn.errors
    preview=conn.last
    assert preview['profile_slug']=='jan_willem'
    print('PASS WS settings import preview')
    await api.ws_settings_apply(h,conn,dict(id=6,type=const.DOMAIN+'/settings_import_apply',profile='jan_willem',content=jsontext,
        expected_revision=preview['old_revision'],import_sha256=preview['import_sha256'],confirm=True))
    assert not conn.errors,conn.errors
    print('PASS WS confirmed settings import')
    await api.ws_settings_apply(h,conn,dict(id=7,type=const.DOMAIN+'/settings_import_apply',profile='jan_willem',content=jsontext,
        expected_revision='outdated',import_sha256=preview['import_sha256'],confirm=True))
    assert conn.errors and conn.errors[-1][1]=='settings_import_failed'
    print('PASS stale settings import blocked at WS boundary')
    api.ws_conversion_preview(h,conn,dict(id=8,type=const.DOMAIN+'/conversion_preview',profile='jan_willem'))
    assert conn.last['mode']=='preview'
    print('PASS read-only conversion WS API')
    print('BETA26_WEBSOCKET_PROFILE_API_PASS')
asyncio.run(check())
