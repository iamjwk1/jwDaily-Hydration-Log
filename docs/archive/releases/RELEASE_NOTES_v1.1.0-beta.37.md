# jwDaily Hydration Log v1.1.0-beta.37 — Profile units, icon-first editors, simplified settings

## What changed

- **Chosen design:** `07 Icon-first compact` for Edit Liquid Type. Uses the actual native Home Assistant `ha-icon-picker` library: search by name/alias, choose a visual MDI icon, Apply/Cancel. The same visual selector is used for Cup Types and profile-specific Quick Buttons. Liquid Types retain validated SVG upload and a live preview.
- **Profile-specific units:** mL, L, US fl oz for the main card, cup/quick display, drink editing and chart labels. Internal records and targets remain stored in mL; changing a display unit never modifies past drink history. A historic drink opened and saved without changing its volume retains the exact original mL value.
- **Edit Profile:** shorter inputs and an embedded, visually consistent Quick buttons section. The Quick manager belongs to the selected profile, not a global setting.
- **Manage Quick Buttons:** named `Edit Quick Buttons - <profile>`, icon/Liquid/Cup/volume/action columns, compact rows, no secondary details or row dividers. Quick-button icon overrides are validated and saved per profile.
- **Liquid Types:** compact manager, aligned Delete placeholders, used-reference safety, Hide retained and no row dividers. `Use default color` resets only color.
- **Maintain cup types:** icon column, vertically centered cup volume / Used counts, compact rows and icon picker.
- **Settings:** four direct destinations, no Active card profile block or Advanced submenu. Import & Export presents the principal actions first, with conditional details for importing/restoring. Migration/rollback controls are removed from normal Settings, while original backups and secure recovery APIs remain intact.
- **Card footer:** only `Export to Excel (.xlsx)` and a single-line version. A separate export dialog selects `All profiles` (default) or one specific profile.
- **Excel:** four-sheet workbook retained; a single-profile export formats targets, volumes, and cup sizes using that profile's selected unit. A mixed-profile export keeps a normalized mL basis *and* adds explicit profile-unit columns; no unlabelled mixed-unit totals. All historic records and global Liquid/Cup catalogs remain accessible; Quick icon overrides are exported. Existing 44 pt rows, Cup used format, Other-last ordering, and embedded Liquid icons are retained.

## History & migration safety

- No destructive migration in beta.37. The global Liquid/Cup catalog, stable IDs, v3/v4 backup and recovery implementations are retained.
- Existing stored profile Quick Buttons remain compatible because the new icon override is optional.
- No back-end drink-history rewrite, record renumbering, automatic restore or cleanup is performed by this release.
- Existing Lovelace `unit` remains accepted in configuration for backwards compatibility but **does not override** the attached profile's unit.

## Installation

1. Save your Home Assistant full backup and retain your original pre-migration ZIP.
2. Install beta.37 via HACS, restart Home Assistant Core, then refresh the dashboard with Ctrl+F5.
3. Verify the card reports `v1.1.0-beta.37`, test icon picker and profile units, and export a fresh Excel workbook.
4. The migration/rollback actions are deliberately absent from normal Settings. Contact the maintainer for recovery assistance if needed; do not delete the backups.

## QA requirements

- Native Python tests include mixed-unit Excel export (mL, L, fl oz), worksheet/XML integrity and ZIP CRC.
- Chromium interactively checks Settings, icon-library selection and Excel dialog at seven widths from 360–1400 px.
- HACS, Hassfest and legacy migration/history regression workflows must be green on the release commit before tagging or publishing.