# jwDaily Hydration Log

**Hydration tracking for Home Assistant — stable release v2.0.0**

jwDaily Hydration Log is a Home Assistant integration and dashboard card for recording what you drink, monitoring your daily intake and reviewing your drinking history. It supports multiple independent profiles, configurable drink and cup types, editable history, daily and weekly charts, Excel reports and verified backups. Data is managed inside Home Assistant; no external hydration account is needed.

This project is an independent, MIT-licensed fork of [Personal Hydration Manager](https://github.com/loryanstrant/HA-Personal-Hydration-Manager). The original MIT license notice is preserved in [LICENSE-UPSTREAM-MIT](LICENSE-UPSTREAM-MIT).

## Purpose and functionality

The integration provides a personal hydration log inside Home Assistant. It helps you record drinks, see your progress towards a daily target and review or correct earlier entries. Each person has independent records.

| Function | What it does |
| --- | --- |
| **Hydration dashboard** | Shows today's consumed volume, remaining amount, target, progress and number of drink moments |
| **Multiple profiles** | Keeps separate drink records and daily summaries for different people |
| **Log a drink** | Saves the liquid, cup, actual amount and local date/time of each drink |
| **Quick drink entry** | Adds a familiar Liquid/Cup combination with one selection |
| **Drink history** | Lets you view, edit or delete recorded drinks, including entries from earlier days |
| **Charts and daily snapshots** | Shows intake by hour, the last seven days and per-liquid breakdowns; preserves daily summaries |
| **Home Assistant entities and actions** | Exposes sensors, an editable target entity and services for automations and other dashboards |
| **Excel export** | Produces a six-sheet workbook for drink history, daily intake and configuration |
| **Backup and restore** | Creates a checked ZIP backup and previews a full, settings-only or data-only restore before confirmation |

Historical drink entries retain their recorded actual amounts even if you later change a Cup's default volume or a Quick button.

## Configurable settings

Configure these options in the integration's **Settings** dialog or, where noted, in the Lovelace card configuration.

| Settings area | What you can configure |
| --- | --- |
| **Profiles** | Create and manage profiles; set the name, age, gender, preferred unit (mL, L or fl oz) and daily intake target |
| **Add drink display** | Per profile, show **Quick buttons**, **Liquid types and Cup types**, or both; at least one entry method must remain visible |
| **Liquid types** | Add custom liquids; edit names, MDI icons and colours; control visibility and ordering |
| **Cup types** | Set names, default volumes and icons; show or hide available cups |
| **Quick buttons** | Choose a Liquid/Cup combination, adjust its label, visibility and order, or remove it |
| **Dashboard card** | Choose a profile and title and configure card display elements such as the glass, history, Add drink and Excel export controls |
| **Daily target** | Adjust the daily goal for an individual profile, including via the Home Assistant target override entity |

**Data & Backup** is a separate set of actions—Excel export, creating a backup and previewing or confirming a restore—not a profile preference. Restore scope (**Everything**, **Settings only** or **Data only**) is selected for each restore operation.

## Interface at a glance

The built-in Lovelace card shows the current intake against your target, an editable drink history, and access to **Add drink**, **Settings** and **Export Excel**. The Settings dialog groups **Manage profiles**, **Liquid types**, **Cup types**, **Quick buttons**, and **Data & Backup**.

The **Add drink** view can show Quick buttons, separate Liquid/Cup selectors, or both, according to the profile settings. Chart data is also available through Home Assistant sensors for custom dashboards.

For a guided tour of the dialog screens, daily snapshots, chart sensors and backup/restore screens, see the [User guide](docs/USER_GUIDE.md).

## Installation (HACS)

1. In **HACS**, add this repository as a custom repository with category **Integration** if it is not already listed:
   `https://github.com/iamjwk1/jwDaily-Hydration-Log`
2. Install **jwDaily Hydration Log**, selecting the stable **v2.0.0** release.
3. Restart **Home Assistant Core**.
4. Open **Settings → Devices & services → Add integration**, search for **jwDaily Hydration Log**, and create a profile.
5. Add a Manual card to your dashboard:

```yaml
type: custom:jwdaily-hydration-log-card
profile: jane_doe
title: Hydration
```

Replace `jane_doe` with the profile slug created from your profile's name. The integration registers its dashboard JavaScript resource. Refresh the browser after installation or upgrades.

**Updating:** create a current Home Assistant backup and download the integration's **Full Backup ZIP** before updating in HACS. Restart Home Assistant Core and refresh the dashboard after installation. The v2.0.0 release uses the existing data format; no new data migration is required.

## Example Home Assistant entities

For a profile slug such as `jane_doe`, the integration exposes entities with names like:

| Entity | Meaning |
| --- | --- |
| `sensor.jwdhl_jane_doe_consumed_today` | Today's consumed total |
| `sensor.jwdhl_jane_doe_manual_consumed` | Manually logged intake |
| `sensor.jwdhl_jane_doe_daily_target` | Daily target |
| `sensor.jwdhl_jane_doe_remaining` | Remaining volume |
| `sensor.jwdhl_jane_doe_progress` | Daily progress percentage |
| `sensor.jwdhl_jane_doe_drink_count_today` | Number of logged drinks today |
| `sensor.jwdhl_jane_doe_hourly_intake_today` | Today’s per-hour intake buckets |
| `sensor.jwdhl_jane_doe_daily_intake_last_7_days` | Seven-day intake history |
| `number.jwdhl_jane_doe_target_override` | Editable daily target override |

There are also Home Assistant actions under the `jw_daily_hydration_log` domain, including `log_drink`, `reset_today` and `set_consumed`. See [services.yaml](custom_components/jw_daily_hydration_log/services.yaml) for parameter definitions.

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
