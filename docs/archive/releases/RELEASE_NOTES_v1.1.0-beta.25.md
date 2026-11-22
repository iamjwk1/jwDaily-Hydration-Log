# jwDaily Hydration Log v1.1.0-beta.25

**Official HACS prerelease candidate. Base: complete beta.24.**

## Highlights

- New guided **Convert existing data** in Settings → Advanced: review old liquid IDs and volumes, create named Cup types, map historical Liquid/Cup IDs and generate Quick buttons. An explicit downloadable profile backup, revision check and two-step confirmation precede applying changes. Existing drink records and total consumption are never rewritten. Same-Liquid confirmed cup defaults are stored without guessing from individual volume amounts.
- New **Settings import / export** (JSON): includes Liquid, Cup and Quick button definitions, personal liquid colors, prior volume button configuration, target override and same-profile historical mappings. Does *not* export drink records, user data logs, sensor readings or Home Assistant IDs. Import is validated against an independent schema, with a summary of changes, a target profile and expected-revision check. Import into another profile does not copy historical mapping records.
- Manage profiles inside the card: add a profile through Home Assistant's native config flow, optionally copy Liquid/Cup/Quick settings from an existing profile; edit profile display name and preferences without changing the stable profile slug. Histories and personal daily targets are never copied.
- Main card: Settings left and Add drink right on one bottom row, both with MDI icons; full single-line labels and narrower bars in Today by liquid; accurate 19/14/14 px intake/target/remaining labels, including remaining volume at 97% full.
- Add drink: one Settings control at lower-left; obsolete Manage liquid/legacy volume buttons removed from the normal input workflow. Access to old volume configuration only in Advanced before conversion. Manage navigation is compact and neutral.
- Existing chart cards, four-sheet Excel formulas, cup animation, five-row scroll history and HH:MM display remain unchanged; actual historic amounts and seconds remain stored.

## Safety and migration

1. Upgrade from beta.24 using HACS and restart Home Assistant Core if required by the running-backend version guard.
2. Open Settings → Advanced → Convert existing data; review suggested cups and mappings. The wizard never applies guesses silently.
3. Download and *independently verify* the raw profile backup before confirming conversion. Only then apply; all historical records must be preserved.
4. For settings transfer, download JSON from the source profile, choose it on the target profile, inspect the preview and explicitly confirm. Only configuration settings are replaced, never drink history.
5. Keep beta.24 installed ZIP/tag and raw profile backup for rollback. Live HA acceptance is still required.

## QA contract

Python syntax, legacy backend regression, beta25 storage/conversion/settings/API regression, real Chromium responsive and popup interaction tests, valid four-sheet XLSX/CRC, HACS, Hassfest, and deterministic release archive/sha256 must all succeed before prerelease publication.
