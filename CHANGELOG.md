# jwDaily Hydration Log — changelog

## v1.1.0-beta.3 (HACS pre-release)
- Save now verifies the running Python backend version first. Stale backends produce a restart instruction instead of generic `Unknown command` and no partial write is attempted.
- Add/Edit popup now has a complete calendar picker displaying `DD-MM-YYYY`; time remains in 24h format.
- New current-day liquid-by-type bar chart. Main card displays blue consumed volume aligned with animated fill, red target label and black remaining volume inside glass. Target line stays ~15 px lower and glass rim open.
- Remove redundant totals beneath history; compact Excel export button.
- Built-in Wine type and cow, soup-bowl and ordinary water-glass icons; Excel daily breakdown includes Wine.
- All profile data and existing v1.1.0-beta.2 registrations remain stored unchanged. Release via HACS only.

## v1.1.0-beta.2 (HACS pre-release)
- Compact glass/history/Add card; same Add/Edit popup; larger liquid icons.
- Custom liquid types with name, MDI icon or SVG file, and optional default volume, stored per profile.
- Automatic volume preselection only after selecting a custom type with a configured default.
- Red dashed 100% target line moved approximately 15 px lower (SVG y=39); level animates to it and the water surface gently ripples.
- Card version shown bottom-right.
- Excel extended to eight sheets including complete Liquid Types catalog, plus human-readable liquid names and custom-type breakdown.
- Existing v1.0.2 and beta.1 data retained; no separate edit/delete history.
- HACS-only distribution. No changes to upstream Personal Hydration Manager.

## v1.1.0-beta.1
- Explicit liquid and volume, popup edit/delete, backdated records, Dutch date + 24h time.
- Pace removed, compact open glass, seven-tab Excel export, Undo last drink.

## v1.0.2
- First stable independent release with timestamped history and complete Excel export.
