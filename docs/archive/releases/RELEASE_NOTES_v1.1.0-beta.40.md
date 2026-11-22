# jwDaily Hydration Log v1.1.0-beta.40

**HACS prerelease**. Upgrades preserve the existing profile storage, ledger, historical drink IDs, timestamps, mL volumes, and previous backups. Stable releases are unchanged.

## User-requested interface fixes
- Add drink: compact amount/date/time fields; profile Quick Buttons with full configured liquid background and visible icon, without duplicated default amount text.
- Manage profiles: no unnecessary horizontal dividers and less whitespace before Edit.
- Edit profile: compact Age/Gender/Units/Target and wrapping Quick Buttons matching Add drink; remove technical slug/entity footer.
- Liquid types: column headings, regular-weight names, only numeric use counts in dark text, compact right-aligned icon actions, eye toggle for hidden/visible, clear tooltips, and Add liquid type label.
- Edit liquid type: consistent left alignment; live Preview of the real colored button; separate icon and button colors; select HA/MDI or safe SVG using the shared Choose icon dialog; compact inputs and Save liquid type.
- Cup types: descriptive deletion/hiding guidance, Cup type / Default volume / Times used column headings with non-overlapping values; Add cup type.
- Edit cup type: Icon first, Cup name and Default volume side-by-side, compact modal.
- Universal Choose icon: HA icon picker or custom SVG (max 16 KB), independently configurable icon color, one source at a time; Cancel/Apply isolated from persistence.
- Import & Export: three simple tabs — Export to Excel, Backup settings + data (ZIP), Restore. Advanced separate JSON tools remain available in a collapsed section for backward compatibility.

## Restore integrity and safety
- Existing full backup ZIP remains compatible and is validated with its checksummed manifest.
- Restore scopes: Everything, Settings only, Drink history only.
- The backend recreates the restore preview with unchanged current data for Settings-only, or unchanged current settings for Data-only; same-profile enforcement, checksum validation, version/revision guard and atomic rollback apply.
- Settings-only restore cannot orphan Liquid/Cup references in retained history; Data-only restore is checked against the existing catalog.
- A separate current backup is required before applying a restore; explicit preview and confirmation are required.

## Testing
Automated tests and HACS/Hassfest validations are release gates; live Home Assistant acceptance remains distinct. The pre-existing four user acceptance items for historical history, import/export and backup evidence remain pending a live installation.

Install from HACS using **v1.1.0-beta.40**, then restart Home Assistant Core and hard-refresh the dashboard. Do not manually overwrite the integration files.
