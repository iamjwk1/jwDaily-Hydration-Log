# jwDaily Hydration Log v1.1.0-beta.44 — test release

Published as a **prerelease**, not a stable release. Based on v1.1.0-beta.43.

## Implemented changes

1. **Edit profile → Add drink moment:** two profile-specific visibility settings, `Show Quick buttons` and `Show Liquid types and Cup types`. Existing and new profiles default to both checked. Users may select either group or both; at least one group must remain enabled. If no valid Quick button exists, manual Liquid/Cup selectors are shown as a safe fallback.
2. **Add drink moment manual fields:** Custom amount, Date (DD-MM-YYYY) and Time (24-hour) use a single horizontal row with matching 50px field heights on desktop; on smaller screens columns wrap without being cropped.
3. **Maintain cup types:** remove extra `Hidden` text beside the cup name. Eye/eye-off icon is the sole visible status marker; Hide/Show functionality and delete protection remain unchanged.
4. **Edit Quick Buttons:** remove redundant `(Hidden)` text in the type name; eye icon continues showing state.

## Compatibility and safety

- Settings persist in Home Assistant ConfigEntry options, scoped by profile. Copied profiles may inherit the source profile's display preferences; no history is copied.
- Exported full ZIP backups include the new profile preferences. Older ZIPs lacking these fields restore to the safe default (both enabled). Invalid types and both-hidden settings are rejected before writes.
- Do not alter canonical drink volumes, original ledger IDs, daily archives, liquid and cup catalogs, Excel export or existing backup/restore workflows.
- No removal of legacy migration or rollback code. Four previous live acceptance checks and technical debt remain documented in `BETA44_PENDING_ACCEPTANCE.md`.

## QA gates

Native Python source/restore/Excel/migration checks; new profile preference and WebSocket persistence test; Chromium Add drink visibility combinations, fallback, input geometry and Hidden status tests across mobile and desktop widths; HACS and Home Assistant Hassfest; deterministic ZIP member-byte equality, CRC and SHA-256 checksum.

**Live HA acceptance, historical data and actual dashboard configuration remain to be verified.**
