# Changelog

## v1.0.2 — First official jwDaily Hydration Log release

Independent Home Assistant integration derived from Loryan Strant's MIT-licensed Personal Hydration Manager v0.4.1.

### Features
- Independent integration domain `jw_daily_hydration_log` and entities prefixed `jwdhl_`.
- Lovelace card `custom:jwdaily-hydration-log-card` with animated daily progress and configurable quick-add amounts.
- Persistent per-drink history: local timestamps, actual volumes, unique event IDs and source information.
- History table beneath the buttons, with the newest drink first.
- Complete administrator-only Excel (.xlsx) export with six worksheets: Profiles, Drink Moments, Daily Totals, Source Readings, Adjustments and Export Info.
- Multiple independent hydration profiles and configurable daily targets.
- Services, external sensor tracking and optional notification/TTS blueprints.
- Unified slug normalization: names such as `Jan-Willem` and `Jan Willem` resolve consistently.
- Dedicated integration branding and a separate MIT copyright/attribution notice.

### Important
- This fork does **not** replace, remove or alter the upstream Personal Hydration Manager installation.
- Existing profiles and hydration history stored by the original integration are **not** automatically imported. The fork uses a separate storage namespace.
- Dashboard YAML: `type: custom:jwdaily-hydration-log-card`.
- If upgrading from the earlier pre-release card name `custom:jw-daily-hydration-log-card`, update your dashboard configuration.
- GitHub's automatically generated source ZIP is **not** the special executable HA ZIP installer previously supplied separately.
- Install and update through HACS as a custom integration, after backing up your working Home Assistant configuration.
- Home Assistant requires a restart after a new integration installation or a Python-code update.

### Licensing
MIT. The original `Copyright (c) 2026 Loryan Strant` notice and full upstream MIT license are retained.

### Quality
Offline source QA and Home Assistant hassfest validated. A functional HA v1.0.2 installation was accepted, including manual additions, drink history and Excel export.
