# jwDaily Hydration Log v1.1.0-beta.39 — frontend/backend version guard correction

This prerelease corrects one defect in beta.38: the Add drink moment dialog incorrectly rejected the current backend version.

- Fixed the frontend's capabilities check to accept backend `1.1.0-beta.39` rather than hard-coded `1.1.0-beta.37`.
- Synchronized the card display, manifest and backend constant to `1.1.0-beta.39`.
- Updated browser test fixtures to match the new release and added a regression check for guard/manifest parity.
- No intentional changes to drink history, settings, imports, exports, migration, layout, or calculation logic.

## Release validation

Publication is gated by the Python/Node regression suite, Chromium browser tests, HACS and Hassfest. Live Home Assistant acceptance remains required after installation. Existing historical-data/backup acceptance items remain open.
