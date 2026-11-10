"""Ensure the real downloaded Excel workbook is not damaged by XML style prefix rewrites."""
from pathlib import Path
import sys,importlib.util,zipfile,io,xml.etree.ElementTree as ET
from datetime import datetime, timezone
source=Path("custom_components/jw_daily_hydration_log/excel.py")
spec=importlib.util.spec_from_file_location("jwdhl_office14",source)
x=importlib.util.module_from_spec(spec);spec.loader.exec_module(x)
original=x.STYLES.decode("utf8")
modified,orange=x._styles_with_legacy_header()
updated=modified.decode("utf8")
for prefix in ("mc","x14ac","x16r2","xr"):
    assert "xmlns:"+prefix+"=" in updated, "Missing Office namespace "+prefix
assert 'mc:Ignorable="x14ac x16r2 xr"' in updated
assert updated.startswith(original[:90])
assert "<ns0:" not in updated and "<ns1:" not in updated
N="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
root=ET.fromstring(updated)
fills=root.find(N+"fills")
xfs=root.find(N+"cellXfs")
assert int(fills.get("count"))==len(fills)
assert int(xfs.get("count"))==len(xfs)
assert orange==len(xfs)-1
p={"config":{"name":"QA","age":58,"gender":"male"},"date":"2026-11-10","target_ml":2000,"consumed_ml":180,
   "liquid_definitions":[{"id":"water","name":"Water"},{"id":"tea","name":"Tea"}],"daily_archive":{},"volume_buttons":[],
   "records":[{"kind":"drink","timestamp":"2026-11-10T12:00:00+01:00","liquid_type":"retired","volume_ml":180}]}
data=x.export_xlsx([p],when=datetime(2026,11,10,14,tzinfo=timezone.utc))
with zipfile.ZipFile(io.BytesIO(data)) as z:
 assert z.testzip() is None
 for name in z.namelist():
  if name.endswith((".xml",".rels")):
   ET.fromstring(z.read(name))
 styles=z.read("xl/styles.xml").decode("utf8")
 assert "xmlns:x14ac=" in styles and "xmlns:x16r2=" in styles and "xmlns:xr=" in styles
 main=ET.fromstring(styles)
 assert int(main.find(N+"fills").get("count"))==len(main.find(N+"fills"))
 assert int(main.find(N+"cellXfs").get("count"))==len(main.find(N+"cellXfs"))
 for i in range(1,5):
  sheet=ET.fromstring(z.read(f"xl/worksheets/sheet{i}.xml"))
  for c in sheet.iter(N+"c"):
   assert int(c.get("s","0"))<len(main.find(N+"cellXfs")), (i,c.get("r"))
 assert z.read("xl/tables/table2.xml").count(b"<tableColumn ")==12
print("OFFICE_STYLE_NAMESPACE_QA_PASS")
