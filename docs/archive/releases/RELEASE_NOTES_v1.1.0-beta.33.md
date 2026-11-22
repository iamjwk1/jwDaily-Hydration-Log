# jwDaily Hydration Log v1.1.0-beta.33 — Migration buttons hotfix

## Fixed
- **Check migration status** now dispatches its action to the authenticated `jw_daily_hydration_log/migration_status` backend call. The migration state, profile count and backup verification appear in the migration dialog.
- **Download pre-migration ZIP** now dispatches `jw_daily_hydration_log/migration_backup_export` and initiates the protected original-backup download.
- The guarded **Rollback migration** action is routed correctly; it remains disabled until the user has confirmed verification of the original ZIP and the backend confirms a valid backup. No automatic rollback takes place.
- Adds a real Chromium browser regression at five responsive widths that clicks both actions and checks the WebSocket calls, displayed status and download initiation.

## Data safety
- No profile records, historic timestamps, volumes, daily archives, Liquid/Cup IDs, or backend migration/store schema changes.
- This release is a frontend hotfix with aligned backend/Excel version identifiers required by the integration's version safety check.
- Original beta.32 migration backups are preserved.
- Beta.32 Release 1 behavior remains in effect. Legacy cleanup remains deferred to a later independent release.

## Updating from beta.32
1. Update to `v1.1.0-beta.33` in HACS, restart Home Assistant, then force refresh the browser tab (`Ctrl+F5`).
2. Open the Hydration dashboard → **Settings → Advanced → Import & Export → Migration v3**.
3. Click **Check migration status**. Expected: `Status: active`, correct Profiles count and `Backup: Verified`. If not, do not force migration or rollback.
4. Click **Download pre-migration ZIP**. Independently open and verify the archive and its manifest; retain it outside HA.
5. Do **not** click **Rollback migration** during normal post-install checks.
