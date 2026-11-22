# jwDaily Hydration Log v1.1.0-beta.35 — Release 2 (Legacy Cleanup)

## Scope
Only Release-2 legacy cleanup of obsolete profile-store settings. This release does **not** change the dashboard layout or the Excel workbook data contract.

## What changes
- When the global v3 catalog is **active and verified**, a separate v4 read-only preflight checks every existing profile for obsolete top-level settings.
- It removes only these old **top-level** fields if they are present: `volume_buttons`, `legacy_mappings`, `legacy_cup_defaults`, `conversion_state`, `pregnancy`, `lactation`, `source_sensor`, `source_mode`.
- It does not remove or alter old *historical* source readings, past day archives, records, individual timestamps, volumes, source contributions, personal targets, Cup/Liquid definitions or profile Quick buttons.
- Before the **first deletion**, the full **current** profile stores (not just the older beta.32 baseline) are preserved in an immutable, SHA-256 verified Home Assistant Store: `jw_daily_hydration_log.legacy_cleanup_v4_backup`.
- Every removal performs pre-write fingerprint checks and post-write history fingerprints/readback verification. A v4 transaction journal records progress in `jw_daily_hydration_log.legacy_cleanup_v4_journal`; completion status is persisted in `jw_daily_hydration_log.legacy_cleanup_v4_status`.
- If an individual profile-store write fails, initialization fails closed and the next restart safely resumes the remaining field deletions, never restoring a stale backup over drinks recorded later.
- The original v3 migration archive `jw_daily_hydration_log.migration_v3_backup`, the pre-beta30 backup (if any), old import compatibility and profile history are *never purged*.
- Migration status API adds a read-only `legacy_cleanup_v4` report (when available) without changing the migration dialog's existing controls.
- Existing custom source sensor/mode and pregnancy/lactation options remain hidden and inactive; historical import/target-migration readers required for old backups are retained deliberately.

## Preconditions and safety
- A v3 catalog with state `active`, intact checksum and verified original v3 migration backup is mandatory.
- A full Home Assistant backup is strongly recommended before updating from beta.34.
- If the v4 current-state backup or journal is corrupted, the cleanup is blocked **before writing**.
- If no obsolete fields exist, cleanup is a no-op; no unnecessary profile write or backup is performed.
- Source records remain intact even when they contain historical sensor metadata.
- This is **not** a full-profile rewind or drink-history restore; older copies must never overwrite recent drink data.

## Validation
- Multi-profile migration, native history, Excel workbook QA, Chromium UI regression at five widths, HACS and Hassfest.
- New v4 tests: partial failure and restart recovery, post-failure drink entry survival, immutable current-state + original v3 backups, idempotence and corrupted-backup fail-closed checks.
- Verified release ZIP with file-by-file checks, CRC and SHA-256.

## Upgrade
1. Keep your downloaded v3 pre-migration ZIP outside Home Assistant and make a fresh full HA backup.
2. Update to v1.1.0-beta.35 via HACS, restart Home Assistant, Ctrl+F5.
3. Confirm the card footer shows v1.1.0-beta.35. Check Migration v3 remains active with Backup Verified and the correct profile count.
4. Confirm the drink history and Excel export still match your pre-update data.
5. Do not use **Rollback migration** unless a specific recovery requires it.
