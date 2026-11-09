# jwDaily Hydration Log v1.1.0-beta.6 — HACS pre-release

## Corrected layout
- Left: today's blue consumed volume, aligned with the glass liquid level.
- Centre-left: open glass with persistent red target label and dashed line, remaining volume and animated liquid.
- Right: complete horizontal bar chart by today's liquid type with visible numeric amounts (not cut off).
- **+ Add drink** is smaller, directly below the chart. Drink count immediately below the glass.
- No extra full-width button section. Date navigation and Excel export remain left-aligned.
- Responsive layout retained for narrower dashboards and phones.

## Upgrade
Back up Home Assistant, then install **v1.1.0-beta.6** from HACS using the prerelease/version selector. Restart Home Assistant Core and hard-refresh your browser. Keep the existing profile. This beta changes frontend layout only, not historical drinking data.
