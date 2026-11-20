"""Beta46 Excel six-sheet contract, true Place in Cell images, heights and alignment."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import importlib.util
import sys
import types
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]/"custom_components"/"jw_daily_hydration_log"
pkg=types.ModuleType("beta46_excel_test");pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
for name in ("const","excel_icons","excel"):
    spec=importlib.util.spec_from_file_location(pkg.__name__+"."+name,ROOT/(name+".py"))
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
from beta46_excel_test import excel

N="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
def get(cell):
    ins=cell.find(N+"is")
    return "".join(x.text or "" for x in ins.iter(N+"t")) if ins is not None else (
           cell.find(N+"v").text if cell.find(N+"v") is not None else "")
def values(sheet):
    return {c.get("r"):get(c) for c in sheet.iter(N+"c")}
def sample(name):
    return {
      "config":{"name":name,"unit":"mL","age":58,"gender":"male"},
      "entry_id":name,"date":"2026-11-19","target_ml":2000,"target_override_ml":2000,
      "consumed_ml":180,"liquid_colors":{},"source_readings":[],"daily_archive":{},
      "liquid_definitions":[
       {"id":"coffee","name":"Coffee","icon_mdi":"mdi:coffee","custom":False,"color":"#A67800"},
       {"id":"water","name":"Water","icon_mdi":"mdi:water","custom":False,"color":"#55CCFF"},
       {"id":"other","name":"Other","icon_mdi":"mdi:glass-water","custom":False,"color":"#9C9C9C"}],
      "cup_types":[{"id":"glass","name":"Glazen beker","default_volume_ml":180,
                    "icon_mdi":"mdi:cup","hidden":False}],
      "quick_buttons":[{"id":"q1","liquid_type_id":"coffee","cup_type_id":"glass",
                         "label":"Coffee (Glazen beker)","hidden":False}],
      "records":[{"kind":"drink","id":name+"_drink_1","timestamp":"2026-11-19T09:30:00+01:00",
                  "volume_ml":180,"liquid_type_id":"coffee","cup_type_id":"glass",
                  "cup_default_volume_ml_at_log":180}]
    }
profiles=[sample("QA1"),sample("QA2")]
original=deepcopy(profiles)
raw=excel.export_xlsx(profiles,when=datetime(2026,11,20,12,tzinfo=timezone.utc))
assert profiles==original,"Export mutated the source records or profiles"
with ZipFile(BytesIO(raw)) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    assert len([n for n in names if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")])==6
    assert "xl/drawings/drawing1.xml" not in names
    assert "xl/worksheets/_rels/sheet3.xml.rels" in names
    assert b"drawing" not in z.read("xl/worksheets/_rels/sheet3.xml.rels")
    for n in names:
        if n.endswith((".xml",".rels")):ET.fromstring(z.read(n))
    workbook=ET.fromstring(z.read("xl/workbook.xml"))
    tabs=[x.get("name") for x in workbook.find(N+"sheets")]
    assert tabs==excel.SHEETS,tabs
    sheets=[ET.fromstring(z.read(f"xl/worksheets/sheet{i}.xml")) for i in range(1,7)]
    for i,ws in enumerate(sheets,1):
        head=11 if i in (1,2) else 8 if i==6 else 9
        rows=ws.findall(N+"sheetData/"+N+"row")
        assert float(next(x for x in rows if int(x.get("r"))==head).get("ht"))==(38 if i==1 else 44 if i==2 else 43.75)
        for row in rows:
            if int(row.get("r"))>head:
                assert float(row.get("ht","0"))==18,(i,row.get("r"),row.get("ht"))
    # Only the dynamic Liquid type columns are marked fitted; other widths are fixed.
    columns=sheets[1].find(N+"cols")
    fitted=[int(c.get("min")) for c in columns if c.get("bestFit")=="1"]
    assert fitted==[11,12,13],fitted
    for col in list(columns)[:10]:assert col.get("bestFit") is None
    log=values(sheets[0]);daily=values(sheets[1])
    assert log["I11"]=="Cup used" and log["I12"]=="Glazen beker (180 mL)"
    assert daily["K11"].startswith("Coffee") and daily["M11"].startswith("Other")
    assert "All profiles" in z.read("xl/worksheets/sheet4.xml").decode()
    assert "Glazen beker" in z.read("xl/worksheets/sheet4.xml").decode()
    assert "Coffee (Glazen beker)" in z.read("xl/worksheets/sheet5.xml").decode()
    assert "QA1" in z.read("xl/worksheets/sheet6.xml").decode()
    # Native Excel rich-value / metadata icon: F10, F11... with 1-based vm indexes.
    icons=[c for c in sheets[2].iter(N+"c") if c.get("vm") is not None]
    count=len(icons)
    assert count==6,count
    assert [int(c.get("vm")) for c in icons]==list(range(1,count+1))
    assert all(c.get("r").startswith("F") for c in icons)
    assert all(c.get("t")=="e" for c in icons)
    meta=ET.fromstring(z.read("xl/metadata.xml"))
    future=meta.find(N+"futureMetadata");value=meta.find(N+"valueMetadata")
    assert int(future.get("count"))==count and int(value.get("count"))==count
    richns="{http://schemas.microsoft.com/office/spreadsheetml/2017/richdata}"
    rich=ET.fromstring(z.read("xl/richData/rdrichvalue.xml"))
    assert len(rich.findall(richns+"rv"))==count
    for i in range(1,count+1):
        image=z.read(f"xl/media/image{i}.png")
        assert image[:8]==b"\x89PNG\r\n\x1a\n"
        assert int.from_bytes(image[16:20],"big")==60
    # Every referenced cell style must preserve horizontal properties while
    # having verticalCenter turned on, not merely the new blank default style.
    styles=ET.fromstring(z.read("xl/styles.xml"))
    xfs=styles.find(N+"cellXfs")
    for i,ws in enumerate(sheets,1):
        for row in ws.findall(N+"sheetData/"+N+"row"):
            for c in row.findall(N+"c"):
                xf=xfs[int(c.get("s","0"))]
                align=xf.find(N+"alignment")
                assert align is not None and align.get("vertical")=="center",(i,c.get("r"),c.get("s"))
    assert len([n for n in names if n.startswith("xl/tables/table")])==6
    assert [ET.fromstring(z.read(f"xl/tables/table{i}.xml")).get("name") for i in range(3,7)]==["Table1","Table2","Table3","Table4"]
    assert len(profiles[0]["records"])==1
print("BETA46_SIX_SHEETS_TRUE_PLACE_IN_CELL_QA_PASS",len(raw),"bytes")
