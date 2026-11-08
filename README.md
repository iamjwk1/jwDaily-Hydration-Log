# jwDaily Hydration Log v1.1.0-beta.2

**Home Assistant custom integration — HACS pre-release.** Stable production release is still `v1.0.2`.

Repository: https://github.com/iamjwk1/jwDaily-Hydration-Log

Independent MIT-licensed fork of [Personal Hydration Manager](https://github.com/loryanstrant/HA-Personal-Hydration-Manager), copyright 2026 Loryan Strant. Original MIT notice retained verbatim in `LICENSE-UPSTREAM-MIT`.

## What's new in beta.2

- **Compact card:** only daily progress glass, drink history, and **+ Add drink** are visible initially. The version is displayed at the bottom-right of the card.
- **Same popup for Add and Edit:** choose a liquid using large icons, select a volume button or enter an amount, and enter date (`DD-MM-YYYY`) and 24-hour time. Edit mode additionally provides **Delete**, requiring confirmation. No forgotten previous liquid/volume selections.
- **Own liquid type buttons:** in Add/Edit popup, choose **+ Add custom liquid type** (HA administrator). Supply a unique name, an `mdi:` icon **or** a local `.svg` file (max 16 KB), and optionally a default volume in mL. The definitions are stored **per profile** in Home Assistant's existing `.storage/jw_daily_hydration_log.*` data. They survive restarts and HACS updates.
- **Smart volume default:** standard liquid types do not select a volume automatically. A custom type only preselects its volume after you explicitly select that type and only if a default was configured. New drink popups otherwise start with no type or volume selected.
- **Safety for SVGs:** uploads are sanitized by the backend against scripts, remote resources and unsupported XML elements; previewed as inert image elements (not inline markup).
- **Animated glass:** rising water level on changes plus a gently moving wave. The red dashed 100% target is **16 SVG units (~15 displayed px)** lower than before. The top stays open, with the 100% fill level aligned to the target line.
- **Excel export:** eight worksheets; the new **Liquid Types** sheet includes each custom type's name, ID, icon configuration and default volume. **Drink Moments** also includes a human-readable liquid name; **Daily Breakdown** includes custom types. Prior Excel data remains exportable.
- Existing drink modifications replace stored values. Deletions remove the integration's record. Previously saved records from v1.0.2 show **Unknown (legacy)** if they lack a type. Changes to existing historical records are not archived separately.
- The `hourly_pace` sensor, pace settings and pace calculations remain removed since beta.1.

## Install / update — only through HACS

1. Make a current full HA backup including the integration's `.storage` data, and check scripts and automations for the service change described below.
2. Open **HACS → jwDaily Hydration Log → ⋮ → Redownload → Need a different version?**. If necessary enable pre-releases for the repository.
3. Select **`v1.1.0-beta.2`**, download, then **restart Home Assistant**.
4. Refresh the dashboard with `Ctrl+Shift+R` and verify that the card footer shows beta.2. Keep the existing profile `Jan-Willem` and existing dashboard configuration.
5. Test a new custom liquid (name, SVG icon, default amount), register a drink via Add popup, edit/delete only a **test entry**, verify Excel's eight tabs. Do not delete valuable records to test the beta.

This repository's GitHub source ZIP is **not an executable installer**. Do not manually copy files into `/config/custom_components/`; HACS owns their upgrades.

## Backward compatibility and cautions

- Integration domain remains `jw_daily_hydration_log`; entity IDs, config entries and storage keys remain intact.
- Drink entries, archives, source readings and daily targets persist across the update. `custom_liquid_types` is an optional new storage key (empty until configured).
- **Breaking API change introduced in beta.1:** service `jw_daily_hydration_log.log_drink` and drink events now require `liquid_type`. Values: `water`, `coffee`, `tea`, `milk`, `soup`, `other`, or an existing `custom_<id>` from this profile. Audit existing automations before upgrading.
- Editing or deleting a drink changes stored history irreversibly within this integration; old values may still exist in HA backups or the Recorder. No hidden edit log is kept.
- You may remove an unused custom liquid type; the backend prohibits removing one that has been used in saved drink history.
- The updated Excel export contains **all stored records for all profiles**, including custom liquid definitions and SVG markup. It remains restricted to HA administrators.
- Rollback **code** through HACS version selection to `v1.1.0-beta.1` or `v1.0.2` only after a current full backup. **Older versions may overwrite the new custom-type catalog when they save state; custom type definitions could be lost on downgrade.** Rolling back code never recovers edited/deleted records; restore the relevant separate HA backup to recover data.

### Dashboard YAML (unchanged)

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
quick_add: [120, 150, 300, 500]
```

### Service example

```yaml
action: jw_daily_hydration_log.log_drink
data:
  profile: jan_willem
  liquid_type: water
  volume: 120
  unit: mL
```

## Quality & release policy

The beta branch must pass Python offline tests, JavaScript browser-shell tests, Home Assistant Hassfest and HACS Validation. Stable v1.0.2 stays unchanged until live acceptance on the HA system. PR reviews, tags and releases remain public on GitHub; updates are offered only through HACS.
