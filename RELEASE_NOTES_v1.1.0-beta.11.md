# jwDaily Hydration Log v1.1.0-beta.11

HACS test pre-release based on the complete v1.1.0-beta.10 source.

## Changes
- Restore right-hand Today by liquid chart next to glass at usable card widths; stack below at narrow widths.
- Remove Undo last drink button and its reserved spacing.
- Compact history rows to 40 CSS pixels with editing retained.
- Set action/selection button background to #B3E5FC and manage buttons to neutral #EEEEEE.
- Keep calendar date selector white (#FFFFFF).
- Compact liquid types and volume buttons with the same font size.
- Compact Manage liquid types and Manage volume buttons layouts, including aligned actions.
- Apply precisely specified Excel column widths to Hydration log and Daily intake; preserve historical data, formulas, and four-sheet workbook.
- Version consistency across manifest, backend and frontend.

## Safety
No storage schema changes, profile migration, or destructive actions.
User data remains in Home Assistant storage.
The original v1.1.0-beta.10 tag and stable release remain unchanged.

## Acceptance
Release workflow gates: backend tests, frontend interactions, Excel export QA, browser geometry screenshots, Hassfest, HACS validation. If a gate fails, do not publish the release.
