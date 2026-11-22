# jwDaily Hydration Log

**Hydration tracking for Home Assistant — stable release v2.0.0**

jwDaily Hydration Log is a Home Assistant integration and dashboard card for recording what you drink, monitoring your daily intake and reviewing your drinking history. It supports multiple independent profiles, configurable drink and cup types, editable history, daily and weekly charts, Excel reports and verified backups. Data is managed inside Home Assistant; no external hydration account is needed.

This project is an independent, MIT-licensed fork of [Personal Hydration Manager](https://github.com/loryanstrant/HA-Personal-Hydration-Manager). The original MIT license notice is preserved in [LICENSE-UPSTREAM-MIT](LICENSE-UPSTREAM-MIT).

## What can it do?

| Feature | Description |
| --- | --- |
| **Multiple profiles** | Separate drink histories, daily targets, units and settings for each person |
| **Add a drink** | Record a liquid, cup, amount, date and time using the dashboard; use Quick buttons for frequently used combinations |
| **Liquid types** | Use built-in or custom liquids; configure names, icons, colours, visibility and order |
| **Cup types** | Define named cups with default volumes and icons; keep the actual volume saved with every drink |
| **Quick buttons** | Combine a liquid and cup in a one-touch entry; configure, reorder, hide or remove buttons |
| **Edit drink history** | View, correct or remove recorded drinks without recreating the entire day's data |
| **Daily target** | Monitor consumed, remaining and target volumes, progress and number of drink moments |
| **Charts and sensors** | Inspect hourly intake and the last seven days, including per-liquid breakdowns |
| **Excel reporting** | Export one or all profiles to a six-worksheet XLSX report with history, daily totals and settings |
| **Backup and restore** | Create a verified profile ZIP, preview a restore and choose Everything, Settings only or Data only |
| **Units and automation** | Choose mL, L or fl oz; interact through Home Assistant sensors, a target number entity and services |

Each profile keeps its own settings and drink history. When a Quick button or Cup definition changes, previously recorded drink amounts and event identifiers are not retrospectively rewritten.

## Interface at a glance

The built-in Lovelace card shows the current intake against your target, an editable drink history, and access to **Add drink**, **Settings** and **Export Excel**. The Settings dialog groups **Manage profiles**, **Liquid types**, **Cup types**, **Quick buttons**, and **Data & Backup**.

The **Add drink** view can show Quick buttons, separate Liquid/Cup selectors, or both, according to the profile settings. Chart data is also available through Home Assistant sensors for custom dashboards.

For a guided tour of the dialog screens, daily snapshots, chart sensors and backup/restore screens, see the [User guide](docs/USER_GUIDE.md).

## Installation (HACS)

1. In **HACS**, add this repository as a custom repository with category **Integration** if it is not already listed:
   \`https://github.com/iamjwk1/jwDaily-Hydration-Log\`
2. Install **jwDaily Hydration Log**, selecting the stable **v2.0.0** release.
3. Restart **Home Assistant Core**.
4. Open **Settings → Devices & services → Add integration**, search for **jwDaily Hydration Log**, and create a profile.
5. Add a Manual card to your dashboard:

\`\`\`yaml
type: custom:jwdaily-hydration-log-card
profile: jane_doe
title: Hydration
\`\`\`

Replace \`jane_doe\` with the profile slug created from your profile's name. The integration registers its dashboard JavaScript resource. Refresh the browser after installation or upgrades.

**Updating:** create a current Home Assistant backup and download the integration's **Full Backup ZIP** before updating in HACS. Restart Home Assistant Core and refresh the dashboard after installation. The v2.0.0 release uses the existing data format; no new data migration is required.

## Example Home Assistant entities

For a profile slug such as \`jane_doe\`, the integration exposes entities with names like:

| Entity | Meaning |
| --- | --- |
| \`sensor.jwdhl_jane_doe_consumed_today\` | Today's consumed total |
| \`sensor.jwdhl_jane_doe_manual_consumed\` | Manually logged intake |
| \`sensor.jwdhl_jane_doe_daily_target\` | Daily target |
| \`sensor.jwdhl_jane_doe_remaining\` | Remaining volume |
| \`sensor.jwdhl_jane_doe_progress\` | Daily progress percentage |
| \`sensor.jwdhl_jane_doe_drink_count_today\` | Number of logged drinks today |
| \`sensor.jwdhl_jane_doe_hourly_intake_today\` | Today’s per-hour intake buckets |
| \`sensor.jwdhl_jane_doe_daily_intake_last_7_days\` | Seven-day intake history |
| \`number.jwdhl_jane_doe_target_override\` | Editable daily target override |

There are also Home Assistant actions under the \`jw_daily_hydration_log\` domain, including \`log_drink\`, \`reset_today\` and \`set_consumed\`. See [services.yaml](custom_components/jw_daily_hydration_log/services.yaml) for parameter definitions.

## History, daily snapshots and backups

- **Drink history** records individual entries with their actual volume, liquid type and timestamp.
- **Daily snapshots** preserve day-level totals for historical views and the last-seven-days chart.
- **Full Backup ZIP** includes profile configuration and drink records. The ZIP is validated before previewing restore options.
- **Restore preview** identifies the target profile, compares complete saved settings and drink data against the selected backup, and reports **Identical to current**, **Different from current** or **Not included** according to the selected restore scope. A preview is read-only; an actual restore requires explicit confirmation.
- **Excel export** provides six sheets: Hydration log, Daily intake, Settings - Liquid Types, Settings - Cup types, Settings - Quick buttons, and Settings - Profiles.

## Documentation

- [User guide and interface walkthrough](docs/USER_GUIDE.md)
- [Release notes (current and previous versions)](docs/RELEASE_NOTES.md)
- [Version 2.0.0 release notes](docs/releases/v2.0.0.md)
- [Complete changelog](docs/CHANGELOG.md)
- [Optional ApexCharts example](docs/examples/apexcharts.md)
- [Historical documentation archive](docs/archive/INDEX.md)
- [GitHub issues and feature requests](https://github.com/iamjwk1/jwDaily-Hydration-Log/issues)

## Support and licensing

Report reproducible bugs or feature requests via [GitHub Issues](https://github.com/iamjwk1/jwDaily-Hydration-Log/issues). Include the installed version, relevant symptoms and safe-to-share error logs; **never post real personal drink histories or backups publicly**.

The integration is distributed under the [MIT license](LICENSE). See [LICENSE-UPSTREAM-MIT](LICENSE-UPSTREAM-MIT) for the upstream attribution.
