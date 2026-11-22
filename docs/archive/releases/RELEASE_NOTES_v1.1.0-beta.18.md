# jwDaily Hydration Log v1.1.0-beta.18

Complete HACS test release, based on v1.1.0-beta.17. Addresses visual review of both charts and the main intake card without changing data storage or APIs.

- Deterministic consistent liquid colors in Today by hour and Last 7 days.
- Responsive charts with clearer y-axis labels, compact card and version bottom-right.
- Weekly y-axis now ends at 3,000 mL for highest bar of 2,550 mL; daily totals remain above bars.
- Main card: five 28px drink history rows, compact date selector and export button, larger drink moments and slightly closer intake total.
- Excel export preserved: Hydration log Date+time width 19; Daily intake row 11 44 pt; dynamic present and historical-only columns, orange retired headers.
- Existing profile data, volumes, Add/Edit/Delete, calendar and graph cards preserved. No migrations.
- Browser security: local HTTP may still block XLSX downloads; access via HTTPS/Nabu Casa (already confirmed operational).

Release gates: Python+Excel OOXML, JS interactions, main-card Chrome geometry, both chart types, cross-chart color consistency, HACS, Hassfest, full ZIP CRC and SHA-256.
