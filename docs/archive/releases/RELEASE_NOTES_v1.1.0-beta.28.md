# jwDaily Hydration Log v1.1.0-beta.28

**Targeted bugfix of the complete v1.1.0-beta.27 integration.** No destructive operations, automatic conversions or stored-data changes.

## Fixed: historical Cup types were omitted from Excel

The backend kept two complementary historic Cup associations:

- `legacy_mappings`: old Liquid IDs renamed/merged under a canonical Liquid, optionally with a Cup.
- `legacy_cup_defaults`: historic Cup type assigned to an unchanged Liquid ID (such as `coffee`, `tea`, `milk` or `water`).

The historical drink display already handled both. The Excel export tried to read both, but its `export_snapshot()` did not include `legacy_cup_defaults`. Thus historical Cup cells could be blank even when the Cup assignment had been saved correctly.

beta.28 adds the missing mapping to the export snapshot, without changing source drink records. Excel follows the same precedence as the live backend: a directly saved Cup ID wins over a renamed-liquid alias Cup, which wins over an unchanged-liquid default. If no reliable Cup assignment exists, leave it blank; never guess from the consumed volume.

## Preservation and QA

- No changes to Add/Edit/Delete, Liquid/Cup/Quick configurations, profile settings import/export, conversions or confirmed mappings.
- Original recorded drink IDs, complete timestamps including seconds, volumes and Liquid IDs stay untouched.
- Exactly four Excel sheets. Preserve Date+time column width 19 and Daily intake row 11 at 44 pt, formulas, structured tables, colors and historical column behavior.
- Regressions compare backend history to the generated XLSX record by record for direct, alias, unchanged-liquid-default and unknown Cup cases, plus daily sums and Office XML validity.

### What to expect on your profile

Export a new XLSX after installing/restarting beta.28. Existing Cup mappings, if actually saved, now appear for older records. Drinks whose historic Cup was never mapped remain deliberately blank. You can inspect and add missing associations using **Settings → Advanced → Convert existing data** after backing up and reviewing the mapping preview. This is a separate, explicitly confirmed operation.

**Release requirement:** all GitHub Source QA, HACS and Hassfest checks must pass. Prior beta.27 remains available for rollback.
