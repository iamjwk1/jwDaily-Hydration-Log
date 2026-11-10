# jwDaily Hydration Log v1.1.0-beta.13

New clean-layout HACS pre-release based on beta.12. At sufficient width, the per-liquid bar chart stays to the right of the glass. The history shows a sticky header and at most five complete 38px drink rows; older records remain scrollable. All existing data and behavior are preserved.

Excel: the Hydration log Date+time column has Excel width 19. Daily intake generates an individual column for every currently defined liquid ID (including those with zero recorded volume), plus separate columns for historical-only IDs with orange headers. Both Excel tables have dynamically matching ranges, and existing total/percentage formulas remain intact.

This is a test build. Python, frontend, Chrome visual layout, Excel reference/dynamic schema, Hassfest, HACS and CRC/SHA-256 packaging checks are required for release.