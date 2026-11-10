"""Beta.13: dynamic liquid Excel schema, including zero-usage and retired types."""
from __future__ import annotations
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import importlib.util
import xml.etree.ElementTree as ET
from zipfile import ZipFile

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('jwdhl_excel_dynamic',root/'custom_components/jw_daily_hydration_log/excel.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
sample={
 'config':{'name':'QA profile','age':58,'gender':'male'},
 'date':'2026-11-10','target_ml':2000,'consumed_ml':350,
 'liquid_definitions':[
  {'id':'water','name':'Water (glass)','custom':False,'hidden':False},
  {'id':'custom_orange','name':'Orange juice','custom':True,'hidden':False},
  {'id':'tea','name':'Tea','custom':False,'hidden':True},
 ],
 'daily_archive':{},'source_readings':[], 'volume_buttons':[180,300],
 'records':[
  {'kind':'drink','timestamp':'2026-11-10T10:30:00+01:00','liquid_type':'water','volume_ml':200},
  {'kind':'drink','timestamp':'2026-11-10T11:30:00+01:00','liquid_type':'retired_juice','volume_ml':150},
 ]}
raw=mod.export_xlsx([sample],when=datetime(2026,11,10,12,tzinfo=timezone.utc))
with ZipFile(BytesIO(raw)) as z:
 assert z.testzip() is None
 main=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
 one=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
 table=ET.fromstring(z.read('xl/tables/table2.xml'))
 styles=ET.fromstring(z.read('xl/styles.xml'))
 def cell(sh,ref):
  node=sh.find(f'.//{ns}c[@r="{ref}"]')
  assert node is not None,ref
  inline=node.find(ns+'is')
  v=node.find(ns+'v')
  text=''.join((i.text or '') for i in inline.iter(ns+'t')) if inline is not None else (v.text if v is not None else '')
  return text,int(node.attrib.get('s','0'))
 cols=lambda sh: [float(c.attrib['width']) for c in sh.find(ns+'cols')]
 assert cols(one)[1]==19
 assert cols(main)==[4.285,16,15,7,9,6,10,9,11,6,10,10,10,10]
 assert [cell(main,f'{column}11')[0] for column in 'KLMN']==[
  'Water (glass)\n(mL)','Orange juice\n(mL)','Tea\n(mL)','retired_juice\n(mL)']
 assert [float(cell(main,f'{column}12')[0]) for column in 'KLMN']==[200,0,0,150]
 assert table.attrib['ref']=='B11:N12'
 assert len(table.find(ns+'tableColumns'))==13
 xfs=styles.find(ns+'cellXfs')
 legacy_style=xfs[cell(main,'N11')[1]]
 fill=styles.find(ns+'fills')[int(legacy_style.attrib['fillId'])]
 fg=fill.find(f'.//{ns}fgColor')
 assert fg is not None and fg.attrib.get('rgb')=='FFFFA500'
 assert cell(main,'K11')[1]!=cell(main,'N11')[1]
 assert cell(main,'J12')[0]=='17.5',cell(main,'J12')
 assert main.find(ns+'tableParts') is not None
 # The table header must wrap even on the orange legacy column.
 assert legacy_style.find(ns+'alignment').attrib.get('wrapText')=='1'
print('DYNAMIC_LIQUID_EXCEL_QA_PASS: width19, all current IDs, zero volume, retired orange, table range, CRC')
