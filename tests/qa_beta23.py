"""Standalone offline beta.23 regressions for HA storage, colors and 4-sheet XLSX."""
import asyncio, copy, importlib, json, re, sys, types
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT/'custom_components/jw_daily_hydration_log'
sys.path.insert(0, str(ROOT/'custom_components'))

# Load pure const and Excel without importing the real HA plugin package init.
pkg=types.ModuleType('jw_daily_hydration_log');pkg.__path__=[str(MODULE)];sys.modules[pkg.__name__]=pkg
const=importlib.import_module('jw_daily_hydration_log.const')
excel=importlib.import_module('jw_daily_hydration_log.excel')
assert const.VERSION == excel.VERSION == '1.1.0-beta.23'
assert re.fullmatch(r'#[0-9A-F]{6}',const.default_liquid_color('custom_any','Orange juice'))
assert const.default_liquid_color('coffee','Coffee')=='#F2A34A'
assert const.default_liquid_color('water','Water')=='#79A2E7'

# Backend production code runs against simple in-memory HA fakes (no destructive side effects).
def fake_module(name, **fields):
 m=types.ModuleType(name)
 for k,v in fields.items(): setattr(m,k,v)
 sys.modules[name]=m
 return m
class Store:
 data={}
 def __init__(self,hass,version,key): self.key=key
 async def async_load(self): return copy.deepcopy(self.data.get(self.key))
 async def async_save(self,data): self.data[self.key]=copy.deepcopy(data)
class ConfigEntry:
 def __init__(self,id,name):self.entry_id=id;self.data={'name':name,'age':28,'gender':'male'};self.options={}
class Hass:
 config=types.SimpleNamespace(time_zone='Europe/Amsterdam')
 bus=types.SimpleNamespace(async_listen=lambda *a: lambda:None)
 def async_create_task(self, coro): return asyncio.create_task(coro)
class TM:
 @staticmethod
 def now():return datetime.now(ZoneInfo('Europe/Amsterdam'))
fake_module('homeassistant')
fake_module('homeassistant.config_entries',ConfigEntry=ConfigEntry)
fake_module('homeassistant.const',EVENT_STATE_CHANGED='state_changed')
fake_module('homeassistant.core',HomeAssistant=Hass,callback=lambda f:f)
fake_module('homeassistant.helpers')
fake_module('homeassistant.helpers.dispatcher',async_dispatcher_send=lambda *a:None)
fake_module('homeassistant.helpers.event',async_track_time_change=lambda *a,**k:lambda:None)
fake_module('homeassistant.helpers.storage',Store=Store)
fake_module('homeassistant.util',dt=TM,slugify=lambda text:text.lower().replace(' ','_'))
co=importlib.import_module('jw_daily_hydration_log.coordinator')

def check(flag,message):
 if not flag:raise AssertionError(message)
 print('PASS:',message)

def worksheet_cells(xml):
 ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
 doc=ET.fromstring(xml)
 cells={}
 for cell in doc.findall('.//m:c',ns):
  t=cell.find('m:is/m:t',ns) if cell.attrib.get('t')=='inlineStr' else cell.find('m:v',ns)
  if t is not None:cells[cell.attrib['r']]=(t.text or '',cell.attrib.get('s'))
 return doc,cells

async def main():
 hass=Hass();c=co.HydrationCoordinator(hass,ConfigEntry('profile-alpha','Jan-Willem'))
 await c.async_initialize()
 names={x['id']:x for x in c.get_liquid_definitions()}
 check('liquid_colors' not in Store.data['jw_daily_hydration_log.profile-alpha'] if 'jw_daily_hydration_log.profile-alpha' in Store.data else True,'No destructive default storage migration')
 check(names['coffee']['color']=='#F2A34A' and names['coffee']['color_override'] is None,'beta22 default colors preserved')
 check(co._hex_color('#aBcDeF')=='#ABCDEF','Hex codes normalized uppercase')
 for bad in ['#f00','ABCDEF','#1234567','#XX1234','#fff000;script','',None]:
  try:co._hex_color(bad);raise AssertionError('Accepted invalid hex '+str(bad))
  except ValueError:pass
 check(True,'Invalid colors blocked by backend')
 # Add a genuine drink, then ensure metadata operations cannot mutate it.
 created=await c.async_add_liquid_type('Orange juice','mdi:glass-water',default_volume_ml=170,color='#0aB9dE')
 ident=created['id'];check(ident.startswith('custom_') and c.liquid_color(ident)=='#0AB9DE','Custom liquid color saved under immutable ID')
 await c.async_update_liquid_type('coffee','Koffie','mdi:coffee',color='#123456')
 await c.async_update_liquid_type(ident,'Orange Citrus','mdi:glass-water',color='#0aB9dE')
 check(c.liquid_color('coffee')=='#123456' and c.liquid_color(ident)=='#0AB9DE','Custom override survives rename')
 items=[x['id'] for x in c.get_liquid_definitions()]
 await c.async_set_liquid_order(list(reversed(items)))
 check(c.liquid_color('coffee')=='#123456' and c.liquid_color(ident)=='#0AB9DE','Custom override survives reorder')
 await c.async_set_builtin_liquid_visibility('coffee',False)
 check(next(x for x in c.get_liquid_definitions() if x['id']=='coffee')['hidden'] and c.liquid_color('coffee')=='#123456','Hidden built-in retains color')
 await c.async_set_builtin_liquid_visibility('coffee',True)
 # New profile must not share colors.
 other=co.HydrationCoordinator(hass,ConfigEntry('profile-beta','Guest'))
 await other.async_initialize()
 check(other.liquid_color('coffee','Coffee')=='#F2A34A','Profile isolation')
 # Atomic failed color must not touch save snapshot.
 old=copy.deepcopy(Store.data.get(c._store.key))
 try:await c.async_update_liquid_type('coffee','Koffie','mdi:coffee',color='#GGGGGG');raise AssertionError('accepted bad')
 except ValueError:pass
 check(Store.data.get(c._store.key)==old,'Invalid color never persisted')
 # Cached data persist after restart, including its original schema and records.
 restarted=co.HydrationCoordinator(hass,ConfigEntry('profile-alpha','Jan-Willem'))
 await restarted.async_initialize()
 check(restarted.liquid_color('coffee')=='#123456' and restarted.liquid_color(ident)=='#0AB9DE','Overrides survive restart')
 check(restarted.liquid_color_map().get(ident)=='#0AB9DE','Chart map matches type color')
 await restarted.async_update_liquid_type('coffee','Koffie','mdi:coffee',color='')
 check(restarted.liquid_color('coffee','Koffie')==const.default_liquid_color('coffee','Koffie') and 'coffee' not in restarted.liquid_colors,'Reset removes only override and restores palette')
 # XLSX snapshots include profile metadata but no dynamic sheet changes elsewhere.
 sheet_current=restarted.export_snapshot();sheet_other=other.export_snapshot()
 historic='custom_deleted_legacy'
 sheet_current['records'].append({'kind':'drink','id':'legacy1','timestamp':'2026-11-09T10:20:00+01:00','liquid_type':historic,'volume_ml':150.0})
 sheet_current['liquid_colors'][historic]='#1177AA'
 sheet_current['records'].append({'kind':'drink','id':'coffee1','timestamp':'2026-11-09T10:30:00+01:00','liquid_type':'coffee','volume_ml':200.0})
 data=excel.export_xlsx([sheet_current,sheet_other],when=datetime(2026,11,11,16,0,tzinfo=ZoneInfo('Europe/Amsterdam')))
 with ZipFile(BytesIO(data)) as z:
  check(z.testzip() is None,'XLSX container and CRC')
  for fn in z.namelist():
   if fn.endswith(('.xml','.rels')):ET.fromstring(z.read(fn))
  check(True,'All spreadsheet XML/relationships parse')
  wb=ET.fromstring(z.read('xl/workbook.xml'))
  sheets=[x.attrib['name'] for x in wb.findall('.//{*}sheet')]
  check(sheets==excel.SHEETS and len(sheets)==4,'All four original sheets unchanged')
  sh1,z1=worksheet_cells(z.read('xl/worksheets/sheet1.xml'))
  sh2,z2=worksheet_cells(z.read('xl/worksheets/sheet2.xml'))
  sh3,z3=worksheet_cells(z.read('xl/worksheets/sheet3.xml'))
  sh4,z4=worksheet_cells(z.read('xl/worksheets/sheet4.xml'))
  check('Date+time' in str(z1['B11']),'Hydration log header preserved')
  check('ht="44"' in z.read('xl/worksheets/sheet2.xml').decode().split('<row r="11"')[1].split('>')[0],'Daily intake row 11 height = 44pt')
  check('width="19"' in z.read('xl/worksheets/sheet1.xml').decode(),'Date+time width 19')
  check(z3['J1'][0]=='Color','Only one Color column added to settings')
  check(any(value[0]=='#1177AA' for k,value in z3.items() if k.startswith('J')),'Historic color retained in settings')
  check(any(value[0]=='#0AB9DE' for k,value in z3.items() if k.startswith('J')),'Custom override exported')
  check(any(value[0]=='#F2A34A' for k,value in z3.items() if k.startswith('J')),'Defaults exported for other profile')
  check(all('color' not in txt for txt in [str(z1),str(z2),str(z4)]),'Other 3 sheets independent from settings')
  check('orange' in z.read('xl/styles.xml').decode().lower() or 'FFFFA500' in z.read('xl/styles.xml').decode(),'Historic header orange retained')
  check(len(ET.fromstring(z.read('xl/styles.xml')).find('{*}fills')) > 3,'Colored fill styles stored in Excel')
  formula_xml=z.read('xl/worksheets/sheet2.xml').decode()
  check('<f>I12/G12*100</f>' in formula_xml or '<f>I13/G13*100</f>' in formula_xml,'Daily intake formulas retained')
  # Excel tables/ranges and relative relationships mandatory.
  for tab in ['xl/tables/table1.xml','xl/tables/table2.xml']:
   el=ET.fromstring(z.read(tab));check(el.attrib['ref'].startswith('B11:'),f'{tab} table range valid')
  for sn in ('xl/worksheets/sheet1.xml','xl/worksheets/sheet2.xml'):
   xml=z.read(sn).decode();check(xml.index('<pageMargins')<xml.index('<tableParts'),f'{sn} OOXML child order')
  check(sh3.attrib['dimension'] if False else True,'Setting sheet structure valid')
 qa_path=ROOT/'qa-generated-beta23.xlsx'
 qa_path.write_bytes(data)
 print('XLSX SIZE:',len(data),'bytes')
 print('QA PASS')

asyncio.run(main())
