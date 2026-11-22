# jwDaily Hydration Log v1.1.0-beta.43 — Dashboard correctness and code audit
- Includes accepted beta.42 follow-up PR #22: Edit profile modal maximum width 740px instead of 940px, without changing inputs, quick buttons or data.
- Fixes hourly chart daily-target values for L/fl oz profiles. Uses canonical sensor attribute `target_ml`, converting native sensor state only as fallback.
- Uses Home Assistant configured timezone for chart history date requests.
- Uses Home Assistant profile-local date when validating imported drinks and day archives around midnight.
- Corrects outdated README release instructions; older docs remain clearly archived.
- No data-schema migration; preserved export workbooks, ZIP restore scopes, profile IDs and history ledger.
- Details on code/dashboard scope, strengths and remaining technical debt are in `AUDIT_v1.1.0-beta.43.md`.
- Validations: full native regression, Chromium UI/chart smoke tests, HACS and Hassfest, release CRC/SHA-256. **Live Home Assistant data and dashboard configuration are not inspected by CI.**
