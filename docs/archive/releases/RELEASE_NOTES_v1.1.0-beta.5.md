# jwDaily Hydration Log v1.1.0-beta.5

**HACS PRE-RELEASE — test before approving a stable release.** The stable v1.0.2 remains unchanged.

## New
- Manage liquid types now offers **Delete** for built-in installation types (Water, Coffee, Tea, Milk, Soup, Wine, Other), as well as your own custom types.
- Delete on a built-in hides its button from the Add popup only. Previously logged drinks retain their original type ID, their history and totals; the type remains available for reporting, Excel and **Restore**.
- A two-step confirmation prevents accidental removal. Custom types can be permanently deleted only while unused.
- Profile-local hidden/visible status survives HA restart and HACS updates. Previously saved custom liquids (including Orange juice), their icons, defaults and order are preserved.
- Reorganized the liquid-edit popup into a compact two-column editor with a full-row SVG file picker.
- Improved compact dashboard alignment: chart confined to the right column, Add right-aligned, history date controls and Excel export left-aligned. Larger scrollable history area.
- The existing 9-worksheet Excel export adds a **Visible in picker** column in Liquid Types.

## Upgrade through HACS only
1. Back up Home Assistant, including `.storage/jw_daily_hydration_log.*` and dashboard settings.
2. In HACS → jwDaily Hydration Log → Redownload → Need a different version? choose **v1.1.0-beta.5**. Enable prereleases for the repository when needed.
3. Restart **Home Assistant Core** completely and refresh the browser with `Ctrl+Shift+R`.
4. Confirm the footer shows **v1.1.0-beta.5**. Open Add drink → Manage liquid types. Hide e.g. Milk, verify prior Milk entries remain in the history, then Restore Milk.
5. Verify editing a name, icon, default volume and button order; check the updated Excel export.

**No code-file ZIP install.** This GitHub release is only for HACS distribution. The original Personal Hydration Manager is not changed. Upgrading the code does not itself alter stored drinks. Edits/deletions of *drink moments* from the popup remain permanent, as previously agreed.

Rollback code through HACS to v1.1.0-beta.4 if needed; restoring drink-data changes requires a separate HA backup.
