# Beta.42 implementation and release contract

**Source of truth:** User acceptance screenshots and requirements, 15 Nov 2026, following v1.1.0-beta.41. Baseline is the latest `main` at branch creation; do not overwrite beta.41.

## Goal and non-goals
Apply only visual acceptance fixes below. Preserve Home Assistant Core compatibility, profile IDs, exact drink record IDs/timestamps, canonical millilitre values, dashboard behaviour, exports, all ZIP manifest/checksum and selective restore safety guards, and existing JSON endpoints used internally. No migrations or destructive data writes; no unnecessary refactors.

## Exact dialog requirements

### Edit profile
1. Title `Edit profile - <profile display name>` (HTML escaped; Add profile retains Add title).
2. One compact upper row of Profile name, Age, Gender, Units and Daily target in that order. Inputs size to content, labels untruncated, responsive stacking on narrow phones.
3. Remove horizontal dividers; Quick Buttons section below compact input row.
4. Replace Quick buttons text Edit control with the existing small pencil icon button; hover title/accessible label `Edit quick buttons`.
5. Show Quick Buttons in the persisted maintenance order, with the established full-colour pill rendering (do not alphabetically sort); no changes to drink or profile data.

### Maintain liquid types
1. Dialog and content width follow intrinsic column widths; remove yellow-marked excessive empty gaps.
2. `Liquid type` header aligns with names (not the icon); use one shared grid track definition for header and every row.
3. Times-used count centered under `Times used`; the count remains numeric and accurate.
4. Keep 8px gap between icon and name.
5. Preserve icon-only actions. Accessible hover text on both move arrows.

### Edit liquid type
1. Render the *configured icon colour* identically in the live pill preview, selected-icon sample and shared Choose icon dialog. Do not substitute liquid/button background colour.
2. Place icon colour picker immediately right of icon selector; add `Default` control resetting icon colour to black `#000000`. The selected colour is persisted only on Save.
3. Liquid name input normal font weight and 1px normal control border/focus treatment (no heavy black outline at rest).
4. Preview updates immediately for icon/colour/name, Cancel does not persist.

### Maintain cup types
1. Remove yellow-marked empty horizontal gap; shrink dialog to required column widths.
2. `Cup type` header aligned with cup-name text, not icon; default volume and Times used values centered under the corresponding headers.
3. Preserve icon action parity with Maintain liquid types and delete guards.

### Edit cup type and Choose icon
1. Add icon colour picker beside `Choose icon`, with colour state tied to the cup's saved `icon_color` (never inferred from liquid color).
2. Icon sample in Edit cup type and Choose icon must use the same configured colour. Default fallback black `#000000`.
3. Shared picker remains HA/MDI or SVG, never both; no change to validation, Apply/Cancel or safe SVG handling.

### Data & Backup
Make `Export Excel` and `Create backup` buttons equal width. Preserve three workflows, preview, explicit confirmation and restore scopes. Do not re-expose independent JSON UI.

### Delete liquid type
Remove sentence `Only unused custom types can be deleted.` from confirmation body. Keep type name and irreversible-action confirmation. Dialog should shrink accordingly. Backend deletion guards unchanged.

### Edit Quick Buttons
1. Remove yellow-marked excess empty horizontal gaps; shrink dialog to column content.
2. Shared header/row grid tracks. Align `Liquid type` header over liquid name, center cup-name and volume values under their headers.
3. Replace text actions with small icon-only move up/down, visibility eye, edit pencil, delete bin, same button size/hover/disabled styles as Maintain liquid types.
4. Remove horizontal row dividers; preserve user-maintained order and per-profile ownership and deletion semantics.

## Acceptance and release gates
- Real Chromium browser tests include 390, 768, 1280 px widths; assert key heading/row X alignment, absence of horizontal overflow, no row/button overlap, pill ordering, correct icon colours.
- Test colour preview and picker roundtrip, that Cancel preserves original, and that no profile/drink write is triggered by UI preview.
- Native Python + JS syntax; existing XLSX and ledger/backup/migration regression; HACS and Hassfest; checksum-validated ZIP with CRC and SHA-256.
- Publish `v1.1.0-beta.42` only after green gates. Upload exact ZIP (spaced filename) to persistent File Library, re-fetch and verify hash before delivering FileNavList.
- Stable version remains unchanged; live Home Assistant acceptance and four historical-data/import/backup checks remain explicitly open.
