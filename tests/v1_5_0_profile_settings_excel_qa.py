"""v1.5.0: Excel Settings - Profiles exports live Add drink visibility settings."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import importlib.util
import sys
import types

root = Path(__file__).resolve().parents[1] / "custom_components" / "jw_daily_hydration_log"
pkg = types.ModuleType("v150_excel_qa")
pkg.__path__ = [str(root)]
sys.modules[pkg.__name__] = pkg
for name in ("const", "excel_reference_format", "excel_icons", "excel"):
    spec = importlib.util.spec_from_file_location(pkg.__name__ + "." + name, root / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
from v150_excel_qa import excel

def profile(name, slug, quick_visible=None, selectors_visible=None):
    cfg = {"name": name, "unit": "mL", "age": 36, "gender": "female"}
    if quick_visible is not None:
        cfg["show_add_quick_buttons"] = quick_visible
    if selectors_visible is not None:
        cfg["show_add_liquid_cup_types"] = selectors_visible
    return {
        "config": cfg, "entry_id": "entry_" + slug, "slug": slug,
        "date": "2026-11-21", "target_ml": 2000, "target_override_ml": 2000,
        "consumed_ml": 0, "daily_archive": {}, "source_readings": [],
        "liquid_colors": {},
        "liquid_definitions": [
            {"id": "tea", "name": "Tea", "icon_mdi": "mdi:tea",
             "color": "#EDB92C", "custom": False}
        ],
        "cup_types": [{"id": "glass1", "name": "Glass", "default_volume_ml": 220,
                       "icon_mdi": "mdi:cup"}],
        "quick_buttons": [{"id": "quick_" + slug, "cup_type_id": "glass1",
                           "liquid_type_id": "tea", "label": "Tea (Glass)"}],
        "records": []
    }

profiles = [
    profile("Legacy defaults", "legacy"),           # absent flags mean both on
    profile("Quick disabled", "quick_off", False, True),
    profile("Selectors disabled", "selectors_off", True, False),
]
source = deepcopy(profiles)
fixed = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)
workbook = excel.export_xlsx(profiles, when=fixed)
assert profiles == source, "Excel export must never modify Home Assistant records/settings"

# Visibility options must not affect any of the first five worksheets.
reference_profiles = deepcopy(profiles)
for p in reference_profiles:
    p["config"].pop("show_add_quick_buttons", None)
    p["config"].pop("show_add_liquid_cup_types", None)
unchanged_book = excel.export_xlsx(reference_profiles, when=fixed)

ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
def cell_text(cell):
    return "".join(node.text or "" for node in cell.iter(ns + "t"))

with ZipFile(BytesIO(workbook)) as z, ZipFile(BytesIO(unchanged_book)) as previous:
    assert z.testzip() is None and previous.testzip() is None
    assert len([x for x in z.namelist() if x.startswith("xl/tables/table")]) == 6
    for i in range(1, 6):
        for component in (f"xl/worksheets/sheet{i}.xml", f"xl/tables/table{i}.xml"):
            assert z.read(component) == previous.read(component), component
    ws = ET.fromstring(z.read("xl/worksheets/sheet6.xml"))
    table = ET.fromstring(z.read("xl/tables/table6.xml"))
    assert ws.find(ns + "dimension").get("ref") == "B2:K11"
    assert table.get("ref") == "B8:K11"
    assert table.find(ns + "autoFilter").get("ref") == "B8:K11"
    headers = [cell_text(cell) for cell in ws.find(ns + "sheetData").findall(ns + "row[@r='8']/" + ns + "c")]
    assert len(headers) == 10, headers
    assert headers[-2:] == ["Show Quick buttons", "Show Liquid types and Cup types"], headers
    columns = [col for col in ws.find(ns + "cols")]
    # Reference metadata may group original columns into <col min=... max=...> ranges.
    assert (columns[-2].get("min"), columns[-2].get("max")) == ("10", "10")
    assert (columns[-1].get("min"), columns[-1].get("max")) == ("11", "11")
    assert (columns[-2].get("width"), columns[-1].get("width")) == ("24", "31")
    expected = {
        9: ("Legacy defaults", "Yes", "Yes"),
        10: ("Quick disabled", "No", "Yes"),
        11: ("Selectors disabled", "Yes", "No"),
    }
    cells = {cell.get("r"): cell for cell in ws.iter(ns + "c")}
    for r, (name, quick, selectors) in expected.items():
        assert cell_text(cells[f"B{r}"]) == name
        assert cell_text(cells[f"J{r}"]) == quick
        assert cell_text(cells[f"K{r}"]) == selectors
    assert all(float(row.get("ht", 0)) == 18 for row in
               ws.findall(ns + "sheetData/" + ns + "row") if int(row.get("r")) >= 9)
    for p in z.namelist():
        if p.endswith((".xml", ".rels")):
            ET.fromstring(z.read(p))
print("V1_5_0_PROFILE_SETTINGS_EXCEL_QA_PASS", len(workbook), "bytes", "6 sheets", "CRC_OK")
