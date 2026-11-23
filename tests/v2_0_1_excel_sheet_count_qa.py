"""v2.0.1: the UI must accurately describe the six-sheet Excel workbook."""
from pathlib import Path
import json
import re

root=Path(__file__).resolve().parents[1]
component=root/"custom_components/jw_daily_hydration_log"
manifest=json.loads((component/"manifest.json").read_text(encoding="utf-8"))
assert manifest["version"]=="2.0.1",manifest["version"]
js=(component/"www/jwdaily-hydration-log-card.js").read_text(encoding="utf-8")
excel=(component/"excel.py").read_text(encoding="utf-8")

# Both export UI paths: the user-facing export dialog and secondary Settings path.
modal=("The workbook contains six sheets: Hydration log, Daily intake, and "
       "settings for Liquid types, Cup types, Quick buttons and Profiles.")
settings=("Export the six-sheet Excel workbook with Hydration log, "
          "Daily intake and four settings sheets.")
assert modal in js,"Export to Excel modal does not describe six worksheets"
assert settings in js,"Secondary Settings Export still has an incorrect count"
assert not re.search(r"four[\s-]+sheets?",js,re.IGNORECASE),"Obsolete four-sheet text remains"

# The workbook builder must still enumerate exactly the same six sheet sources.
assert "all_rows=[logrows,drows,typesrows,cupsrows,quick_rows,profrows]" in excel
assert "for sheet_index, sheet_rows in enumerate(all_rows,1)" in excel
assert "[logrows,drows,typesrows,cupsrows,quick_rows,profrows]" in excel

assert (root/"docs/releases/v2.0.1.md").is_file()
assert "six-sheet" in (root/"docs/releases/v2.0.1.md").read_text()
print("V201_EXCEL_SIX_SHEET_UI_QA_PASS")
