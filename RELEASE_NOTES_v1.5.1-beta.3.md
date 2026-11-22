# jwDaily Hydration Log v1.5.1-beta.3 — Settings footer Close

**Prerelease: 22 November 2026.** Stable v1.5.0 and earlier betas remain available, unchanged.

## Change

A **Close** button is now visible at the **bottom-right of the main Settings dialog** on every Settings page: Settings Home, Manage profiles, Maintain liquid types, Maintain cup types, Edit Quick Buttons and Data & Backup.

- The **Close** button invokes the same existing action as the top-right close (✕), exiting Settings without editing saved data.
- Existing **Back to settings**, **Back to profile**, **+ Add profile**, **+ Add cup type**, **+ Add liquid type**, and **+ Add Quick button** controls remain functional.
- On Settings Home, the Close button appears alone at the bottom-right.
- This is the main Settings footer, **not** the child editor's Cancel/Save footer. Child editor behavior is preserved.
- Previous v1.5.1-beta.2 profile-save fix and v1.5.1-beta.1 Excel improvements are retained.

## Verification

Automated Chromium regression tests cover Settings Home, Data & Backup, Manage profiles, Maintenance, Close and reopen behavior, footer right alignment and seven browser widths. Existing storage, backup/restore, Excel regression, HACS and hassfest checks remain mandatory before publishing. A release ZIP is CRC-checked and distributed with a SHA-256 file.

## Installation

1. Back up Home Assistant and the integration's hydration data.
2. In HACS → jwDaily Hydration Log → Redownload → Need a different version → select **v1.5.1-beta.3**.
3. Restart Home Assistant Core and refresh the browser.
4. Open **Settings**. Confirm the **Close** button appears at the bottom-right of the dialog. Navigate to Manage profiles, then click **Close**; the entire Settings dialog should close without modifying the profile.

This release has no storage schema, migration, intake ledger, Excel, or backup changes.
