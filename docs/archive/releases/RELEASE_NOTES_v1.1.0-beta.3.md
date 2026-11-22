# jwDaily Hydration Log v1.1.0-beta.3

**Home Assistant / HACS TEST RELEASE.** Stable v1.0.2 remains the default stable version.

## Fix: Save → Unknown command
The updated dashboard could load before the new Python integration was restarted, causing Save to display `Unknown command`. This version checks the running backend **before writing**. If versions differ, the popup explains that Home Assistant Core must be restarted; the card never silently records an incorrect drink.

**Important:** This check does not make a Home Assistant restart optional. Install beta.3 using HACS, **restart Home Assistant Core**, then hard-refresh the dashboard browser with Ctrl+Shift+R. The card and Python backend must both report v1.1.0-beta.3.

## User interface
- Date picker calendar (not a text field); visible dates DD-MM-YYYY, time 24-hour.
- Daily summary: blue consumed amount aligned with animated glass level; red target above dashed line; black remaining amount inside glass.
- New current-day liquid-by-type horizontal bar chart beside the glass; includes custom types and legacy Unknown without guessing.
- Removed redundant history total; smaller Excel-export button.
- Wine selectable as its own liquid; cow for Milk, soup bowl for Soup, normal glass for Other.
- Existing Add/Edit popup, custom SVG liquids, default volumes, editing, deleting and eight-tab Excel export retained.

## Migration and safety
- No change to integration domain `jw_daily_hydration_log`, profile IDs, store keys or existing records.
- All older drink history remains, with missing type marked `Unknown (legacy)`.
- The wine type is new and is included in the daily breakdown exported to Excel.
- The service now validates custom liquid IDs against the profile's liquid catalog, rather than rejecting valid custom types at schema validation.
- Deleting a record remains permanent in the integration ledger. Test with a new entry and create a complete HA backup first.
- Scripts invoking `jw_daily_hydration_log.log_drink` must provide `liquid_type` (breaking change introduced in beta.1).

## Install exclusively with HACS
Open HACS → jwDaily Hydration Log → ⋮ → Redownload → Need a different version? → **v1.1.0-beta.3**. Restart Home Assistant Core, then reload the browser (`Ctrl+Shift+R`). Keep the existing profile and dashboard card configuration.

Code rollback via HACS to a previous version cannot restore deleted records or guarantee the newer custom liquid catalog will survive subsequent saves by older code. Preserve the complete HA backup.

## Quality
Python regression tests, browser-shell tests, visual browser review, Hassfest and HACS Validation. This is a **pre-release** and still requires live acceptance on the target Home Assistant installation.
