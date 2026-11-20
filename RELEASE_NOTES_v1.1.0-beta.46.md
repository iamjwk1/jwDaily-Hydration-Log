# jwDaily Hydration Log v1.1.0-beta.46 — Reference Excel export

New six-sheet export layout based on the uploaded **20261120-1703** Excel reference. Exported values always come from the selected real Home Assistant profiles, catalog and saved drink history; no user sample data is embedded in the integration.

## Excel formatting and layout
- Six tabs: **Hydration log**, **Daily intake**, **Settings - Liquid Types**, **Settings - Cup types**, **Settings - Quick buttons**, **Settings - Profiles**.
- **All data rows 18pt**, all cell styles **vertically centered**, **Hydration log header 38pt**.
- **Daily intake** fixed metadata widths; only dynamic Liquid type columns use computed content-based widths with `bestFit` metadata. Last liquid column remains Other.
- Each sheet has an independently sortable/filterable Excel table with the reference's headings/positions. Export date remains left-aligned. Existing unit conversions, cup used label, metadata and target formulas are retained.
- **Liquid icons are genuine Microsoft Excel "Place in Cell" images** stored via `xl/metadata.xml`, rich-value parts and image-media relationships, exactly the same class of Office XML used by the supplied workbook. They are **not floating pictures** or remote IMAGE formulas. A valid native in-cell image has a rich-value metadata index and a cached fallback value; Excel versions supporting Place in Cell render the picture itself.
- Empty catalogs produce valid table headers/empty data rows. A current liquid used by historical records remains represented in the native catalog export.

## Compatibility and safety
- No changes to hydration measurement, Quick buttons, profile settings, original record IDs or recorder / database data.
- **Excel for Microsoft 365 / versions supporting Place in Cell** is needed to display native in-cell pictures. Other spreadsheet viewers may not render them (the user's example uses the same Excel-rich metadata).
- Export XLSX is generated in memory only; no live data is stored in the release ZIP.
- Earlier import/export, ZIP full backup/restore, unit conversion and safety guards unchanged.

## QA
Six-sheet workbook source tests validate all six table definitions, all row heights, vertical style alignment, column-width policy, per-sheet content headers, `vm` image references, image metadata/relation counts, actual PNG dimensions, no floating DrawingML, ZIP CRC and native Python/JS plus HACS/Hassfest.

Live Home Assistant data/history acceptance remains open, as does a manual opening in your desktop Excel to confirm exact visual rendition.
