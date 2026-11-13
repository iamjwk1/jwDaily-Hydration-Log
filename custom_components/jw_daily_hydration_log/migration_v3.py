"""Release 1: read-only, fail-closed migration preflight.

This module deliberately performs no HA Store writes. Migration commit,
readback verification and rollback are separate release gates. Historical
ledger entries are never edited by this module.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import math

GLOBAL_KEYS = ("custom_liquid_types", "liquid_overrides", "liquid_colors",
               "hidden_builtin_liquids", "liquid_order", "cup_types")
BUILTIN_LIQUIDS = frozenset(("water", "coffee", "tea", "milk", "soup", "wine", "other"))
PROFILE_KEYS = ("quick_buttons", "target_override_ml")


class MigrationBlocked(ValueError):
    """Preflight failed; no state may be modified."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def fingerprint(value):
    return sha256(canonical(value)).hexdigest()


def _record_signature(storage):
    return fingerprint({
        "records": storage.get("records", []),
        "daily_archive": storage.get("daily_archive", {}),
        "source_readings": storage.get("source_readings", []),
        "consumed_ml": storage.get("consumed_ml", 0),
        "manual_consumed_ml": storage.get("manual_consumed_ml", 0),
        "last_reset_date": storage.get("last_reset_date"),
    })


def build_preflight(profile_stores: dict[str, dict]) -> dict:
    """Return a deterministic preview without modifying inputs.

    Identically keyed catalog entries must be identical. Different IDs may
    coexist, but duplicate names with different definitions are flagged for
    explicit review. No historical IDs are remapped or rewritten.
    """
    if not isinstance(profile_stores, dict) or not profile_stores:
        raise MigrationBlocked("No profile stores supplied")
    source = deepcopy(profile_stores)
    global_catalog = {key: ({} if key in ("liquid_overrides", "liquid_colors")
                            else []) for key in GLOBAL_KEYS}
    indexed = {"custom_liquid_types": {}, "cup_types": {}}
    color_owners = {}
    overrides_owners = {}
    hidden = set()
    order = []
    summaries = []
    warnings = []
    for profile_id in sorted(source):
        store = source[profile_id]
        if not isinstance(profile_id, str) or not profile_id or not isinstance(store, dict):
            raise MigrationBlocked("Malformed profile store")
        if int(store.get("data_model_version", 0)) != 2:
            raise MigrationBlocked(f"{profile_id}: expected finalized native model v2")
        records = store.get("records")
        if not isinstance(records, list):
            raise MigrationBlocked(f"{profile_id}: records must be an array")
        local_liquids = {item["id"] for item in store.get("custom_liquid_types", [])}
        local_cups = {item["id"] for item in store.get("cup_types", [])}
        seen = set()
        drinks = 0
        for record in records:
            if not isinstance(record, dict):
                raise MigrationBlocked(f"{profile_id}: invalid ledger entry")
            record_id = record.get("id")
            if not isinstance(record_id, str) or not record_id or record_id in seen:
                raise MigrationBlocked(f"{profile_id}: missing or duplicate record ID")
            seen.add(record_id)
            if record.get("kind") != "drink":
                continue
            drinks += 1
            if record.get("liquid_type_id") not in BUILTIN_LIQUIDS | local_liquids:
                raise MigrationBlocked(f"{profile_id}: unresolved liquid reference")
            cup = record.get("cup_type_id")
            if cup is not None and cup not in local_cups:
                raise MigrationBlocked(f"{profile_id}: unresolved cup reference")
            volume = record.get("volume_ml")
            if type(volume) not in (int, float) or not math.isfinite(volume) or volume <= 0:
                raise MigrationBlocked(f"{profile_id}: invalid historical volume")
            if not isinstance(record.get("timestamp"), str) or len(record["timestamp"]) < 10:
                raise MigrationBlocked(f"{profile_id}: invalid historical timestamp")
        for key in ("custom_liquid_types", "cup_types"):
            for item in store.get(key, []):
                ident = item.get("id")
                if not isinstance(ident, str) or not ident:
                    raise MigrationBlocked(f"{profile_id}: invalid {key} ID")
                previous = indexed[key].get(ident)
                if previous is not None and previous != item:
                    raise MigrationBlocked(
                        f"Conflicting global {key} ID {ident!r} in {profile_id}; "
                        "historical records must not be rewritten automatically")
                indexed[key][ident] = deepcopy(item)
        for key, owners in (("liquid_overrides", overrides_owners),
                            ("liquid_colors", color_owners)):
            for ident, value in (store.get(key) or {}).items():
                if ident in owners and owners[ident] != value:
                    raise MigrationBlocked(
                        f"Conflicting global {key} for {ident!r} in {profile_id}")
                owners[ident] = deepcopy(value)
        hidden.update(store.get("hidden_builtin_liquids") or [])
        for ident in store.get("liquid_order") or []:
            if ident not in order:
                order.append(ident)
        quick = store.get("quick_buttons") or []
        for button in quick:
            if (button.get("liquid_type_id") not in BUILTIN_LIQUIDS | local_liquids
                    or button.get("cup_type_id") not in local_cups):
                raise MigrationBlocked(f"{profile_id}: orphaned Quick button reference")
        summaries.append({
            "profile_entry_id": profile_id,
            "store_sha256": fingerprint(store),
            "ledger_sha256": _record_signature(store),
            "records": len(records),
            "drinks": drinks,
            "quick_buttons": len(quick),
            "target_override_ml": store.get("target_override_ml", 0),
        })
    global_catalog["custom_liquid_types"] = list(indexed["custom_liquid_types"].values())
    global_catalog["cup_types"] = list(indexed["cup_types"].values())
    global_catalog["liquid_overrides"] = overrides_owners
    global_catalog["liquid_colors"] = color_owners
    global_catalog["hidden_builtin_liquids"] = sorted(hidden)
    global_catalog["liquid_order"] = order
    # Detect non-equal definitions that happen to share a human-readable name.
    for key in ("custom_liquid_types", "cup_types"):
        by_name = {}
        for row in global_catalog[key]:
            name = str(row.get("name", "")).casefold().strip()
            if name and name in by_name and by_name[name] != row["id"]:
                warnings.append(f"{key}: duplicate display name {name!r} across IDs")
            by_name[name] = row["id"]
    return {
        "phase": "READ_ONLY_PREFLIGHT",
        "ready_for_automatic_commit": not warnings,
        "global_catalog": global_catalog,
        "global_sha256": fingerprint(global_catalog),
        "profiles": summaries,
        "warnings": warnings,
        "source_snapshot_sha256": fingerprint(source),
        "history_preserved": True,  # No source objects mutated; no write performed.
        "writes_performed": False,
    }


def assert_source_unchanged(before, after):
    """Mandatory release gate for every migration/rollback transaction."""
    if fingerprint(before) != fingerprint(after):
        raise MigrationBlocked("Historical source snapshot changed")
