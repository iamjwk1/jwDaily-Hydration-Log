# jwDaily Hydration Log v1.1.0-beta.17

Full installation beta based on v1.1.0-beta.16.

- Rebuilt the two chart cards using accessible SVG charts, explicit mL y-axes and 24 individual hour labels (1–24) or seven human-readable dates (e.g. 7 Nov).
- Hourly legend includes cumulative mL per liquid; the chart also shows daily total compared with the HA-configured target when available.
- Seven-day chart labels each nonzero stack with its total in mL and keeps its version in the lower-right footer.
- Main-card history uses five compact 30px data rows with a sticky 30px header; the rest is scrollable. Date selector and Excel button are smaller, footer aligned.
- All previous Excel export workbook formatting, dynamic liquid columns, 44pt Daily intake header, CRUD and profile configuration remain unchanged.
- No data migrations or new placeholder data.

Security note: Chrome can warn about an insecure downloaded file if Home Assistant is accessed over HTTP or a reverse proxy has a mixed-content configuration. Such a transport warning cannot reliably be overridden by card JavaScript; serve HA over correctly configured HTTPS.