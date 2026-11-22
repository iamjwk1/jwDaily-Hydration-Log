# jwDaily Hydration Log v1.1.0-beta.42

**User acceptance corrections** for the published beta.41. No schema migration or drink ledger change.

- **Edit profile:** shows `Edit profile - <profile name>`, compact profile inputs on one row where space permits, no horizontal separators, pencil Edit Quick Buttons action with tooltip, and Quick Buttons in the same persisted maintenance order.
- **Maintain liquid types:** removes excess horizontal gaps; Liquid type header aligned to names; Times used values centered; 8px icon/name spacing; existing icon actions and move tooltips preserved.
- **Edit liquid type:** configured icon colour (black fallback) used by the live Preview, icon sample and shared selector. The icon-colour control is beside Choose icon with a Default (black) action. Liquid name input uses standard border/weight.
- **Maintain cup types:** narrower grid, centered Default volume / Times used, title aligned to names; icon actions retained.
- **Edit cup type:** icon colour picker and Default (black), consistent with Choose icon preview and original saved state.
- **Data & Backup:** equal-width Export Excel and Create backup buttons; underlying ZIP operations unchanged.
- **Delete liquid type:** short confirmation without redundant deletion-policy text; server-side deletion eligibility unchanged.
- **Edit Quick Buttons:** compact consistent grid, centered Cup type / Cup volume, icon-only action buttons with tooltips, no horizontal rules. Maintained order remains authoritative.

## No changes to data and safety
Original drink IDs, timestamp and millilitre totals, profiles, XLSX exports, the native JSON storage representation, backups and selective restore safeguards are unchanged. The formerly visible standalone JSON import/export UI stays removed.

## QA and release
Automated validation includes native Python + JS syntax, historical data/Excel/backup regression, strict version guard, Chromium UI tests on narrow/medium/desktop viewports, HACS and Hassfest. ZIP must pass CRC, all member content comparisons, SHA-256. Home Assistant live installation acceptance and four prior historical-data/restore checks remain open.
