"""Standalone QA: user's four-sheet Excel export contract (stdlib only)."""
from __future__ import annotations
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import importlib.util
import math
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'custom_components' / 'jw_daily_hydration_log' / 'excel.py'
spec = importlib.util.spec_from_file_location('jwdhl_excel_export_reference', source)
excel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(excel)

N = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
NS = '{' + N['m'] + '}'
when=datetime(2026,11,9,13,28,tzinfo=timezone.utc)
assert excel.export_filename('Europe/Amsterdam',when)=='20261109-1428 jwDaily Hydration Log - All Data.xlsx'
assert excel.export_filename('Europe/Amsterdam',datetime(2026,7,19,13,28,tzinfo=timezone.utc))=='20260719-1528 jwDaily Hydration Log - All Data.xlsx'

profile={
 'config':{'name':'Test profile','age':42,'gender':'female'},
 'date':'2026-11-09','target_ml':2500,'consumed_ml':750,
 'liquid_definitions':[
  {'id':'water','name':'Water (cup)','custom':False,'default_volume_ml':250,'icon_mdi':'mdi:water','hidden':False},
  {'id':'coffee','name':'Coffee','custom':False,'default_volume_ml':180,'icon_mdi':'mdi:coffee','hidden':False},
  {'id':'custom_abc','name':'Test juice','custom':True,'default_volume_ml':200,'icon_mdi':'mdi:glass-water','hidden':False},
 ],
 'volume_buttons':[120,180,220,300,500],
 'daily_archive':{'2026-11-08':{'target_ml':2500,'consumed_ml':750,'drink_count':3}},
 'source_readings':[],
 'records':[
  {'id':'id_1','kind':'drink','timestamp':'2026-11-08T12:00:00+01:00','volume_ml':250,'liquid_type':'water'},
  {'id':'id_2','kind':'drink','timestamp':'2026-11-08T13:00:00+01:00','volume_ml':300,'liquid_type':'coffee'},
  {'id':'id_3','kind':'drink','timestamp':'2026-11-08T14:00:00+01:00','volume_ml':200,'liquid_type':'custom_abc'},
  {'id':'id_4','kind':'drink','timestamp':'2026-11-09T14:00:00+01:00','volume_ml':750,'liquid_type':'water'},
  {'id':'id_set','kind':'set_target','timestamp':'2026-11-08T15:00:00+01:00','volume_ml':2500},
 ],
}
# Export ordering must be chronological even if the storage ledger was edited out of order.
unordered=dict(profile)
unordered['records']=[profile['records'][3], profile['records'][2], profile['records'][0],
                       profile['records'][4], profile['records'][1]]
ordered=excel._record_table([unordered],excel.ZoneInfo('Europe/Amsterdam'))
assert [round(row[1],8) for row in ordered]==sorted(round(row[1],8) for row in ordered)
assert [row[9] for row in ordered]==['water','coffee','custom_abc','water']

raw=excel.export_xlsx([profile],'Europe/Amsterdam',when=when)
with ZipFile(BytesIO(raw)) as zipf:
 assert zipf.testzip() is None, 'ZIP CRC error'
 names=set(zipf.namelist())
 expected={f'xl/worksheets/sheet{i}.xml' for i in range(1,5)}
 assert expected.issubset(names)
 assert 'xl/worksheets/sheet5.xml' not in names
 for name in names:
  if name.endswith(('.xml','.rels')): ET.fromstring(zipf.read(name))
 wb=ET.fromstring(zipf.read('xl/workbook.xml'))
 assert [s.attrib['name'] for s in wb.find(NS+'sheets')] == [
  'Hydration log','Daily intake','Settings - Liquid Types','Settings - Volume Buttons']
 def root(index): return ET.fromstring(zipf.read(f'xl/worksheets/sheet{index}.xml'))
 def c(r,ref):
  v=r.find(f'.//{NS}c[@r="{ref}"]'); assert v is not None,ref
  vt=v.find(NS+'v');it=v.find(NS+'is');f=v.find(NS+'f')
  return ((vt.text if vt is not None else ''.join((x.text or '') for x in it.iter(NS+'t')) if it is not None else None),
          f.text if f is not None else None,v.attrib.get('s','0'))
 log=root(1);day=root(2);types=root(3);buttons=root(4)
 assert c(log,'B2')[0]=='Home Assistant jwDaily Hydration log - Hydration log'
 assert c(log,'B4')[0]=='Export date' and c(log,'B11')[0]=='Date+time'
 assert c(log,'C8')[0]=='4' and c(log,'F11')[0]=='Target\n(mL)'
 assert c(log,'G12')[0]=='water', 'Built-in must show raw lowercase ID as user reference'
 assert c(log,'G14')[0]=='Test juice', 'Custom must show configured display name'
 assert c(log,'B12')[2]=='25' and c(log,'G11')[2]=='23'
 assert c(day,'B2')[0]=='Home Assistant jwDaily Hydration Log  - Daily totals'
 assert c(day,'C8')[0]=='2' and c(day,'K11')[0]=='Water\n(mL)'
 assert c(day,'I12')[0]=='750.0' and c(day,'J12')[1]=='I12/G12*100'
 assert c(day,'I13')[0]=='750.0' and c(day,'J13')[1]=='I13/G13*100'
 assert c(day,'K12')[0]=='250.0' and c(day,'L12')[0]=='300.0'
 assert c(day,'M12')[0]=='200.0', 'Custom liquid must have its own dynamic column'
 assert c(types,'C1')[0]=='Name' and c(types,'C4')[0]=='Test juice'
 assert c(buttons,'C1')[0]=='Volume mL' and c(buttons,'C6')[0]=='500'
 for sh in (log,day):
  pane=sh.find('.//'+NS+'pane');assert pane is not None and pane.attrib['ySplit']=='11'
 assert log.find(NS+'tableParts') is not None and day.find(NS+'tableParts') is not None
 # Desktop Excel rejects worksheets with tableParts before pageMargins.
 for sheet in (log,day):
  names=[x.tag.removeprefix(NS) for x in sheet]
  assert names.index('pageMargins') < names.index('tableParts'), names
 for sheet_num in (1,2):
  xml=zipf.read(f'xl/worksheets/sheet{sheet_num}.xml').decode()
  assert xml.index('<pageMargins') < xml.index('<tableParts')
 assert excel._xml('Valid\x01\ud800name')=='Validname'
 # FIX-10/11 exact Excel column widths, in Excel units, including leading A.
 expected_log=[4,19,16,6,9,9,17,11]
 expected_daily=[4.285,16,15,7,9,6,10,9,11,6,10,10,10]
 def widths(sheet):
  return [float(x.attrib['width']) for x in sheet.find(NS+'cols').findall(NS+'col')]
 assert widths(log)==expected_log,('Hydration log',widths(log))
 assert widths(day)==expected_daily,('Daily intake',widths(day))
 assert c(log,'F11')[0]=='Target\n(mL)' and c(log,'H11')[0]=='Volume\n(mL)'
 assert c(day,'H11')[0]=='Drink\ncount' and c(day,'I11')[0]=='Volume\n(mL)'
 assert c(day,'G11')[0]=='Target\n(mL)'
 assert all(c(day,k+'11')[0].endswith('\n(mL)') for k in 'KLM')
 for sheet in (log,day):
  assert float(sheet.find(NS+'sheetData').find(f'{NS}row[@r="11"]').attrib['ht'])>=30
 # Reference header-cell styles have wrapText enabled; without it line breaks clip.
 xfs=ET.fromstring(zipf.read('xl/styles.xml')).find(NS+'cellXfs')
 for idx in sorted(set(int(c(sh,ref)[2]) for sh,ref in [
   (log,'F11'),(log,'H11'),(day,'G11'),(day,'H11'),(day,'I11'),
   (day,'K11'),(day,'M11')])):
  xf=xfs[idx];alignment=xf.find(NS+'alignment')
  assert alignment is not None and alignment.attrib.get('wrapText')=='1',('No wrapText',idx)
 # Every settings header must fit within its configured worksheet column.
 def col_widths(sheet):
  cols=sheet.find(NS+'cols')
  return [float(col.get('width')) for col in cols.findall(NS+'col')]
 assert col_widths(types)[4]>=18 and col_widths(types)[5]>=25
 assert col_widths(types)[8]>=25
 assert col_widths(buttons)[2]>=18 and col_widths(buttons)[3]>=25
 assert types.find(NS+'autoFilter') is not None and buttons.find(NS+'autoFilter') is not None
 t1=ET.fromstring(zipf.read('xl/tables/table1.xml'))
 t2=ET.fromstring(zipf.read('xl/tables/table2.xml'))
 assert t1.attrib['name']=='tblHydrationLog' and t1.attrib['ref']=='B11:H15'
 assert t2.attrib['name']=='tblDailyIntake' and t2.attrib['ref']=='B11:M13'
 styles=ET.fromstring(zipf.read('xl/styles.xml'))
 assert len(styles.find(NS+'cellXfs'))>=30
 # Date+time, color, header rows and percentage formulas follow the reference.
 assert c(log,'B12')[2]=='25' and c(log,'H15')[2]=='32'
 assert c(day,'J12')[2]=='18' and c(day,'J13')[2]=='22'
 print('REFERENCE_EXCEL_QA_PASS: 4 sheets, exact requested Excel widths, wrapped headers, date/formulas, table integrity and CRC')