# jwDaily Hydration Log v1.1.0-beta.21

Complete Home Assistant / HACS test integration based on beta.19, incorporating the beta.20 history change and all screenshot corrections.

## Corrected
- Right-align blue intake immediately to the left of the cup at a fixed 24 CSS px on narrow and wide cards.
- Move glass slightly left on wide cards, preserving a safe gap on narrow cards.
- Move Today by liquid left, enlarge the horizontal graph bars and right-align bar volumes with the Add drink button.
- Pin Add drink to the bottom of the hero/cup row, eliminating its previous blank space.
- Target and remaining amount use equal 17 CSS px HTML labels independent of SVG size.
- Drink history displays HH:MM, while internal records and edit forms keep seconds.
- Small Excel export button on far left and version number on far right of the compact footer.
- No red/blue reference guide lines or demo/placeholder content is shipped.

## Preserved
Stored histories, profiles, settings, Add/Edit/Delete, liquid/volume managers, date input and calendar, up-to-five scrollable history entries, both chart cards, chart colors, Excel formulas and data including Date+time width 19 and Daily intake header height 44pt, dynamic active and orange historical liquid columns.

## Browser security
Chrome may reject XLSX downloads from unsecured local HTTP. The existing Nabu Casa HTTPS URL is confirmed to download successfully; beta.21 does not disable browser protection.

## Quality gates
Python/JavaScript integrity, Chrome geometry and modal testing at multiple card widths, Excel Office-XML and CRC validation, HACS and Hassfest compatibility, ZIP CRC and SHA-256. Visual acceptance in the user's own HA instance remains to be confirmed.
