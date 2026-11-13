"""Non-destructive migration preflight regression tests (standard library)."""
import importlib.util
from pathlib import Path
from copy import deepcopy

p=Path(__file__).resolve().parents[1]/"custom_components/jw_daily_hydration_log/migration_v3.py"
spec=importlib.util.spec_from_file_location("migration_v3",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def profile(lid="custom_a", cup="cup_a", quick="quick_a"):
    return {
        "data_model_version":2,
        "custom_liquid_types":[{"id":lid,"name":"Juice","custom":True}],
        "cup_types":[{"id":cup,"name":"Glass","default_volume_ml":250}],
        "liquid_overrides":{},"liquid_colors":{},
        "hidden_builtin_liquids":[],"liquid_order":[lid],
        "quick_buttons":[{"id":quick,"liquid_type_id":lid,"cup_type_id":cup}],
        "target_override_ml":2250,
        "records":[{"id":"drink_1","kind":"drink","timestamp":"2026-11-11T12:00:00+01:00",
                    "volume_ml":250,"liquid_type_id":lid,"cup_type_id":cup}],
        "daily_archive":{"2026-11-11":{"consumed_ml":250}},
        "consumed_ml":250,"manual_consumed_ml":250,"last_reset_date":"2026-11-11"
    }


a=profile()
b=profile("custom_b","cup_b","quick_b")
before=deepcopy({"p1":a,"p2":b})
res=m.build_preflight(before)
assert res["writes_performed"] is False
assert res["ready_for_automatic_commit"] is False  # duplicate names require review
assert len(res["global_catalog"]["cup_types"])==2
assert len(res["global_catalog"]["custom_liquid_types"])==2
assert before=={"p1":a,"p2":b}
assert res["profiles"][0]["ledger_sha256"]==m._record_signature(a)
assert m.build_preflight(before)==res

b["custom_liquid_types"][0]["id"]="custom_a"
try:
    m.build_preflight({"p1":a,"p2":b})
except m.MigrationBlocked as e:
    assert "Conflicting" in str(e)
else:
    raise AssertionError("conflicting IDs accepted")

b=profile("custom_b","cup_b","quick_b")
b["records"][0]["cup_type_id"]="missing"
try:
    m.build_preflight({"p1":a,"p2":b})
except m.MigrationBlocked as e:
    assert "unresolved cup" in str(e)
else:
    raise AssertionError("orphaned historic cup accepted")

b=profile("custom_b","cup_b","quick_b")
b["records"][0]["volume_ml"]=float("nan")
try:
    m.build_preflight({"p1":a,"p2":b})
except m.MigrationBlocked:
    pass
else:
    raise AssertionError("invalid historical volume accepted")

assert m.build_preflight({"p1":a})["ready_for_automatic_commit"]
try:
    m.assert_source_unchanged(a,{**a,"consumed_ml":251})
except m.MigrationBlocked:
    pass
else:
    raise AssertionError("data modification not detected")
print("PASS: read-only v3 preflight, ID conflict, orphan, unchanged fingerprints")
