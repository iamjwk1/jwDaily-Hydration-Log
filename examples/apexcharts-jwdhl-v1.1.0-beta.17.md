# ApexCharts examples for jwDaily Hydration Log v1.1.0-beta.17

The Home Assistant integration creates two additional **sensors per profile**, both
derived from the existing stored drink ledger (no new recording database):

* `sensor.jwdhl_<slug>_hourly_intake_today` – numerical state: total registered drinks today in mL. Attribute `buckets`: exactly 24 local wall-clock hour buckets (`hour`, `start`, `total_ml`, `liquids`). On fall DST days, the repeated 02:00 wall-clock hour is intentionally combined into one displayed clock-hour bucket.
* `sensor.jwdhl_<slug>_daily_intake_last_7_days` – numerical state: total registered drinks across the seven days in mL. Attribute `days`: seven entries from oldest through today, each with `date`, `total_logged_ml`, `consumed_ml`, `target_ml`, `drink_count` and `liquids`.

Each `liquids` map uses a **stable liquid type ID**, so renaming a liquid does not
break the graph. A `liquid_names` attribute maps those IDs to current names.
Unlike the glass total, chart breakdown values represent only **typed individual
drink entries**; unattributed source-sensor volume is deliberately excluded.
Adding/editing/deleting a drink updates both chart sensors, including historical changes.
The next midnight reset advances the hourly/weekly window; existing records are never destroyed.

Install `ApexCharts Card` through HACS. The two YAML configurations below are
independent Lovelace cards. They plot the seven built-in liquid IDs. For a custom
liquid, duplicate any series and replace the ID with the custom type ID from
the sensor `liquid_names` attribute. No JavaScript is added to the integration's
Lovelace card; `data_generator` is the ApexCharts Card feature.

```yaml
# Today's intake by hour
# Requires HACS ApexCharts Card; replace jan_willem with your profile slug.
# Values include manually registered drinks only; untyped source sensor readings
# cannot be attributed to water/coffee/etc without guessing.
type: custom:apexcharts-card
header:
  show: true
  title: "Today's intake by hour"
graph_span: 24h
span:
  start: day
stacked: true
hours_12: false
cache: false
series:
  - entity: sensor.jwdhl_jan_willem_hourly_intake_today
    name: Water
    type: column
    data_generator: |
      return (entity.attributes.buckets || []).map(row => [
        new Date(row.start).getTime(),
        Number((row.liquids || {}).water || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_hourly_intake_today
    name: Coffee
    type: column
    data_generator: |
      return (entity.attributes.buckets || []).map(row => [
        new Date(row.start).getTime(),
        Number((row.liquids || {}).coffee || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_hourly_intake_today
    name: Tea
    type: column
    data_generator: |
      return (entity.attributes.buckets || []).map(row => [
        new Date(row.start).getTime(),
        Number((row.liquids || {}).tea || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_hourly_intake_today
    name: Milk
    type: column
    data_generator: |
      return (entity.attributes.buckets || []).map(row => [
        new Date(row.start).getTime(),
        Number((row.liquids || {}).milk || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_hourly_intake_today
    name: Soup
    type: column
    data_generator: |
      return (entity.attributes.buckets || []).map(row => [
        new Date(row.start).getTime(),
        Number((row.liquids || {}).soup || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_hourly_intake_today
    name: Wine
    type: column
    data_generator: |
      return (entity.attributes.buckets || []).map(row => [
        new Date(row.start).getTime(),
        Number((row.liquids || {}).wine || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_hourly_intake_today
    name: Other
    type: column
    data_generator: |
      return (entity.attributes.buckets || []).map(row => [
        new Date(row.start).getTime(),
        Number((row.liquids || {}).other || 0)
      ]);
# To chart a custom liquid, add another series and use
# (row.liquids || {})['your_stable_custom_liquid_id'] instead of .water.
```

```yaml
# Daily intake — last 7 days
# Requires HACS ApexCharts Card; replace jan_willem with your profile slug.
# Values include manually registered drinks only; untyped source sensor readings
# cannot be attributed to water/coffee/etc without guessing.
type: custom:apexcharts-card
header:
  show: true
  title: "Daily intake — last 7 days"
graph_span: 7d
span:
  end: day
stacked: true
hours_12: false
cache: false
series:
  - entity: sensor.jwdhl_jan_willem_daily_intake_last_7_days
    name: Water
    type: column
    data_generator: |
      return (entity.attributes.days || []).map(row => [
        new Date(row.date + 'T12:00:00').getTime(),
        Number((row.liquids || {}).water || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_daily_intake_last_7_days
    name: Coffee
    type: column
    data_generator: |
      return (entity.attributes.days || []).map(row => [
        new Date(row.date + 'T12:00:00').getTime(),
        Number((row.liquids || {}).coffee || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_daily_intake_last_7_days
    name: Tea
    type: column
    data_generator: |
      return (entity.attributes.days || []).map(row => [
        new Date(row.date + 'T12:00:00').getTime(),
        Number((row.liquids || {}).tea || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_daily_intake_last_7_days
    name: Milk
    type: column
    data_generator: |
      return (entity.attributes.days || []).map(row => [
        new Date(row.date + 'T12:00:00').getTime(),
        Number((row.liquids || {}).milk || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_daily_intake_last_7_days
    name: Soup
    type: column
    data_generator: |
      return (entity.attributes.days || []).map(row => [
        new Date(row.date + 'T12:00:00').getTime(),
        Number((row.liquids || {}).soup || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_daily_intake_last_7_days
    name: Wine
    type: column
    data_generator: |
      return (entity.attributes.days || []).map(row => [
        new Date(row.date + 'T12:00:00').getTime(),
        Number((row.liquids || {}).wine || 0)
      ]);
  - entity: sensor.jwdhl_jan_willem_daily_intake_last_7_days
    name: Other
    type: column
    data_generator: |
      return (entity.attributes.days || []).map(row => [
        new Date(row.date + 'T12:00:00').getTime(),
        Number((row.liquids || {}).other || 0)
      ]);
# To chart a custom liquid, add another series and use
# (row.liquids || {})['your_stable_custom_liquid_id'] instead of .water.
```
