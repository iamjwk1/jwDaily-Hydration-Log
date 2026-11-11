# jwDaily Hydration Log v1.1.0-beta.21

**Home Assistant custom integration — HACS pre-release.** Stable production release is still `v1.0.2`.

Repository: https://github.com/iamjwk1/jwDaily-Hydration-Log

Independent MIT-licensed fork of [Personal Hydration Manager](https://github.com/loryanstrant/HA-Personal-Hydration-Manager), copyright 2026 Loryan Strant. Original MIT notice retained verbatim in `LICENSE-UPSTREAM-MIT`.

## What's new in beta.21

- Right-align the blue daily intake directly beside the glass rim; fixed 24px text in both broad and narrow cards.
- Shift the cup slightly left, move Today by liquid left, widen the liquid bars and align their volumes and Add drink on one common right edge.
- Move Add drink to the bottom of the hero zone, reducing redundant vertical white space before Drink history.
- Use fixed, equal 17px typography for the red target and black remaining volume, independent of SVG scaling.
- Display HH:MM in Drink history; edit and persistent records retain full HH:MM:SS.
- Align compact 28px Excel export button at the far left and version number at the far right, without adding reference guide lines.
- Preserve all profile data, drink history, volume/type settings, the two charts and existing 4-sheet Excel workbook.
- Browser acceptance at six real Chromium widths, including cup/blue-label separation, font sizes, right alignment, five-row scroll and edit seconds.

## Changes retained from beta.19

- Enlarge the glass in the main card by approximately 10-13%, maintaining side-by-side charts and avoiding collisions with the blue volume and red target label.
- Make the Excel export button only 28 CSS pixels high, keeping its bottom-left position and the version number at bottom-right.
- Strict browser regression assertions for cup dimensions and exact button height.
- Preserve all graph, Excel/OOXML, storage, calendar, profile and Add/Edit/Delete functionality from beta.18.

## Changes retained from beta.18

- Unified stable chart colors: the same liquid type uses the same color on both chart cards, even if its data appears in a different order.
- Responsive charts with more legible y-axis labels, a compact card height and version bottom-right.
- Weekly chart scale adapts to actual volumes: 2,550 mL highest day → 3,000 mL maximum instead of 4,000 mL.
- Main card: day total closer to cup; drink moments larger; history date narrower; five uniform 28px history rows and shortened Excel export button.
- Existing Excel export (44pt Daily intake header, dynamic liquid types, orange historical headers, exact column widths) preserved with all stored data.
- Excel download from unsecured local HTTP may still be blocked by Chrome; use HTTPS/Nabu Casa.

## Changes retained from beta.16

- One responsive two-column hero that keeps Today by liquid to the right even in a 720px screenshot at browser zoom (card ~360 CSS pixels).
- Beverage total, glass, target, and drink moments retain consistent alignment.
- Five visible 38px history rows; compact editable calendar date field and compact footer retained.
- Excel Daily intake second sheet header row 11 explicitly 44 pt high, while Hydration log header remains 34 pt. Exact workbook formulas and styles retained.
- No profile migrations or changes to existing stored data.

## Changes retained from beta.15

- Unified responsive glass/chart grid with bars to the right whenever available card width permits.
- Readable goal label, compact date field with native calendar popup, five 38px history rows.
- Removed footer divider and extra whitespace; aligned Excel button and version.
- No storage, Excel or functionality changes from beta.14.

## Changes retained from beta.14

- Preserve Office XML namespaces in styles.xml when generating orange historical-liquid headers; prevent desktop Excel repair warnings.
- Use direct in-page Excel data download instead of blob:http links; browser origin security still depends on how Home Assistant is accessed.
- Register two independent Lovelace cards in Add card: jwDaily Hydration – Today by hour and jwDaily Hydration – Last 7 days.
- Align Excel export button at bottom-left and version at bottom-right.
- Add a real history calendar popup beside editable DD-MM-YYYY text with a narrower date control.
- Restore readable red target label and full-size cup; align consumed volume closer to glass.
- Keep only five recent drink rows visible; older records accessible via scroll.
- No profile/data migrations.

## Earlier beta.13 changes

- Clean rebuilt responsive main card: keep liquid chart beside glass at usable widths; narrow fallback only below 280 CSS pixels.
- Show exactly five latest drink-history rows (38 CSS px each), with the column header always visible and older entries accessible by scrolling.
- Excel Hydration log Date+time column width 19.
- Daily intake generates columns for every defined liquid type even when unused, with separate orange headers for IDs present only in historical records. Uses actual stored records only.
- All settings and historical data remain unchanged.

## Retained beta.12 changes

- Fix card breakpoint and position liquid chart to the right of the glass on sufficiently wide cards.
- Reduce actual history row height and prevent vertical padding expansion.
- Make volume manager a true one-line input/action layout.
- Rename the second Excel worksheet to Daily intake.
- Preserve all profile data, history and choices.

## Changes retained from beta.11

- **FIX-01:** side-by-side chart to the right of the open glass and selected-day total on cards with sufficient room, stacking only on small cards; percentage line, bar totals and water animation unchanged.
- **FIX-02:** removed Undo last drink button from the card, with no empty placeholder; Add/Edit/Delete are unchanged.
- **FIX-03:** all history entries use compact, consistent **38px** rows with edit icons and separator lines.
- **FIX-04/08:** normal action and selection buttons use **#B3E5FC** background; selected, hover, focus, disabled styles differ without looking disabled by default; liquid and volume quick-selection controls are shorter and use the same font size.
- **FIX-05:** the date picker button remains pure white **#FFFFFF**, with calendar icon and existing DD-MM-YYYY validation.
- **FIX-06/07:** compact Manage liquid types and Manage volume buttons dialogs, aligned reorder/edit/delete controls and right-aligned footer actions.
- **FIX-09:** Manage liquid types and Manage volume buttons controls use neutral **#EEEEEE**.
- **Excel:** exact requested Excel column widths on Hydration log and Daily Totals, with tall wrapped two-line header cells and existing four-sheet metadata, data, date formats and formulas intact.
- **Packaging:** complete integration release ZIP with SHA-256 and ZIP CRC inspection, published as an asset on the HACS beta release.
- **Preserved:** user profiles, saved drink moments, custom liquids and quick buttons, historic selected-day data, Android 24-hour clock parsing, chart-data sensors, HACS installation.


- **Reference-aligned compact dashboard:** one consistent card-width layout with a 24px blue intake total, fixed non-overlapping separation from the glass, wider right-side chart, smaller and lower Add drink button, and *Drink moments kept directly under the glass*. On narrow cards the chart stacks below the glass.
- **History rows now 40 CSS px high**, uniform and vertically centered; the large bold date selector remains. No persistent `Drink saved` / `Saving…` status row or wasted gap. Excel export stays compact and flush left.
- **Enabled buttons are unmistakably active:** pale blue background/border/focus for date, volume, liquid and secondary controls, unlike disabled controls.
- **Excel readability:** four-sheet export is sorted **oldest → newest** and uses wider columns for `SVG Image`, `Default volume mL`, `Volume mL` and `Custom configured`; native formulas and Excel desktop OOXML compatibility fix retained.
- **No changes to stored data or backend API.** Profiles, historical records, water animation, target, custom liquids, Android time parsing, date selection and ApexCharts outputs all preserved.


- **Excel desktop repair:** Fixed OOXML worksheet element ordering (`pageMargins` must precede `tableParts`) which caused Excel Desktop to repair or empty sheets 1 and 2. The four customized reference sheets, tab labels, formatting, formulas and timestamped filename remain intact. XML/ZIP/reference structure tested; final Microsoft Excel Desktop compatibility still requires a user-side open/save/reopen acceptance test.
- **Card layout:** reference-aligned left blue total, glass moved left, wider right-hand bar chart, compact Add button under chart; equal-height drink-history rows, larger bold history date, and left-aligned Excel export.
- **Android clock input:** numeric keypad accepts `930` → `09:30`, `1430` → `14:30`, `14.30` → `14:30`, optional seconds; invalid `2431` is rejected because 24:31 is not a valid time. Later times today remain allowed, future calendar days prohibited.
- **ApexCharts integration:** two new per-profile chart-data sensors (24 clock-hour buckets today; seven calendar-day totals), typed series by persistent liquid ID. Working example Lovelace configurations in `examples/apexcharts-jwdhl-v1.1.0-beta.10.md`. Existing source sensor volume is not attributed to a liquid type without evidence.
- **QA:** full backend/frontend regressions, XML order verification and real Chrome geometry checks on 888/721/412/360-px cards. No changes to history storage or existing sensor IDs.


- **Reference-matched Excel:** Export now follows the user-edited four-sheet workbook: `Hydration log`, `Daily Totals`, `Settings - Liquid Types` and `Settings - Volume Buttons`, including the chosen B2 export header, B4–B8 metadata, B11 table header, frozen rows, original styles and native Excel percentage formulas. The workbook uses the literal file naming format `YYYYMMDD-HHMM jwDaily Hydration Log - All Data.xlsx`.
- **The selected day controls everything:** the open glass, blue volume, remaining volume, red goal, count and drink-type bar chart now show the day chosen in history. Historical days read archived totals and their historic target when saved; missing external source values are not invented.
- **Responsive layout rebuilt:** card-width-based columns keep the cup and blue total to the left, all chart volumes and the smaller Add control visible on the right at card widths 721/888 px and mobile sizes.
- **Improved history readability:** larger date selector text and larger drink moment fonts. Excel export stays compact at bottom left.
- **Export scope:** All retained individual drink moments and configured liquid/volume settings are exported to the four reference sheets. Raw source reading and adjustment diagnostics, which are absent from the reference workbook, are not exported in this four-tab view.


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
- **Today summary redesigned:** blue consumed volume aligned with the glass waterline, target in red above the dashed line, and remaining volume in the white area of the glass. The horizontal bar chart on the right summarizes the *selected* day, synchronized with the glass and its target. The redundant history total is removed and Excel button is more compact.
- **Native-like calendar picker:** the date picker is now a calendar popup with a visible `DD-MM-YYYY` date, previous/next month and keyboard-focusable day buttons. Time remains in 24-hour notation. Popup fields have compact widths.
- **Wine and icon adjustments:** Wine is a built-in type; Milk uses `mdi:cow`, Soup uses `mdi:bowl-mix`, and Other uses `mdi:glass-water`.
- **Backend version handshake:** Save checks the running Home Assistant backend version before writing. If a card has updated but HA Core has not restarted, the UI explains the mismatch and prevents a partial/invalid registration rather than showing an unhelpful `Unknown command`.

- **Same popup for Add and Edit:** choose a liquid using large icons, select a volume button or enter an amount, and enter date (`DD-MM-YYYY`) and 24-hour time. Edit mode additionally provides **Delete**, requiring confirmation. No forgotten previous liquid/volume selections.
- **Own liquid type buttons:** in Add/Edit popup, choose **+ Add custom liquid type** (HA administrator). Supply a unique name, an `mdi:` icon **or** a local `.svg` file (max 16 KB), and optionally a default volume in mL. The definitions are stored **per profile** in Home Assistant's existing `.storage/jw_daily_hydration_log.*` data. They survive restarts and HACS updates.
- **Smart volume default:** standard liquid types do not select a volume automatically. A custom type only preselects its volume after you explicitly select that type and only if a default was configured. New drink popups otherwise start with no type or volume selected.
- **Safety for SVGs:** uploads are sanitized by the backend against scripts, remote resources and unsupported XML elements; previewed as inert image elements (not inline markup).
- **Animated glass:** rising water level on changes plus a gently moving wave. The red dashed 100% target is **16 SVG units (~15 displayed px)** lower than before. The top stays open, with the 100% fill level aligned to the target line.
- **Excel export:** four reference-matched worksheets with native Excel tables: **Hydration log**, **Daily Totals**, **Settings - Liquid Types** and **Settings - Volume Buttons**. All saved drink moments are retained in Hydration log, including custom liquid names.
- Existing drink modifications replace stored values. Deletions remove the integration's record. Previously saved records from v1.0.2 show **Unknown (legacy)** if they lack a type. Changes to existing historical records are not archived separately.
- The `hourly_pace` sensor, pace settings and pace calculations remain removed since beta.1.

## Install / update — only through HACS

1. Make a current full HA backup including the integration's `.storage` data, and check scripts and automations for the service change described below.
2. Open **HACS → jwDaily Hydration Log → ⋮ → Redownload → Need a different version?**. If necessary enable pre-releases for the repository.
3. Select **`v1.1.0-beta.10`**, download, then **restart Home Assistant Core** (browser refresh alone cannot load new backend commands).
4. Refresh the dashboard with `Ctrl+Shift+R` and verify that the card footer shows beta.5. Keep the existing profile `Jan-Willem` and existing dashboard configuration.
5. Test Add with a built-in liquid and the new date picker, then a custom liquid (name, SVG icon, default amount), register a drink via Add popup, edit/delete only a **test entry**, verify all four Excel tabs. Do not delete valuable records to test the beta.

This repository's GitHub source ZIP is **not an executable installer**. Do not manually copy files into `/config/custom_components/`; HACS owns their upgrades.

## Backward compatibility and cautions

- Integration domain remains `jw_daily_hydration_log`; entity IDs, config entries and storage keys remain intact.
- Drink entries, archives, source readings and daily targets persist across the update. `custom_liquid_types` is an optional new storage key (empty until configured).
- **Breaking API change introduced in beta.1:** service `jw_daily_hydration_log.log_drink` and drink events now require `liquid_type`. Values: `water`, `coffee`, `tea`, `milk`, `soup`, `wine`, `other`, or an existing `custom_<id>` from this profile. Audit existing automations before upgrading.
- Editing or deleting a drink changes stored history irreversibly within this integration; old values may still exist in HA backups or the Recorder. No hidden edit log is kept.
- You may remove an unused custom liquid type; the backend prohibits removing one that has been used in saved drink history.
- The updated Excel export contains **all stored records for all profiles**, including custom liquid definitions and SVG markup. The four-sheet export remains restricted to HA administrators.
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

Choose **⚙ Manage volume buttons** within the same Add/Edit popup. Add, change, remove or reorder any of the 0–24 presets, and save the new sequence. These profile-specific buttons override the original dashboard `quick_add` only after you save them. All choices persist across restarts and are included in the four-tab Excel export.

**Over-target:** The red dashed goal stays 15px below the rim; 100% fill meets that line, and when consumption exceeds the goal the blue fill is capped at the open top. The red target line and target label remain legible above the blue. The numeric intake remains uncapped.