"""Beta32 Excel contract: exact headers, structured table, targets, icon PNGs."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from io import BytesIO
from pathlib import Path
import importlib.util
import sys,types
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]/"custom_components/jw_daily_hydration_log"
pkg=types.ModuleType("jwdhl_excel_beta32")
pkg.__path__=[str(ROOT)]
sys.modules[pkg.__name__]=pkg
for name in ("const","excel_icons","excel"):
    spec=importlib.util.spec_from_file_location(pkg.__name__+"."+name,ROOT/(name+".py"))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
from jwdhl_excel_beta32 import excel

LIQUIDS=[
    {"id":"water","name":"Water","icon_mdi":"mdi:water","color":"#3399CC","custom":False,"hidden":False},
    {"id":"other","name":"Other","icon_mdi":"mdi:glass-water","color":"#777777","custom":False,"hidden":False},
    {"id":"coffee","name":"Coffee","icon_mdi":"mdi:coffee","color":"#CC7722","custom":False,"hidden":False}
]
CUPS=[{"id":"cup_glass","name":"Glass","default_volume_ml":250,"icon_mdi":"mdi:glass-water","hidden":False}]
def profile(name,goal,vol,liquid):
    return {
        "config":{"name":name,"age":40,"gender":"male","unit":"mL"},
        "entry_id":name,"date":"2026-11-12","target_ml":goal,"target_override_ml":goal,
        "consumed_ml":vol,"manual_consumed_ml":vol,"source_contribution_ml":0,
        "liquid_definitions":deepcopy(LIQUIDS),"cup_types":deepcopy(CUPS),
        "liquid_colors":{},"hidden_builtin_liquids":[],"quick_buttons":[
            {"id":"q_"+name,"liquid_type_id":"water","cup_type_id":"cup_glass",
             "label_mode":"automatic","label":"Water (Glass)","hidden":False}],
        "records":[{"kind":"drink","id":"r_"+name,
            "timestamp":"2026-11-12T10:00:00+01:00","volume_ml":vol,
            "liquid_type_id":liquid,"cup_type_id":"cup_glass",
            "cup_default_volume_ml_at_log":250,"quick_button_id":"q_"+name}],
        "daily_archive":{}
    }

p1=profile("Jan-Willem",2100,250,"water")
p2=profile("Second profile",3100,125,"other")
when=datetime(2026,11,13,13,0,tzinfo=timezone.utc)
raw=excel.export_xlsx([p1,p2],when=when)
assert raw.startswith(b"PK")
ns={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
def cells(worksheet):
    out={}
    for c in worksheet.findall(".//m:sheetData/m:row/m:c",ns):
        t=c.find(".//m:t",ns)
        v=c.find("m:v",ns)
        out[c.get("r")]=t.text if t is not None else (v.text if v is not None else "")
    return out

with ZipFile(BytesIO(raw)) as book:
    assert book.testzip() is None,"CRC mismatch"
    xmls=[ET.fromstring(book.read(f"xl/worksheets/sheet{i}.xml")) for i in range(1,5)]
    log=cells(xmls[0]);daily=cells(xmls[1]);types=cells(xmls[2]);prefs=cells(xmls[3])
    assert log["I11"]=="Cup used"
    assert log["H11"]=="Volume\n(mL)"
    assert log["I12"]=="Glass (250 mL)" and log["I13"]=="Glass (250 mL)"
    assert "Current Cup default" not in book.read("xl/worksheets/sheet1.xml").decode()
    assert "Quick button" not in book.read("xl/worksheets/sheet1.xml").decode()
    assert log["F12"]=="2100" and log["F13"]=="3100"
    firstrows=xmls[0].findall(".//m:sheetData/m:row",ns)
    assert all(float(row.get("ht","0"))==44 for row in firstrows if int(row.get("r"))>=11)
    assert xmls[0].find(".//m:c[@r='C4']",ns).get("s") != xmls[1].find(".//m:c[@r='C4']",ns).get("s")
    table=ET.fromstring(book.read("xl/tables/table1.xml"))
    assert table.attrib["ref"]=="B11:I13",table.attrib["ref"]
    names=[x.get("name") for x in table.findall(".//m:tableColumn",ns)]
    assert names[-1]=="Cup used" and len(names)==8,names
    dh=[daily[f"{col}11"] for col in ("K","L","M")]
    assert dh[-1].startswith("Other"),dh
    assert len([p for p in book.namelist() if p.startswith("xl/media/liquid")])==3
    assert "xl/drawings/drawing1.xml" in book.namelist()
    for media in [p for p in book.namelist() if p.startswith("xl/media/liquid")]:
        data=book.read(media)
        assert data[:8]==b"\x89PNG\r\n\x1a\n"
        assert int.from_bytes(data[16:20],"big")==48 and int.from_bytes(data[20:24],"big")==48
    assert types["A2"]=="All profiles" and types["E1"]=="Icon graphic"
    assert len([v for k,v in types.items() if k.startswith("B") and k[1:].isdigit() and int(k[1:])>1])==3
    assert "Source mode" not in book.read("xl/worksheets/sheet4.xml").decode()
    assert "Pregnancy" not in book.read("xl/worksheets/sheet4.xml").decode()
    assert "Quick button count" in book.read("xl/worksheets/sheet4.xml").decode()
    assert "Jan-Willem" in book.read("xl/worksheets/sheet4.xml").decode()
    assert "Second profile" in book.read("xl/worksheets/sheet4.xml").decode()

p_only=excel.export_xlsx([p1],when=when)
with ZipFile(BytesIO(p_only)) as book:
    assert book.testzip() is None
    assert "Second profile" not in book.read("xl/worksheets/sheet1.xml").decode()
assert excel.export_filename("Europe/Amsterdam",when,profile_name="Jan-Willem").endswith(
    "jwDaily Hydration Log - Jan-Willem.xlsx")
print("BETA32_EXCEL_HEADERS_PROFILE_SCOPE_ICONS_ZIP_CRC_PASS")
