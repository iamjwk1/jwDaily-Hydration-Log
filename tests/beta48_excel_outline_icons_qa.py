"""Beta48 Excel: all six thin black table outlines, native Cup & Quick icons and columns."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from xml.etree import ElementTree as ET
from datetime import datetime,timezone
import importlib.util, types, sys,collections,hashlib,copy
r=Path('/mnt/data/beta48_staging/custom_components/jw_daily_hydration_log');p=types.ModuleType('hydro_qa');p.__path__=[str(r)];sys.modules[p.__name__]=p
for name in ('const','excel_reference_format','excel_icons','excel'):
 spec=importlib.util.spec_from_file_location('hydro_qa.'+name,r/(name+'.py'));mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
from hydro_qa import excel
sample={'config':{'name':'Test 123','unit':'mL','age':58,'gender':'male'},'entry_id':'s1','slug':'test1','date':'2026-11-20','target_ml':2000,'target_override_ml':2000,'consumed_ml':220,'daily_archive':{},'source_readings':[],'liquid_colors':{},'liquid_definitions':[{'id':'tea','name':'Thee','icon_mdi':'mdi:tea','color':'#EDB92C','icon_color':'#151515'},{'id':'milk','name':'Melk','icon_mdi':'mdi:cow','color':'#F2F2F2'}],'cup_types':[{'id':'cup1','name':'Glas','icon_mdi':'mdi:cup','default_volume_ml':220,'icon_color':'#000000'},{'id':'cup2','name':'Fles','icon_mdi':'mdi:bottle-wine','default_volume_ml':500}],'quick_buttons':[{'id':'q1','liquid_type_id':'tea','cup_type_id':'cup1','label':'Thee (Glas)'},{'id':'q2','liquid_type_id':'milk','cup_type_id':'cup2','label':'Melk (Fles)','icon_mdi':'mdi:cow'}],'records':[{'kind':'drink','id':'d1','timestamp':'2026-11-20T11:00:00+01:00','volume_ml':220,'liquid_type_id':'tea','cup_type_id':'cup1','cup_default_volume_ml_at_log':220}]}
orig=copy.deepcopy(sample)
xlsx=excel.export_xlsx([sample],when=datetime(2026,11,21,10,0,tzinfo=timezone.utc))
assert sample==orig,'Unexpected source mutation'
# No QA example is written during GitHub CI: all validation is in memory.
N='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
with ZipFile(BytesIO(xlsx)) as z:
 assert z.testzip() is None
 for f in z.namelist():
  if f.endswith(('.xml','.rels')):ET.fromstring(z.read(f))
 sheets=[ET.fromstring(z.read('xl/worksheets/sheet%d.xml'%i)) for i in range(1,7)]
 st=ET.fromstring(z.read('xl/styles.xml'));xf=st.find(N+'cellXfs');bd=st.find(N+'borders')
 print('STYLES',len(xf),'BORDERS',len(bd),'members',len(z.namelist()),'xlsx bytes',len(xlsx))
 images=[]
 for idx,ws in enumerate(sheets,1):
  head=11 if idx<=2 else 8 if idx==6 else 9
  rows=ws.findall(N+'sheetData/'+N+'row');data=[rr for rr in rows if int(rr.get('r'))>=head]
  last=int(data[-1].get('r'))
  cels={x.attrib['r']:x for rr in data for x in rr.findall(N+'c')}
  colmax=max(next(j for j in range(1,29) if excel._col(j)==''.join(ch for ch in a if ch.isalpha())) for a in cels)
  edges=([(col,head,'top') for col in range(2,colmax+1)] +
         [(col,last,'bottom') for col in range(2,colmax+1)] +
         [(2,r,'left') for r in range(head,last+1)] +
         [(colmax,r,'right') for r in range(head,last+1)])
  for edge in edges:
   col,rn,side=edge;address=excel._col(col)+str(rn);cell=cels[address];style=xf[int(cell.get('s','0'))];b=bd[int(style.get('borderId','0'))];node=b.find(N+side)
   assert node is not None and node.get('style')=='thin' and node.find(N+'color').get('indexed')=='64',(idx,address,side)
  for row in data:
   if int(row.get('r'))>head: assert float(row.get('ht'))==18
  icons=[(c.get('r'),int(c.get('vm'))) for c in cels.values() if c.get('vm')]
  print('SHEET',idx,'head',head,'endrow',last,'right',excel._col(colmax),'in cell icons',icons)
  images.extend(icons)
 assert [s for s in images if s[0].startswith('F')]==[('F10',1),('F11',2)]
 assert [s for s in images if s[0].startswith('G')]==[('G10',3),('G11',4)]
 assert [s for s in images if s[0].startswith('J')]==[('J10',5),('J11',6)]
 assert len(images)==6
 assert sum(n.startswith('xl/media/image') for n in z.namelist())==6
 assert not any(x.startswith('xl/drawings') for x in z.namelist())
 meta=ET.fromstring(z.read('xl/metadata.xml'))
 assert int(meta.find(N+'valueMetadata').get('count'))==len(images)
 assert len([a for a in z.namelist() if a.startswith('xl/tables/table')])==6
 assert ET.fromstring(z.read('xl/tables/table5.xml')).get('ref')=='B9:O11'
 assert 'cup1' in z.read('xl/worksheets/sheet4.xml').decode()
 assert 'q1' in z.read('xl/worksheets/sheet5.xml').decode()
 tab5=sheets[4];cells={c.get('r'):c for c in tab5.iter(N+'c')};
 for cc in ('I9','J9','K9','O9'):
  v=cells[cc].find(N+'is');print(cc,''.join(t.text or '' for t in v.iter(N+'t')) if v is not None else '?')
 print('BETA48_SIX_TABLE_OUTLINES_AND_NATIVE_ICONS_QA_PASS',hashlib.sha256(xlsx).hexdigest())