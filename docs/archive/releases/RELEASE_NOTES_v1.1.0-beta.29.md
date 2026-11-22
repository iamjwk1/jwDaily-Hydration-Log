# jwDaily Hydration Log v1.1.0-beta.29

## Native data model and import/export

- A dedicated one-time **Finalize data model** operation writes canonical Liquid IDs and known Cup IDs into every historical drink record after a read-only audit and verified external backup. Original record IDs, timestamps and recorded volumes are preserved. Unknown historical cups remain explicitly unknown. Beta.28 legacy mappings remain stored for a verified rollback, but are no longer consulted for normal reads after finalization.
- Profile **Settings JSON** can still be exported and imported independently without changing drink history. Imports that orphan existing Liquid/Cup references are rejected.
- Profile **Data JSON** export/import added, with preview and mutually exclusive **Merge** (skip existing IDs), **Update existing** (replace matching IDs), or **Replace all** (only same-profile data) modes. Settings are not changed by Data imports. New/changed drinks are indexed by stable record ID, and daily totals are adjusted.
- Full profile backup ZIP contains `settings.json`, `data.json` and a checksum manifest. Restore requires an exact same-profile match, per-file checksum validation, a preview, and explicit confirmation. Profile preferences, Settings and Data are restored together.
- Before potentially destructive actions, users must export and verify a new full backup. Raw data imports with missing Liquid/Cup references, duplicate IDs, or invalid schemas are rejected.

## Excel — four worksheets preserved

- **Hydration log** now has a separate **Current Cup default (mL)** column beside recorded volume and Cup name; actual drink volumes are never inferred from the Cup. Liquid names use the configured display names.
- **Settings – Liquid Types** distinguishes active, hidden and mapped historic IDs; shows canonical targets and reference counts.
- **Settings – Volume Buttons** lists Cup types and Quick buttons first, readable Liquid/Cup names, profile preferences and a clearly labeled legacy-only volume section.
- All day totals, filters, formulas, tables and the four-sheet format remain intact.

## Rollback and migration caveats

The one-time rewrite is **not triggered by installing** this version. Install, make a Home Assistant backup and a Full Backup ZIP, review the conversion mapping, then explicitly finalize it. Historic Cup defaults cannot be reconstructed reliably and remain null when unknown. Legacy-removal is intentionally deferred to a later release after live acceptance.

**Required QA:** Python integration tests, WebSocket contract, real Chromium UI smoke tests, four-sheet OOXML structure, HACS and Hassfest.
