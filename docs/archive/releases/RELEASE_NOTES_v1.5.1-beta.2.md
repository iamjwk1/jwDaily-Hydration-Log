# jwDaily Hydration Log v1.5.1-beta.2 — Profile Save reload-race fix

Date: 22 November 2026. This is a prerelease; v1.5.0 remains stable and beta.1 is retained.

## Fixed

When a user opened **Settings → Manage profiles → Edit profile**, disabled **Show Liquid types and Cup types**, and clicked **Save profile**, the previous backend updated Home Assistant ConfigEntry options. The unconditional options update listener reloaded the entire integration, temporarily removing the profile coordinator from Home Assistant's profile map. The card then immediately called profile history and could show:

`Unknown jwDaily Hydration Log profile: jan_willem`

The disappearance is a reload race, not a validation error for that visibility option.

- The options update listener now applies changes to the two Add drink visibility switches **live** without a full integration reload. The listener permits only unchanged age/gender/unit values that may have been copied into the options by the editor; changed identity or unrelated options still use the original reload mechanism.
- The card now reads back the profile list and active profile history **together** after a successful save. For a legitimate reload, transient empty lists and unknown-profile errors are retried without incorrectly presenting them as a failed save.
- The allowed combinations remain **Quick buttons only**, **Liquid/Cup selectors only**, or **both visible**. Neither selector group may be hidden simultaneously.
- Profile IDs, existing drink history, Cup and Liquid definitions, Excel export (including beta.1 Yes/No and column autofit), storage, backup and import/restore are unchanged.

## Quality checks

Native test: editing an existing profile `jan_willem` with only visibility toggles saves the correct flags without calling Home Assistant `async_reload` or losing the profile; both disabled is rejected; genuine other option updates still trigger reload.

Chromium UI regression: a list request first returns an empty profile map, history temporarily throws `Unknown jwDaily Hydration Log profile`, then both recover; user-visible error remains empty.

Release gated on full Python storage/migration/Excel regression, Chromium, HACS, and Home Assistant hassfest. ZIP integrity and SHA-256 are checked before publishing.

## Install and verification

1. Create a Home Assistant backup and download the integration's verified Full Backup ZIP.
2. In HACS → jwDaily Hydration Log → Redownload → Need a different version → select **v1.5.1-beta.2**.
3. Restart Home Assistant Core; hard-refresh the dashboard.
4. Under **Manage profiles**, edit the existing profile, turn off **Show Liquid types and Cup types**, and save.
5. Confirm the Manage profiles list remains populated and no red unknown-profile message is shown. Open **Add drink** and confirm only Quick buttons appear.
6. Re-enable Liquid/Cup selectors and confirm both groups return, without changing drink history.

No live Home Assistant instance was modified by source development.
