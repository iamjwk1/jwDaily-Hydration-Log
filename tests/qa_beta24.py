"""Offline beta.24 integration/migration, persistence, OOXML and rollback-contract QA."""
from __future__ import annotations
import asyncio, copy, importlib, json, math, sys, types
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def mod(name,**kwargs):
 m=types.ModuleType(name)
 for k,v in kwargs.items():setattr(m,k,v)
 sys.modules[name]=m
 return m
for x in ['homeassistant','homeassistant.helpers','homeassistant.util']:
 mod(x)
class Store:
 data={}
 def __init__(self,hass,version,key):self.key=key
 async def async_load(self):return copy.deepcopy(self.data.get(self.key))
 async def async_save(self,value):self.data[self.key]=copy.deepcopy(value)
def now():return datetime(2026,11,11,16,19,tzinfo=ZoneInfo('Europe/Amsterdam'))
def slugify(s):return str(s).lower().replace(' ','_')
mod('homeassistant.config_entries',ConfigEntry=object)
mod('homeassistant.const',EVENT_STATE_CHANGED='state_changed')
mod('homeassistant.core',HomeAssistant=object,callback=lambda fn:fn)
mod('homeassistant.helpers.dispatcher',async_dispatcher_send=lambda *a:None)
mod('homeassistant.helpers.event',async_track_time_change=lambda *a,**kw:lambda:None)
mod('homeassistant.helpers.storage',Store=Store)
mod('homeassistant.util.dt',now=now)
sys.modules['homeassistant.util'].dt=sys.modules['homeassistant.util.dt']
sys.modules['homeassistant.util'].slugify=slugify
package=mod('custom_components')
package.__path__=[str(ROOT/'custom_components')]
mod('custom_components.jw_daily_hydration_log').__path__=[str(ROOT/'custom_components/jw_daily_hydration_log')]
from custom_components.jw_daily_hydration_log.coordinator import HydrationCoordinator
from custom_components.jw_daily_hydration_log.excel import export_xlsx

class Entry:
 entry_id='TEST-24'
 data={'name':'Jan-Willem','age':40,'gender':'male','unit':'mL'}
 options={}
class Hass:
 config=types.SimpleNamespace(time_zone='Europe/Amsterdam')
 bus=types.SimpleNamespace(async_listen=lambda *a:lambda:None)

checks=[]
def ck(cond,msg):
 assert cond,msg
 checks.append(msg)
 print('PASS',msg)

async def main():
 legacy=[('water_cup','Water (beker)',500,'2026-11-11T16:00:31+01:00'),
         ('water_glass','Water (glas)',220,'2026-11-11T15:00:21+01:00'),
         ('coffee','Coffee',180,'2026-11-11T14:02:11+01:00')]
 saved_records=[{'kind':'drink','id':f'h{i}','timestamp':stamp,'volume_ml':vol,'liquid_type':ident,
                 'origin':'dashboard'} for i,(ident,_,vol,stamp) in enumerate(legacy)]
 Store.data['jw_daily_hydration_log.TEST-24']={
  'records':copy.deepcopy(saved_records),'consumed_ml':900,'manual_consumed_ml':900,
  'last_reset_date':'2026-11-11','target_override_ml':2000,
  'custom_liquid_types':[dict(id=lid,name=name,icon_mdi='mdi:water',icon_svg='',custom=True,default_volume_ml=180) for lid,name,_,_ in legacy if lid!='coffee'],
  'liquid_colors':{'water_cup':'#9280D0','water_glass':'#DD7BA6'},
  'volume_buttons':[180,220,500]}
 before=copy.deepcopy(Store.data['jw_daily_hydration_log.TEST-24'])
 c=HydrationCoordinator(Hass(),Entry());await c.async_initialize()
 ck(c.records==saved_records,'Legacy drink IDs, timestamps and volumes unchanged on load')
 ck(c.volume_buttons==[180,220,500] and c.cup_types==[],'Legacy volume buttons kept, no fabricated cups')
 preview=c.migration_preview()
 ck(preview['record_count']==3 and preview['total_logged_ml']==900,'Preview sums source volumes without mutation')
 ck('cup_types' not in Store.data['jw_daily_hydration_log.TEST-24'],'Read-only migration preview makes no store writes')
 await c.async_manage_cup('add',name='Beker',volume_ml=180,icon_mdi='mdi:cup')
 await c.async_manage_cup('add',name='Glas',volume_ml=220)
 cup=c.get_cup_types();ck(len(cup)==2 and cup[0]['default_volume_ml']==180,'Cup types created with stable IDs and volumes')
 await c.async_manage_quick('add',liquid_type_id='water',cup_type_id=cup[0]['id'])
 q=c.get_quick_buttons()[0];ck(q['label']=='Water (Beker)' and q['default_volume_ml']==180,'Automatic Liquid (Cup) label')
 await c.async_manage_cup('update',cup_id=cup[0]['id'],name='Mug',volume_ml=250)
 ck(c.get_quick_buttons()[0]['label']=='Water (Mug)' and c.get_quick_buttons()[0]['default_volume_ml']==250,'Automatic button label and default follow cup rename')
 await c.async_manage_quick('update',quick_id=q['id'],liquid_type_id='water',cup_type_id=cup[0]['id'],label_mode='custom',custom_label='My big bottle')
 ck(c.get_quick_buttons()[0]['label']=='My big bottle','User-defined Quick label saved independently')
 await c.async_manage_cup('update',cup_id=cup[0]['id'],name='Large mug',volume_ml=300)
 ck(c.get_quick_buttons()[0]['label']=='My big bottle','Custom Quick label does not follow cup rename')
 await c.async_manage_quick('update',quick_id=q['id'],liquid_type_id='water',cup_type_id=cup[0]['id'],label_mode='automatic')
 ck(c.get_quick_buttons()[0]['label']=='Water (Large mug)','Automatic label restores dynamically')
 for bad in [0,-1,float('nan'),100001]:
  try:await c.async_manage_cup('add',name='invalid',volume_ml=bad)
  except ValueError:pass
  else:raise AssertionError('Invalid volume accepted')
 ck(True,'Invalid cup volumes rejected')
 try:await c.async_manage_quick('add',liquid_type_id='water',cup_type_id=cup[0]['id'])
 except ValueError:pass
 else:raise AssertionError('Duplicate quick pair accepted')
 ck(True,'Duplicate Liquid/Cup button prohibited')
 before_mapping=copy.deepcopy(c.records)
 await c.async_set_legacy_mapping('water_cup','water',cup[0]['id'])
 await c.async_set_legacy_mapping('water_glass','water',cup[1]['id'])
 ck(c.records==before_mapping,'Explicit alias mapping never rewrites historic record bytes')
 today=c.liquid_breakdown('2026-11-11');totals={x['liquid_type']:x['volume_ml'] for x in today}
 ck(totals=={'coffee':180,'water':720},'Day aggregation merges both Water types by canonical ID')
 hist=c.get_history('2026-11-11');ck(len(hist)==3 and hist[1]['cup_type_id']==cup[1]['id'],'History includes resolved cup with original record ID')
 ck(any(x['original_liquid_type']=='water_cup' for x in hist),'History preserves raw legacy liquid ID')
 ck(c.chart_hourly_today()['buckets'][16]['liquids']=={'water':500},'Hourly chart aliases by canonical liquid')
 week=c.chart_last_7_days();ck(week['days'][-1]['liquids']=={'coffee':180,'water':720},'Seven-day chart aggregates by liquid')
 await c.async_set_legacy_mapping('water_cup','water',cup[0]['id'])
 ck(c.records==before_mapping and c.liquid_breakdown('2026-11-11')==today,'Migration mapping is idempotent')
 await c.async_add_drink(120,'mL','dashboard','water','11-11-2026','15:59:31',cup[0]['id'],q['id'])
 new=c.records[-1]
 ck(new['volume_ml']==120 and new['cup_type_id']==cup[0]['id'] and new['quick_button_id']==q['id'], 'New drink stores real volume, cup and button ID')
 ck(c.get_quick_buttons()[0]['default_volume_ml']==300,'Cup volume and recorded volume stay independent')
 before_edit={x['id']:x['volume_ml'] for x in c.records if x['kind']=='drink'}
 await c.async_edit_drink(new['id'],125,'water','11-11-2026','16:00:55',cup[0]['id'])
 ck(next(x for x in c.records if x['id']==new['id'])['volume_ml']==125,'Edit preserves ID and corrects volume')
 snap=c.export_snapshot();ck(len(snap['records'])==4 and len(snap['cup_types'])==2 and len(snap['quick_buttons'])==1,'Export snapshot includes full original ledger and new catalogs')
 xlsx=export_xlsx([snap],when=now());zz=ZipFile(BytesIO(xlsx));ck(zz.testzip() is None,'XLSX ZIP CRC valid')
 for name in zz.namelist():
  if name.endswith('.xml') or name.endswith('.rels'):
   ET.fromstring(zz.read(name))
 ck(True,'All Excel OOXML files parse successfully')
 wb=load_workbook(BytesIO(xlsx));ck(wb.sheetnames==['Hydration log','Daily intake','Settings - Liquid Types','Settings - Volume Buttons'],'Excel retains exactly four original worksheets')
 ck(wb.worksheets[0].column_dimensions['B'].width==19,'Hydration Date+time column remains width 19')
 ck(wb.worksheets[1].row_dimensions[11].height==44,'Daily intake row 11 remains 44 pt')
 header=[cell.value for cell in wb.worksheets[1][11]]
 ck(header.count('Water\n(mL)')==1 and not any('Water (beker)' in str(x) or 'Water (glas)' in str(x) for x in header),
    'Daily intake has exactly one canonical Water column')
 names=[cell.value for cell in wb.worksheets[0][11]]
 ck('Cup type' in names and 'Quick button' in names and 'Legacy liquid ID' in names,'Hydration log appends cup/quick/legacy columns')
 vals=[row[6].value for row in wb.worksheets[0].iter_rows(min_row=12,max_row=15)]
 ck(vals.count('water')==3,'Hydration export labels Water as canonical liquid')
 settings=[row for row in wb.worksheets[3].values]
 ck(any(row[0]=='Cup types' for row in settings) and any(row[0]=='Quick buttons' for row in settings),'Fourth sheet has cup and Quick button sections')
 ck(any(cell.data_type=='f' for row in wb.worksheets[1].iter_rows(min_row=12) for cell in row),'Excel preserves daily percentage formulas')
 await c.async_shutdown();restarted=HydrationCoordinator(Hass(),Entry());await restarted.async_initialize()
 ck(restarted.records==c.records and restarted.cup_types==c.cup_types and restarted.quick_buttons==c.quick_buttons,'New and legacy configurations survive restart')
 ck(restarted.legacy_mappings==c.legacy_mappings and restarted.liquid_colors==c.liquid_colors,'Mappings and historic color information survive restart')
 await restarted.async_clear_legacy_mapping('water_cup')
 ck('water_cup' in {v['liquid_type'] for v in restarted.liquid_breakdown('2026-11-11')},'Undo mapping restores legacy grouping with unchanged records')
 await restarted.async_shutdown()
 print(f'QA_BETA24_PASS {len(checks)} checks')

if __name__=='__main__':asyncio.run(main())
