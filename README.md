# jwDaily Hydration Log v1.1.0 (pre-release candidate)

Independent Home Assistant custom integration derived from [Personal Hydration Manager](https://github.com/loryanstrant/HA-Personal-Hydration-Manager), copyright 2026 Loryan Strant. MIT licensed; the verbatim upstream notice is included in `LICENSE-UPSTREAM-MIT`.

## New in v1.1.0

- All new cards start with **neither a selected liquid nor a selected volume**. Select one of Water, Coffee, Tea, Milk, Soup or Other **and** one quick volume, then press **Add drink**. Both selections clear after a successful addition and after reopening the card.
- Clicking an existing record opens an edit dialog with liquid, amount, date (`DD-MM-YYYY`) and time (24-hour `HH:MM` or `HH:MM:SS`). Actions: **Save, Delete, Cancel**. Delete requires confirmation.
- Changes overwrite the existing record in-place; Delete permanently removes it from the integration ledger. There is **no edit/delete audit log and no undo**. Existing external HA backups and Recorder history are outside the integration and are not purged.
- **Custom date & time** adds a new entry with both liquid and volume explicitly entered (no pre-selected liquid/volume).
- Compact responsive glass layout: open-top glass with dashed red target line; numbers to the right; no large unused margin.
- Pace feature removed: no hourly-pace sensor or calculated pace, no minute updates, and no pace settings. A previous `hourly_pace` entity is removed from the entity registry for this integration when the v1.1.0 code is first loaded.
- XLSX export now contains seven worksheets: Profiles, Drink Moments, Daily Totals, Source Readings, Adjustments, Export Info and Daily Breakdown. Dates are numeric Excel dates displayed `DD-MM-YYYY`, timestamps 24-hour `DD-MM-YYYY HH:MM:SS`.

## Data and upgrade safety

- The same integration domain `jw_daily_hydration_log`, profiles, entity unique IDs and storage namespace are preserved from v1.0.2.
- Old v1.0.2 drink moments remain intact and are shown as `Unknown (legacy)` for their missing liquid type (never guessed as Water).
- Existing v1.0.2 `day_start`/`day_end` config-entry keys, if any, are ignored by v1.1.0; the settings no longer appear in the UI.
- `log_drink` and external drink events now **require** `liquid_type` to prevent unclassified new entries. Review any pre-existing automations or scripts that call this service. The bundled push-notification blueprint now has a required liquid selector; existing automations based on it must be reviewed before upgrade.
- When editing, moving or deleting a moment, current or archived daily totals are adjusted. External sensor readings remain separately preserved.
- Stored drink history is kept across restarts, daily reset and exports. The package never touches the original `personal_hydration_manager` domain.
- This is a **pre-release candidate**. The offline QA suite does not replace runtime acceptance in Home Assistant; do not publish a stable v1.1.0 tag until the runtime test passes.

## Installation (installer package, not a GitHub source ZIP)

Upload the ZIP to `/config`; do not unpack. First run a read-only preflight. This archive contains a tested executable installer and an integrity manifest. Ensure a verified backup of current HA before applying; the installer creates an additional backup including the current integration code and ledger.

```bash
python3 '/config/20261108 jwDaily Hydration Log v1.1.0.zip' --preflight
python3 '/config/20261108 jwDaily Hydration Log v1.1.0.zip' --upgrade
```

**HACS-managed installations:** do not manually overwrite HACS-managed files. Instead publish and test v1.1.0 via a separate GitHub development branch/release after validating a safe migration. The production `v1.0.2` release remains unchanged during review.

After `ha core check: PASS`, manually restart HA and verify card, ledger, modified old record, deletion, cross-day totals and seven-tab Excel export.

### Card YAML

```yaml
type: custom:jwdaily-hydration-log-card
profile: jan_willem
title: Vocht intake
show_title: true
show_cup: true
show_manual: true
show_history: true
show_export: true
unit: mL
quick_add:
  - 120
  - 150
  - 300
  - 500
```

`profile: jan_willem` works when the display name is `Jan-Willem` because the integration uses Home Assistant's `slugify()`.

### Updated service example

```yaml
action: jw_daily_hydration_log.log_drink
data:
  profile: jan_willem
  liquid_type: water
  volume: 120
  unit: mL
```

### Excel export

Use the admin-only **Export all data to Excel (.xlsx)** button. Drink Moments contains the *current edited* entries only; deleted entries are absent. The adjustments worksheet contains explicit `set_consumed` and `reset` commands, not a hidden log of drink edits/deletions. The source readings sheet is unaffected.

### Rollback

For rollback to the previous **code** without overwriting the latest drink data, the installer uses `--rollback --backup '/backup/<actual backup file>.zip'`. This keeps the current ledger intact. **Do not use `--restore-storage`** without specifically approving a data restoration because it replaces newer drink data with an older copy.
