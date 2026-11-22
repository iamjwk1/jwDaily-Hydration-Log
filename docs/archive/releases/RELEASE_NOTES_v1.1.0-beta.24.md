# jwDaily Hydration Log v1.1.0-beta.24

**Official HACS pre-release. Upgrade from beta.23; beta.23 remains the rollback point.**

## New profile-scoped model

- Separate **Liquid types** (stable ID, name, icon and color) from user-maintained **Cup types** (stable ID, name, icon and default volume).
- Configure **Quick buttons** linking one Liquid and one Cup. Automatic labels follow `Liquid (Cup)` and dynamically update after renames; optional custom labels stay unchanged after renames. Quick button labels are presentation only.
- Recorded drink volumes remain independent of later cup-default changes, and original timestamps retain seconds.
- Add drink supports Quick button presets and independent liquid/cup selection. Historic volume buttons remain available as a safe legacy fallback.

## Safe migration and aggregation

- **Settings → Migration preview** proposes—but never automatically applies—legacy aliases (e.g. `Water (beker)` and `Water (glas)` → `Water` + optional Cup). Review source/target IDs, counts, volume and color conflicts.
- Download and independently verify a raw per-profile JSON backup before confirming any mapping. Historical ledger IDs, amounts and timestamps are never rewritten. Alias mapping is reversible and survives restart.
- All liquid bar charts, hourly, weekly, legend and Excel daily aggregations group by the canonical **Liquid ID/name**, never Cup or custom Quick button label. Cup details remain visible in history.

## Main card and settings

- Keep blue intake at 19 CSS px; reduce target and remaining labels to 14 px and preserve cup proportions, movement and overflow safeguards.
- Long names in **Today by liquid** wrap instead of being cut off; bars compress while their displayed volumes remain aligned to the right.
- Colorize liquid icons in Manage Liquid types instead of adding colored dots; keep accessible contrast for Liquid choice buttons and all charts.
- Central gear **Settings** entry with Profile, Daily target, Liquid types, Cup types, Quick buttons, Migration preview, Export and About. Profile settings link to the existing HA integration options flow.

## Excel

- Exactly four retained worksheets: `Hydration log`, `Daily intake`, `Settings - Liquid Types`, and `Settings - Volume Buttons`.
- Hydration log appends Cup, Quick and original legacy-ID information; Daily intake shows canonical Liquid totals; the fourth sheet contains legacy buttons and separate Cup/Quick definitions.
- Retain `Date+time` width 19, Daily intake header row 11 exactly 44 pt, dynamic liquid columns, existing percentage formulas, orange legacy headers and effective hex-color fills. No destructive data migrations.

## Validation & rollback

- Python backend/persistence/migration/Excel tests; real Chromium responsive 360–920 px and UI interaction tests; ZIP CRC/SHA-256; GitHub Actions Source QA, Hassfest and HACS gates all required to publish.
- Beta.23 remains available as a rollback. New beta.24-only settings are not editable in beta.23; original ledger and beta.23 settings are retained.
- Live Home Assistant acceptance with the user's actual profile data remains required after installation.
