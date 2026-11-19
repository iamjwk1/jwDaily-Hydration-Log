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
print("PROFILE_ADD_DRINK_SETTINGS_QA_PASS")
