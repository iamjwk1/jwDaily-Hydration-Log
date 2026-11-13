"""Release 1 global migration, multi-profile safety and journal/rollback QA."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components/jw_daily_hydration_log"
for name in ("homeassistant","homeassistant.helpers","homeassistant.helpers.storage"):
    if name not in sys.modules:
        mod=types.ModuleType(name)
        mod.__path__=[]
        sys.modules[name]=mod

class Store:
    data={}
    fail_key=None
    def __init__(self,hass,version,key):
        self.key=key
    async def async_load(self):
        return deepcopy(self.data.get(self.key))
    async def async_save(self,payload):
        if self.key==self.fail_key:
            raise RuntimeError("injected storage failure")
        self.data[self.key]=deepcopy(payload)

sys.modules["homeassistant.helpers.storage"].Store=Store
pkg=types.ModuleType("jwdhl_beta32_test")
pkg.__path__=[str(ROOT)]
sys.modules[pkg.__name__]=pkg
for name in ("const","migration_v3","global_catalog_v3"):
    spec=importlib.util.spec_from_file_location(pkg.__name__+"."+name,ROOT/(name+".py"))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
from jwdhl_beta32_test.global_catalog_v3 import GlobalCatalogV3
from jwdhl_beta32_test.migration_v3 import MigrationBlocked, fingerprint, GLOBAL_KEYS

class Hass:
    def __init__(self,entry_ids):
        self.config_entries=types.SimpleNamespace(
            async_entries=lambda domain:[types.SimpleNamespace(entry_id=eid) for eid in entry_ids])

def profile(cup_extra=False,used=False):
    cups=[{"id":"cup_glass","name":"Glass","default_volume_ml":250,"hidden":False}]
    if cup_extra:
        cups.append({"id":"cup_extra","name":"Bottle","default_volume_ml":500,"hidden":False})
    return {
        "data_model_version":2,
        "records":([{"kind":"drink","id":"one","timestamp":"2026-11-12T13:00:00+01:00",
                     "volume_ml":250.0,"liquid_type_id":"water","cup_type_id":"cup_glass"}]
                   if used else []),
        "consumed_ml":250 if used else 0,
        "manual_consumed_ml":250 if used else 0,
        "daily_archive":{"2026-11-12":{"target_ml":2000,"consumed_ml":250}} if used else {},
        "source_readings":[],
        "last_reset_date":"2026-11-12",
        "target_override_ml":2500 if used else 2000,
        "custom_liquid_types":[],
        "liquid_overrides":{},
        "liquid_colors":{},
        "hidden_builtin_liquids":[],
        "liquid_order":[],
        "cup_types":cups,
        "quick_buttons":([{"id":"q_bottle","liquid_type_id":"water","cup_type_id":"cup_extra",
                           "label_mode":"automatic","custom_label":"","hidden":False}]
                         if cup_extra else []),
    }

class Coordinator:
    def __init__(self,hass,entry_id):
        self.entry_id=entry_id
        self._store=Store(hass,1,f"jw_daily_hydration_log.{entry_id}")
        raw=Store.data[self._store.key]
        self.records=deepcopy(raw["records"])
        self.quick_buttons=deepcopy(raw["quick_buttons"])
        self.dispatched=0
        for key in GLOBAL_KEYS:
            setattr(self,key,deepcopy(raw[key]))
    def _dispatch(self):
        self.dispatched+=1

async def main():
    Store.data.clear()
    prefix="jw_daily_hydration_log."
    p1=profile(cup_extra=True)
    p2=profile(used=True)
    # Same global cup ID must be identical across profiles.
    p2["cup_types"].append(deepcopy(p1["cup_types"][1]))
    original={"p1":deepcopy(p1),"p2":deepcopy(p2)}
    Store.data[prefix+"p1"]=deepcopy(p1)
    Store.data[prefix+"p2"]=deepcopy(p2)
    hass=Hass(["p1","p2"])
    manager=GlobalCatalogV3(hass)
    await manager.async_initialize()
    baseline=Store.data[prefix+"migration_v3_backup"]
    assert baseline["profiles"]==original
    assert baseline["source_sha256"]==fingerprint(original)
    assert manager.state["status"]=="active"
    assert Store.data[prefix+"p1"]==p1 and Store.data[prefix+"p2"]==p2
    print("BETA32_FULL_PROFILE_BACKUP_READBACK_PASS")

    c1=Coordinator(hass,"p1");c2=Coordinator(hass,"p2")
    await manager.async_attach(c1);await manager.async_attach(c2)
    assert len(c1.cup_types)==2 and len(c2.cup_types)==2
    # The other profile contains a drink using Glass. Deleting from p1 must
    # fail without changing either live catalog or any stored source record.
    c1.cup_types=[c for c in c1.cup_types if c["id"]!="cup_glass"]
    try:
        await manager.async_save(c1,deepcopy(Store.data[prefix+"p1"]))
        raise AssertionError("cross-profile historical deletion accepted")
    except MigrationBlocked as e:
        assert "drink history" in str(e)
    assert len(c1.cup_types)==2
    assert Store.data[prefix+"p1"]==original["p1"]
    assert Store.data[prefix+"p2"]==original["p2"]
    print("BETA32_CROSS_PROFILE_HISTORICAL_DELETE_BLOCK_PASS")

    # Unused Bottle can be deleted globally even when another profile has a
    # profile-unique Quick button referring to it; no past drinks are touched.
    c1.cup_types=[c for c in c1.cup_types if c["id"]!="cup_extra"]
    await manager.async_save(c1,deepcopy(Store.data[prefix+"p1"]))
    assert len(manager.state["catalog"]["cup_types"])==1
    assert c2.quick_buttons==[]
    assert Store.data[prefix+"p2"]["quick_buttons"]==[]
    assert Store.data[prefix+"p2"]["records"]==original["p2"]["records"]
    assert Store.data[prefix+"p2"]["daily_archive"]==original["p2"]["daily_archive"]
    assert Store.data[prefix+"migration_v3_backup"]==baseline
    assert Store.data[prefix+"migration_v3_journal"]["status"]=="committed"
    print("BETA32_GLOBAL_CUP_DELETE_QUICK_CASCADE_HISTORY_PASS")

    # Simulate Core restart: global configuration survives, native history
    # and the original rollback archive remain unchanged.
    new_manager=GlobalCatalogV3(hass)
    await new_manager.async_initialize()
    assert new_manager.state["catalog_sha256"]==manager.state["catalog_sha256"]
    await new_manager.async_rollback_to_local(new_manager.state["catalog_sha256"])
    assert Store.data[prefix+"global_catalog_v3"]["status"]=="inactive"
    assert Store.data[prefix+"p2"]["records"]==original["p2"]["records"]
    assert Store.data[prefix+"migration_v3_backup"]==baseline
    try:
        await GlobalCatalogV3(hass).async_initialize()
        raise AssertionError("rollback was silently reactivated")
    except MigrationBlocked as e:
        assert "rolled back" in str(e)
    print("BETA32_ROLLBACK_STICKY_NO_DRINK_LOSS_PASS")

    # A conflicted source must fail before creating any migration archive.
    Store.data.clear()
    p1=profile();p2=profile()
    p2["cup_types"][0]["default_volume_ml"]=300
    Store.data[prefix+"p1"]=p1
    Store.data[prefix+"p2"]=p2
    try:
        await GlobalCatalogV3(hass).async_initialize()
        raise AssertionError("ID conflict accepted")
    except MigrationBlocked:
        pass
    assert prefix+"migration_v3_backup" not in Store.data
    assert prefix+"global_catalog_v3" not in Store.data
    print("BETA32_CONFLICT_FAIL_CLOSED_ZERO_WRITES_PASS")

asyncio.run(main())
