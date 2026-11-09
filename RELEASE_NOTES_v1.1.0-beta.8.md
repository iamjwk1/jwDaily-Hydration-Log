# jwDaily Hydration Log v1.1.0-beta.8 — HACS pre-release

This preview contains the integrated layout, historic-day summary, readability and Excel-export fixes requested after beta.7. **Stable v1.0.2 is unchanged.**

## Dashboard
- The selected drink-history date also drives the glass, red goal, total consumed, amount remaining, number of drink moments and per-liquid bar chart. Past dates use archived daily totals and historic goal where available; missing sensor readings are never invented.
- Two-column responsive layout measured at 721px and 888px card widths: blue consumed volume near the cup on the left, full chart and numeric labels on the right, small Add under the chart, left-aligned date and Excel actions.
- Larger date selector and drink-history text, preserving edit/delete and the popup.
- All existing drink records, profile settings, custom liquid types and volume buttons remain in HA storage.

## Excel export — follows the user-supplied customized workbook
Exactly four worksheets in this order:
1. **Hydration log** — export metadata and every retained individual drink moment, with date/time, profile, age, gender, goal, liquid name, amount.
2. **Daily Totals** — date, profile, age/gender, complete-day flag, goal, count, total volume, native Excel target percentage formula, and the seven built-in types.
3. **Settings - Liquid Types** — each type, its stable ID, name, MDI/SVG, default volume, order, custom flag and visibility.
4. **Settings - Volume Buttons** — ordered configured buttons.

The reference workbook's table headers and locations, formatting, column widths, frozen header, and Excel cell number formats are reproduced. Personal records are not embedded in the GitHub source. The exported filename uses Home Assistant local time, for example `20261109-1428 jwDaily Hydration Log - All Data.xlsx`. Extra raw source-reading and adjustment diagnostics are not separately included because they are not present in the four-sheet reference.

## HACS-only upgrade
Make an up-to-date Home Assistant backup. Open HACS → jwDaily Hydration Log → ⋮ → Redownload → Need a different version? → **v1.1.0-beta.8**. Restart Home Assistant Core, then refresh the dashboard (Ctrl+Shift+R). Preserve the existing profile.

## Acceptance
Check selected-day switching, dashboard layout at the actual card width, add/edit/delete on test records, and Excel output. Automatic Python, frontend, reference Excel, Hassfest, and HACS tests gate this release. Live testing on your HA remains required.
