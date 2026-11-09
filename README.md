# jwDaily Hydration Log v1.1.0-beta.7

**Home Assistant custom integration — HACS pre-release.** Stable production release is still `v1.0.2`.

Repository: https://github.com/iamjwk1/jwDaily-Hydration-Log

Independent MIT-licensed fork of [Personal Hydration Manager](https://github.com/loryanstrant/HA-Personal-Hydration-Manager), copyright 2026 Loryan Strant. Original MIT notice retained verbatim in `LICENSE-UPSTREAM-MIT`.

## What's new in beta.7

- **Future time permitted:** On today's HA-local calendar date, any valid 24-hour time can be entered, even if later than now.
- **Future calendar day blocked:** Tomorrow and later dates remain rejected in the popup and Python backend. Earlier days remain permitted; impossible DST wall times remain rejected.
- The glass/chart and compact Add layout from beta.6 remains intact.


- **Layout fixed against the supplied reference screenshot:** blue volume left and close to the open glass, glass moved substantially left, daily liquid bar chart on the right. Full bar volumes are no longer clipped.
- **Compact Add button directly below the right-side chart** instead of a separate tall full-width button row. Drink count sits under the glass.
- **Left-aligned history controls and smaller Excel export** remain in the intended positions; no changes to stored profile data or logging.


- **Compact card:** only daily progress glass, drink history, and **+ Add drink** are visible initially. The version is displayed at the bottom-right of the card.
- **Delete installation-provided liquid buttons:** every built-in type now has a Delete action with confirmation. A built-in Delete hides it from the Add popup; it can be restored through the **Hidden built-in liquid types** section. Existing drink records, type IDs, chart labels, totals and exported data remain intact. A custom type can still be permanently deleted only when unused.
- **Responsive manager and dashboard:** the edit-liquid form now uses compact two-column inputs with a full-width SVG picker (no cut-off filename controls). The main card follows the accepted modified screenshot: better-contained liquid bars, right-aligned Add, left-aligned date controls and export; history provides more scrollable space.
- **Excel visibility metadata:** the Liquid Types sheet includes whether each type is currently visible in the picker.
- **Full liquid-button management (admin):** open Add drink → Manage liquid types to add or edit the name, MDI icon / SVG, optional default amount, and position (↑ / ↓) for *both built-in and custom* liquids. Only unused custom types can be permanently deleted; built-in types can be removed from the Add picker and restored later without deleting drink history. History retains each stable type ID and the new label is reflected in views and exports.
- **Persistent volume-button management (admin):** open Add drink → Manage volume buttons to add, edit, delete, or move each preset. Values are saved per hydration profile; zero buttons is valid and leaves manual custom amount input available. Existing dashboard `quick_add` YAML remains the default until a profile-specific change is saved.
- **Over-target waterline:** 100% reaches the lowered red target line. Any intake beyond 100% fills to the open rim, never above it; red target line and goal text remain layered *above* the blue fill, and the consumed total can continue increasing without limit from the graphic.
- **Legibility:** larger volume, date and time controls; more readable labels in the popup.
- **Today summary redesigned:** blue consumed volume aligned with the glass waterline, target in red above the dashed line, and remaining volume in the white area of the glass. A live horizontal bar chart to the right summarizes current-day drinks by liquid type, independent of the date viewed in history. The redundant history total is removed and Excel button is more compact.
- **Native-like calendar picker:** the date picker is now a calendar popup with a visible `DD-MM-YYYY` date, previous/next month and keyboard-focusable day buttons. Time remains in 24-hour notation. Popup fields have compact widths.
- **Wine and icon adjustments:** Wine is a built-in type; Milk uses `mdi:cow`, Soup uses `mdi:bowl-mix`, and Other uses `mdi:glass-water`.
- **Backend version handshake:** Save checks the running Home Assistant backend version before writing. If a card has updated but HA Core has not restarted, the UI explains the mismatch and prevents a partial/invalid registration rather than showing an unhelpful `Unknown command`.

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
3. Select **`v1.1.0-beta.7`**, download, then **restart Home Assistant Core** (browser refresh alone cannot load new backend commands).
4. Refresh the dashboard with `Ctrl+Shift+R` and verify that the card footer shows beta.5. Keep the existing profile `Jan-Willem` and existing dashboard configuration.
5. Test Add with a built-in liquid and the new date picker, then a custom liquid (name, SVG icon, default amount), register a drink via Add popup, edit/delete only a **test entry**, verify Excel's eight tabs. Do not delete valuable records to test the beta.

This repository's GitHub source ZIP is **not an executable installer**. Do not manually copy files into `/config/custom_components/`; HACS owns their upgrades.

## Backward compatibility and cautions

- Integration domain remains `jw_daily_hydration_log`; entity IDs, config entries and storage keys remain intact.
- Drink entries, archives, source readings and daily targets persist across the update. `custom_liquid_types` is an optional new storage key (empty until configured).
- **Breaking API change introduced in beta.1:** service `jw_daily_hydration_log.log_drink` and drink events now require `liquid_type`. Values: `water`, `coffee`, `tea`, `milk`, `soup`, `wine`, `other`, or an existing `custom_<id>` from this profile. Audit existing automations before upgrading.
- Editing or deleting a drink changes stored history irreversibly within this integration; old values may still exist in HA backups or the Recorder. No hidden edit log is kept.
- You may remove an unused custom liquid type; the backend prohibits removing one that has been used in saved drink history.
- The updated Excel export contains **all stored records for all profiles**, including custom liquid definitions and SVG markup. It remains restricted to HA administrators.
- Rollback **code** through HACS version selection to `v1.1.0-beta.4`, `v1.1.0-beta.3`, `v1.1.0-beta.2`, `v1.1.0-beta.1` or `v1.0.2` only after a current full backup. **Older versions may overwrite the new custom-type catalog when they save state; custom type definitions could be lost on downgrade.** Rolling back code never recovers edited/deleted records; restore the relevant separate HA backup to recover data.

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

### Managing liquids and volume presets (beta.4)

With **Add drink** open, choose **⚙ Manage liquid types**. The list supports **Edit** for built-in and custom types, **↑ / ↓** for order and **Delete** only for unused custom types. Enter a display name, MDI icon or uploaded safe SVG, and optional default volume. The original liquid ID is never changed; existing historical records remain associated with that type. Choose **Back to drink** when finished.

Choose **⚙ Manage volume buttons** within the same Add/Edit popup. Add, change, remove or reorder any of the 0–24 presets, and save the new sequence. These profile-specific buttons override the original dashboard `quick_add` only after you save them. All choices persist across restarts and are included in the nine-tab Excel export.

**Over-target:** The red dashed goal stays 15px below the rim; 100% fill meets that line, and when consumption exceeds the goal the blue fill is capped at the open top. The red target line and target label remain legible above the blue. The numeric intake remains uncapped.
