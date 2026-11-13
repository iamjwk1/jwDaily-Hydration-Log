"""Release 2: lossless, idempotent legacy profile-storage cleanup.

The immutable Release-1 v3 backup is NEVER modified. A second SHA-256-verified
full pre-cleanup backup preserves the *current* multi-profile state, including
every drink recorded since migration. Only whitelisted OBSOLETE top-level
settings are removed. Historical ledgers, source observations, daily
snapshots, targets, quick buttons and shared Liquid/Cup IDs remain byte-for-byte
identical at the JSON data level.

Interrupted multi-profile cleanup is resumed, never restored from a stale
backup: restoring would erase drink moments logged after that snapshot.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .migration_v3 import MigrationBlocked, fingerprint, _record_signature, GLOBAL_KEYS

BACKUP_FORMAT = "jwDaily-Hydration-Log-v4-precleanup-backup"
JOURNAL_FORMAT = "jwDaily-Hydration-Log-v4-cleanup-journal"
STATUS_FORMAT = "jwDaily-Hydration-Log-v4-cleanup-status"

# Verified unused by the native v2 + global v3 runtime. Values within the
# historical ledger (and even historical source sensor readings) are NEVER
# cleaned, because they form part of the user's drink history.
OBSOLETE_TOP_LEVEL = frozenset({
    "volume_buttons", "legacy_mappings", "legacy_cup_defaults",
    "conversion_state", "pregnancy", "lactation",
    "source_sensor", "source_mode",
})


def cleanup_plan(raw: dict) -> dict:
    """Read-only candidate; all unsupported/malformed data fails closed."""
    if not isinstance(raw, dict) or type(raw.get("data_model_version")) is not int or raw["data_model_version"] != 2:
        raise MigrationBlocked("v4 cleanup requires finalized data model 2")
    if not isinstance(raw.get("records"), list) or not isinstance(raw.get("daily_archive", {}), dict):
        raise MigrationBlocked("v4 cleanup requires valid historical ledger and archive")
    if not isinstance(raw.get("source_readings", []), list):
        raise MigrationBlocked("v4 cleanup requires the original source-reading history")
    if not isinstance(raw.get("quick_buttons", []), list):
        raise MigrationBlocked("v4 cleanup requires valid per-profile Quick buttons")
    if any(k not in raw for k in GLOBAL_KEYS):
        raise MigrationBlocked("v4 cleanup requires complete shared Liquid/Cup mirrors")
    if not isinstance(raw.get("target_override_ml", 0), (int, float)):
        raise MigrationBlocked("v4 cleanup requires numeric profile target")
    candidate = deepcopy(raw)
    for key in OBSOLETE_TOP_LEVEL:
        candidate.pop(key, None)
    if _record_signature(raw) != _record_signature(candidate):
        raise MigrationBlocked("v4 cleanup would change historical records or summaries")
    for key in (*GLOBAL_KEYS, "quick_buttons", "target_override_ml", "profile_target_model_v3"):
        if raw.get(key) != candidate.get(key):
            raise MigrationBlocked(f"v4 cleanup would modify protected field {key}")
    return candidate


def verified_backup(backup: dict) -> bool:
    return (isinstance(backup, dict)
            and backup.get("format") == BACKUP_FORMAT
            and isinstance(backup.get("profiles"), dict)
            and backup.get("source_sha256") == fingerprint(backup["profiles"]))


class LegacyCleanupV4:
    def __init__(self, manager):
        self.manager = manager
        hass = manager.hass
        self._backup = Store(hass, 1, f"{DOMAIN}.legacy_cleanup_v4_backup")
        self._journal = Store(hass, 1, f"{DOMAIN}.legacy_cleanup_v4_journal")
        self._status = Store(hass, 1, f"{DOMAIN}.legacy_cleanup_v4_status")

    async def _save_verified(self, store, value, label):
        await store.async_save(deepcopy(value))
        if await store.async_load() != value:
            raise MigrationBlocked(f"v4 {label}: storage readback differs")

    async def async_apply(self):
        """Run before coordinators attach, under the global v3 write lock.

        The current v3 catalog and its original rollback backup must already
        be verified by the caller. No legacy values are deleted from an
        unverified pre-migration installation.
        """
        manager = self.manager
        if not manager.state or manager.state.get("status") != "active":
            raise MigrationBlocked("v4 cleanup requires an active verified v3 catalog")
        async with manager._write_lock:
            # Recovering a pending v3 catalog transaction takes priority and is
            # handled by GlobalCatalogV3 before this function is called.
            journal = await self._journal.async_load()
            if journal is not None:
                if journal.get("format") != JOURNAL_FORMAT or journal.get("status") not in ("pending", "committed"):
                    raise MigrationBlocked("Unknown v4 cleanup journal; refusing writes")
                backup = await self._backup.async_load()
                if not verified_backup(backup):
                    raise MigrationBlocked("v4 cleanup journal exists without valid backup")

            before = {}
            after = {}
            retired = {}
            for entry_id in manager._entry_ids():
                original = await manager._profile_store(entry_id).async_load()
                # A profile which has never been initialized has no legacy
                # data to delete. Never create a phantom Store.
                if original is None:
                    continue
                if not isinstance(original, dict):
                    raise MigrationBlocked(f"Malformed profile Store {entry_id}")
                before[entry_id] = deepcopy(original)
                after[entry_id] = cleanup_plan(original)
                retired[entry_id] = sorted(set(original) & OBSOLETE_TOP_LEVEL)

            existing_backup = await self._backup.async_load()
            if existing_backup is not None and not verified_backup(existing_backup):
                raise MigrationBlocked("Original v4 pre-cleanup backup is corrupt")
            needs_changes = any(before[e] != after[e] for e in before)
            if not needs_changes and journal is None:
                return {"status": "clean", "profiles_checked": len(before),
                        "removed_fields": 0, "writes": False,
                        "backup_status": "not_needed"}
            if existing_backup is None and (needs_changes or journal):
                backup = {
                    "format": BACKUP_FORMAT,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "source_sha256": fingerprint(before),
                    "profiles": deepcopy(before),
                }
                await self._save_verified(self._backup, backup, "immutable pre-cleanup backup")
            else:
                backup = existing_backup
            if not verified_backup(backup):
                raise MigrationBlocked("Pre-cleanup backup missing or invalid")

            # If a crash occurred after one profile was cleaned, rescan current
            # states and resume only the remaining whitelisted removals.
            if not needs_changes and journal is not None and journal["status"] == "committed":
                return {"status": "clean", "profiles_checked": len(before),
                        "removed_fields": 0, "writes": False, "backup_status": "verified"}

            record_digests = {e: _record_signature(p) for e, p in before.items()}
            if needs_changes:
                pending = {
                    "format": JOURNAL_FORMAT, "status": "pending",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "backup_sha256": backup["source_sha256"],
                    "profile_history_sha256": record_digests,
                    "profile_fields_removed": retired,
                }
                await self._save_verified(self._journal, pending, "transaction journal")
                # Every write is preceded by a second read. Fail closed if
                # another actor changed that profile since the plan was made.
                for entry_id in sorted(after):
                    if before[entry_id] == after[entry_id]:
                        continue
                    store = manager._profile_store(entry_id)
                    live = await store.async_load()
                    if fingerprint(live) != fingerprint(before[entry_id]):
                        raise MigrationBlocked(f"Profile {entry_id} changed during v4 cleanup")
                    await self._save_verified(store, after[entry_id], f"profile {entry_id}")
                    readback = await store.async_load()
                    if _record_signature(readback) != record_digests[entry_id]:
                        raise MigrationBlocked(f"Profile {entry_id} history changed in v4")
                # Do not replace stored profiles with a prior backup, even if
                # completing the journal fails. The next restart can resume.
                manager.profile_snapshots = await manager._load_profiles()

            report = {
                "format": STATUS_FORMAT, "status": "clean",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "profiles_checked": len(before),
                "removed_fields": sum(len(v) for v in retired.values()),
                "profile_fields_removed": retired,
                "original_v4_backup_sha256": backup["source_sha256"],
                "v3_baseline_preserved": True,
                "history_unchanged": True,
            }
            await self._save_verified(self._status, report, "completion status")
            await self._save_verified(self._journal, {
                "format": JOURNAL_FORMAT, "status": "committed",
                "backup_sha256": backup["source_sha256"],
                "completion_status_sha256": fingerprint(report),
            }, "committed journal")
            return dict(report, backup_status="verified", writes=needs_changes)
