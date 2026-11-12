"""beta.28: backend-history/Excel parity regression, no Home Assistant dependency.

Exercises the actual coordinator methods via AST and the full XLSX exporter.
All fixture data is synthetic. No user records or profile identifiers are bundled.
"""
from __future__ import annotations
import ast
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re
import sys
import types
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT/'custom_components'/'jw_daily_hydration_log'
NS = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def load_excel():
    for key in ('custom_components','custom_components.jw_daily_hydration_log'):
        pkg = types.ModuleType(key)
        pkg.__path__=[str(COMP if key.endswith('jw_daily_hydration_log') else ROOT/'custom_components')]
        sys.modules[key]=pkg
    for name in ('const','excel'):
        module_name='custom_components.jw_daily_hydration_log.'+name
        spec=spec_from_file_location(module_name,COMP/(name+'.py'))
        mod=module_from_spec(spec)
        sys.modules[module_name]=mod
        spec.loader.exec_module(mod)
    return sys.modules['custom_components.jw_daily_hydration_log.excel']

def coordinator_method(name):
    source=ast.parse((COMP/'coordinator.py').read_text(encoding='utf-8'))
    klass=next(x for x in source.body if isinstance(x,ast.ClassDef) and x.name=='HydrationCoordinator')
    method=next(x for x in klass.body if isinstance(x,ast.FunctionDef) and x.name==name)
    method=deepcopy(method)
    # Function annotations in coordinator use builtin types; no runtime HA refs.
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])), '<actual coordinator.py>', 'exec'),namespace:={})
    return namespace[name]

class InMemoryProfile:
    _today = lambda self:'2026-11-12'
    def __init__(self):
        self.name=self.profile_display_name='Regression Fixture'
        self.age=42
        self.gender='female'
        self.pregnancy=self.lactation=False
        self.source_sensor=''
        self.source_mode='absolute'
        self.unit='mL'
        self.entry_id='test_entry'
        self.slug='fixture'
        self.target_ml=2000
        self.source_contribution_ml=0
        self.consumed_ml=0
        self.manual_consumed_ml=0
        self.last_reset_date='2026-11-12'
        self.source_readings=[]
        self.daily_archive={}
        self.liquid_overrides={}
        self.hidden_builtin_liquids=[]
        self.custom_liquid_types=[]
        self.volume_buttons=[180,220,500]
        self.liquid_colors={}
        self.liquid_definitions=[dict(id=x,name=x.title(),hidden=False,custom=False,color='#9ABBD0') for x in ('water','coffee','tea','milk','wine')]
        self.cup_types=[dict(id='cup_mug',name='Mug',default_volume_ml=180,hidden=False),
                        dict(id='cup_glass',name='Glass',default_volume_ml=220,hidden=False),
                        dict(id='cup_bottle',name='Bottle',default_volume_ml=500,hidden=False)]
        self.quick_buttons=[]
        self.legacy_mappings={'old_water_glass':dict(liquid_type_id='water',cup_type_id='cup_glass')}
        self.legacy_cup_defaults={'coffee':'cup_mug','tea':'cup_mug','water':'cup_bottle'}
        self.records=[
            dict(kind='drink',id='drink01',timestamp='2026-11-09T10:00:01+01:00',liquid_type='coffee',volume_ml=180),
            dict(kind='drink',id='drink02',timestamp='2026-11-09T12:59:19+01:00',liquid_type='tea',volume_ml=120),
            dict(kind='drink',id='drink03',timestamp='2026-11-10T09:01:30+01:00',liquid_type='old_water_glass',volume_ml=500),
            dict(kind='drink',id='drink04',timestamp='2026-11-10T11:20:04+01:00',liquid_type='water',volume_ml=220),
            dict(kind='drink',id='drink05',timestamp='2026-11-11T15:19:16+01:00',liquid_type='coffee',cup_type_id='cup_glass',volume_ml=350),
            dict(kind='drink',id='drink06',timestamp='2026-11-11T17:26:01+01:00',liquid_type='milk',volume_ml=180),
            dict(kind='drink',id='drink07',timestamp='2026-11-12T11:45:05+01:00',liquid_type='wine',volume_ml=80),
            dict(kind='drink',id='drink08',timestamp='2026-11-12T11:59:01+01:00',liquid_type='tea',volume_ml=180),
            dict(kind='reset',id='reset01',timestamp='2026-11-12T00:00:00+01:00',volume_ml=0),
        ]
        self.consumed_ml=260
        self.manual_consumed_ml=260
    def get_liquid_definitions(self):return deepcopy(self.liquid_definitions)
    def get_cup_types(self):return deepcopy(self.cup_types)
    def get_quick_buttons(self):return deepcopy(self.quick_buttons)

for _n in ('canonical_liquid','mapped_cup','get_history','export_snapshot'):
    setattr(InMemoryProfile,_n,coordinator_method(_n))

def row_values(z, sheet_id):
    tree=ET.fromstring(z.read(f'xl/worksheets/sheet{sheet_id}.xml'))
    output={}
    for row in tree.findall('./m:sheetData/m:row',NS):
        result={}
        for cell in row.findall('m:c',NS):
            key=re.match(r'([A-Z]+)',cell.get('r')).group(1)
            v=cell.find('m:v',NS)
            if v is not None:
                result[key]=float(v.text) if v.text is not None else None
            else:
                result[key]=''.join(cell.itertext()) if cell.get('t')=='inlineStr' else ''
        output[int(row.get('r'))]=result
    return tree,output

def serial_as_datetime(serial):
    return datetime(1899,12,30)+timedelta(days=serial)

def check(profile):
    excel=load_excel()
    original_records=deepcopy(profile.records)
    snap=profile.export_snapshot()
    assert 'legacy_cup_defaults' in snap, 'Export drops same-liquid legacy Cup mappings!'
    assert snap['legacy_cup_defaults']==profile.legacy_cup_defaults
    assert snap['legacy_mappings']==profile.legacy_mappings
    snap['config']['name']='Fixture'
    raw=excel.export_xlsx([snap],'Europe/Amsterdam',datetime(2026,11,12,13,0,tzinfo=timezone.utc))
    from io import BytesIO
    with ZipFile(BytesIO(raw)) as z:
        assert z.testzip() is None
        assert len([x for x in z.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml',x)])==4
        for name in z.namelist():
            if name.endswith(('.xml','.rels')):ET.fromstring(z.read(name))
        book=ET.fromstring(z.read('xl/workbook.xml'))
        assert [s.get('name') for s in book.findall('.//m:sheet',NS)]==['Hydration log','Daily intake','Settings - Liquid Types','Settings - Volume Buttons']
        hdr,rr=row_values(z,1)
        _,daily=row_values(z,2)
        assert hdr.find('.//m:col[@min="2"]',NS) is not None or 'width="19"' in z.read('xl/worksheets/sheet1.xml').decode()
        assert daily[11]['B']=='Date'
        height=ET.fromstring(z.read('xl/worksheets/sheet2.xml')).find('./m:sheetData/m:row[@r="11"]',NS).attrib['ht']
        assert float(height)==44.0
        assert sum(len([x for x in daily if x>=12 and 'B' in daily[x]]) for _ in [0])==len({r['timestamp'][:10] for r in profile.records if r['kind']=='drink'})
        expected=[]
        for day in sorted({r['timestamp'][:10] for r in profile.records if r.get('kind')=='drink'}):
            expected += profile.get_history(day)
        expected.sort(key=lambda r:(r['timestamp'],r['id']))
        actual=[v for row,v in rr.items() if row>=12 and 'B' in v]
        assert len(actual)==len(expected),(len(actual),len(expected))
        cups={x['id']:x['name'] for x in profile.cup_types}
        counts=Counter()
        for idx,(a,e) in enumerate(zip(actual,expected),1):
            dt=serial_as_datetime(a['B'])
            expect_dt=datetime.fromisoformat(e['timestamp']).replace(tzinfo=None)
            assert abs((dt-expect_dt).total_seconds()) < 0.02,(idx,dt,expect_dt)
            assert a['H']==e['volume_ml'],(idx,'volume',a.get('H'),e['volume_ml'])
            assert a['G']==e['liquid_type'],(idx,'liquid',a.get('G'),e['liquid_type'])
            cup_name=cups.get(e['cup_type_id'],'') if e.get('cup_type_id') else ''
            assert a['I']==cup_name,(idx,'cup',a.get('I'),cup_name)
            if cup_name:counts[cup_name]+=1
            else:counts['UNKNOWN']+=1
            assert a['K']==(e['original_liquid_type'] if e['original_liquid_type']!=e['liquid_type'] else '')
        assert counts==Counter({'Mug':3,'Glass':2,'Bottle':1,'UNKNOWN':2}),counts
        assert sum(v['H'] for v in actual)==sum(r['volume_ml'] for r in profile.records if r.get('kind')=='drink')
        assert 'xl/tables/table1.xml' in z.namelist() and 'xl/tables/table2.xml' in z.namelist()
        assert b'<f>' in z.read('xl/worksheets/sheet2.xml')
        assert 'legacy_cup_defaults' not in z.namelist(), 'settings must not leak raw internal JSON'
    assert profile.records==original_records,'Export mutated drink ledger'
    print('BETA28_BACKEND_XLSX_PARITY_PASS',len(expected),'records',dict(counts),'4 sheets','ZIP CRC+OOXML+formulas')

if __name__=='__main__':check(InMemoryProfile())
