# jwDaily Hydration Log v1.1.0-beta.31 — permanent Quick button delete and cleaner settings popups

This beta addresses the Cup types and Quick buttons settings issues observed in v1.1.0-beta.30.

## Interface

- **Quick buttons:** a compact **Hide/Restore** control now appears immediately before **Edit**, followed by **Delete**. Permanent deletion has its own clear confirmation and a Cancel control.
- **Cup types:** a compact **Hide/Restore** control appears immediately before **Edit**.
- Only one **Cup types** heading and one **Quick buttons** heading are displayed in their respective popups.
- Quick-row controls wrap at narrow dashboard widths. Confirmed in Chromium at 360, 420, 540, 720 and 950 CSS pixels.

## Safe Quick button deletion

- Removes the shortcut entry and leaves drink timestamps, IDs, actual volumes, native Liquid and Cup references, and existing daily totals unmodified.
- Historical drink records using the deleted shortcut retain a human-readable **Quick button label at log time**, instead of a broken Quick ID. The snapshot appears in Excel and survives Data JSON and Full Backup restores.
- A cancelled deletion has no effect. A storage-write error rolls back both shortcut configuration and affected record metadata.
- New drink records created through Quick buttons save their label at logging time, so future catalog renames or deletions do not erase this provenance.

## Compatibility

- Native model 2, Settings/Data JSON import and export, Full Backup ZIP, four-sheet XLSX, and beta.30 guarded legacy cleanup remain available.
- Upgrade normally from beta.30 after taking a Home Assistant backup and a verified Full Backup ZIP. Upgrades directly from old pre-finalization profiles still require beta.29 data-model finalization first.
- No automatic data deletion or Quick button removal occurs on installation.

## Quality gates

Independent Python storage/history/Excel regressions, Chromium responsive and real Delete/Cancel UI tests, HACS, Hassfest, deterministic ZIP checksum and CRC before publishing the prerelease. Live Home Assistant acceptance remains a separate step.
