# jwDaily Hydration Log v1.1.0-beta.1 (HACS pre-release)

Independent Home Assistant custom integration derived from [Personal Hydration Manager](https://github.com/loryanstrant/HA-Personal-Hydration-Manager), copyright 2026 Loryan Strant. MIT licensed; the verbatim upstream notice is included in `LICENSE-UPSTREAM-MIT`.

## New in v1.1.0-beta.1

- All new cards start with **neither a selected liquid nor a selected volume**. Select one of Water, Coffee, Tea, Milk, Soup or Other **and** one quick volume, then press **Add drink**. Both selections clear after a successful addition and after reopening the card.
- Clicking an existing record opens an edit dialog with liquid, amount, date (`DD-MM-YYYY`) and time (24-hour `HH:MM` or `HH:MM:SS`). Actions: **Save, Delete, Cancel**. Delete requires confirmation.
- Changes overwrite the existing record in-place; Delete permanently removes it from the integration ledger. There is **no edit/delete audit log**. The optional immediate **Undo last drink** permanently removes the just-added record. Existing external HA backups and Recorder history are outside the integration and are not purged.
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

## Install beta using HACS only

**Development preview** — the stable release remains `v1.0.2`. Before testing this beta, make a full Home Assistant backup, including `.storage/jw_daily_hydration_log.*` and your dashboard configuration. Do not manually copy files into `/config/custom_components/` and do not delete or re-create the existing profile.

1. Open **HACS → jwDaily Hydration Log** (custom integration repository: `https://github.com/iamjwk1/jwDaily-Hydration-Log`).
2. Enable **Pre-release** for this repository if HACS requires it, or open **⋮ → Redownload → Need a different version?**.
3. Select release **`v1.1.0-beta.1`** and download it.
4. Restart Home Assistant after HACS has replaced the integration code.
5. Refresh the dashboard in your browser (`Ctrl+Shift+R`) to load the new card JavaScript. Verify that the card displays `v1.1.0-beta.1`.
6. Verify your **existing** `Jan-Willem` profile, the old drink history (marked `Unknown (legacy)`), editing/deleting, a new typed drink, daily totals and the seven-sheet Excel export.

**Breaking change:** `jw_daily_hydration_log.log_drink` and drink events now require `liquid_type`. Existing automations calling them must be updated. The obsolete `hourly_pace` sensor is removed. Because deletes are permanent in the current storage, test deletion on a newly created test entry, not a valuable historical entry.

**Rollback:** In HACS choose `v1.0.2` from the version selector and restart Home Assistant. Downgrading code does not automatically undo data already changed by the beta. To recover deleted or edited records, restore a separate HA backup; review all changes since that backup before restoring.

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

### Rollback via HACS

In HACS use **⋮ → Redownload → Need a different version? → v1.0.2** and restart HA. This restores older **code**, not drink entries already edited or deleted by this beta. Restore a verified HA backup if you need historical values back.
