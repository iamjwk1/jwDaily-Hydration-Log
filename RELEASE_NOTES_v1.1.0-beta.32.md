# jwDaily Hydration Log v1.1.0-beta.32 — Release 1

## Full-history-preserving migration
- First-run read-only preflight across every configured Home Assistant profile.
- Immutable original profile-storage snapshot, SHA-256 manifests, verified downloadable ZIP.
- Journaled, readback-verified global Liquid/Cup catalog updates; explicit guarded rollback.
- Existing drink records, timestamps, volumes, IDs and daily archive data are never deleted or converted.
- Existing zero-override profiles retain their previously calculated effective daily target at migration; new profiles default to 2000 mL.
- Legacy settings and original source data remain available throughout beta.32. **Do not delete the migration backup.** Legacy cleanup is deferred to the following release.
- Fail closed when conflicting catalog IDs, corrupt historical references or unexpected storage data are detected. The integration remains on the previous version until the conflict is resolved.

## Profiles and Quick buttons
- Daily target is edited within each profile; all dashboard target entities follow that profile.
- Profile-specific Quick buttons are accessible from Manage Profiles.
- Liquid and Cup definitions are shared between all profiles; Quick buttons never become global.
- Custom Liquid and Cup types may be deleted only when no profile has used them in drink history. Used types can be hidden instead.
- Quick buttons may always be deleted without modifying historical drink metadata.
- Source mode, source sensor, pregnancy and lactation inputs are removed from active configuration. Historic source records remain available for rollback.

## Excel
- Hydration log row height: 44 pt; first-sheet export date left aligned.
- Cup used header and values such as `Glass (250 mL)`; retired Current Cup default and Quick button columns.
- Daily intake Other is always the last liquid column.
- Liquid Types settings sheet has embedded symbolic PNG icon graphics.
- Export data selection defaults to All profiles, with every profile available in the dropdown.
- Profile-specific exports include only that profile's records and preferences; global Liquid and Cup definitions are included.
- XLSX contains Excel tables and verified DrawingML assets, with ZIP CRC validation.

## Installation and rollback
Install only through HACS after the published release has passed Source QA, HACS validation and Hassfest. Download and independently verify a full Home Assistant backup before updating. After installation, use **Settings → Advanced → Import & Export → Migration v3** to inspect the migrated status and download the original pre-migration ZIP, and verify its SHA-256/CRC outside Home Assistant. If the preflight fails, do not force or bypass it. For rollback, download the preserved source backup, explicitly confirm migration rollback, restore the previous integration release, then restart Home Assistant. Migration rollback never deletes any drink history.

## Scope
Release 1 only. No automatic removal of legacy storage or migration modules. The next release may clean these only after a successful live audit and explicit acceptance.
