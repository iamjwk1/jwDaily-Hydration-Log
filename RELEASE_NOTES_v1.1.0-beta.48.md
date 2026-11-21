# jwDaily Hydration Log v1.1.0-beta.48 — Excel table outlines and cell graphics

Beta.48 is a focused test prerelease based on beta.47. It addresses three concrete issues visible in the exported screenshots from 21 November 2026.

## Corrected Excel output

1. **All six table borders:** complete rectangular outside border of the same *thin* stroke and automatic black color (indexed 64) as the existing interior row lines. The formatting preserves existing fonts, number formats, HA liquid-color swatches and data-row heights.
2. **Settings - Cup types:** the existing **Icon graphic** column is now populated with actual native Excel **Place in Cell** image values, not floating overlays.
3. **Settings - Quick buttons:** a new **Icon graphic** column is inserted immediately after **MDI icon** and before **Order**. Actual native in-cell icons use the button's selected icon, otherwise the linked Liquid Type's icon, then the linked Cup's icon as fallback. The icon color is inherited from the selected icon or linked liquid when available.

## Additional consistency fix

The Quick buttons table range no longer reuses the unrelated Profile row counter. Table rows, auto-filter ranges, borders and the bottom-of-table bound are now calculated independently.

## Unchanged

- The six worksheets and previous reference-derived formatting, table filters, vertical center alignment, 18pt data rows and 38pt Hydration log header.
- Dynamic Liquid Type column sizing in Daily intake, original technical IDs from Home Assistant, recorded drink volumes, timestamps and archives.
- Profile settings, importer and full ZIP restore. No schema or migration changes.

## QA

Excel OOXML regressions verify all four thin black perimeter edges on all six tables, correct Cup/Quick image cell coordinates, rich-value indices and PNG relationships, the new Quick column order/widths, CRC, count of six filterable tables and unchanged source data. Existing storage, import/export, browser/Chromium, HACS and Hassfest checks remain required.

**Live acceptance pending:** please open a real beta.48 export in desktop Microsoft Excel and confirm the black outlines and image rendering. Native Place in Cell display requires a compatible Excel version.
