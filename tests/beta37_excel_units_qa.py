from __future__ import annotations
import io, sys, types, importlib.util, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone
root=Path(__file__).resolve().parents[1]/'custom_components/jw_daily_hydration_log'
pkg=types.ModuleType('jdhl_excel_beta37');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
for n in ('const','excel_icons','excel'):
 spec=importlib.util.spec_from_file_location(pkg.__name__+'.'+n,root/(n+'.py'))
 mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
from jdhl_excel_beta37.excel import export_xlsx
NS={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
liquids=[{'id':'coffee','name':'Coffee','icon_mdi':'mdi:coffee','custom':False},{'id':'water','name':'Water','icon_mdi':'mdi:water','custom':False},{'id':'other','name':'Other','icon_mdi':'mdi:glass-water','custom':False}]
cups=[{'id':'cup_glass','name':'Glass','default_volume_ml':180,'icon_mdi':'mdi:cup','hidden':False}]
def profile(name,unit,volume):
 return {'config':{'name':name,'age':58,'gender':'male','unit':unit},'date':'2026-11-14','consumed_ml':volume,'target_ml':2000,'target_override_ml':0,
 'records':[{'id':name+'_1','kind':'drink','volume_ml':volume,'liquid_type_id':'coffee','cup_type_id':'cup_glass','timestamp':'2026-11-14T08:30:00+01:00'}],
 'daily_archive':{},'source_readings':[],'liquid_definitions':liquids,'cup_types':cups,'quick_buttons':[{'id':'quick_'+name,'liquid_type_id':'coffee','cup_type_id':'cup_glass'}]}
fixed=datetime(2026,11,14,11,tzinfo=timezone.utc)
def xmltext(cell):
 t=cell.find('x:is/x:t',NS)
 if t is None:t=cell.find('x:v',NS)
 return t.text if t is not None else ''
for units in [('mL',),('L',),('fl_oz',),('mL','L','fl_oz')]:
 profiles=[profile('Person'+str(i),u,180) for i,u in enumerate(units,1)]
 content=export_xlsx(profiles,when=fixed)
 z=zipfile.ZipFile(io.BytesIO(content));assert z.testzip() is None
 assert set(z.namelist())>={'xl/worksheets/sheet1.xml','xl/worksheets/sheet2.xml','xl/workbook.xml','xl/styles.xml'}
 for f in z.namelist():
  if f.endswith(('.xml','.rels')):ET.fromstring(z.read(f))
 one=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
 two=ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
 row=one.find("x:sheetData/x:row[@r='12']",NS);assert row is not None and row.get('ht')=='44'
 logheaders=' '.join(xmltext(c) for c in one.findall("x:sheetData/x:row[@r='11']/x:c",NS))
 assert 'Cup used' in logheaders and 'Current cup default' not in logheaders and 'Quick button' not in logheaders
 dayheaders=[xmltext(c) for c in two.findall("x:sheetData/x:row[@r='11']/x:c",NS)]
 assert dayheaders[-1].startswith('Other')
 if len(units)==1:
  lab='fl oz' if units[0]=='fl_oz' else units[0]
  assert f'Volume\n({lab})' in logheaders,(units,logheaders)
  assert 'Profile unit' not in logheaders
 else:
  assert 'Volume\n(mL)' in logheaders and 'Profile unit' in logheaders and 'Volume (profile unit)' in logheaders
  assert 'Profile unit' in dayheaders and 'Volume (profile unit)' in dayheaders
 print('EXCEL_BETA37_PASS',units,len(content),'bytes')