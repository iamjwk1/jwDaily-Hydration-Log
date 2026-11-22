# jwDaily Hydration Log v1.1.0-beta.10 — HACS pre-release

Complete visual and Excel readability corrections requested after beta.9.

**Dashboard:** Blue current/selected-day intake is fixed at 24px on large and small cards and positioned beside — never over — the left-positioned glass. Drink moments **remains directly under the glass**. Bar chart values remain visible on the right. Smaller Add drink button is at the bottom-right. Drink-history rows are **40 CSS px**, equal-height, with centered content and the existing large bold DD-MM-YYYY selector. Excel export button is small and directly left-aligned under the table. No persistent 'Drink saved' status line or reserved empty space. Enabled secondary buttons look active with blue-tinted borders and backgrounds.

**Excel:** Retains the reference four sheets, desktop-compatible sheet XML, date/formula formatting, and timestamp filename `YYYYMMDD-HHMM jwDaily Hydration Log - All Data.xlsx`. The hydration log is now strictly chronological, oldest → newest, regardless of record edits or storage order. Wider settings, volumes, and log columns prevent cropped headers such as SVG Image and Custom configured.

**Preserved:** Stored profiles, sensor identities, history, liquid types and defaults, icon management, selected historical day summaries, open/animated glass and red target, Android numeric time input, ApexCharts data sensors.

**Quality gates:** Python/backend, JavaScript/browser shell, independent four-sheet Excel ZIP/XML/formula checks, Hassfest, HACS validation and actual Chromium element positions and row heights at 888, 721, 412 and 360 px.

**Upgrade:** Back up HA (including hydration records), then HACS → jwDaily Hydration Log → ⋮ → Redownload → Need a different version? → v1.1.0-beta.10. Fully restart HA Core, hard refresh browser. Validate on your screen and in Microsoft Excel Desktop. Automated tests cannot replace live acceptance in your HA/Excel. Stable v1.0.2 remains available.

**ApexCharts examples:** `examples/apexcharts-jwdhl-v1.1.0-beta.9.md` in this release.
