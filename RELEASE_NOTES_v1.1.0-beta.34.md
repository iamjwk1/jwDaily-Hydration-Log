# jwDaily Hydration Log v1.1.0-beta.34 — Consistent dialog UX

## User-requested UI review and corrections
- Cup types: uniform, compact rows with name, default volume, **Used: N** (historical drink moments across all profiles) and **Up / Down / Hide / Edit / Delete** on one aligned action row. Buttons never wrap into separate vertical columns; narrow displays place the *whole* action group below the information as necessary.
- Liquid types: narrower dialog, identical single-row action bar and **Used: N** for visible and hidden liquid types. Suppress the duplicated heading. Show **Back to settings** on the left and **+ Add liquid** on the right. **Back to drink** is offered only when management was opened from Add drink.
- Manage profiles: align the profile icon, name, slug and personal goal together on the left with **Edit** at the right, matching the agreed reference composition. **+ Add profile** is right-aligned in the footer.
- Profile editor: a distinct modal layered over Manage profiles. Inputs remain profile-scoped: daily target, age, gender and units. Source mode, source sensor, pregnancy and lactation remain removed. Quick-button management is accessible through the profile editor rather than the global Settings menu.
- Liquid, Cup and Quick editors: Edit / Add opens a separate, smaller modal above the unchanged list; Cancel, Close or Escape restores the same list with no write.
- Delete confirmation for Liquid, Cup and Quick also uses a top-layer modal, with consistent heading and Cancel / Confirm buttons.
- Quick-button dialog: compact, uniformly aligned action buttons, more space for labels, profile-aware navigation back to the originating profile and consistent Back/Add footer.
- Shared dialog styles: compact widths, responsive layout, accessible labels, keyboard Escape and focus outlines. Input validation errors are visible in the active editor.

## Confirmed retained behavior
- No change to backend storage schema, migration v3 data, immutable rollback backup, historical drink records or Excel workbook data; changes are UI and version metadata only.
- Shared Liquid/Cup catalogs are retained across profiles; their use counts and deletion locks are calculated from every profile's historical drinks.
- Used Liquid/Cup types cannot be deleted; Hide remains available. Unused custom types may be deleted, and Quick buttons may always be deleted without deleting drink records.
- Personal daily targets and quick buttons remain profile-scoped. New profile target remains 2000 mL/day.
- Existing Excel scope dropdown (All profiles default or single profile), workbook structure, cup used formatting, Other-last, icons and historical data remain in place.
- Legacy data is *not* removed by beta.34; Release 2 cleanup remains separate.

## Upgrade and validation
1. Keep the existing v3 pre-migration backup safely stored.
2. Update to beta.34 through HACS, restart Home Assistant, refresh the browser with Ctrl+F5.
3. Verify the bottom-right card version is beta.34; open Settings and inspect Cups, Liquid types, Manage profiles and profile-specific Quick buttons.
4. Verify the displayed Used counts against historical data; Edit/Cancel should leave the underlying list in place. Check ZIP backup and Excel if desired.
5. **Do not use Rollback migration unless a separate migration recovery is needed.**

Source QA includes Python v2/v3 migration and Excel regression, Chrome/Chromium responsive browser automation at five viewport widths, HACS and Hassfest gates. Release ZIP is byte-checked, CRC-checked and SHA-256 verified.
