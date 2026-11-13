"""Release-2 v4 cleanup regression: historical integrity, backup, crash recovery.

Uses isolated in-memory Home Assistant Store stubs. Never touches a live HA.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1] / "custom_components/jw_daily_hydration_log"
for name in ("homeassistant", "homeassistant.helpers", "homeassistant.helpers.storage"):
    if name not in sys.modules:
        module = types.ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module


class Store:
    data = {}
    fail_key = None
    def __init__(self, hass, version, key):
        self.key = key
    async def async_load(self):
        return deepcopy(self.data.get(self.key))
    async def async_save(self, value):
        if self.key == self.fail_key:
            raise RuntimeError("injected second-profile write failure")
        self.data[self.key] = deepcopy(value)


sys.modules["homeassistant.helpers.storage"].Store = Store
pkg = types.ModuleType("jwdhl_v4_test")
pkg.__path__ = [str(ROOT)]
sys.modules[pkg.__name__] = pkg
for mod in ("const", "migration_v3", "legacy_cleanup_v4", "global_catalog_v3"):
    spec = importlib.util.spec_from_file_location(pkg.__name__ + "." + mod, ROOT / (mod + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
from jwdhl_v4_test.global_catalog_v3 import GlobalCatalogV3
from jwdhl_v4_test.legacy_cleanup_v4 import cleanup_plan, verified_backup, OBSOLETE_TOP_LEVEL
from jwdhl_v4_test.migration_v3 import fingerprint, _record_signature, MigrationBlocked


class Hass:
    def __init__(self, entries):
        self.config_entries = types.SimpleNamespace(async_entries=lambda domain: [
            types.SimpleNamespace(entry_id=ident) for ident in entries])


def profile(entry, used):
    record = {"id":entry+"_drink_1", "kind":"drink",
              "timestamp":"2026-11-13T10:30:00+01:00", "volume_ml":180.0,
              "liquid_type_id":"water", "cup_type_id":"cup_glass",
              "details":{"origin":"existing"}}
    return {
        "data_model_version":2,
        "records":[record] if used else [],
        "daily_archive":{"2026-11-13":{"consumed_ml":180,"target_ml":2050,
                         "source_ml":0,"drink_count":1}} if used else {},
        "source_readings":[{"timestamp":"2026-10-01T14:00:00+01:00",
                            "value_ml":190,"sensor":"sensor.legacy"}],
        "consumed_ml":180 if used else 0,
        "manual_consumed_ml":180 if used else 0,
        "last_reset_date":"2026-11-13",
        "last_source_value":190,
        "source_baseline":0,
        "target_override_ml":2050,
        "profile_target_model_v3":True,
        "quick_buttons":[{"id":"quick_glass","liquid_type_id":"water",
                          "cup_type_id":"cup_glass"}],
        "custom_liquid_types":[], "liquid_overrides":{}, "liquid_colors":{},
        "hidden_builtin_liquids":[], "liquid_order":[],
        "cup_types":[{"id":"cup_glass","name":"Glass","default_volume_ml":180}],
        "volume_buttons":[120,180,250],
        "legacy_mappings":{"obsolete":{"liquid_type_id":"water"}},
        "legacy_cup_defaults":{"coffee":"cup_glass"},
        "conversion_state":{"model_finalized":True},
        "source_sensor":"sensor.old_source",
        "source_mode":"delta",
        "pregnancy":False, "lactation":False,
        "unrecognized_future_field":{"must_remain":"unchanged"}
    }


async def run():
    Store.data.clear()
    prefix = "jw_daily_hydration_log."
    p1, p2 = profile("p1",True),profile("p2",True)
    original={"p1":deepcopy(p1),"p2":deepcopy(p2)}
    Store.data[prefix+"p1"]=deepcopy(p1)
    Store.data[prefix+"p2"]=deepcopy(p2)
    hass=Hass(["p1","p2"])
    # Initial Release-1 migration makes the immutable v3 backup.
    old_manager=GlobalCatalogV3(hass)
    await old_manager.async_initialize()
    assert Store.data[prefix+"migration_v3_backup"]["profiles"]==original
    assert Store.data[prefix+"legacy_cleanup_v4_backup"] if prefix+"legacy_cleanup_v4_backup" in Store.data else True
    original_ledger = {key:_record_signature(value) for key,value in original.items()}
    assert not any(k in cleanup_plan(p1) for k in OBSOLETE_TOP_LEVEL)
    assert cleanup_plan(p1)["records"] == p1["records"]
    assert cleanup_plan(p1)["source_readings"] == p1["source_readings"]
    assert cleanup_plan(p1)["unrecognized_future_field"] == p1["unrecognized_future_field"]

    # Trigger an interrupted multi-profile cleanup after the first write.
    Store.fail_key = prefix+"p2"
    try:
        await GlobalCatalogV3(hass).async_initialize()
        raise AssertionError("Injected v4 write failure not propagated")
    except RuntimeError:
        pass
    finally:
        Store.fail_key=None
    assert not any(k in Store.data[prefix+"p1"] for k in OBSOLETE_TOP_LEVEL)
    assert Store.data[prefix+"p2"]==p2
    backup=deepcopy(Store.data[prefix+"legacy_cleanup_v4_backup"])
    assert verified_backup(backup)
    assert backup["source_sha256"]==fingerprint(original)
    assert Store.data[prefix+"legacy_cleanup_v4_journal"]["status"]=="pending"
    assert Store.data[prefix+"migration_v3_backup"]["profiles"]==original

    # A newly logged drink after an interrupted cleanup MUST survive restart.
    later={"id":"post_crash_drink","kind":"drink","timestamp":"2026-11-13T14:30:00+01:00",
           "volume_ml":220.0,"liquid_type_id":"water","cup_type_id":"cup_glass"}
    Store.data[prefix+"p1"]["records"].append(later)
    Store.data[prefix+"p1"]["consumed_ml"]=400
    Store.data[prefix+"p1"]["manual_consumed_ml"]=400
    current=deepcopy(Store.data[prefix+"p1"])
    restarted=GlobalCatalogV3(hass)
    await restarted.async_initialize()
    assert restarted.legacy_cleanup_status["status"]=="clean"
    assert Store.data[prefix+"legacy_cleanup_v4_journal"]["status"]=="committed"
    assert Store.data[prefix+"p1"]==current
    assert Store.data[prefix+"p2"]==cleanup_plan(p2)
    assert Store.data[prefix+"legacy_cleanup_v4_backup"]==backup
    assert Store.data[prefix+"migration_v3_backup"]["profiles"]==original
    assert _record_signature(Store.data[prefix+"p2"])==original_ledger["p2"]
    assert later in Store.data[prefix+"p1"]["records"]
    assert Store.data[prefix+"p2"]["target_override_ml"]==2050
    assert Store.data[prefix+"p2"]["source_readings"]==p2["source_readings"]
    print("BETA35_INTERRUPTED_CLEANUP_NO_DRINK_LOSS_PASS")

    # Idempotence: the next restart performs ZERO profile writes or backups.
    before=deepcopy(Store.data)
    again=GlobalCatalogV3(hass)
    await again.async_initialize()
    assert again.legacy_cleanup_status["writes"] is False
    assert Store.data==before
    print("BETA35_IDEMPOTENT_CLEANUP_PASS")

    # Backup corruption must refuse to modify anything.
    Store.data[prefix+"legacy_cleanup_v4_backup"]["source_sha256"]="0"*64
    Store.data[prefix+"p1"]["volume_buttons"]=[100]
    corrupted=deepcopy(Store.data)
    try:
        await GlobalCatalogV3(hass).async_initialize()
        raise AssertionError("Invalid backup was accepted")
    except MigrationBlocked as exc:
        assert "backup" in str(exc).lower()
    assert Store.data==corrupted
    print("BETA35_CORRUPT_BACKUP_FAIL_CLOSED_PASS")

    # No partially initialized or unknown storage model may be cleaned.
    try:
        cleanup_plan({"data_model_version":1, "records":[]})
        raise AssertionError("Legacy data model silently changed")
    except MigrationBlocked:
        pass
    print("BETA35_UNKNOWN_MODEL_NO_WRITES_PASS")

    # Already-clean profile: persist only a verified CLEAN status. No
    # additional profile write, archive, or journal. Next startup is no-op.
    Store.data.clear()
    clean=cleanup_plan(profile("p1",True))
    Store.data[prefix+"p1"]=deepcopy(clean)
    one=Hass(["p1"])
    await GlobalCatalogV3(one).async_initialize()  # Bootstrap verified v3.
    original_v3_backup=deepcopy(Store.data[prefix+"migration_v3_backup"])
    before_profile=deepcopy(Store.data[prefix+"p1"])
    manager=GlobalCatalogV3(one)
    await manager.async_initialize()
    assert manager.legacy_cleanup_status["status"]=="clean"
    assert manager.legacy_cleanup_status["removed_fields"]==0
    assert manager.legacy_cleanup_status["history_unchanged"] is True
    assert manager.legacy_cleanup_status["backup_status"]=="not_needed"
    assert Store.data[prefix+"legacy_cleanup_v4_status"]["status"]=="clean"
    assert prefix+"legacy_cleanup_v4_backup" not in Store.data
    assert prefix+"legacy_cleanup_v4_journal" not in Store.data
    assert Store.data[prefix+"p1"]==before_profile
    assert Store.data[prefix+"migration_v3_backup"]==original_v3_backup
    before_reboot=deepcopy(Store.data)
    # Once clean, normal startup must not execute the old cleanup routine.
    from jwdhl_v4_test.legacy_cleanup_v4 import LegacyCleanupV4
    original_apply=LegacyCleanupV4.async_apply
    async def should_not_run(self):
        raise AssertionError("One-time legacy cleanup ran on verified clean store")
    LegacyCleanupV4.async_apply=should_not_run
    try:
        await GlobalCatalogV3(one).async_initialize()
    finally:
        LegacyCleanupV4.async_apply=original_apply
    assert Store.data==before_reboot
    print("BETA36_CLEAN_START_BYPASSES_LEGACY_CLEANUP_CODE_PASS")


asyncio.run(run())
