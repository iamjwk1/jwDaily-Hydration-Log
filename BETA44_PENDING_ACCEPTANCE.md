# beta.44 — still open after test-release build

## User feedback now implemented

- Add drink visibility per profile (Quick Buttons and/or Liquid/Cup Types, defaults enabled) — implemented; live acceptance pending.
- Custom amount / Date / Time aligned and equal height — implemented; live acceptance pending.
- Cup maintenance: remove redundant Hidden status text — implemented; live acceptance pending.
- Quick maintenance: remove redundant Hidden status text — implemented for consistency; live acceptance pending.

## Four earlier data-safety acceptance items — OPEN until checked in live Home Assistant

1. Preserve historic drink events and original record IDs.
2. No unintended volume changes or modifications to day archives.
3. Import/export settings and drink history behaves correctly.
4. Migration backup and restoration facilities remain intact and recoverable.

These are **not failures** in beta.44 but cannot be certified from fake-HA tests alone.

## Remaining technical maintenance debt — deferred, no unsafe bulk cleanup

- CSS consolidation: hundreds of historical `!important` overrides; need baseline screenshot and mobile regression prior to refactor.
- Old GitHub release workflows and version-specific ApexCharts examples: archive/retire cautiously without rewriting published tags or migration guides.
- Legacy v3/v4 migration, rollback and hidden JSON endpoints: do not remove until startup/older-backup compatibility and rollback testing prove they are unused.
- Actual Home Assistant Lovelace dashboard YAML and production datastore not mounted in this session: obtain read-only export before claiming full live dashboard audit.

No arbitrary config files or live HA records were changed. Stable v1.0.2 remains unchanged.
