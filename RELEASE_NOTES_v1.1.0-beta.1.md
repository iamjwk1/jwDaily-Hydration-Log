# jwDaily Hydration Log v1.1.0-beta.1

**TESTING / PRE-RELEASE — install via HACS only. The stable version remains v1.0.2.**

## Upgrade precautions
- Back up Home Assistant **including** `.storage/jw_daily_hydration_log.*` and dashboards before installing. No automatic backup is made by a normal HACS download.
- **Breaking API change:** `jw_daily_hydration_log.log_drink` and `jw_daily_hydration_log_drink` events now **require** a `liquid_type`: `water`, `coffee`, `tea`, `milk`, `soup`, or `other`. Update affected scripts and automations first; review the bundled push-notification blueprint.
- **Removed:** `hourly_pace` sensor, pace calculation and pace UI; old pace registry entity is removed on integration load.
- The existing profile and recorded drinks remain in the same integration storage, but **edits overwrite and deletes physically remove entries** from the integration ledger. No edit/delete audit trail. Test destructive actions on newly created sample entries; restore a backup to recover deleted records.
- Entries created in v1.0.2 have no liquid type; they appear as **Unknown (legacy)** without guessing their type.

## Improvements
- Explicit liquid type + volume selection required for each new drink, neither choice is remembered.
- Click an existing drink to edit in a **Save / Delete / Cancel** popup; date `DD-MM-YYYY`, time 24-hour.
- Backdated registrations and adjustments update the appropriate day's totals.
- Compact, top-open glass with a dashed red goal line.
- **Undo last drink** deletes the most recently added entry.
- Full Excel export with **seven** worksheets, including Daily Breakdown and liquid types.

## How to install via HACS
1. Open HACS → **jwDaily Hydration Log**.
2. Enable prereleases for this repository if needed, then select **⋮ → Redownload → Need a different version? → v1.1.0-beta.1**.
3. Restart Home Assistant, refresh the dashboard (`Ctrl+Shift+R`) and verify the card version and existing profile.
4. Test with new sample drinks, and check the seven-sheet Excel export.
5. For a code rollback select **v1.0.2** in HACS. Restoring previously deleted/edited records requires a separate full HA backup.

## Source and licensing
Based on the MIT-licensed Personal Hydration Manager by Loryan Strant; original copyright and license retained.

**This is not the stable v1.1.0 release.** GitHub source archives are for HACS; do not run them as a standalone installation script.
