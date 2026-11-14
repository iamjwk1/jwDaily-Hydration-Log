# jwDaily Hydration Log v1.1.0-beta.38 — acceptance corrections

Status: candidate on review branch; **not a published HACS release** until CI, browser acceptance and release publication succeed.

Based on user acceptance results for beta.37: 49 accepted, 6 UI failures, 4 independent data/backup checks open; one additional glass-formatting failure was reported subsequently.

## Targeted fixes
1. Edit Profile: narrower age, gender, units and daily-target fields and reduced dialog width.
2. Liquid Types: tighten the horizontal space between icon/name and the global Used counter.
3. Edit Liquid: shorten the hex colour field and remove the redundant colour patch to its right (the actual colour picker remains).
4. Cup Types: render default volume and global Used count in dedicated columns on one line, removing the unnecessary second row.
5. Edit Cup: narrower Cup name, Default volume and dialog.
6. Main card: for mL profiles, values at or above 1000 mL in the left intake label and in-glass target/remaining labels automatically display in litres, e.g. 1000 mL → 1.0 L, 1250 mL → 1.25 L and 2000 mL → 2.0 L. Values below 1000 remain in mL. Other profile units remain governed by their settings.

This change is frontend-only except for synchronized manifest/constant version identifiers. It does not change the canonical mL storage model or backend business logic, and does not intentionally modify the 49 approved features.

## Validation before HACS publication
- [x] JavaScript source parses successfully.
- [x] Code-level checks confirm a dedicated cup-volume field and removed redundant colour preview.
- [x] Code-level checks confirm all three glass labels invoke the new display formatter.
- [ ] Browser visual regression at desktop and 360 px mobile.
- [ ] Complete Python/JS regression tests, Hassfest, HACS validation, CI.
- [ ] Live Home Assistant acceptance.
- [ ] Four open historical-data/import/backup checks.

Do not mark as released or recommend installation until all required publication tests pass.
