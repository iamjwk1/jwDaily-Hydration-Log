# jwDaily Hydration Log v1.1.0-beta.45 — Add drink dialog overflow fix

This is a **test prerelease** based on beta.44. Only the modal sizing and its regression checks are changed.

## Fixed
- The **Add drink moment** dialog no longer uses manual-input grid tracks totaling 748 CSS pixels inside a 660px-wide modal. This caused an unwanted horizontal scrollbar and clipped Time field.
- The Custom amount / Date / Time fields have compact content-appropriate widths (165 / 190 / 145 CSS px plus two 10px gaps) and retain the same 50px control height, with responsive layout on tablet/mobile.
- Chromium tests now assert the dialog never has `scrollWidth > clientWidth` and all three controls remain inside its right edge at tested mobile, tablet and desktop widths.

## Unchanged
- Per-profile show Quick Buttons / Liquid Types & Cup Types preferences.
- Visibility status shown by eye/eye-off icons without redundant Hidden text.
- Original drinks, record IDs, historical totals, daily archives, Excel and full ZIP restore.

## Validation
Native Python, JavaScript, historical storage/migration, Excel, profile settings/backup and restore regressions, Chromium UI, HACS, Hassfest, deterministic ZIP integrity checks and SHA-256.

**Open live-acceptance checks:** historical records and IDs; volume/archive integrity; import/export of settings and drink history; migration backups/rollback. Legacy cleanup and live installed Lovelace configuration validation remain separate from this targeted test release.
