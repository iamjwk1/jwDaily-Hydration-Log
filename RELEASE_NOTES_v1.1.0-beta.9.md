# jwDaily Hydration Log v1.1.0-beta.9 — HACS test release

**Upgrade only through HACS. This is a pre-release; stable v1.0.2 stays unchanged.**

## Excel: Microsoft Excel repair warning
- Fixed the `xl/worksheets/sheet1.xml` and `sheet2.xml` element order reported in beta.8: `pageMargins` precedes `tableParts` as required by Excel's OOXML worksheet schema.
- Sanitize XML 1.0-invalid controls in user-supplied names.
- Kept the four customized worksheets, native Excel tables and formulas, referenced styling and filename `YYYYMMDD-HHMM jwDaily Hydration Log - All Data.xlsx`.
- Added independent structural regression checks. **Opening, saving and reopening in Microsoft Excel Desktop must still be confirmed during live acceptance.** No Microsoft Excel installation is available on GitHub runners.

## Card usability and layout
- More compact header based on the edited reference screenshot: glass left, blue volume close to the glass, wider visible daily breakdown to the right, smaller Add button, uniform drink row heights, larger bold history date, Excel left.
- Android numeric-only clock typing: `930` = `09:30`, `1430` = `14:30`, `14.30` = `14:30`. Invalid `2431` is refused (24:31 does not exist). No colon key needed.
- Switching historical dates still updates the glass, goal and bar chart; existing edit/delete behavior preserved.

## Two new chart data sensors (ApexCharts Card)
- `sensor.jwdhl_<slug>_hourly_intake_today` – 24 clock-hour buckets and per-type values under `attributes.buckets`.
- `sensor.jwdhl_<slug>_daily_intake_last_7_days` – seven day buckets and per-type values under `attributes.days`.
- Use `examples/apexcharts-jwdhl-v1.1.0-beta.9.md` for two ApexCharts Lovelace card examples.
- Data are derived from stored drink moments; source sensor readings that cannot be assigned a liquid type remain excluded from the per-type bars.

## Upgrade and validation
1. Make a full HA backup including stored hydration history.
2. HACS → jwDaily Hydration Log → ⋮ → Redownload → Need a different version? → `v1.1.0-beta.9`.
3. Restart Home Assistant Core and refresh the browser with Ctrl+Shift+R.
4. Confirm the card footer version, test Android time entry, adjust a test drink and verify bar charts.
5. Export Excel and perform **Microsoft Excel desktop open/save/reopen** with no repair warnings. If Excel still reports a problem, keep the exported sample and Excel repair log for a targeted correction.

Release is automatically gated on Python tests, Node frontend tests, OOXML structural checks, real Chromium browser geometry, Hassfest and HACS validation. HA and Microsoft Excel live acceptance are separate.
