"""Profile Add drink visibility: old backups default to fully visible; strict flags."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
root=Path(__file__).resolve().parents[1]/"custom_components"/"jw_daily_hydration_log"
spec=importlib.util.spec_from_file_location("settings_qa",root/"settings_io.py")
si=importlib.util.module_from_spec(spec)
spec.loader.exec_module(si)
assert "show_add_quick_buttons" in si.PROFILE_FIELDS
assert "show_add_liquid_cup_types" in si.PROFILE_FIELDS
source=ast.parse((root/"coordinator.py").read_text(encoding="utf-8"))
cls=next(node for node in source.body if isinstance(node,ast.ClassDef) and node.name=="HydrationCoordinator")
fn=next(node for node in cls.body if isinstance(node,ast.FunctionDef) and node.name=="_validate_restored_preferences")
namespace={}
exec(compile(ast.Module(body=[fn],type_ignores=[]),str(root/"coordinator.py"),"exec"),namespace)
validate=namespace["_validate_restored_preferences"]
base={"age":58,"gender":"male","unit":"mL"}
assert validate(None,base)==dict(base,show_add_quick_buttons=True,show_add_liquid_cup_types=True)
assert validate(None,dict(base,show_add_quick_buttons=False,show_add_liquid_cup_types=True))["show_add_quick_buttons"] is False
assert validate(None,dict(base,show_add_quick_buttons=True,show_add_liquid_cup_types=False))["show_add_liquid_cup_types"] is False
for wrong in (
    dict(base,show_add_quick_buttons=False,show_add_liquid_cup_types=False),
    dict(base,show_add_quick_buttons="false"),
    dict(base,show_add_liquid_cup_types=0),
):
    try:validate(None,wrong)
    except ValueError:pass
    else:raise AssertionError("Invalid profile flags accepted: "+repr(wrong))
model=SimpleNamespace(name="Jan-Willem",slug="jan_willem",**base,
                      show_add_quick_buttons=False,show_add_liquid_cup_types=True)
for field in si.FIELDS:setattr(model,field,[] if field.endswith("_types") or field in ("liquid_order","quick_buttons","hidden_builtin_liquids","cup_types") else {} if field in ("liquid_overrides","liquid_colors") else 2000)
backup=si.export_payload(model)
assert backup["profile_preferences"]["show_add_quick_buttons"] is False
assert backup["profile_preferences"]["show_add_liquid_cup_types"] is True
# Exercise the actual profile-edit handler without importing Home Assistant.
import asyncio
import math
init_ast=ast.parse((root/"__init__.py").read_text(encoding="utf-8"))
edit=next(n for n in init_ast.body if isinstance(n,ast.AsyncFunctionDef) and n.name=="ws_profile_edit")
edit.decorator_list=[]
class FakeCoordinator:
    def __init__(self):
        self.slug="one"
        self.entry_id="entry-one"
        self.target_ml=2000
        self.show_add_quick_buttons=True
        self.show_add_liquid_cup_types=True
        self.entry=SimpleNamespace(options={},title="Jan-Willem",entry_id="entry-one")
    def _catalog_name(self,name,_label):return name
    async def async_update_profile_identity_target(self,name,goal):
        self.target_ml=goal
coordinator=FakeCoordinator()
class FakeConfigEntries:
    def async_update_entry(self,entry,options,title):
        entry.options=options
        entry.title=title
hass=SimpleNamespace(config_entries=FakeConfigEntries())
class FakeConnection:
    def __init__(self):self.last=None;self.err=None
    def send_result(self,mid,data):self.last=(mid,data)
    def send_error(self,mid,code,message):self.err=(mid,code,message)
conn=FakeConnection()
namespace={"_resolve":lambda _h,_slug:coordinator,"math":math,
           "UNITS":("mL","L","fl_oz"),"ServiceValidationError":ValueError}
exec(compile(ast.Module(body=[edit],type_ignores=[]),str(root/"__init__.py"),"exec"),namespace)
handler=namespace["ws_profile_edit"]
def msg(**kwargs):
    return dict(id=1,profile="one",name="Jan-Willem",age=58,gender="male",
                unit="mL",daily_target_ml=2000,**kwargs)
asyncio.run(handler(hass,conn,msg(show_add_quick_buttons=False,show_add_liquid_cup_types=True)))
assert conn.last is not None and conn.err is None
assert coordinator.entry.options["show_add_quick_buttons"] is False
assert coordinator.show_add_quick_buttons is False
assert coordinator.entry.options["show_add_liquid_cup_types"] is True
conn=FakeConnection()
asyncio.run(handler(hass,conn,msg(show_add_quick_buttons=False,show_add_liquid_cup_types=False)))
assert conn.err is not None and conn.last is None
assert coordinator.entry.options["show_add_liquid_cup_types"] is True
assert coordinator.entry.options["show_add_quick_buttons"] is False
print("PROFILE_ADD_DRINK_SETTINGS_QA_PASS")
