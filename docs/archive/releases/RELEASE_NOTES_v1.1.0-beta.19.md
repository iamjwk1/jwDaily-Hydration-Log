# jwDaily Hydration Log v1.1.0-beta.19

Small, focused HACS beta update based on the complete working beta.18 integration.

- **Glass enlarged:** the main card glass becomes ~10-13% wider. The adjacent chart remains on the right at usable card widths; the daily total, red target and drink-moment count remain readable.
- **Excel button smaller:** the bottom-left **Export to Excel (.xlsx)** button is fixed at 28 CSS pixels high. The version stays bottom-right on the same compact footer.
- **No data changes:** existing histories, profiles, preferences, Add/Edit/Delete controls, type/volume managers and both chart cards are preserved.
- **Excel remains unchanged:** valid OOXML, correct column widths, dynamic liquid types, orange historical-only type headers and 44-point Daily intake header.

Release gates include Python functional tests, Excel/Office OOXML, frontend interactions, Chrome layout geometry (including explicit glass and export button measurements), both charts, color consistency, Hassfest, HACS and full ZIP CRC/SHA-256 integrity.

Chrome may block local insecure HTTP downloads; HTTPS/Nabu Casa works as previously verified.
