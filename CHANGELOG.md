# jwDaily Hydration Log — changelog

## v1.1.0-beta.22
- Unified main card geometry; drink count aligned under glass and shorter unused whitespace.
- Fixed stable liquid colors, new 6px type indicators in main card, responsive chart axes and per-bucket drilldown.
- Distinguish unrecorded vs recorded zero-intake days through additive sensor metadata.
- Preserve profiles/history, time precision, Excel schema and both HACS chart types.


## v1.1.0-beta.22
- Align consumption number, cup, liquid bars, right-side action, history and Excel/version footer to approved screenshot guides.
- Fixed 24px blue intake and equal fixed 17px cup labels on all card widths.
- HH:MM display in history while internally retaining HH:MM:SS.
- No storage migrations, changes to data, Excel calculations or existing chart cards.


## v1.1.0-beta.19
- Increase glass width by approximately 10-13% at normal and narrow card widths.
- Reduce Excel export button height to 28 CSS px without changing its position.
- Retain all beta.18 functions, records, styles and dynamic Excel exports.


## v1.1.0-beta.18
- Consistent deterministic per-liquid colors across both charts; weekly scale and responsive axes improved.
- Compact chart cards, five 28px history rows and smaller date/Excel controls.
- All data, history, APIs and the validated Excel export preserved.


## v1.1.0-beta.17
- Responsive HA card layout at browser zoom: side-by-side liquid bars and glass until 280 CSS px.
- Excel Daily intake header row 11 exactly 44 pt, Hydration log unchanged at 34 pt.
- No data or storage changes; all previous Excel and chart fixes retained.


## v1.1.0-beta.15
- Rebuild hero breakpoint and compact history/date/footer; preserve all beta.14 functionality.


## v1.1.0-beta.14
- Office styles XML prefix preservation fixes corrupt XLSX export.
- Excel in-page download and 2 selectable self-contained HACS Lovelace chart cards.
- Revised card layout, calendar input and aligned Excel/version footer.
- Retains five-row history, profiles, history and settings without data migration.


## v1.1.0-beta.14
- Rebuilt card's complete stylesheet for fluid side-by-side layout and five-row history viewport.
- Dynamic Excel Daily intake columns for current and historical-only types, flagged orange.
- Hydration log Date+time column width 19.
- No data migrations or destructive changes.


## v1.1.0-beta.12 (HACS pre-release)
- Correct side-by-side bar-chart layout on wider cards with named container query.
- Enforce 38px history rows and single-line volume manager rows.
- Rename second export worksheet to Daily intake; existing data unchanged.


## v1.1.0-beta.11 — HACS pre-release
- FIX-01: right-aligned daily-by-liquid chart on normal/wide cards, responsive stack only on small screens.
- FIX-02: removed Undo last drink button, keeping existing Add/Edit/Delete behavior.
- FIX-03: reduced history rows to equal 38px heights.
- FIX-04: centralized enabled button style with #B3E5FC background and clear selected/hover/focus/disabled states.
- FIX-05: date picker remains #FFFFFF with calendar icon.
- FIX-06/07: compact Manage liquid types and Manage volume buttons modals and aligned actions.
- FIX-08: more compact choice buttons using the same font size for both liquid and volume.
- FIX-09: distinct neutral #EEEEEE Manage controls.
- Excel: mandated 7 Hydration log and 16 Daily Totals column widths, native two-line wrapped headers (mL/count), pre-existing formulas and history unchanged.
- Release: full integration ZIP, ZIP CRC/SHA-256 checks and browser-modal geometry regression gates.


## v1.1.0-beta.10 — HACS pre-release
- Matched user-edited visual reference: fixed 24px blue intake next to left glass without overlap; wider right chart; smaller Add control anchored at the lower right.
- Kept dynamic *Drink moments* directly beneath glass. Removed only persistent success/status text beneath the hero.
- Uniform compact 40px history table rows; big bold selected date retained; Excel export aligned left and close to table.
- Enabled secondary and picker buttons have blue active states distinct from truly disabled buttons.
- Four-sheet Excel export is chronologically sorted and has readable expanded headers for liquid settings, volume buttons and drink log.
- Regression browser geometry tests strengthened at 888/721/412/360px. Existing history, profile settings, WebSocket interface, Android time normalization and ApexCharts entities unaffected.


## v1.1.0-beta.9 — HACS pre-release
- Repaired OOXML sheet1/sheet2 order for Excel desktop; added explicit regression test `pageMargins` before `tableParts`, XML illegal characters filtering.
- Rebalanced glass/chart left-right layout, compact Add, readable history dates, fixed uniform drink-row heights.
- Android numeric-only time entry normalized and validated without needing colon key.
- Added 2 per-profile entities: hourly intake today and daily intake last 7 days, with stable ID based typed liquid breakdown; ApexCharts samples included.
- Strengthened automated browser layout verification at 888/721/412/360 px.
- Existing drink records, historical daily archive, profile settings and stable v1.0.2 unaffected.


## v1.1.0-beta.8 (HACS pre-release)
- Fixed responsive dashboard layout at 721px and 888px: glass and blue total grouped left, uncropped liquid breakdown on the right, compact Add directly below the chart, smaller Undo and Excel buttons, and left-aligned history/date controls.
- Selecting an earlier date now updates every part of the daily summary: consumed volume, glass level, remaining amount, historic goal, drink count and per-liquid bars; no inconsistent today-only sensor values.
- Increased history date and drink moment font sizes.
- Rebuilt Excel export to match the supplied customized **four-sheet workbook**, including Excel-style table formatting, frozen rows, B2/B4/B11 positions, columns, liquid settings, volume button settings and native target-percentage formulas.
- Export filenames now include Home Assistant-local date and time: `YYYYMMDD-HHMM jwDaily Hydration Log - All Data.xlsx`.
- Included an independent reference workbook regression test and kept raw profile history/storage untouched.
- Existing `v1.0.2` remains the stable public release.


## v1.1.0-beta.7 (HACS pre-release)
- Permit future 24-hour CLOCK times when the selected date is TODAY; reject any calendar date later than TODAY.
- Validate date using HA's configured local timezone in the backend and block future dates in the popup.
- Continue rejecting invalid calendar dates and nonexistent daylight-saving-time wall times.
- Retain beta.6 layout and all stored drink records without migration changes.


## v1.1.0-beta.6 (HACS pre-release)
- Matched the card's daily header to the user's reference screenshot: total close to a left-positioned open glass and a wider bar chart on the right, with readable, unclipped numeric volumes.
- Moved the **+ Add drink** button under the chart and made it smaller; kept **Undo last drink** as a compact secondary action when appropriate.
- Placed the drink-count below the glass; removed the full-width Add row that pushed the history down.
- Kept the date selector and Excel export left-aligned. Narrow-card breakpoints adjusted.
- No changes to drink history, stored data or backend service behavior.


## v1.1.0-beta.5 (HACS pre-release)
- Added **Delete** to all installation-provided liquid types. Deleting a built-in removes its selection button, not its stable ID, history, historical totals or Excel data. A **Restore** control is provided in the manager. Changes persist by profile across HA restarts.
- The manager provides a confirmation before deleting a type; custom types continue to be deleted physically only when unused.
- Fixed the Manage liquid edit layout: two short columns, labels no longer awkwardly wrap and SVG input has an entire row with visible picker controls.
- Reworked hero grid and liquid bar chart to fit dashboard width; right-aligned Add, left-aligned history date and Excel button, scrollable history area enlarged.
- Added Excel visibility status (Liquid Types tab), plus backend and frontend regression tests for hide/restore and old record preservation.
- All original Personal Hydration Manager code and stored jwDaily Hydration Log drink events remain untouched by code publication.

## v1.1.0-beta.4 (HACS pre-release)
- Added persistent profile-level administration of built-in and custom liquid labels, MDI/SVG icons, default volumes, and button ordering while preserving stable history IDs.
- Added 0–24 customizable, reorderable quick-add volume buttons with add/edit/delete UI and persistent profile storage. Original per-card `quick_add` remains the fallback until customized.
- Popup volume, date and time field text enlarged for better legibility.
- Glass at exactly 100% reaches lowered target line; any amount over the target fills to the open rim without overflowing. The red goal line and red goal text render above blue liquid for readability.
- Excel export now includes nine workbooks tabs, adding Volume Buttons and exporting all built-in liquid overrides/order in Liquid Types. Existing drinks and data remain intact.
- Python backend and frontend regression tests extended; HACS/Hassfest gate before GitHub prerelease publication.

## v1.1.0-beta.3 (HACS pre-release)
- Save now verifies the running Python backend version first. Stale backends produce a restart instruction instead of generic `Unknown command` and no partial write is attempted.
- Add/Edit popup now has a complete calendar picker displaying `DD-MM-YYYY`; time remains in 24h format.
- New current-day liquid-by-type bar chart. Main card displays blue consumed volume aligned with animated fill, red target label and black remaining volume inside glass. Target line stays ~15 px lower and glass rim open.
- Remove redundant totals beneath history; compact Excel export button.
- Built-in Wine type and cow, soup-bowl and ordinary water-glass icons; Excel daily breakdown includes Wine.
- All profile data and existing v1.1.0-beta.2 registrations remain stored unchanged. Release via HACS only.

## v1.1.0-beta.2 (HACS pre-release)
- Compact glass/history/Add card; same Add/Edit popup; larger liquid icons.
- Custom liquid types with name, MDI icon or SVG file, and optional default volume, stored per profile.
- Automatic volume preselection only after selecting a custom type with a configured default.
- Red dashed 100% target line moved approximately 15 px lower (SVG y=39); level animates to it and the water surface gently ripples.
- Card version shown bottom-right.
- Excel extended to eight sheets including complete Liquid Types catalog, plus human-readable liquid names and custom-type breakdown.
- Existing v1.0.2 and beta.1 data retained; no separate edit/delete history.
- HACS-only distribution. No changes to upstream Personal Hydration Manager.

## v1.1.0-beta.1
- Explicit liquid and volume, popup edit/delete, backdated records, Dutch date + 24h time.
- Pace removed, compact open glass, seven-tab Excel export, Undo last drink.

## v1.0.2
- First stable independent release with timestamped history and complete Excel export.