# jwDaily Hydration Log v1.1.0-beta.36 — Compact dialogs and safe startup cleanup

## Updated dialogs (approved visual references)
- **Manage profiles:** compact, approximately 486px wide on desktop. Profile icon, display name and stable slug/target remain left aligned, with Edit to the right. Consistent Back to settings / Add profile footer.
- **Liquid types:** compact, approximately 590px wide on desktop; usage counts, labels and all actions remain logically grouped. Small-screen layouts keep the action buttons together rather than breaking individual buttons.
- **Cup types:** reduced desktop dialog width to approximately 545px, minimal whitespace between the cup name and action controls, no horizontal divider lines between cup rows, and less vertical row spacing. Default volume and historical **Used** count are vertically centered.
- **Edit Liquid Type:** reduced to approximately 468px; shorter liquid name, material icon, filename selector and hexadecimal color controls. A thumbnail of the currently selected MDI/SVG is always shown, and uploading an SVG refreshes the preview immediately. SVG artwork is not lost when cancelling the editor.
- Popup buttons and footer ordering remain consistent with beta.34. Labels and visual content are in English.
- Responsive verification covers 360, 420, 540, 720, 950 and 1400 px screen widths. Browser tests assert correct popup widths, cup-row divider removal, aligned controls, bounded inputs and live SVG upload preview.

## Release 2 cleanup finalization
- In installations with no obsolete fields, migration/cleanup status is now **persistently recorded** as `clean`, `removed_fields=0`, `history_unchanged=true` after readback verification. No unnecessary profile backup or journal is created.
- The Migration v3 status view now shows **Legacy cleanup: Clean · Removed: 0 · History: Unchanged**.
- Once this status is present and all live profile stores are confirmed free of obsolete top-level fields, subsequent Home Assistant starts bypass the one-time v4 cleanup code entirely.
- The unused `SOURCE_MODES` integration constant was removed.
- The migration/upgrade and recovery modules are deliberately retained for installations still upgrading from older releases and for safe back-up/restore. Active global liquid/cup catalog logic is not legacy code and remains in place.
- A partial cleanup, unexpected profile, corrupted status or pending journal never takes the fast path; the protective migration checks remain in force.

## Historical-data and export safeguards
- No drink record, timestamp, volume, daily archive, source history, profile target, profile Quick button or global Cup/Liquid ID is changed.
- The original immutable v3 pre-migration backup and v4 pre-cleanup backup (if one exists) are preserved.
- Excel export structure and profile selection remain unchanged.

## Upgrade
1. Keep your saved v3 pre-migration ZIP and make a fresh Home Assistant backup.
2. Install v1.1.0-beta.36 via HACS; restart Home Assistant and refresh the dashboard with Ctrl+F5.
3. Check the card version, new compact dialogs, and Edit Liquid SVG preview.
4. Under Settings → Advanced → Import & Export → Migration v3, click **Check migration status**. Expected for an already-clean profile: **Status active**, **Backup Verified**, **Legacy cleanup Clean**, **Removed 0**, **History Unchanged**.
5. Confirm drink history and Excel export if you need final end-to-end acceptance. Do not use migration rollback for ordinary updates.

## Test gates
Full Python native storage, migration/rollback, Excel, Chromium multi-width dialog tests, HACS validation and Hassfest; release archive individually content-checked, CRC-checked, and SHA-256 verified.
