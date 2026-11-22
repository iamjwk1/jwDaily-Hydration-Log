# jwDaily Hydration Log v1.1.0-beta.7 — HACS pre-release

## Date/time correction
- A later 24-hour time on today's HA-local date is allowed (e.g. 21:30 entered at 13:00).
- A future calendar date is never allowed; dates in the past remain selectable.
- Drink entries are stored immediately for the selected date; a later time does not schedule a future action.
- Date-only checks now run in both the frontend and Python backend, with existing nonexistent daylight-saving-time guards retained.

## Layout
Includes beta.6's reference screenshot layout: blue total near the left-positioned open glass; full today-by-liquid chart on the right; smaller Add control beneath the chart; left-aligned date navigation and Excel export.

## HACS
Back up HA including stored hydration data before selecting v1.1.0-beta.7 in HACS (Redownload → Need a different version?). Restart HA Core and reload the browser after installing. Historical registrations and the existing profile are unchanged. Stable v1.0.2 remains available.
