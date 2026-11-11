# jwDaily Hydration Log v1.1.0-beta.22 — HACS pre-release

Full integration release based on the verified v1.1.0-beta.21 tag.

## Main card
- X drink moments centered under the actual cup instead of the entire left grid column.
- Blue intake total kept at 24 CSS px and aligned with the visible cup outline at all tested widths.
- Add drink moves up: no fixed 224px minimum right-column height or absolute positioning.
- Left-shifted Today by liquid title/names with maintained bar and volume alignment; subtle liquid-color dots.
- Five scrollable 28px history records; HH:MM displayed, HH:MM:SS stored and used in editor.
- Compact 28px Excel button and right-aligned version retained.

## Charts
- Today by hour: readable y axis; non-colliding responsive 1–24 hour labels; per-liquid totals and daily target context; click/tap/keyboard-accessible hourly breakdown.
- Last 7 days: readable separated y-axis mL and tick values; adaptive scale; totals above bars, e.g. 5 Nov; coffee and orange juice colors clearly different.
- Both chart legends follow today's descending volumes; historical-only types follow by total period volume.
- Bars open real per-liquid detail on selection.
- An unrecorded day displays — (No data), whereas a recorded zero day displays 0 mL, based on an additive, read-only has_data field from the integration.

## Unchanged
- No data migrations or destructive writes; all history, settings, Add/Edit/Delete, date navigation and liquid/volume management remain.
- Existing four-sheet Excel OOXML export, Date+time 19, dynamic liquid headers and Daily intake header 44 pt remain unmodified.
- HTTPS/Nabu Casa Excel downloads operate; Chrome can block downloads through insecure local HTTP.

## Mandatory gates
- Python, Excel/OOXML, frontend interactions, Chromium main-card geometry and chart accessibility tests, browser console, Hassfest and HACS, ZIP CRC, SHA-256.
- Live visual acceptance remains with the Home Assistant instance owner.
