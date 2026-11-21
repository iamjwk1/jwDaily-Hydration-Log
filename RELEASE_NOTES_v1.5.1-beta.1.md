# jwDaily Hydration Log v1.5.1-beta.1

Prerelease, 21 November 2026. **v1.5.0 remains the latest stable release**.

## Excel export changes

- Boolean fields in exported Excel data are now legible **Yes / No** rather than native Excel **TRUE / FALSE** values. This includes the **Custom** and **Visible in picker** fields on **Settings - Liquid Types**, without changing the underlying Home Assistant settings.
- **Settings - Cup types**: **Cup Type ID** (column C) and **MDI icon** (column F) now receive widths calculated from the actual longest ID or MDI path, with safe bounds to avoid excessive worksheet width.
- The **MDI Icon** column E in **Settings - Liquid Types** and **MDI icon** column I in **Settings - Quick buttons** use the same content-based adjustment.
- The generated OOXML includes the calculated `width` and `bestFit` metadata; it does not rely on Microsoft Excel to resize a column on first opening.
- All other approved reference column widths and the six worksheet structures, cell styles, header heights, filters, black table borders, rich-value native icons and records remain unchanged.

## Validation

Automated regression tests cover both Boolean cases, multiple profiles, legacy defaults, the maximum Cup ID length scenario, MDI icon paths, unchanged HA source snapshot, six structured tables, native in-cell image packages and CRC integrity. Existing storage/migration tests, HACS validation and hassfest remain release gates.

No database changes, no history or profile mutations, no import/backup changes.

## Install / acceptance

1. Export the integration's **Full Backup ZIP** and make a Home Assistant backup.
2. In HACS choose **v1.5.1-beta.1** and restart Home Assistant Core.
3. Refresh the dashboard; confirm frontend/backend version **v1.5.1-beta.1**.
4. Export to Excel and check **Yes / No** in Settings - Liquid Types, then check Cup Type ID and MDI icon widths in Settings - Cup types.
5. Check that other data, colors, graph bars and six-sheet report formatting still match the accepted v1.5.0 reference.

Next beta is **v1.5.1-beta.2**. This prerelease does not replace the stable v1.5.0 tag or its assets.
