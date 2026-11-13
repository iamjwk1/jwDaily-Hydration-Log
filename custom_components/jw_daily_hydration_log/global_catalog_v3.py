"""Release-1 transactional global catalog store.

Read-only preflight precedes the first write. Legacy profile storage is retained
throughout beta32. A full original snapshot backup is never deleted. Every
multi-store catalog transaction has a recovery journal and checks readback.
No automatic rollback may replace new drink records with an older backup.
"""
from __future__ import annotations

import asyncio
import json
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from copy import deepcopy
from datetime import datetime, timezone
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .migration_v3 import (
    GLOBAL_KEYS, MigrationBlocked, build_preflight, fingerprint,
    _record_signature,
)

GLOBAL_FORMAT = "jwDaily-Hydration-Log-catalog-v3"
BACKUP_FORMAT = "jwDaily-Hydration-Log-v3-source-backup"
JOURNAL_FORMAT = "jwDaily-Hydration-Log-v3-journal"


class GlobalCatalogV3:
    """The shared liquid/cup settings owner; profile Quick buttons remain local."""

    def __init__(self, hass):
        self.hass = hass
        self._init_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._started = False
        self._store = Store(hass, 1, f"{DOMAIN}.global_catalog_v3")
        self._backup = Store(hass, 1, f"{DOMAIN}.migration_v3_backup")
        self._journal = Store(hass, 1, f"{DOMAIN}.migration_v3_journal")
        self.state = None
        self.profile_snapshots = {}
        self.live = {}

    def _entry_ids(self):
        return sorted(e.entry_id for e in self.hass.config_entries.async_entries(DOMAIN))

    def _profile_store(self, entry_id):
        return Store(self.hass, 1, f"{DOMAIN}.{entry_id}")

    async def _verified_save(self, store, value, label):
        await store.async_save(deepcopy(value))
        loaded = await store.async_load()
        if loaded != value:
            raise MigrationBlocked(f"{label}: storage readback differs from committed data")
        return loaded

    async def _load_profiles(self):
        result = {}
        for entry_id in self._entry_ids():
            raw = await self._profile_store(entry_id).async_load()
            result[entry_id] = deepcopy(raw) if raw is not None else {
                "data_model_version": 2, "records": [],
                "custom_liquid_types": [], "cup_types": [], "quick_buttons": [],
                "liquid_overrides": {}, "liquid_colors": {},
                "hidden_builtin_liquids": [], "liquid_order": [],
            }
        return result

    def _restore_catalog_only(self, current, original):
        """Never overwrite drink observations captured after a failed transaction."""
        recovered=deepcopy(current)
        for key in (*GLOBAL_KEYS, "quick_buttons"):
            if key in original:
                recovered[key]=deepcopy(original[key])
        return recovered

    async def _recover_pending(self):
        journal=await self._journal.async_load()
        if not journal or journal.get("status")!="pending":
            return
        if journal.get("format")!=JOURNAL_FORMAT or not isinstance(journal.get("before_profiles"),dict):
            raise MigrationBlocked("Invalid or incomplete global catalog rollback journal")
        originals=journal["before_profiles"]
        if fingerprint(originals)!=journal.get("before_profiles_sha256"):
            raise MigrationBlocked("Rollback journal checksum mismatch")
        global_before=journal.get("before_global")
        if (global_before is None or
                fingerprint(global_before)!=journal.get("before_global_sha256")):
            raise MigrationBlocked("Rollback global catalog checksum mismatch")
        # Any current post-crash drink records, day archives, consumption or
        # target changes must survive a catalog-only recovery.
        await self._verified_save(self._store,global_before,"rollback global catalog")
        for entry_id,original in originals.items():
            store=self._profile_store(entry_id)
            current=await store.async_load()
            if not isinstance(current,dict):
                raise MigrationBlocked(f"Profile {entry_id} missing after interrupted transaction")
            restored=self._restore_catalog_only(current,original)
            await self._verified_save(store,restored,f"rollback catalog profile {entry_id}")
        await self._verified_save(self._journal,{**journal,"status":"rolled_back"},
                                  "rollback journal")

    async def async_initialize(self):
        async with self._init_lock:
            if self._started:
                return
            await self._recover_pending()
            existing = await self._store.async_load()
            current = await self._load_profiles()
            if existing is not None and existing.get("status") == "active":
                if existing.get("format") != GLOBAL_FORMAT:
                    raise MigrationBlocked("Unrecognized active global catalog format")
                if fingerprint(existing.get("catalog")) != existing.get("catalog_sha256"):
                    raise MigrationBlocked("Global catalog checksum mismatch")
                backup = await self._backup.async_load()
                if (not backup or backup.get("format") != BACKUP_FORMAT or
                        fingerprint(backup.get("profiles")) != backup.get("source_sha256")):
                    raise MigrationBlocked("Original migration backup missing or damaged")
                self.state = deepcopy(existing)
                self.profile_snapshots = current
                # Release 2: remove only verified obsolete top-level fields.
                # Original v3 backup and current records are never rewritten.
                from .legacy_cleanup_v4 import LegacyCleanupV4
                self.legacy_cleanup_status = await LegacyCleanupV4(self).async_apply()
                self._started = True
                return
            if existing is not None:
                # A user-initiated rollback is sticky across restarts. Never
                # silently auto-reactivate a migration that was rolled back.
                raise MigrationBlocked("Global catalog has been rolled back; restore the prior release or run an explicit repair preflight")
            preview = build_preflight(current)
            if not preview["ready_for_automatic_commit"]:
                raise MigrationBlocked(
                    "Global catalog migration requires manual duplicate-name review: "
                    + "; ".join(preview["warnings"]))
            # This is the user's immutable release-1 baseline, not disposable migration work.
            backup = await self._backup.async_load()
            if backup is None:
                backup = {
                    "format": BACKUP_FORMAT,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source_sha256": fingerprint(current),
                    "profiles": deepcopy(current),
                }
                await self._verified_save(self._backup, backup, "migration baseline backup")
            elif backup.get("format") != BACKUP_FORMAT or fingerprint(backup.get("profiles")) != backup.get("source_sha256"):
                raise MigrationBlocked("Existing migration baseline backup is corrupt")
            # Never overwrite a backup merely because source data changed.
            # A subsequent run may use the oldest valid backup for disaster recovery.
            fresh = {
                "format": GLOBAL_FORMAT,
                "status": "active",
                "schema": 3,
                "catalog": deepcopy(preview["global_catalog"]),
                "catalog_sha256": preview["global_sha256"],
                "initial_profile_fingerprints": {
                    p["profile_entry_id"]: p["store_sha256"] for p in preview["profiles"]
                },
                "initial_history_fingerprints": {
                    p["profile_entry_id"]: p["ledger_sha256"] for p in preview["profiles"]
                },
                "baseline_backup_sha256": backup["source_sha256"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await self._verified_save(self._store, fresh, "global catalog v3")
            # No profile ledger or original Store is modified during migration.
            after = await self._load_profiles()
            for entry_id in current:
                if fingerprint(after[entry_id]) != fingerprint(current[entry_id]):
                    # Fail closed: restore earlier global state, never overwrite history.
                    await self._verified_save(self._store, {
                        **fresh, "status": "inactive"
                    }, "migration abort")
                    raise MigrationBlocked("Profile changed during migration preflight")
            self.state = fresh
            self.profile_snapshots = after
            self._started = True

    def _catalog_from(self, coordinator):
        return {key: deepcopy(getattr(coordinator, key)) for key in GLOBAL_KEYS}

    def _bind_catalog(self, coordinator):
        for key, value in self.state["catalog"].items():
            setattr(coordinator, key, deepcopy(value))
        coordinator._global_catalog_sha256 = self.state["catalog_sha256"]
        coordinator._global_catalog_v3 = self

    async def async_attach(self, coordinator):
        if not self._started or self.state["status"] != "active":
            raise MigrationBlocked("Global catalog not initialized")
        # New profiles may be created after migration. Keep their profile-local
        # observations and Quick buttons without introducing a second catalogue.
        raw = await coordinator._store.async_load()
        if raw is None:
            raw = {"data_model_version":2,"records":[],"quick_buttons":[],"cup_types":[],
                   "custom_liquid_types":[],"liquid_overrides":{},"liquid_colors":{},
                   "hidden_builtin_liquids":[],"liquid_order":[]}

        self.profile_snapshots[coordinator.entry_id] = deepcopy(raw)
        self.live[coordinator.entry_id] = coordinator
        self._bind_catalog(coordinator)

    def detach(self, coordinator):
        self.live.pop(coordinator.entry_id, None)
        coordinator._global_catalog_v3 = None

    def _current_history(self, entry_id):
        if entry_id in self.live:
            return self.live[entry_id].records
        return self.profile_snapshots.get(entry_id, {}).get("records", [])

    def liquid_use_count(self, liquid_id):
        return sum(1 for entry_id in self.profile_snapshots for row in self._current_history(entry_id)
                   if row.get("kind")=="drink" and row.get("liquid_type_id")==liquid_id)

    def cup_use_count(self, cup_id):
        return sum(1 for entry_id in self.profile_snapshots for row in self._current_history(entry_id)
                   if row.get("kind")=="drink" and row.get("cup_type_id")==cup_id)

    def _check_deleted_references(self, before, after):
        old_liquids = {t["id"] for t in before["custom_liquid_types"]}
        new_liquids = {t["id"] for t in after["custom_liquid_types"]}
        old_cups = {t["id"] for t in before["cup_types"]}
        new_cups = {t["id"] for t in after["cup_types"]}
        deleted_liquids = old_liquids - new_liquids
        deleted_cups = old_cups - new_cups
        for entry_id in self.profile_snapshots:
            for record in self._current_history(entry_id):
                if record.get("kind") != "drink":
                    continue
                if (record.get("liquid_type_id") in deleted_liquids or
                        record.get("cup_type_id") in deleted_cups):
                    raise MigrationBlocked(
                        f"Cannot delete Liquid or Cup used in {entry_id} drink history; hide it")
        return deleted_liquids, deleted_cups

    async def async_save(self, coordinator, local_payload):
        """Persist a profile and, when required, the shared catalog transactionally."""
        async with self._write_lock:
            if self.state.get("status") != "active":
                raise MigrationBlocked("Migration rollback pending; reload prior version before writing")
            candidate = self._catalog_from(coordinator)
            previous = self.state["catalog"]
            current_revision = self.state["catalog_sha256"]
            changed = candidate != previous
            if coordinator._global_catalog_sha256 != current_revision:
                if changed:
                    self._bind_catalog(coordinator)
                    raise MigrationBlocked("Stale global catalog; reload settings before editing")
                self._bind_catalog(coordinator)
                candidate = self._catalog_from(coordinator)
            if not changed:
                # A normal drink or target update never modifies the global catalog.
                for k in GLOBAL_KEYS:
                    local_payload[k] = deepcopy(candidate[k])
                await coordinator._store.async_save(local_payload)
                self.profile_snapshots[coordinator.entry_id] = deepcopy(local_payload)
                return
            try:
                removed_liquids, removed_cups = self._check_deleted_references(previous, candidate)
            except Exception:
                self._bind_catalog(coordinator)
                raise
            # All impacted profile Quick buttons must be removed. They are profile
            # preferences only; deleting them never modifies historical drink entries.
            before_profiles = {}
            after_profiles = {}
            for entry_id in self.profile_snapshots:
                raw = (deepcopy(local_payload) if entry_id == coordinator.entry_id
                       else deepcopy(self.profile_snapshots[entry_id]))
                original = deepcopy(self.profile_snapshots[entry_id])
                quick = raw.get("quick_buttons") or []
                raw["quick_buttons"] = [
                    q for q in quick
                    if q.get("liquid_type_id") not in removed_liquids
                    and q.get("cup_type_id") not in removed_cups
                ]
                for key in GLOBAL_KEYS:
                    raw[key] = deepcopy(candidate[key])
                before_profiles[entry_id] = original
                after_profiles[entry_id] = raw
            old_global = deepcopy(self.state)
            new_global = {**self.state, "catalog": deepcopy(candidate),
                          "catalog_sha256": fingerprint(candidate)}
            journal = {
                "format": JOURNAL_FORMAT, "status": "pending",
                "before_profiles": before_profiles,
                "before_profiles_sha256": fingerprint(before_profiles),
                "before_global": old_global,
                "before_global_sha256": fingerprint(old_global),
                "after_profiles_sha256": fingerprint(after_profiles),
                "after_global_sha256": fingerprint(new_global),
            }
            try:
                await self._verified_save(self._journal, journal, "catalog transaction journal")
            except Exception:
                self._bind_catalog(coordinator)
                raise
            try:
                await self._verified_save(self._store, new_global, "global catalog transaction")
                for entry_id, raw in after_profiles.items():
                    await self._verified_save(self._profile_store(entry_id), raw,
                                              f"profile catalog mirror {entry_id}")
                await self._verified_save(self._journal, {**journal, "status": "committed"},
                                          "catalog commit journal")
            except Exception:
                await self._verified_save(self._store,old_global,"catalog rollback")
                for entry_id,original in before_profiles.items():
                    store=self._profile_store(entry_id)
                    current=await store.async_load()
                    if not isinstance(current,dict):
                        raise MigrationBlocked("Rollback profile storage unavailable")
                    restored=self._restore_catalog_only(current,original)
                    await self._verified_save(store,restored,
                                              f"catalog rollback profile {entry_id}")
                await self._verified_save(self._journal,{**journal,"status":"rolled_back"},
                                          "catalog rollback journal")
                self._bind_catalog(coordinator)
                raise
            self.state = new_global
            self.profile_snapshots = after_profiles
            for entry_id, bound in self.live.items():
                bound.quick_buttons = deepcopy(after_profiles[entry_id].get("quick_buttons", []))
                self._bind_catalog(bound)
                bound._dispatch()

    async def async_export_baseline_backup(self):
        """Verified complete pre-migration restore archive, never auto-purged."""
        baseline=await self._backup.async_load()
        if (not baseline or baseline.get("format")!=BACKUP_FORMAT or
                fingerprint(baseline.get("profiles"))!=baseline.get("source_sha256")):
            raise MigrationBlocked("Migration backup unavailable or checksum invalid")
        buffer=BytesIO()
        with ZipFile(buffer,"w",ZIP_DEFLATED,compresslevel=7) as archive:
            manifest={"format":BACKUP_FORMAT,"schema":3,
                      "created_at":baseline.get("created_at"),
                      "source_sha256":baseline["source_sha256"],
                      "profiles":[]}
            for entry_id,raw in sorted(baseline["profiles"].items()):
                filename=f"profiles/{entry_id}.json"
                manifest["profiles"].append({
                    "entry_id":entry_id,"path":filename,"sha256":fingerprint(raw)})
                archive.writestr(filename, json.dumps(raw,sort_keys=True,
                    ensure_ascii=False,separators=(",",":"),allow_nan=False))
            archive.writestr("manifest.json",json.dumps(manifest,sort_keys=True,
                ensure_ascii=False,separators=(",",":"),allow_nan=False))
        payload=buffer.getvalue()
        with ZipFile(BytesIO(payload)) as verified:
            if verified.testzip() is not None:
                raise MigrationBlocked("Migration backup ZIP CRC validation failed")
            for item in manifest["profiles"]:
                data=json.loads(verified.read(item["path"]).decode())
                if fingerprint(data)!=item["sha256"]:
                    raise MigrationBlocked("Exported profile checksum differs")
        return payload,manifest

    async def async_rollback_to_local(self, expected_catalog_sha256):
        """Disable shared ownership without rolling old drink data backwards.

        Legacy copies are deliberately retained during release 1. Historical
        records created since migration are NEVER restored from the old backup.
        """
        async with self._write_lock:
            if self.state["catalog_sha256"] != expected_catalog_sha256:
                raise MigrationBlocked("Catalog changed since rollback preview")
            current = await self._load_profiles()
            for entry_id, coordinator in self.live.items():
                if _record_signature(current[entry_id]) != _record_signature(
                        self.profile_snapshots[entry_id]):
                    raise MigrationBlocked("Live ledger differs from stored ledger")
            before = deepcopy(self.state)
            inactive = {**before, "status": "inactive"}
            await self._verified_save(self._store, inactive, "migration rollback")
            self.state = inactive
            return {"rolled_back": True, "histories_modified": False,
                    "profiles": len(current), "backup_retained": True}
