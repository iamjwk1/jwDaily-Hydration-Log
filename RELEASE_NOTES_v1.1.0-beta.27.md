# jwDaily Hydration Log v1.1.0-beta.27

**Targeted correction of beta.26. Complete integration, no destructive migration.**

## Fix 1 — aligned Today by liquid bars

All rows now share one three-column CSS grid. The left edges of every bar and the right edges of every total line up across narrow and wide card widths. Ordinary labels remain readable beside the bars; long custom labels may wrap without moving other bars. Chart values and order are unchanged.

## Fix 2 — complete historical mapping review and repair

- The conversion inventory now covers **all stored drink records, over all dates**, including historical liquid IDs absent from the active Liquid type list. Such IDs must be explicitly mapped to a defined Liquid before applying.
- An already-converted beta.26 profile can reopen the conversion wizard and repair missing liquid/cup mappings; it is no longer blocked after the first conversion. Existing mappings are preloaded for review.
- A read-only audit displays total historic records and volumes, classified/unclassified liquid records, and records with known/unknown cup type. An unknown cup stays unknown until explicitly assigned; it is never inferred from the recorded volume.
- Import and conversion preview revisions now include a historic-ledger fingerprint. If drinks change before confirmation, conversion is rejected until the preview is refreshed. A bad or incomplete mapping is rejected atomically.
- Existing record IDs, timestamps including seconds, volumes, and original liquid IDs remain untouched. Alias mappings apply consistently to the history, daily/hourly/weekly charts, and four-sheet Excel export. The export now also resolves confirmed legacy Cup defaults for same-Liquid records.
- Repeating the same confirmed mapping has no effect and creates no duplicate Cup types, Quick buttons, or drink records. A verified backup and explicit confirmation remain prerequisites.

## Existing beta.26 features retained

Profile-specific Liquid/Cup/Quick settings, custom button names, central Settings, profile add/edit/copy, settings JSON import/export, 19/14/14 px glass labels, scrollable five-row history, four-sheet Excel export, and all recorded drink data remain supported. No existing profile is modified by installing this code.

## Acceptance and safeguards

1. Back up Home Assistant and export the complete profile JSON backup before remapping.
2. Open **Settings → Advanced → Convert existing data**. Inspect the complete inventory, including any historic-only IDs, and set each intended canonical Liquid and historical Cup.
3. Check the totals and unknown-cup count; download and verify the profile backup. Confirm only after review.
4. Check that the mapped record count equals the historical record count and that no volume, timestamp or record ID has changed. Unknown Cups may remain intentionally unknown.
5. Verify Today by liquid, Last 7 days, Today by hour, Drink history and the XLSX for representative days.

**Live acceptance has not been performed on the user's Home Assistant.** Official GitHub prerelease publication requires independent Source QA, HACS and Hassfest validation. beta.26 and beta.25 remain rollback sources.
