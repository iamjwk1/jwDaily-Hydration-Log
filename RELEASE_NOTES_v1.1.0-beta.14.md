# jwDaily Hydration Log v1.1.0-beta.14

Test pre-release based on beta.13, preserving all existing Home Assistant storage and profile data.

## Corrections
- Fix the invalid Excel styles.xml produced for orange legacy type headers by preserving the original Office namespaces/markup-compatibility declarations; prevent desktop Excel's styles/table repair cascade.
- Build the browser .xlsx download as an in-page data URI rather than an opaque blob:http URL. This does not override browser security policies for an insecure HTTP Home Assistant origin; HTTPS is recommended.
- Expose two real selectable Add card entries: `custom:jwdaily-hydration-hourly-card` (today by hour, 24 bins) and `custom:jwdaily-hydration-weekly-card` (last 7 days). Both read the existing Home Assistant hourly/7d sensors.
- Position the Excel export control bottom left and the version bottom right in one footer row.
- Add history calendar dropdown next to editable DD-MM-YYYY text and Go; narrow the date field.
- Restore full-size cup and red target text; bring consumed text closer to glass.
- Show only five full 38px history rows with older records accessible by scrolling.
- Preserve dynamic export liquid columns, 19-unit Date+time column, and orange header for removed historical types.

## Validation
CI gates: Python integration tests, native Excel OOXML integrity and namespace checks, frontend behavior, real Chrome geometry, HACS and Hassfest validation, ZIP CRC and SHA-256 verification. Do not publish if any gate fails.

Rollback: choose HACS v1.1.0-beta.13 if live checks fail. Code rollback does not restore changed drink records, so back up Home Assistant first.