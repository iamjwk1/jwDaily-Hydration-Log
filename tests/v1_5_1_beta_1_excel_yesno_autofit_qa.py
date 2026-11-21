"""v1.5.1-beta.1 Excel regression: Yes/No booleans and bounded content-fit IDs/MDI."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import importlib.util
import sys
import types

base=Path(__file__).resolve().parents[1]/"custom_components"/"jw_daily_hydration_log"
package=types.ModuleType("beta151_excel_qa")
package.__path__=[str(base)]
sys.modules[package.__name__]=package
for name in ("const","excel_reference_format","excel_icons","excel"):
    spec=importlib.util.spec_from_file_location(package.__name__+"."+name,base/(name+".py"))
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
from beta151_excel_qa import excel
ns="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
cup_id="cup_"+"a"*46
liquid_mdi="mdi:coffee-maker-outline"
cup_mdi="mdi:glass-mug-variant-outline"
quick_mdi="mdi:coffee-to-go-outline"
sample={
 "config":{"name":"Reference profile","age":45,"gender":"male","unit":"mL",
           "show_add_quick_buttons":True,"show_add_liquid_cup_types":False},
 "entry_id":"test1","slug":"test1","date":"2026-11-21",
 "target_ml":2000,"target_override_ml":2000,"consumed_ml":0,
 "daily_archive":{},"source_readings":[],"liquid_colors":{},
 "liquid_definitions":[
     {"id":"coffee","name":"Coffee","icon_mdi":liquid_mdi,
      "color":"#BC8811","hidden":False,"custom":True},
     {"id":"water","name":"Water","icon_mdi":"mdi:water",
      "color":"#3399CC","hidden":True,"custom":False}],
 "cup_types":[
     {"id":cup_id,"name":"Large Coffee Glass","icon_mdi":cup_mdi,
      "default_volume_ml":350,"hidden":False}],
 "quick_buttons":[
     {"id":"q1","label":"Coffee","liquid_type_id":"coffee",
      "cup_type_id":cup_id,"icon_mdi":quick_mdi,"hidden":False}],
 "records":[]
}
original=deepcopy(sample)
result=excel.export_xlsx([sample],when=datetime(2026,11,21,13,0,tzinfo=timezone.utc))
assert sample==original,"Excel exporter must not change profile data"
def text_of(cell):
    return "".join(t.text or "" for t in cell.iter(ns+"t"))
def at(ws,ref):
    return next(c for c in ws.iter(ns+"c") if c.get("r")==ref)
def col(ws,number):
    cols=ws.find(ns+"cols")
    return next(x for x in cols if int(x.get("min"))<=number<=int(x.get("max")))
with ZipFile(BytesIO(result)) as z:
    assert z.testzip() is None
    assert len([k for k in z.namelist() if k.startswith("xl/tables/table")])==6
    for name in z.namelist():
        if name.endswith((".xml",".rels")):ET.fromstring(z.read(name))
    sheets=[ET.fromstring(z.read(f"xl/worksheets/sheet{i}.xml")) for i in range(1,7)]
    for ws in sheets:
        assert not any(c.get("t")=="b" for c in ws.iter(ns+"c")),"Workbook contains TRUE/FALSE typed cells"
    liquids,cups,quicks,profiles=sheets[2],sheets[3],sheets[4],sheets[5]
    # Only actual settings booleans change; the identity and icon columns are retained.
    for ref,expect in [("H10","Yes"),("H11","No"),("J10","Yes"),("J11","No")]:
        c=at(liquids,ref)
        assert c.get("t")=="inlineStr" and text_of(c)==expect,(ref,text_of(c))
    assert text_of(at(profiles,"J9"))=="Yes"
    assert text_of(at(profiles,"K9"))=="No"
    assert text_of(at(cups,"C10"))==cup_id
    assert text_of(at(cups,"F10"))==cup_mdi
    assert text_of(at(quicks,"I10"))==quick_mdi
    for ws,position,content in [
      (liquids,5,liquid_mdi),(cups,3,cup_id),(cups,6,cup_mdi),(quicks,9,quick_mdi)
    ]:
        entry=col(ws,position)
        width=float(entry.get("width","0"))
        assert entry.get("bestFit")=="1",(position,"missing Excel content-fit metadata")
        assert len(content)+2 <= width <=72,(position,content,width)
        assert entry.get("customWidth")=="1"
    # Full integrity: table/column positions and native icons unaffected.
    assert ET.fromstring(z.read("xl/tables/table4.xml")).get("ref")=="B9:J10"
    assert len([x for x in z.namelist() if x.startswith("xl/media/image")])==4
    assert all(float(r.get("ht"))==18 for ws in sheets for r in ws.findall(ns+"sheetData/"+ns+"row")
               if int(r.get("r"))>(11 if ws in sheets[:2] else 8 if ws is sheets[5] else 9))
print("BETA151_EXCEL_YES_NO_AND_AUTOFIT_QA_PASS",len(result),"bytes","CRC_OK")
