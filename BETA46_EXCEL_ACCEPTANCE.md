# beta.46 Excel export acceptance contract

**Reference:** user's 20261120-1703 workbook, Excel Place in Cell for Liquid icons.

- [ ] Confirm export opens in desktop Excel without warnings or repaired XML
- [ ] Six tabs match reference, with current HA data for selected profile(s)
- [ ] All data rows are 18pt and vertically centered
- [ ] Hydration log header row 11 is 38pt
- [ ] Daily intake non-liquid widths unchanged; only liquid columns fit values
- [ ] Images are native **Place in Cell** (not overlay shapes) and follow sort/filter
- [ ] Six table filters and headers work
- [ ] Historical entries, original IDs, archive day totals remain intact
- [ ] L, mL, fl oz correctly exported
- [ ] Other last in Daily intake

**Automated source QA vs live acceptance:** Source and workbook structure checks can pass without proving desktop Excel's renderer or production HA data. Beta.46 is a test release pending your live approval.
