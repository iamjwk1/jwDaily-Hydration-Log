"""Beta47 regression: reference Excel style parity and safe technical IDs."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import importlib.util
import sys
import types
import hashlib

root=Path(__file__).resolve().parents[1]/"custom_components"/"jw_daily_hydration_log"
pkg=types.ModuleType("beta47_excel_qa")
pkg.__path__=[str(root)]
sys.modules[pkg.__name__]=pkg
for name in ("const","excel_reference_format","excel_icons","excel"):
    spec=importlib.util.spec_from_file_location(pkg.__name__+"."+name,root/(name+".py"))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
from beta47_excel_qa import excel,excel_reference_format as reference

assert hashlib.sha256(reference.REFERENCE_THEME).hexdigest()=="0c8f48efbaa9f9470fd12aea56b8b7f992d43343c84808b46a0d1738ca46c7ab"
assert hashlib.sha256(reference.REFERENCE_STYLES).hexdigest()=="b0795df0691a50cae4ba628b5a57e95e5298446df9212fb2d1746dd8c834a8c3"

p={
 "config":{"name":"Acceptance QA","unit":"mL","age":58,"gender":"male"},
 "slug":"qa_slug","entry_id":"test_original_id_01","date":"2026-11-20",
 "target_ml":2000,"target_override_ml":2000,"consumed_ml":180,
 "daily_archive":{},"source_readings":[],"liquid_colors":{},
 "liquid_definitions":[
    {"id":"tea","name":"Thee","icon_mdi":"mdi:tea","color":"#EDB92C","custom":False},
    {"id":"water","name":"Water","icon_mdi":"mdi:water","color":"#86CAFE","custom":False},
    {"id":"other","name":"Overige","icon_mdi":"mdi:glass-water","color":"#9F9F9F","custom":False}
 ],
 "cup_types":[{"id":"glass_001","name":"Glas","default_volume_ml":180,"icon_mdi":"mdi:cup"}],
 "quick_buttons":[{"id":"quick_001","cup_type_id":"glass_001","liquid_type_id":"tea",
                   "label":"Thee (Glas)"}],
 "records":[{"id":"original_drink_id","kind":"drink","timestamp":"2026-11-20T11:00:00+01:00",
             "volume_ml":180,"cup_type_id":"glass_001","liquid_type_id":"tea",
             "cup_default_volume_ml_at_log":180}]
}
saved=deepcopy(p)
result=excel.export_xlsx([p],when=datetime(2026,11,20,15,tzinfo=timezone.utc))
assert p==saved,"Excel export must not alter HA data"

ns="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
with ZipFile(BytesIO(result)) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert "xl/drawings/drawing1.xml" not in names,"Floating images are prohibited"
    assert "xl/metadata.xml" in names and "xl/richData/rdrichvalue.xml" in names
    assert len([a for a in names if a.startswith("xl/tables/table")])==6
    assert z.read("xl/theme/theme1.xml")==reference.REFERENCE_THEME
    w=ET.fromstring(z.read("xl/workbook.xml"))
    assert [a.get("name") for a in w.find(ns+"sheets")]==excel.SHEETS
    original_styles=ET.fromstring(reference.REFERENCE_STYLES)
    output_styles=ET.fromstring(z.read("xl/styles.xml"))
    old_xfs=original_styles.find(ns+"cellXfs")
    new_xfs=output_styles.find(ns+"cellXfs")
    assert len(new_xfs)>=len(old_xfs)
    for i,(a,b) in enumerate(zip(old_xfs,new_xfs)):
        assert {k:v for k,v in a.attrib.items() if k!="applyAlignment"}=={k:v for k,v in b.attrib.items() if k!="applyAlignment"},i
        assert b.find(ns+"alignment").get("vertical")=="center",i
    for i in range(1,7):
        ws=ET.fromstring(z.read(f"xl/worksheets/sheet{i}.xml"))
        header_row=11 if i<=2 else 8 if i==6 else 9
        for row in ws.findall(ns+"sheetData/"+ns+"row"):
            j=int(row.get("r"))
            if j>header_row: assert float(row.get("ht","0"))==18,(i,j)
            if j==11 and i==1:assert float(row.get("ht"))==38
            for cell in row.findall(ns+"c"):
                xf=new_xfs[int(cell.get("s","0"))]
                assert xf.find(ns+"alignment").get("vertical")=="center",(i,cell.get("r"))
        if i!=2:
            got=ET.tostring(ws.find(ns+"cols"))
            expected=ET.fromstring(reference.REFERENCE_COLS[i])
            actual=[dict(c.attrib) for c in ws.find(ns+"cols")]
            original=[dict(c.attrib) for c in expected]
            if i==5:
                assert len(actual)==len(original)+1
                assert actual[9]["min"]=="10" and actual[9]["max"]=="10" and actual[9]["width"]=="11.5"
                expected_shifted=[]
                for attrs in original:
                    entry=dict(attrs)
                    if int(entry["min"])>=10:
                        entry["min"]=str(int(entry["min"])+1)
                        entry["max"]=str(int(entry["max"])+1)
                    expected_shifted.append(entry)
                expected_shifted.insert(9,{"min":"10","max":"10","width":"11.5","customWidth":"1"})
                assert actual==expected_shifted,(i,"Quick icon column must not alter existing widths")
            else:
                assert actual==original,(i,"Reference fixed column widths changed")
        else:
            cols=list(ws.find(ns+"cols"))
            assert all(c.get("bestFit")!="1" for c in cols if int(c.get("max"))<=10)
            assert all(c.get("bestFit")=="1" for c in cols if int(c.get("min"))>=11)
        if i==3:
            icons=[c for c in ws.iter(ns+"c") if c.get("vm")]
            assert len(icons)==3,icons
            assert all(c.get("r").startswith("F") for c in icons),"Images not in cell"
    assert b"glass_001" in z.read("xl/worksheets/sheet4.xml"),"Technical cup IDs omitted"
    assert b"quick_001" in z.read("xl/worksheets/sheet5.xml"),"Technical quick IDs omitted"
    assert b"original_drink_id" not in z.read("xl/worksheets/sheet1.xml"),"Unexpected ID column introduced in Hydration log"
    for path in names:
        if path.endswith(".xml") or path.endswith(".rels"):
            ET.fromstring(z.read(path))
print("BETA47_REFERENCE_FORMAT_AND_ID_QA_PASS",len(result),"bytes")
