"""v1.5.1-beta.4: full Restore preview compares content, not just record counts."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, date, timezone
from pathlib import Path
import ast
import importlib.util
import sys
import types

ROOT=Path(__file__).resolve().parents[1]/"custom_components"/"jw_daily_hydration_log"
pkg=types.ModuleType("jwdhl_restore_beta4")
pkg.__path__=[str(ROOT)]
sys.modules[pkg.__name__]=pkg
for n in ("settings_io","data_io"):
    spec=importlib.util.spec_from_file_location(pkg.__name__+"."+n,ROOT/(n+".py"))
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
from jwdhl_restore_beta4 import settings_io,data_io
code=(ROOT/"coordinator.py").read_text(encoding="utf-8")
cls=next(x for x in ast.parse(code).body if isinstance(x,ast.ClassDef) and x.name=="HydrationCoordinator")
methods=[x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name in ("_validate_restored_preferences","full_restore_preview")]
assert len(methods)==2
ns={"validate_payload":settings_io.validate_payload,"extract":settings_io.extract,
    "digest":settings_io.digest,"data_io":data_io,"_safe_svg":lambda svg:svg}
exec(compile(ast.fix_missing_locations(ast.Module(body=methods,type_ignores=[])),str(ROOT/"coordinator.py"),"exec"),ns)

class FakeCoordinator:
    _validate_restored_preferences=ns["_validate_restored_preferences"]
    full_restore_preview=ns["full_restore_preview"]
    def __init__(self):
        self.slug="jan_willem"
        self.name="Jan-Willem"
        self.age=58
        self.gender="male"
        self.unit="mL"
        self.show_add_quick_buttons=True
        self.show_add_liquid_cup_types=False
        initial={
            "liquid_overrides":{},"custom_liquid_types":[],"liquid_colors":{},
            "hidden_builtin_liquids":[],"liquid_order":[],
            "cup_types":[{"id":"cup12345","name":"Glass","default_volume_ml":250.0,
                          "icon_mdi":"mdi:glass-mug-variant","hidden":False}],
            "quick_buttons":[],"target_override_ml":2000.0,
            "records":[
                {"id":"drink0001","kind":"drink","timestamp":"2026-11-22T10:00:00+01:00",
                 "volume_ml":250.0,"liquid_type_id":"water","cup_type_id":"cup12345",
                 "origin":"dashboard"},
                {"id":"drink0002","kind":"drink","timestamp":"2026-11-22T11:00:00+01:00",
                 "volume_ml":150.0,"liquid_type_id":"coffee","cup_type_id":"cup12345",
                 "origin":"dashboard"}],
            "source_readings":[],"daily_archive":{},
            "consumed_ml":400.0,"manual_consumed_ml":400.0,
            "last_reset_date":"2026-11-22","_last_source_value":None,
            "_source_baseline_ml":0.0,
        }
        for k,v in initial.items():setattr(self,k,deepcopy(v))
    def settings_revision(self):
        return settings_io.digest(settings_io.extract(self))
    def data_revision(self):
        return data_io.sha(data_io.extract(self))
    def _now(self):
        return datetime(2026,11,22,15,0,tzinfo=timezone.utc)
    def _validate_import_data(self,raw,*,settings=None):
        current=settings or settings_io.extract(self)
        return data_io.validate(raw,liquids=set(settings_io.BUILTINS)|{
                t["id"] for t in current["custom_liquid_types"]},
                cups={t["id"] for t in current["cup_types"]},today=date(2026,11,22))
    def export_data(self):
        return data_io.export_payload(self)
c=FakeCoordinator()
old_snapshot=deepcopy((settings_io.extract(c),data_io.extract(c)))
settings=settings_io.export_payload(c)
data=data_io.export_payload(c)
same=c.full_restore_preview(settings,data,"a"*64)
assert same["profile"]=="jan_willem" and same["profile_name"]=="Jan-Willem"
assert same["comparison"]=={"settings_identical":True,"data_identical":True},same["comparison"]
assert same["counts"]["records"]==2 and same["counts"]["current_records"]==2
assert same["target_settings_sha256"]==same["settings_revision"]
assert same["target_data_sha256"]==same["data_revision"]
# Same drink count and same total mL are NOT sufficient. Event payload differs.
changed_data=deepcopy(data)
changed_data["data"]["records"][0]["volume_ml"]=251.0
changed_data["data"]["records"][1]["volume_ml"]=149.0
diff=c.full_restore_preview(settings,changed_data,"b"*64)
assert diff["counts"]==same["counts"]
assert diff["comparison"]=={"settings_identical":True,"data_identical":False}
assert diff["target_data_sha256"]!=diff["data_revision"]
# Record identity and timestamps are also included in the hash comparison.
changed_id=deepcopy(data)
changed_id["data"]["records"][0]["id"]="drink0003"
assert c.full_restore_preview(settings,changed_id,"c"*64)["comparison"]["data_identical"] is False
changed_settings=deepcopy(settings)
changed_settings["settings"]["cup_types"][0]["default_volume_ml"]=255.0
diff=c.full_restore_preview(changed_settings,data,"d"*64)
assert diff["counts"]==same["counts"]
assert diff["comparison"]=={"settings_identical":False,"data_identical":True}
# Preferences are compared too, even when only age or selector display differs.
changed_prefs=deepcopy(settings)
changed_prefs["profile_preferences"]["show_add_liquid_cup_types"]=True
diff=c.full_restore_preview(changed_prefs,data,"e"*64)
assert diff["comparison"]=={"settings_identical":False,"data_identical":True}
# A preview must not write, migrate, or alter any profile state.
assert old_snapshot==(settings_io.extract(c),data_io.extract(c))
print("BETA1514_RESTORE_PREVIEW_CONTENT_COMPARISON_QA_PASS")
