"""v1.5.1-beta.2: in-place profile visibility saves must not unload HA coordinator."""
from __future__ import annotations
import ast, asyncio, math
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'custom_components/jw_daily_hydration_log/__init__.py').read_text(encoding='utf-8')
module=ast.parse(source)
selected=[]
for node in module.body:
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in (
        '_async_options_updated','ws_profile_edit'):
        node.decorator_list=[]
        selected.append(node)
assert len(selected)==2
class Coordinator:
    def __init__(self):
        self.entry=SimpleNamespace(
            entry_id='entry_jan_willem',
            title='Jan-Willem',
            data={'name':'Jan-Willem','age':58,'gender':'male','unit':'mL'},
            options={}
        )
        self.entry_id=self.entry.entry_id
        self.slug='jan_willem'
        self.name='Jan-Willem'
        self.age=58
        self.gender='male'
        self.unit='mL'
        self.target_ml=2000
        self.show_add_quick_buttons=True
        self.show_add_liquid_cup_types=True
        self._applied_entry_options={}
        self._applied_entry_title='Jan-Willem'
        self.dispatches=0
        self.history=[{'kind':'drink','id':'drink-1','volume_ml':250,'timestamp':'2026-11-22T09:00:00+01:00'}]
    def _catalog_name(self,name,label):return name
    async def async_update_profile_identity_target(self,name,goal):
        self.name=name
        self.target_ml=goal
    def _dispatch(self):self.dispatches+=1
c=Coordinator()
class Entries:
    def __init__(self):self.reloads=[]
    def async_update_entry(self,entry,options,title):
        entry.options=options
        entry.title=title
    async def async_reload(self,entry_id):
        self.reloads.append(entry_id)
        # A real reload briefly removes the coordinator and causes the bug.
        app.data['jw_daily_hydration_log']['profiles'].pop(entry_id,None)
app=SimpleNamespace(
    data={'jw_daily_hydration_log':{'profiles':{c.entry_id:c}}},
    config_entries=Entries()
)
class Connection:
    def __init__(self):self.result=None;self.error=None
    def send_result(self,msgid,data):self.result=data
    def send_error(self,msgid,code,reason):self.error=(code,reason)
namespace={
    'HomeAssistant':object,'ConfigEntry':object,
    'math':math,'UNITS':('mL','L','fl_oz'),'ServiceValidationError':ValueError,
    '_profiles':lambda hass:hass.data['jw_daily_hydration_log']['profiles'],
    '_resolve':lambda hass,slug: next(
        x for x in hass.data['jw_daily_hydration_log']['profiles'].values()
        if slug in (x.entry_id,x.slug)
    )
}
exec(compile(ast.Module(body=selected,type_ignores=[]),str(ROOT/'custom_components/jw_daily_hydration_log/__init__.py'),'exec'),namespace)
def request(quick,selectors,**extra):
    return dict(id=1,profile='jan_willem',name='Jan-Willem',age=58,gender='male',
                unit='mL',daily_target_ml=2000,
                show_add_quick_buttons=quick,
                show_add_liquid_cup_types=selectors,**extra)
async def case():
    conn=Connection()
    await namespace['ws_profile_edit'](app,conn,request(True,False))
    assert conn.error is None and conn.result['updated'],conn.error
    await namespace['_async_options_updated'](app,c.entry)
    assert app.config_entries.reloads==[], 'Visibility-only edit reloaded Home Assistant'
    assert c.entry_id in app.data['jw_daily_hydration_log']['profiles'], 'Profile disappeared'
    assert (c.show_add_quick_buttons,c.show_add_liquid_cup_types)==(True,False)
    assert c.entry.options['show_add_liquid_cup_types'] is False
    assert c.dispatches>=1
    assert c.history[0]['id']=='drink-1'
    # The other visibility-only setting must also work without any reload.
    conn2=Connection()
    await namespace['ws_profile_edit'](app,conn2,request(False,True))
    assert conn2.error is None and conn2.result['updated']
    await namespace['_async_options_updated'](app,c.entry)
    assert app.config_entries.reloads==[]
    assert c.show_add_quick_buttons is False and c.show_add_liquid_cup_types is True
    # Invalid configuration must not be persisted or cause reload.
    conn3=Connection()
    await namespace['ws_profile_edit'](app,conn3,request(False,False))
    assert conn3.error is not None and conn3.result is None
    assert c.entry.options['show_add_liquid_cup_types'] is True
    # Real identity changes and unrelated external HA options must still reload.
    c.entry.options={**c.entry.options,'age':59}
    await namespace['_async_options_updated'](app,c.entry)
    assert app.config_entries.reloads==['entry_jan_willem'],app.config_entries.reloads
    assert c.entry_id not in app.data['jw_daily_hydration_log']['profiles']
asyncio.run(case())
# Verify frontend save uses the race-safe refresh path.
frontend=(ROOT/'custom_components/jw_daily_hydration_log/www/jwdaily-hydration-log-card.js').read_text(encoding='utf-8')
assert 'async _refreshSavedProfile()' in frontend
assert 'await this._refreshSavedProfile()' in frontend
assert 'Profile saved, but Home Assistant is still reloading' in frontend
print('BETA1512_PROFILE_VISIBILITY_SAVE_NO_RELOAD_QA_PASS')
