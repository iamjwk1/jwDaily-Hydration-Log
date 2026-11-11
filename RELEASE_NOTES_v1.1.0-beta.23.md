# jwDaily Hydration Log v1.1.0-beta.23 — HACS pre-release

Full integration built on the validated v1.1.0-beta.22 release. beta.22 is retained unmodified as the rollback version.

## FIX-01 through FIX-08
- Main-card intake is 19px; target and remaining text are each 17px regardless of card width. The intake remains right-aligned without overlapping the glass.
- The version is right-aligned lower in the card footer; the existing compact Excel button, five-row history and layout are retained.
- Main *Today by liquid* dots and horizontal fills use the actual effective liquid-type colors; the unfilled track stays neutral.
- *Edit liquid* includes a native HTML picker, uppercase `#RRGGBB` input, synchronized preview, strict validation and **Reset to default**. Cancel does not save.
- Custom colors color the liquid choice background with contrast-aware text/icons, and are also used in hourly and weekly stacked charts, legends and details; selected and focused states remain distinguishable.
- Profile-isolated `liquid_colors` overrides are stored by stable liquid ID. Old profiles use exactly the beta.22 color behavior by default; existing records are never migrated or rewritten. Names, order and historical entries are preserved.
- Excel keeps four sheets and existing formula/date/width/44pt header rules while adding a `Color` hex column and matching fills only to the liquid-type settings section. Historical-only types and colors are retained.
- No changes to existing drink history, add/edit/delete, calendar, volume buttons, or chart scales.

## Validation and limitations
- Python, backend persistence, OOXML, browser rendering and color workflow tested, including 280–880 CSS pixel card widths.
- GitHub CI includes source syntax/tests, HACS and Hassfest gates before publication.
- Install through HACS as an integration prerelease and refresh the card frontend resources; a Home Assistant Core restart may be necessary for changed backend code.
- A true live Home Assistant installation with user data remains subject to owner acceptance testing; offline Chromium verification is not equivalent to live HA acceptance.
