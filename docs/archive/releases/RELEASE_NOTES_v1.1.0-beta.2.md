# jwDaily Hydration Log v1.1.0-beta.2

**HACS PRE-RELEASE — not yet approved for stable production.** Stable release remains `v1.0.2`.

## Visual and interaction improvements
- Main card is now compact: open-top animated glass, daily measurements, **+ Add drink**, drink history and existing Excel export.
- The version number is at the **bottom-right**.
- **The dashed red goal line is approximately 15 px lower in the glass** (from SVG y=23 to y=39), and the water fill reaches that same line at exactly 100%.
- Rising fill animation and a continuously moving subtle waterline have been restored.
- Both adding and editing drink moments use the same popup with large drink icons, volume buttons, a custom volume field, date `DD-MM-YYYY` and 24-hour time.
- Clicking a historic row opens the edit popup with **Save, Delete, Cancel**. Delete requires confirmation and permanently removes the current integration entry.

## Your own drink types
- In the Add/Edit popup, Home Assistant administrators can click **+ Add custom liquid type**.
- Enter a name, choose a Material Design icon (`mdi:...`) **or upload a local SVG file**, and optionally configure a default volume in mL.
- Built-in types still require an intentional volume choice. A custom type **only preselects a volume after it has been consciously selected**, and only if it has a configured default. Opening Add never remembers the previous selection.
- Custom types and SVG data are stored per hydration profile and survive HA restarts and updates. SVGs are checked for unsafe elements/remote resources before saving.
- Custom types that have already been used in saved drinks cannot be removed until those drinks have been edited or deleted.

## Data and Excel
- Existing profiles, drink entries, daily targets and history remain in the same storage namespace. Unknown types from earlier v1.0.2 remain **Unknown (legacy)**.
- Excel now exports **eight** sheets, including **Liquid Types**, with custom icons, default volumes and readable custom liquid names. `Daily Breakdown` also counts custom drinks.
- Pace remains removed, as agreed in beta.1. Old integrations / automations should not depend on the obsolete hourly-pace sensor.

## Installation through HACS only
1. Create a full Home Assistant backup including `.storage/jw_daily_hydration_log.*` and your dashboard configuration.
2. In **HACS → jwDaily Hydration Log → ⋮ → Redownload → Need a different version?**, enable pre-releases if necessary and select **`v1.1.0-beta.2`**.
3. Restart Home Assistant and refresh the dashboard (`Ctrl+Shift+R`) to load the new card JavaScript.
4. Keep the existing profile `Jan-Willem`. Test with a new disposable record before modifying valuable historic data.
5. Verify custom SVG type creation, default volume, Add/Edit/Delete popup, glass animation, 15px lower red target line, and eight-sheet Excel export.

**Breaking change from v1.0.2:** the `jw_daily_hydration_log.log_drink` service and `jw_daily_hydration_log_drink` event require `liquid_type`; update any existing automations or scripts first. There is no automatic rollback of deleted/edited drink history; restore a separate HA backup if recovery is required. Code rollback can be performed through HACS version selection, but **older versions do not understand the custom-type catalog and may drop those definitions when saving**. Back up the full storage first.

Based on the MIT-licensed Personal Hydration Manager by Loryan Strant, with original notice retained.
