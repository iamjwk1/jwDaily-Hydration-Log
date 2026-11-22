# jwDaily Hydration Log v1.1.0-beta.4

**TEST / HACS PRE-RELEASE.** Stable v1.0.2 stays the default stable version. Do not overwrite files manually.

## Requested improvements
- **Liquid types:** In **Add drink → Manage liquid types**, add, edit, reorder or remove unused custom liquids. Standard types can also be renamed and given a different MDI or safe SVG icon and optional default volume; stable liquid IDs preserve all recorded history. Buttons are ordered by up/down actions.
- **Volume buttons:** In **Add drink → Manage volume buttons**, add/change/delete/reorder presets in mL. Saved values belong to the hydration profile and survive Home Assistant restart. Can intentionally have no preset buttons; custom input stays available. Existing Lovelace `quick_add` remains the initial fallback.
- **Larger input text** for amount, date (`DD-MM-YYYY` calendar) and 24-hour time.
- **Full glass over target:** at exactly 100%, the blue waterline reaches the lowered red target line. Above 100%, blue water fills to the open top rim and stays capped there, even as daily consumption continues rising. The red dashed target line and goal text remain above/visible on the blue liquid.
- **Excel export:** Nine worksheets; `Liquid Types` now includes ordered built-in overrides, and `Volume Buttons` includes the persisted profile presets.

## Safety and migration
- All beta.3 profiles, drink records, editable IDs, custom liquid SVGs and saved history are retained under the same storage key. Built-in overrides and volume presets are separate optional keys.
- Name, icon or position changes do not alter stored drink events. Deleting a used custom type is prohibited. Removing a preset does not delete drinks.
- Existing automations using `jw_daily_hydration_log.log_drink` require a valid `liquid_type` (since beta.1).
- A HACS code rollback to beta.3 does not guarantee it will preserve beta.4-only settings if that older code saves the profile state. Keep a full Home Assistant backup (including `.storage/jw_daily_hydration_log.*`) before updating.

## Install via HACS
HACS → jwDaily Hydration Log → ⋮ → Redownload → Need a different version? → **v1.1.0-beta.4**. Restart **Home Assistant Core** and refresh browser (Ctrl+Shift+R). Test with existing `Jan-Willem` profile; do not remove/re-create profiles.

## Quality gate
Offline backend regression tests, frontend interaction tests, Home Assistant Hassfest and HACS Validation all run before publication. Live on-device acceptance remains necessary.
