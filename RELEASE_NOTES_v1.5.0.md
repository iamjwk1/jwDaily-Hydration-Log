# jwDaily Hydration Log v1.5.0 — stable release

Date: 21 November 2026. Supersedes the v1.1.0-beta.48 prerelease line.

## Scope

- Promotes the current native hydration integration and its six-sheet Excel report to the stable 1.5.0 release.
- In **Settings - Profiles**, the existing eight columns (Profile, Profile ID, Age, Gender, Unit, Daily target mL, Target override mL, Quick button count) are preserved. Two columns are appended to the right:
  - **Show Quick buttons** (Yes / No).
  - **Show Liquid types and Cup types** (Yes / No).
- These values reflect the real per-profile **Edit profile → Add drink moment** switches; missing values in older profiles default to Yes, as in the running integration.
- The Profiles table expands from B8:I to B8:K and preserves filtering, formatting and the thin outside border. Other five worksheet contents are unchanged when only the two visibility options differ.
- Dashboard-card-level visual options (such as Show glass, Show history and Show Excel export) are **Lovelace card configuration**, not profile settings; they are deliberately not presented as profile settings.

## Preservation and verification

The patch does not alter user records, archives, targets, Cup/Liquid/Quick catalogs, profile storage format, Full Backup ZIP, settings import or data restore. Regression coverage validates profile-specific combinations, legacy defaults, three-profile exports, workbook XML, ZIP CRC, source immutability and byte-parity of the other five sheets. Existing beta.46–48 Excel style/icon regression suites and Home Assistant/HACS validation remain release gates. Desktop Excel display of native Place in Cell icons still needs live practical acceptance.

## Installation

1. Create a Home Assistant backup and download a verified **Full Backup ZIP** from jwDaily Hydration Log.
2. Select **v1.5.0** in HACS → jwDaily Hydration Log → Redownload → Need a different version.
3. Restart Home Assistant Core, refresh the browser and confirm the card footer and About show **v1.5.0**.
4. Export All profiles and inspect **Settings - Profiles** columns J and K. Verify they match both profile toggles for each profile. Also verify the six tables and in-cell graphics in desktop Microsoft Excel.

## Future version numbering

v1.5.0 is stable. The next development versions use **v1.5.1-beta.1**, **v1.5.1-beta.2**, ... (not continuation of the v1.1.0 beta numbering). Future stable patch releases use v1.5.1, v1.5.2, etc.

## Distribution

GitHub release assets contain a verified ZIP and the matching SHA-256 checksum file. The release workflow must pass native regressions, HACS and hassfest before creating the stable (non-prerelease) release. Existing release tags are never overwritten.
