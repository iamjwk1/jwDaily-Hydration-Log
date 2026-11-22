# jwDaily Hydration Log v1.1.0-beta.11 — HACS prerelease

This beta is a complete integration release based on v1.1.0-beta.10. It contains FIX-01 through FIX-09, the user-requested Excel column widths, uniform button styling and modal compaction.

**Dashboard**
- Day total, open cup and **X drink moments** remain on the left; by-liquid bar chart is on the right at normal/wide card widths and stacks only on narrower cards.
- Undo last drink is completely removed from the main card; no empty button placeholder.
- Compact, uniform 38px edit-enabled history rows retain separators, dates and volumes.
- Normal action, choice and selection buttons use #B3E5FC; Manage liquid types/volume buttons are neutral #EEEEEE; the calendar date entry stays white #FFFFFF.
- The two Manage dialogs are narrower with aligned rows, compact forms and right-aligned footer actions. Liquid/volume choices share identical fonts and compact padding.
- Hover, selected, focus, disabled states remain distinct.

**Excel**
- Hydration log column C/H: Profile 16, Age 6, Gender 9, Target 9, Liquid name 17, Volume 11.
- Daily Totals B:Q: Date 16, Profile 15, Age 7, Gender 9, Full day 6, Target 10, Drink count 9, Volume 11, % 6 and all seven liquid columns 10.
- Wrapped two-line Excel headers with taller header rows. Four sheets, existing formulas, history and file naming format retained.

**Data safety**
Existing profiles, drink entries, custom liquid types, ordering/default amounts, target history, chart sensors and Android time entry are not modified by the release itself. A Home Assistant restart and hard browser refresh are recommended after HACS upgrade.

**Installation**
1. Back up Home Assistant and the hydration profile.
2. HACS > jwDaily Hydration Log > Redownload > Need a different version? > v1.1.0-beta.11.
3. Restart Home Assistant Core. Hard refresh the browser (Ctrl+Shift+R).
4. Review both card widths, dialogs and exported workbook in Microsoft Excel. Automated QA cannot establish actual use on your HA or Excel Desktop.

The downloadable integration ZIP is suitable for a manual /config deployment and contains the complete custom_components/jw_daily_hydration_log tree, README and license files, plus the version changelog and documentation. A separate .sha256 file provides integrity reference. Stable v1.0.2 stays unchanged.
