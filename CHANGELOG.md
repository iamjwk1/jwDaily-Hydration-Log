# jwDaily Hydration Log — changelog

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
