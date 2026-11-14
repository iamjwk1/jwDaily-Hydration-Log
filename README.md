# jwDaily Hydration Log v1.1.0-beta.31

**Home Assistant custom integration — HACS pre-release.** Stable production release is still `v1.0.2`.

Repository: https://github.com/iamjwk1/jwDaily-Hydration-Log

Independent MIT-licensed fork of [Personal Hydration Manager](https://github.com/loryanstrant/HA-Personal-Hydration-Manager), copyright 2026 Loryan Strant. Original MIT notice retained verbatim in `LICENSE-UPSTREAM-MIT`.

## Current release: v1.1.0-beta.31

**Quick button controls:** Settings → Quick buttons now includes **Hide / Restore → Edit → Delete** in the compact row actions. Hide is a smaller, reversible visibility control. Delete is permanent and requires explicit confirmation. Deleting a Quick button never deletes a drink or changes its Liquid, Cup, timestamp or recorded volume. Its historical label remains in the drink record and the Excel export, even if the button catalog entry is removed. Both Cup types and Quick buttons have a single popup title, not duplicate headings.

**Upgrading from beta.30:** The storage schema remains native model 2. Take a Full Backup ZIP plus a Home Assistant backup before upgrading. If you still have beta.29 or older, first complete the documented native model finalization and protective beta.30 upgrade. All independent integration capabilities and the four Excel worksheets are retained.

### Prior beta.30 prerequisites and features



**Required before upgrading:** Use **beta.29** to complete `Settings → Advanced → Finalize data model` for the entire profile. Verify **Model 2 / Already finalized**, save a Full Backup ZIP, and make a Home Assistant backup. If a profile still uses the old model, beta.30 refuses to start that profile rather than rewriting unknown drink history.

**Drink history:** Four columns **Time | Liquid | Cup | Volume**. Tap a row to independently edit Liquid, Cup, date/time and actual volume. Unknown Cups remain `Unknown`; they are never inferred from recorded mL.

**Native storage cleanup:** Once all per-record references are verified, startup makes a separate SHA-256-verified pre-beta30 profile Store backup, then safely deletes old mapping and volume-button metadata, historic per-record aliases and obsolete Liquid default volumes. Drink IDs, timestamps, actual amounts and other events are unchanged. The archive is retained for recovery, not used by the live integration.

**No old converter:** The migration wizard, historic ID-mapping WS routes, and old volume-button editor are no longer part of normal operation. Cups and Quick buttons define reusable volumes; Liquid types own only name, icon and color.

**Import & Export:** Separate schema-v2 Settings and Data JSON; Data modes Merge, Update existing and Replace all; checksummed Full Backup ZIP/restore. v1 beta.29 Settings JSON is still accepted via a validation/normalization path; historic raw Data from before native finalization must be migrated in beta.29 first.

**Excel:** The four worksheets are **Hydration log**, **Daily intake**, **Settings - Liquid Types**, and **Settings - Cups and Quick**. Historical records use native Liquid and Cup IDs; the log distinguishes actual mL from the current Cup default mL. No obsolete alias columns or legacy preset section.

**Rollback:** A plain downgrade to beta.29 is not sufficient once old fields are retired. Restore the full Home Assistant backup or the protected pre-beta30 Store snapshot if you need to revert the storage model.

Older release notes follow below for history; their migration/menu instructions are **not** instructions for beta.30.

## What's new in beta.24

- **Liquid, Cup and Quick buttons:** Liquid types now own names/icons/colors; Cup types own names/default volumes; Quick buttons link both. Quick button names automatically follow `Liquid (Cup)` or use an independent custom label. Charts group by canonical Liquid type ID only, never Cup or button label.
- **Central Settings:** Profile (existing HA options), Daily target, Liquids, Cups, Quick buttons, Migration preview, Export and About in one Settings dialog.
- **Non-destructive legacy mapping:** read-only proposals (such as Water (beker)/Water (glas) to Water), backed up to downloadable JSON and explicitly confirmed before stored alias mapping. Historic records retain original IDs, amounts and times. Undo mapping is available.
- **Main card:** intake 19 CSS px; target and remaining 14 CSS px; tinted liquid icons replace Manage color dots; long Today by liquid names wrap while bars shrink and volumes stay aligned.
- **Excel:** exactly four sheets preserved; added Cup/Quick/historic-ID columns to Hydration log and Cup/Quick sections to sheet 4, canonical Liquid daily totals, original formulas, 19 Date+time width, 44pt row-11 header and color cells retained.
- **Rollback:** stable beta.23 files and raw data are preserved. User acceptance on live HA remains required.

## What's new in beta.23

- **Intake and footer geometry:** intake total is 19 CSS px on all card widths; target and remaining volume stay at 17 px. Version is positioned closer to the lower card margin without modifying the Excel button or inserting a divider.
- **Profile-specific liquid colors:** Edit liquid supports a native color picker, synchronized `#RRGGBB` input, live preview, strict validation and Reset to default. Colors persist using stable per-profile liquid IDs across restarts, reorder, rename and HACS upgrades; missing overrides retain beta.22 defaults.
- **Consistent charts and choices:** chosen colors update the main-card liquid dot and fill bar, liquid choice buttons with accessible text contrast, both charts, legends and per-bucket details. Default selection buttons retain `#B3E5FC`; Manage controls retain `#EEEEEE`.
- **Excel:** the existing four-workbook export adds only the `Color` column and matching cell fill to the liquid-type settings sheet; historical-only liquids are retained with available colors. Existing formulas, column widths, row 11 height (44 pt), historical orange headers and date/time formats are preserved.
- **Non-destructive storage:** all existing profiles, history, time precision and liquid/volume management remain intact. beta.22 remains available for rollback; note that beta.22 does not offer editing color overrides stored by beta.23.

## Previous beta.22 improvements


- **Main card completed:** center X drink moments under the glass, keep the 24px intake aligned to the glass, move Add drink up into the cup zone, reduce unused white space, bring liquid names and title slightly left while retaining aligned graph bars and volumes.
- **Consistent design:** blue volume bars, subtle per-liquid color dots, compact 28px history rows, editable HH:MM display with internal HH:MM:SS, white calendar date field, compact Excel footer.
- **Today by hour:** responsive hour labels (every hour on wide cards, every two hours on narrow cards); readable y-axis without overlap; consistent liquid-color mapping; tap/click/keyboard-accessible volume breakdown per hour.
- **Last 7 days:** y-axis with clear separation from mL label; dynamically scaled max; total volume above each bar; distinct coffee and orange juice colors; consistent legend order with the current day; details on selection.
- **Data integrity:** historical days with no data are marked —, distinctly from logged days with 0 mL; a new read-only has_data flag is added to the 7-day sensor attributes, without changing records or storage.
- **Excel unchanged:** valid OOXML, dynamic liquid type columns, orange retired headers, Date+time width 19 and Daily intake header height 44 pt remain in place.
- **Download security:** HTTPS (Nabu Casa) works; Chrome may block XLSX downloads through unsecured local HTTP as expected.

## Changes retained from beta.21

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


- **Reference-matched Excel:** Export now follows the user-edited four-sheet workbook: `Hydration log`, `Daily Totals`, `Settings - Liquid Types` and `Settings - Cups and Quick`, including the chosen B2 export header, B4–B8 metadata, B11 table header, frozen rows, original styles and native Excel percentage formulas. The workbook uses the literal file naming format `YYYYMMDD-HHMM jwDaily Hydration Log - All Data.xlsx`.
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
- **Excel export:** four reference-matched worksheets with native Excel tables: **Hydration log**, **Daily Totals**, **Settings - Liquid Types** and **Settings - Cups and Quick**. All saved drink moments are retained in Hydration log, including custom liquid names.
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

In beta.30, use **Settings → Cup types / Quick buttons** for reusable amounts; the old volume-button manager is retired. The `quick_add` YAML card values remain optional fallback display choices, not persistent legacy volume-button settings.

**Over-target:** The red dashed goal stays 15px below the rim; 100% fill meets that line, and when consumption exceeds the goal the blue fill is capped at the open top. The red target line and target label remain legible above the blue. The numeric intake remains uncapped.

## v1.1.0-beta.29 — data transfer and one-time model finalization

Use **Settings → Advanced → Import & Export** to download independent Settings JSON, Data JSON, and Full Backup ZIP files. Before importing or finalizing, make a Home Assistant backup and verify a downloaded Full Backup ZIP. Data import modes are Merge (missing record IDs), Update existing (matching record IDs updated), and Replace all (data only; same profile). Settings-only imports never rewrite drink history and cannot orphan linked Liquid/Cup IDs. Full restore is limited to the same profile ID and restores both Settings, Data and profile preferences. The ZIP includes SHA-256 checksums for each JSON member.

Historical beta.29-only instruction: use **Settings → Advanced → Convert existing data** followed by **Finalize data model** before upgrading to beta.30. The migration is not automatic. Original IDs, timestamps and recorded mL remain unchanged, and missing Cups stay explicitly unknown. Existing aliases remain stored temporarily only for rollback to previous beta versions; operational reads use the direct new fields after finalization. A future cleanup release can remove legacy code after live acceptance.

### Profile units and icon picker (beta.37)

Each Home Assistant profile controls its own mL, L or US fl oz display unit, daily goal and Quick buttons. The canonical drink ledger and daily archives remain in mL. The **Edit Liquid Type** and **Edit Cup Type** dialogs open the native Home Assistant visual icon picker (Material Design Icons); profile Quick buttons may override their Liquid icon. The Excel export uses a separate **All profiles / selected profile** dialog.