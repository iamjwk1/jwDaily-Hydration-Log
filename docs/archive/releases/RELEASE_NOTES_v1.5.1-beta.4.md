# jwDaily Hydration Log v1.5.1-beta.4 — Restore Preview review

**Prerelease — 22 November 2026.** Stable v1.5.0 and all previous beta releases remain available.

## Data & Backup: four requested improvements

1. **Unambiguous backup file selector**. The upload control has one clear status, **No file selected** or **Selected: <filename>**. The actual file input remains accessible, while its empty native "No file chosen" text is not shown after a successful selection and rerender.
2. **Profile displayed**. Restore preview shows **Restore to profile: <name>**, taken from the actual selected Home Assistant profile.
3. **Actual content comparison**. Preview reports separately **Settings: Identical to current / Different from current** and **Drink history & data: Identical to current / Different from current**. Comparison hashes the *validated restore settings, including profile preferences*, and all saved data, including event IDs, timestamps, volumes, daily archives and sensor readings. It does **not** infer equality from drink counts. When a restore scope excludes one area, that area is marked **Not included** instead. This is read-only and does not change data.
4. **Readable scope labels**. The preview header and confirmation consistently display **Everything**, **Settings only** or **Data only** rather than the internal `all/settings/data` codes.

## Existing safeguards preserved

The ZIP is still checked for member list, CRC, full archive and per-file SHA-256 checksums, schema and matching profile; restore previews remain bound to the selected scope, the source backup and revision hashes. A real restore still requires the safety checkbox plus two confirmation dialogs. No data is restored while reviewing. No storage model, Excel, intake, graph or backup format changes.

## Acceptance checks

- In **Data & Backup**, select a backup ZIP; the selected filename remains displayed consistently after opening **Preview restore**, including on mobile.
- For the same profile, the preview displays the actual profile name and correct scope wording.
- Equal drink counts with differing history still display **Different from current** for Drink history & data. Identical full content displays **Identical to current**.
- Switching to **Settings only** marks Drink history & data as **Not included**; **Data only** marks Settings as **Not included**.
- With the safety checkbox unchecked, Confirm restore stays disabled. Do not run an actual restore for this acceptance check.

Release gated on full native Python and Chromium regression, HACS, hassfest and verified ZIP+SHA256 output. Previous beta.3 code and release are never overwritten.
