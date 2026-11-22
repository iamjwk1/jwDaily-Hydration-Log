# jwDaily Hydration Log v1.1.0-beta.43 — Code and dashboard audit

Audit date: 2026-11-16. Source: repository main after merging accepted PR #22; reviewed local reproducible beta.42 HACS ZIP and GitHub source for beta.43; CI provides regression and browser evidence.

## Scope
- 14 Python integration modules (config flow, coordinator, storage, migration, Excel, events, services, sensor and number entities, frontend loader).
- Lovelace JavaScript bundle: main hydration card, hourly chart, last-seven-days chart, dialogs, icon picker, restore UI and CSS.
- HACS/manifest/version consistency; release packaging; ZIP verification; automated tests and change history.
- **Not inspected**: the live Home Assistant database, historical user data, runtime logs, browser caching, or a separately maintained Lovelace dashboard YAML. These require an explicit current read-only export from the installation. CI fake-HA Chromium tests are not equivalent to live runtime evidence.

## Confirmed findings addressed in beta.43

| ID | Priority | Finding | Resolution |
|---|---|---|---|
| F01 | High | Hourly chart reads target sensor *state*, already converted to L or fl oz, then formats it again as though it were mL. A 2000 mL target displayed by HA as 2 L could render as 0.002 L or rounded 0 L. | Prefer sensor `target_ml` attribute. Convert native unit back to mL only if the attribute is missing. Chromium assertions for L and fl oz. |
| F02 | Medium | Chart profile-settings history request uses UTC `toISOString()` date, not HA configured timezone. Near midnight it can request the previous local day. | Use a timezone-aware YYYY-MM-DD helper; test Europe/Amsterdam versus Europe/London boundary. |
| F03 | High | Data import's date/ledger timestamp validation uses host OS `date.today()`. In Europe/Amsterdam around midnight, a valid local-day record can be rejected as tomorrow on a UTC host. | Thread coordinator's HA-local day into the import validator. Regression for past/current/future dates. |
| F04 | Medium | README advertised beta.31 as the current beta and included old menu/migration instructions as if current. | Updated to beta.43, linked current notes, marked older instructions archival. |
| F05 | Low | Edit Profile dialog had 200 CSS px of unnecessary right whitespace. | PR #22 reduced maximum from 940 to 740 CSS px. Chromium layout regression verifies no clipping. |

## Reviewed controls, with caveats
- Data model: canonical mL, stable ledger IDs, explicit Quick/Cup references; non-destructive historical export/import guards in source.
- ZIP restore: limited input/archive member sizes, ZIP CRC, SHA-256 manifest, authenticated admin-only WebSocket actions, preview and explicit apply, profile scope/revision checks and rollback path.
- Excel: existing four-sheet export tests and unit conversion regression retained.
- Liquid/Cup/Quick: catalog validation, used-type deletion guards, icon-color/SVG validation and per-profile quick button controls.
- Frontend: renders names using escaped text in dynamic HTML; relevant icon and chart inputs constrained. There is no evidence of an untrusted remote JavaScript dependency in the packaged card.
- UI: responsive Chromium checks exist for 360–1400px (not exhaustive browser/device coverage). Hourly and weekly chart code reviewed; extra chart target/date regressions added.

## Technical debt / cleanup proposals (not removed in beta.43)

| ID | Priority | Finding | Recommended next step |
|---|---|---|---|
| D01 | Medium | Large JS bundle (~2,425 lines in beta.42) contains ~369 `!important` CSS overrides and multiple sequential beta-specific CSS patches. Visual fixes are difficult to reason about. | Refactor into one canonical set of scoped styles after capturing golden snapshots at desktop and mobile widths. Separate change/release. |
| D02 | Medium | 42 historical publish-workflow YAML files remain in `.github/workflows`; previous release workflows still evaluate on new pushes, creating duplicate CI jobs. | Safely retire obsolete push triggers and preserve release history/artifacts. Run workflow matrix QA. Avoid deleting GitHub tags. |
| D03 | Low | 19 versioned ApexCharts example Markdown files and many release notes are near-duplicate archived documentation. | Consolidate to a current example plus archived history, without changing published release assets. |
| D04 | Medium | Standalone Settings/Data JSON dialogs were hidden, but corresponding UI handlers and backend endpoints remain. Backend ZIP and compatibility workflows depend on some JSON code. | Map every reference with code coverage and only remove proven unreachable UI logic; retain internal transfer and restore contracts. |
| D05 | Medium | Legacy v3 migration, v4 cleanup and rollback logic remains after historical conversion. It may still be essential for older installs and disaster recovery. | Do **not** delete without verifying startup conditions for older migrated profiles, backups and rollback; add lifecycle integration tests first. |
| D06 | Medium | Existing CI uses mock Home Assistant for UI. No integration test currently executes against the user's actual Lovelace YAML, installed themes/HACS frontend versions and historical data. | Obtain read-only dashboard YAML + sanitized backup/test profile and validate with Home Assistant staging installation. |

## QA and acceptance
New release gate: `compileall`, JS syntax, existing ledger/migration/Excel tests, selective ZIP restore tests, timezone validator test, Chromium main-card/dialog and hourly-chart unit/date assertions, HACS and Hassfest. ZIP CRC, all member bytes and SHA-256 are checked in the release workflow.

**Verdict:** beta.43 corrects reproducible chart and import defects and one accepted UI issue. No live-data loss or schema migration is intended. Remaining D01–D06 are documented maintenance items, **not** claims that they are safe to delete. Four prior open live acceptance items (historical data/IDs; volume/archive integrity; import/restore; migration backup recovery) remain pending.

No statement in this report implies that the actual installed Home Assistant dashboards have been verified, nor that live data restoration has been performed.
