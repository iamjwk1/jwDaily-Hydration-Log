# jwDaily Hydration Log v1.0.2

[GitHub source code](https://github.com/iamjwk1/jwDaily-Hydration-Log) · [Report an issue](https://github.com/iamjwk1/jwDaily-Hydration-Log/issues)

Independent Home Assistant hydration integration with per-drink history and admin-only full Excel export.

**Upstream attribution:** based on the MIT-licensed Personal Hydration Manager v0.4.1 by Loryan Strant, https://github.com/loryanstrant/HA-Personal-Hydration-Manager. The original copyright and MIT license are retained; this is **not** an official upstream release or update.

## Isolation guarantees

- New integration domain: `jw_daily_hydration_log` (upstream is `personal_hydration_manager`).
- New card: `custom:jwdaily-hydration-log-card` (upstream is `custom:personal-hydration-card`).
- New sensor IDs: `sensor.jwdhl_<profile>_...` (upstream `sensor.phm_<profile>_...`).
- New services: `jw_daily_hydration_log.log_drink`, `reset_today`, `set_consumed`.
- New event: `jw_daily_hydration_log_drink`.
- New storage: `.storage/jw_daily_hydration_log.<config_entry_id>` (upstream unchanged).
- New Lovelace resource: `/jw_daily_hydration_log_static/jwdaily-hydration-log-card.js?v=1.0.2`.
- Existing config entries, data, dashboards, sensor entities, scripts and automations are **not** changed. This installer does not remove or upgrade the upstream integration.

## Rename from v1.0.0 (important)

Version **v1.0.1** originally introduced the *renamed integration identity*; v1.0.2 changes only the card element/module naming within that domain.
It intentionally uses the **new domain** `jw_daily_hydration_log` rather than modifying
`daily_hydration_log` in place. The earlier v1.0.0 local fork, if installed, is
not deleted, overwritten or migrated. Its `.storage/daily_hydration_log.*` files
remain untouched, and the renamed integration does not silently import old records.
If you already installed and used v1.0.0, do not remove it before creating a
separate backup and agreeing on an explicit data-migration procedure. This
package also leaves the original HACS `personal_hydration_manager` untouched.

## v1.0.2 card naming

The Lovelace element is now **`custom:jwdaily-hydration-log-card`** (no hyphen
between `jw` and `daily`). The JavaScript module is now
`jwdaily-hydration-log-card.js`. An existing **v1.0.1** managed Lovelace resource,
if present, will be updated to the new URL when the integration loads after
an explicitly approved upgrade. The domain `jw_daily_hydration_log`, its
sensors, services, stored history and `.storage` files are unchanged.

**Do not use the v1.0.1 card type** in dashboards after upgrading. Existing
v1.0.1 dashboard YAML is not automatically edited by this installer.

## Features

- One or more independent hydration profiles; targets use upstream NASEM age/gender/pregnancy/lactation table.
- Daily goal, running total, manual total, remaining, pace, percentage and drink-count sensors.
- Optional external source in `absolute`, `delta` or `sum` mode. Manual drink logging persists independently.
- Standard service logging and external hydration events.
- Each log_drink action gets a unique ID, timestamp, volume, input unit and origin.
- Today's history table in the card, newest first; scrollable. Entire event ledger survives HA restarts and midnight reset.
- Full Excel `.xlsx` export for admins, 6 tabs: Profiles, Drink Moments, Daily Totals, Source Readings, Adjustments, Export Info.
- Excel contains all retained data for **all profiles**, no row limit or truncated history. It includes the exact original volume and units.
- Export uses HA authenticated WebSocket and downloads in-browser; no web-exposed `.xlsx` file.
- Normalizes `Jan-Willem` and `Jan Willem` with `slugify` consistently.
- Errors from service and export are visible on the dashboard card.
- MIT licensed, no third-party packages for Excel export.

## Install with HACS

1. Open **HACS** → top-right menu → **Custom repositories**.
2. Add `https://github.com/iamjwk1/jwDaily-Hydration-Log` as type **Integration**.
3. Install **jwDaily Hydration Log**, then **restart Home Assistant**.
4. Go to **Settings → Devices & services → Add Integration**, select **jwDaily Hydration Log** and create a profile.
5. Add the card shown below.

The original **Personal Hydration Manager** and this fork have independent configuration and storage.

## Standalone ZIP installer (previously supplied package)

The commands below apply specifically to the separately distributed executable file `20261108 jwDaily Hydration Log v1.0.2.zip`; a generic GitHub source ZIP is **not** an executable installer. Use HACS for normal GitHub installation.

## Before installation

1. Make a Home Assistant backup/snapshot and keep the existing PHM integration running.
2. Upload the **single ZIP** to `/config` without unpacking.
3. Read-only preflight:

   `python3 '/config/20261108 jwDaily Hydration Log v1.0.2.zip' --preflight`

4. After reviewing, explicit install:

   `python3 '/config/20261108 jwDaily Hydration Log v1.0.2.zip' --apply`

5. Installer validates package hashes, creates a backup ZIP, stages files, installs only the new domain and blueprints, and calls `ha core check` if the HA CLI is available. It rolls back code on check failure and preserves all current drink-ledger data. **It does not restart Home Assistant**.
6. After confirming PASS, restart Home Assistant (Settings → System → Restart). For an already-present new domain, use explicit `--upgrade` only after reviewing the preflight.
7. Settings → Devices & services → Add integration → **jwDaily Hydration Log**; add a new profile. This is a new standalone profile: no old records are automatically imported.
8. Add card → **jwDaily Hydration Log**, or use YAML below. Switch your active view only after you have checked the new profile. Never copy the old domain/type to the new card.

## YAML example

```yaml
type: custom:jwdaily-hydration-log-card
profile: jan_willem
title: Vocht intake
show_title: true
show_cup: true
show_countdown: false
show_manual: true
show_history: true
show_export: true
unit: mL
quick_add:
  - 120
  - 150
  - 300
  - 500
```

## Excel export

From an HA admin session click **Export all data to Excel (.xlsx)** below the history table. The default exports **every registered jwDaily Hydration Log profile**, with all retained historical records and source readings. The underlying WebSocket API only grants export to admins. Browser download permission must be enabled. The Excel rows are genuine numbers and local dates, ready to filter/sort. Large histories are sent as one WebSocket payload; for very large archives an HTTP streaming export may be preferable in a future version.

Data that the original Personal Hydration Manager did **not** store (individual old drink timestamps/amounts) cannot be recovered automatically. The new integration starts its own ledger from first use. Old aggregate readings can be viewed in the old integration separately; this fork deliberately does not guess or import synthetic drink events.

## Home Assistant services

```yaml
action: jw_daily_hydration_log.log_drink
data:
  profile: jan_willem
  volume: 120
  unit: mL
  origin: automation
```

```yaml
action: jw_daily_hydration_log.reset_today
data: {profile: jan_willem}
```

```yaml
action: jw_daily_hydration_log.set_consumed
data: {profile: jan_willem, volume: 1200, unit: mL}
```

To log from another automation, fire an event:

```yaml
event_type: jw_daily_hydration_log_drink
event_data: {profile: jan_willem, volume: 120, unit: mL}
```

Two optional automation blueprints are supplied in `blueprints/automation/jw_daily_hydration_log`.

## Rollback and data safety

The backup ZIP is stored in `/backup` and includes any existing fork code, blueprint files and `.storage/jw_daily_hydration_log.*` ledgers. To restore the **previous code** while retaining the latest accumulated drink data:

`python3 '/config/20261108 jwDaily Hydration Log v1.0.2.zip' --rollback --backup '/backup/<exact backup filename>.zip'`

Replace the bracketed filename with the **actual** name printed by the installer; this is an instruction template, not an existing file. The optional `--restore-storage` intentionally replaces the current ledger with an older backup and should not be used unless separately approved. If rolling back an initial installation after HA profiles have already been created, deactivate those profiles first; otherwise HA will report a missing integration until you reinstall the code. No upstream config entries or state are touched by the installer.

## Release QA and limitations

- Static syntax checks, service-path checks, isolated coordinator tests, exporter XLSX validity/CRC tests, and package SHA-256 validation included.
- This package was not exercised against **your running Home Assistant instance**. A successful `ha core check`, successful integration load, and runtime button/export smoke test are still required before calling the deployment accepted.
- Full independent release does not mutate upstream; daily totals of the two installations will differ until they are configured to ingest the same real data.
- Excel export is admin-only and includes all profiles. Handle exported personal data appropriately.
- In `absolute` mode, updates from an external total sensor can overwrite the displayed consumed total. Manual history is kept independently; use `sum` mode when you want cumulative manual + source contributions.
- Source readings are retained without automated pruning to satisfy full-data export. On very long-running systems storage and export size will grow.
- All timestamps are stored as timezone-aware ISO strings; Excel converts to HA local time.
- Daily reset is at local midnight; historical ledgers are not discarded.
- The `set_consumed` action is stored as a correction, **not** invented as a drink event.
- v1.0.2 does not offer deletion/editing of individual drinks; it retains a verifiable audit history. Corrections are recorded as separate actions.

## Developer instructions

Maintainer: [@iamjwk1](https://github.com/iamjwk1). Upstream author: Loryan Strant, copyright 2026. GitHub repository: https://github.com/iamjwk1/jwDaily-Hydration-Log. This is an independent derivative under the retained MIT license.

Source code is provided in this archive. Run tests with `python3 tests/qa.py` on a development computer if you extract the ZIP. **Do not manually extract for normal HA installation**.


## Licensing and attribution

This project is derived from the MIT-licensed [Personal Hydration Manager](https://github.com/loryanstrant/HA-Personal-Hydration-Manager) by Loryan Strant. The original MIT notice is preserved in [LICENSE-UPSTREAM-MIT](LICENSE-UPSTREAM-MIT).

**License:** jwDaily Hydration Log is published under the [MIT License](LICENSE). The original copyright notice (`Copyright (c) 2026 Loryan Strant`) is preserved unchanged in both the primary license and the verbatim [upstream MIT license](LICENSE-UPSTREAM-MIT). The contributors' modifications are identified separately. The repository's initial GPLv3 placeholder is superseded by this MIT license.
