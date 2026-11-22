# jwDaily Hydration Log v1.1.0-beta.41

Beta.41 is a narrow UI acceptance correction to beta.40. The persistent storage format, record identifiers, history, Excel export, and safe ZIP Backup/Restore backend are unchanged.

## Corrections
- **Edit profile**: Quick buttons use the same wrapping pill presentation, border radius, color and dimensions as Add drink. The Quick buttons section spans the full editor width.
- **Maintain liquid types**: corrected dialog title; introductory text uses the full available width. Column headings and row content now share identical CSS grid tracks. Redundant horizontal whitespace reduced; 8px between icon and name. Move-up/down buttons include hover tooltips. Existing action icons and safety guards remain unchanged.
- **Maintain cup types**: headings and data share identical column tracks; unnecessary horizontal whitespace reduced. Hide/Show, Edit and Delete now use the same compact icon controls as Liquid Types, with accessible tooltips.
- **Manage profiles**: dialog narrowed to content; profile details and Edit button sit closer together. Unnecessary footer divider removed.
- **Data & Backup**: removes the optional Advanced individual JSON files panel from the UI. Excel, full ZIP Backup and selective ZIP Restore remain visible and usable. Existing JSON-related backend endpoints remain for import compatibility and ZIP internals.

## Safety
- No changes to the drink ledger, source readings, profile IDs or existing snapshots.
- No schema migrations. Current ZIP manifest, checksums, restore scope previews and rollback guards remain intact.
- Earlier user acceptance items involving historical data, import/export and backup verification remain open for live Home Assistant testing.

## QA
Release gated on Source QA, Chromium browser tests, HACS and Hassfest. Browser tests explicitly check table column alignment, action icons/tooltips, quick button pill layout and removal of JSON UI.
