# jwDaily Hydration Log v1.1.0-beta.30 — native storage cleanup and separate History columns

**Prerequisite: beta.29 native data-model finalization MUST already be complete for every affected profile.**
The day-card screenshot alone cannot certify this; open beta.29 > Settings > Advanced > Finalize data model and verify **Already finalized / Model 2**. Export and verify a Full Backup ZIP and a complete Home Assistant backup before installing beta.30.

## Features

- **Drink history**: four independent, editable-on-row-click columns: Time, Liquid, Cup, Volume. Unknown Cups display "Unknown" rather than silently inferring a cup from logged mL. All columns align at 360, 420, 540, 720 and 950 CSS px.
- **Single native storage model**: all drink records persist `liquid_type_id` and explicit nullable `cup_type_id`. Legacy `liquid_type` and `source_legacy_liquid_id` aliases are removed from active profile storage; the original timestamp, record ID, amount and non-drink ledger events are preserved.
- **No more legacy conversion operations**: removes old mapping APIs, wizard, old volume-buttons management, and historic default-volume fields on Liquid definitions. Cup types and Quick buttons remain the sole active volume settings.
- **Native-only runtime**: all drink summaries, charts, and XLSX totals read direct stored Liquid/Cup IDs. No runtime mapping or guessing.
- **Four Excel sheets**: Hydration log, Daily intake, Settings - Liquid Types, Settings - Cups and Quick. The log shows actual drink volume beside the *current* Cup default volume, but no legacy ID column. Legacy volume-button section is gone.
- **Import/Export preserved**: schema-v2 Settings JSON and Data JSON, Merge / Update existing / Replace all, full profile backup ZIP. Beta.29 Settings schema-v1 files can be imported after obsolete fields have been discarded, but the native ID references of existing data must remain valid.

## Protected cleanup on startup

The first startup is **fail-closed**. It verifies model version 2, every drink's Liquid/Cup IDs, unique record IDs, timestamps and positive recorded volumes *before any cleanup write*. If a record is missing or inconsistent, the existing profile remains untouched, and the integration refuses to initialize with a clear migration error; return to beta.29 and repair/finalize that profile.

If verification passes, beta.30 first creates and SHA-256 verifies a separate Home Assistant Store snapshot named `jw_daily_hydration_log.<entry_id>.pre_beta30` (inside `.storage`). Only after this read-back verification are obsolete profile fields removed. The exact original drink IDs, timestamps, values and event order are checked. The archive is intentionally preserved for recovery; it is *not* part of the active profile schema.

**Rollback warning:** beta.29 expects some old event fields. Do **not** just downgrade the integration; restore the Home Assistant backup or use the archived original profile data. Keep the original Full Backup ZIP and HA backup until beta.30 is accepted live.

## QA acceptance

Python storage/migration/backup/import/XLSX regressions; real Chromium at five widths; ZIP CRC and SHA-256; independent GitHub Source QA, HACS and Hassfest checks before prerelease publication. Live Home Assistant acceptance of the user's entire historical dataset is necessarily separate from synthetic tests.
