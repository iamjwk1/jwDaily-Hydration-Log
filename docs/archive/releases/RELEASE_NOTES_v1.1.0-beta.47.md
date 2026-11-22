# jwDaily Hydration Log v1.1.0-beta.47 — Excel formatting parity

**Purpose:** Correct the beta.46 Excel export that did not visually match the supplied `20261120-1703 jwDaily Hydration Log - All Data.xlsx` example.

## What changed
- Use the approved reference's original Excel styles (font/font size/weight, backgrounds, borders, number formats), workbook theme, base column geometry and corresponding header/body style indices.
- Preserve all **six worksheets**, each with its own sortable/filterable Excel table, and preserve their headings and expected positions.
- Data rows are **18 pt**, every exported cell is vertically centered, and Hydration log header is **38 pt**.
- **Daily intake:** original fixed metadata column widths are preserved; only Liquid Type columns are content-fitted. Other remains the last liquid column.
- Liquid icon images remain genuine native **Place in Cell** Office rich-value images, not floating DrawingML or remote IMAGE formulas.
- The example's empty technical ID fields were intentional sample omissions. **Keep actual IDs populated from Home Assistant**, as explicitly requested.
- No example drink records, identifiers or personal data are packaged in beta.47. The reference-derived style module contains only sanitized XLSX format/style/theme/column information.

## Safety
- Excel export is read-only; no changes to HA profile records, original record IDs, converted quantities, archives, database, settings, native JSON import/export or ZIP restore behavior.
- No data schema migration is introduced.
- Existing beta.46 release remains intact; beta.47 is a new test prerelease.

## Acceptance and testing
- QA compares generated workbook to the original reference in styling, theme, fixed column widths, column header styles, six tables, row heights, real in-cell image metadata, valid CRC and XML structure.
- Chromium integration/frontend, HACS, Hassfest, backup and historical data tests are also required to pass.
- Native Place in Cell rendering in *your* Microsoft Excel, plus visual comparison of the actual HA export, remains a live acceptance check. These cannot be declared complete solely through OOXML tests.
