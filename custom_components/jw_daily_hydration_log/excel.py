"""Export jwDaily Hydration Log as the user's four-sheet Excel reference workbook.

Four worksheets, cell layout, dates, fonts, fills, borders, tables, and frozen
headers follow the user-supplied 20261109-1428 workbook. Profile data, drink
history and UI settings come exclusively from Home Assistant snapshots.

The generated XLSX is in memory, with no public URL, temporary files, macros,
third-party dependencies, embedded personal records, or network access.
"""
from __future__ import annotations

import base64
import collections
import copy
from datetime import datetime, date, timezone
from io import BytesIO
import math
import xml.etree.ElementTree as ET
import zlib
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED
from zoneinfo import ZoneInfo

VERSION = '1.1.0-beta.15'
SHEETS = ['Hydration log', 'Daily intake', 'Settings - Liquid Types', 'Settings - Volume Buttons']

# Compressed styles and Office theme (visual metadata only, no user profile data)
# extracted from the supplied Excel reference. Values contain no workbook cells.
_STYLES_Z = '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'
_THEME_Z = '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'
STYLES = zlib.decompress(base64.b64decode(_STYLES_Z))
THEME = zlib.decompress(base64.b64decode(_THEME_Z))

_BUILTIN = ('water', 'coffee', 'tea', 'milk', 'soup', 'wine', 'other')


def export_filename(timezone_name: str = 'Europe/Amsterdam', when: datetime | None = None) -> str:
    try:
        tz = ZoneInfo(timezone_name)
    except (KeyError, ValueError):
        tz = ZoneInfo('UTC')
    local = when.astimezone(tz) if when is not None else datetime.now(tz)
    return f'{local:%Y%m%d-%H%M} jwDaily Hydration Log - All Data.xlsx'


def _xml(value) -> str:
    """Remove XML 1.0-invalid control and surrogate code points before escaping."""
    clean=''.join(c for c in str(value) if c in '\t\n\r' or
                  (0x20 <= ord(c) <= 0xD7FF) or
                  (0xE000 <= ord(c) <= 0xFFFD) or
                  (0x10000 <= ord(c) <= 0x10FFFF))
    return escape(clean, {'"':'&quot;', "'":'&apos;'})


def _safe_text(value) -> str:
    value = str(value)
    # Prevent formula injection even after a CSV export of this workbook.
    if value.startswith(('=', '+', '-', '@', '\t', '\r')):
        value = "'" + value
    return value


def _col(index: int) -> str:
    letters = ''
    while index:
        index, digit = divmod(index - 1, 26)
        letters = chr(65 + digit) + letters
    return letters


def _cell(address: str, value, style: int = 0, formula: str | None = None) -> str:
    attrs = f' r="{address}" s="{style}"'
    if value is None:
        return f'<c{attrs}/>'
    if isinstance(value, bool):
        return f'<c{attrs} t="b"><v>{int(value)}</v></c>'
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        v = repr(value)
        if formula:
            return f'<c{attrs}><f>{_xml(formula.removeprefix("="))}</f><v>{v}</v></c>'
        return f'<c{attrs}><v>{v}</v></c>'
    # Explicit inline string: never evaluated as Excel formula.
    return f'<c{attrs} t="inlineStr"><is><t xml:space="preserve">{_xml(_safe_text(value))}</t></is></c>'


def _local_dt(value, tz: ZoneInfo) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z','+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(tz)
    except (ValueError, TypeError, OverflowError):
        return None


def _serial(value: datetime | date) -> float:
    if isinstance(value, datetime):
        naive=value.replace(tzinfo=None)
        return (naive - datetime(1899,12,30)).total_seconds()/86400
    return (value - date(1899,12,30)).days


def _dataset_period(profiles: list[dict], tz: ZoneInfo, now: datetime) -> str:
    values=[]
    for p in profiles:
        for item in p.get('records',[]):
            parsed=_local_dt(item.get('timestamp'),tz)
            if parsed: values.append(parsed)
        for item in p.get('source_readings',[]):
            parsed=_local_dt(item.get('timestamp'),tz)
            if parsed: values.append(parsed)
        for v in p.get('daily_archive',{}).values():
            parsed=_local_dt(v.get('closed_at'),tz)
            if parsed: values.append(parsed)
    first=min(values) if values else now
    def part(x): return f"{x.day}-{x:%b}-'{x:%y} {x:%H:%M}"
    return f'{part(first)} - {part(now)}'


def _cols(widths: list[float]) -> str:
    return '<cols>' + ''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i,w in enumerate(widths,1)) + '</cols>'


def _worksheet(index: int, rows: dict[int,list[tuple[int, object, int, str | None]]],
               widths: list[float], last_cell: str, last_row: int,
               table: bool = False) -> bytes:
    """Preformatted worksheet with reference workbook's B2 headings and B11 tables."""
    parts=['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
     '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
     f'<dimension ref="{("B2:" if index in (1,2) else "A1:")}{last_cell}"/>',
     '<sheetViews><sheetView workbookViewId="0"'+(' tabSelected="1"' if index==1 else '')+'>']
    if index in (1,2):
        parts.append('<pane ySplit="11" topLeftCell="A12" activePane="bottomLeft" state="frozen"/>')
    parts+=['</sheetView></sheetViews><sheetFormatPr defaultRowHeight="14.6"/>', _cols(widths), '<sheetData>']
    for row in sorted(rows):
        rowheight=(' ht="44" customHeight="1"' if index==2 else ' ht="34" customHeight="1"') if row==11 and index in (1,2) else (' ht="18.45" customHeight="1"' if row==2 and index in (1,2) else '')
        parts.append(f'<row r="{row}"{rowheight}>')
        for col,value,style,formula in sorted(rows[row],key=lambda x:x[0]):
            parts.append(_cell(f'{_col(col)}{row}',value,style,formula))
        parts.append('</row>')
    parts.append('</sheetData>')
    if index in (3,4):
        parts.append(f'<autoFilter ref="A1:{last_cell}"/>')
    # ECMA-376 worksheet schema: pageMargins MUST precede tableParts.
    # beta.8 reversed these and desktop Excel removed sheets 1 and 2.
    parts.append('<pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>')
    if table:
        parts.append('<tableParts count="1"><tablePart r:id="rId1"/></tableParts>')
    parts.append('</worksheet>')
    return ''.join(parts).encode('utf-8')


def _table(table_number: int, bottom: int, liquid_headers: list[str] | None = None) -> bytes:
    """Structured Excel tables, including table filters and header layout."""
    if table_number==1:
        label='tblHydrationLog'; right='H'
        headers=['Date+time','Profile','Age','Gender','Target_x000a_(mL)','Liquid name','Volume_x000a_(mL)']
        attrs='headerRowDxfId="15" dataDxfId="26" headerRowBorderDxfId="24" tableBorderDxfId="25" totalsRowBorderDxfId="23"'
    else:
        label='tblDailyIntake'
        assert liquid_headers is not None
        right=_col(10+len(liquid_headers))
        headers=['Date','Profile','Age','Gender','Full day','Target_x000a_(mL)','Drink_x000a_count','Volume_x000a_(mL)','%']
        headers += [name.replace('\n','_x000a_') for name in liquid_headers]
        attrs='headerRowDxfId="0" dataDxfId="32" headerRowBorderDxfId="30" tableBorderDxfId="31" totalsRowBorderDxfId="29"'
    # Excel tables must have at least one row below their header in the table range.
    rng=f'B11:{right}{max(12,bottom)}'
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
       f'id="{table_number}" name="{label}" displayName="{label}" ref="{rng}" totalsRowShown="0" {attrs}>'
       f'<autoFilter ref="{rng}"/>'
       f'<tableColumns count="{len(headers)}">' + ''.join(f'<tableColumn id="{i}" name="{_xml(head)}"/>' for i,head in enumerate(headers,1))
       + '</tableColumns><tableStyleInfo showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/></table>').encode('utf-8')



def _styles_with_legacy_header() -> tuple[bytes,int]:
    """Extend the original Office XML *without serializing it with ElementTree*.

    ElementTree discarded x14ac/x16r2/xr prefix declarations while leaving
    mc:Ignorable names intact. Desktop Excel then removed xl/styles.xml and
    repaired every table. Preserve original namespace declarations verbatim.
    """
    import re
    original = STYLES.decode('utf-8')
    root = ET.fromstring(original)
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    fills = root.find(ns+'fills')
    xfs = root.find(ns+'cellXfs')
    if fills is None or xfs is None or len(xfs) < 7:
        raise ValueError('Unexpected Office style structure')
    new_fill_id = len(fills)
    new_style_id = len(xfs)
    fill = '<fill><patternFill patternType="solid"><fgColor rgb="FFFFA500"/><bgColor indexed="64"/></patternFill></fill>'
    # Original header style has wrapText and border/number format settings.
    base = ET.tostring(xfs[6], encoding='unicode').replace('ns0:', '').replace(' xmlns:ns0="http://schemas.openxmlformats.org/spreadsheetml/2006/main"','')
    base = re.sub(r'\bfillId="[^"]*"', f'fillId="{new_fill_id}"', base)
    if 'applyFill=' in base:
        base = re.sub(r'\bapplyFill="[^"]*"', 'applyFill="1"', base)
    else:
        base = base.replace('<xf ', '<xf applyFill="1" ', 1)
    # Do not allow reserialization to change the original xmlns prefix mapping.
    def inject(match, content, count):
        attrs, inside = match.group(1), match.group(2)
        attrs = re.sub(r'\bcount="[^"]+"', f'count="{count}"', attrs)
        return f'<{content[0]}{attrs}>{inside}{content[1]}</{content[0]}>'
    fmatch = re.search(r'<fills([^>]*)>(.*?)</fills>', original, re.S)
    xmatch = re.search(r'<cellXfs([^>]*)>(.*?)</cellXfs>', original, re.S)
    if fmatch is None or xmatch is None:
        raise ValueError('Original styles missing required collections')
    # Edit the last group first to retain original positions for earlier group.
    original = original[:xmatch.start()] + inject(xmatch, ('cellXfs',base),new_style_id+1) + original[xmatch.end():]
    fmatch = re.search(r'<fills([^>]*)>(.*?)</fills>', original, re.S)
    original = original[:fmatch.start()] + inject(fmatch, ('fills',fill),new_fill_id+1) + original[fmatch.end():]
    ET.fromstring(original)  # XML and namespace syntax gate; Excel structure gate in QA.
    return original.encode('utf-8'),new_style_id


def _record_table(profiles: list[dict], tz: ZoneInfo):
    """Actual logged drinks with user-editable liquid display names; no artificial records."""
    result=[]
    for p in profiles:
        cfg=p['config']; target=p.get('target_ml',0)
        definitions={v['id']:v.get('name',v['id']) for v in p.get('liquid_definitions',[])}
        for record in p.get('records',[]):
            if record.get('kind')!='drink':continue
            local=_local_dt(record.get('timestamp'),tz)
            if local is None:continue
            day=local.date().isoformat()
            target_day=p.get('daily_archive',{}).get(day,{}).get('target_ml') or target
            liquid=record.get('liquid_type') or 'unknown'
            # The reference deliberately displays built-in IDs in lowercase;
            # only user-created liquids use their chosen display names.
            display=(liquid if liquid in _BUILTIN else definitions.get(liquid, 'Unknown (legacy)' if liquid=='unknown' else liquid))
            result.append((p,_serial(local),cfg['name'],cfg.get('age'),cfg.get('gender'),
                           target_day,display,float(record.get('volume_ml',0)),day,liquid))
    # Chronological presentation, independent of the original storage order.
    # Stable sorting preserves input order for exact ties.
    result.sort(key=lambda row: (row[1], str(row[2]), str(row[9])))
    return result


def export_xlsx(profiles: list[dict], timezone_name: str='Europe/Amsterdam', when: datetime | None = None) -> bytes:
    """Match the supplied four-sheet reference, retaining ALL drink records.

    All configured liquid IDs receive Daily intake columns. Historical-only
    liquid IDs remain as orange-header columns, never merged into Other.
    """
    try: tz=ZoneInfo(timezone_name)
    except (KeyError,ValueError): tz=ZoneInfo('UTC')
    now=when.astimezone(tz) if when is not None else datetime.now(tz)
    today=now.date().isoformat()
    records=_record_table(profiles,tz)
    current={}
    for profile in profiles:
        for typ in (profile.get('liquid_definitions') or profile.get('custom_liquid_types') or []):
            lid=str(typ.get('id') or '').strip()
            if lid and lid not in current:
                current[lid]=str(typ.get('name') or lid)
    historic={}
    for item in records:
        lid=str(item[9])
        if lid not in current and lid not in historic:
            historic[lid]=str(item[6]) if str(item[6]) not in ('Unknown (legacy)','') else lid
    ordered_types=[(lid,name,False) for lid,name in current.items()]
    ordered_types += [(lid,name,True) for lid,name in historic.items()]
    if not current:
        ordered_types=[(lid,lid.title(),False) for lid in _BUILTIN]
        ordered_types += [(lid,name,True) for lid,name in historic.items() if lid not in _BUILTIN]
    liquid_headers=[f'{name}\n(mL)' for _,name,_ in ordered_types]
    styles_xml,legacy_header_style=_styles_with_legacy_header()
    days=[]
    for p in profiles:
        dates={row[8] for row in records if row[0] is p}
        # Include sensor-driven days even if no manual drink events were saved.
        for datekey,snap in p.get('daily_archive',{}).items():
            if float(snap.get('consumed_ml',0) or 0)>0:
                dates.add(datekey)
        if p.get('date') and p.get('date')<=today and float(p.get('consumed_ml',0) or 0)>0:
            dates.add(p['date'])
        for day in sorted(dates):
            daily=[r for r in records if r[0] is p and r[8]==day]
            counter=collections.defaultdict(float)
            for r in daily: counter[r[9]]+=r[7]
            old=p.get('daily_archive',{}).get(day)
            if day==p.get('date'):
                consumed=p.get('consumed_ml',0);target=p.get('target_ml',0)
            elif old:
                consumed=old.get('consumed_ml',sum(r[7] for r in daily));target=old.get('target_ml',p.get('target_ml',0))
            else:
                consumed=sum(r[7] for r in daily);target=p.get('target_ml',0)
            days.append(dict(day=day,p=p,cfg=p['config'],consumed=float(consumed or 0),
                             target=float(target or 0),count=len(daily),types=counter))
    days.sort(key=lambda row:(row['day'],str(row['cfg'].get('name',''))))

    common_meta=[('Export date',_serial(now)),('Dataset period',_dataset_period(profiles,tz,now)),
                 ('Integration version',VERSION),('Number of profiles',len(profiles))]
    def summary(title: str,count_label: str,count_value: int,second=False):
        rows={2:[(2,title,2,None)],11:[]}
        for row,(name,value) in enumerate(common_meta,4):
            rows[row]=[(2,name,3 if row==4 else 0,None),
                       (3,value,(9 if second else 4) if row==4 else (8 if row==7 else 0),None)]
        rows[8]=[(2,count_label,0,None),(3,count_value,8,None)]
        return rows

    logrows=summary('Home Assistant jwDaily Hydration log - Hydration log','Drink log rows',len(records))
    heads=['Date+time','Profile','Age','Gender','Target\n(mL)','Liquid name','Volume\n(mL)']
    hstyles=[10,11,11,11,11,23,24]
    logrows[11]=[(col,h,sty,None) for col,(h,sty) in enumerate(zip(heads,hstyles),2)]
    for rownum,r in enumerate(records,12):
        _,stamp,name,age,gender,target,liquid,volume,_,_=r
        sty=[25,26,27,27,27,26,28]
        if rownum==len(records)+11:
            sty=[29,30,31,31,31,30,32]
        logrows[rownum]=[(col,value,sty[col-2],None) for col,value in enumerate([stamp,name,age,gender,target,liquid,volume],2)]
    if not records:
        logrows[12]=[]

    drows=summary('Home Assistant jwDaily Hydration Log  - Daily totals','Daily total rows',len(days),second=True)
    dheads=['Date','Profile','Age','Gender','Full day','Target\n(mL)','Drink\ncount','Volume\n(mL)','%']+liquid_headers
    dhstyles=[10,11,11,11,12,13,13,13,14]+[legacy_header_style if legacy else 6 for _,_,legacy in ordered_types]
    drows[11]=[(col,h,sty,None) for col,(h,sty) in enumerate(zip(dheads,dhstyles),2)]
    for rnum,row in enumerate(days,12):
        values=[_serial(date.fromisoformat(row['day'])),row['cfg']['name'],row['cfg'].get('age'),
                row['cfg'].get('gender'),'Yes' if row['day']<today else 'No',
                row['target'],row['count'],row['consumed'],
                round(row['consumed']/row['target']*100,12) if row['target']>0 else 0]
        values += [round(row['types'].get(lid,0),3) for lid,_,_ in ordered_types]
        styles=[15,16,27,27,17,16,16,16,18]+[0]*len(ordered_types)
        if rnum==len(days)+11:
            styles=[19,20,27,27,21,20,20,20,22]+[0]*len(ordered_types)
        drows[rnum]=[(col,value,styles[col-2],f'I{rnum}/G{rnum}*100' if col==10 and row['target']>0 else None)
                     for col,value in enumerate(values,2)]
    if not days:drows[12]=[]

    typesrows={1:[(i,h,1,None) for i,h in enumerate(['Profile','Liquid ID','Name','MDI Icon','SVG Image','Default volume mL','Custom','Button order','Visible in picker'],1)]}
    buttonsrows={1:[(i,h,1,None) for i,h in enumerate(['Profile','Position','Volume mL','Custom configured'],1)]}
    for p in profiles:
        cfg=p['config']
        liquid_defs=p.get('liquid_definitions') or p.get('custom_liquid_types') or []
        for position, typ in enumerate(liquid_defs,1):
            row=len(typesrows)+1
            vals=[cfg['name'],typ.get('id',''),typ.get('name',''),typ.get('icon_mdi',''),
                  typ.get('icon_svg',''),typ.get('default_volume_ml'), bool(typ.get('custom',False)),
                  position,not bool(typ.get('hidden',False))]
            typesrows[row]=[(i,value,0,None) for i,value in enumerate(vals,1)]
        volumes=p.get('volume_buttons')
        if volumes is None:
            volumes=[]
        for position, volume in enumerate(volumes,1):
            row=len(buttonsrows)+1
            vals=[cfg['name'],position,volume,True]
            buttonsrows[row]=[(i,value,0,None) for i,value in enumerate(vals,1)]

    content=[
     _worksheet(1,logrows,[4,19,16,6,9,9,17,11],f'H{max(12,11+len(records))}',max(12,11+len(records)),True),
     _worksheet(2,drows,[4.285,16,15,7,9,6,10,9,11,6]+[10]*len(ordered_types),f'{_col(10+len(ordered_types))}{max(12,11+len(days))}',max(12,11+len(days)),True),
     _worksheet(3,typesrows,[16,24,22,23,18,25,13,19,25],f'I{max(1,len(typesrows))}',len(typesrows)),
     _worksheet(4,buttonsrows,[16,14,18,25],f'D{max(1,len(buttonsrows))}',len(buttonsrows)),
    ]
    # Standard OOXML ZIP container. Includes reference styles and native tables.
    buffer=BytesIO()
    with ZipFile(buffer,'w',ZIP_DEFLATED,compresslevel=6) as z:
        main='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        relbase='http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        contenttypes=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          '<Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
          +''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,5))
          +''.join(f'<Override PartName="/xl/tables/table{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>' for i in range(1,3))+'</Types>')
        z.writestr('[Content_Types].xml',contenttypes)
        z.writestr('_rels/.rels',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{relbase}officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr('xl/workbook.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="'+main+'" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView activeTab="0"/></bookViews><sheets>'+''.join(f'<sheet name="{_xml(n)}" sheetId="{i}" r:id="rId{i}"/>' for i,n in enumerate(SHEETS,1))+'</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rId{i}" Type="{relbase}worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,5))+f'<Relationship Id="rId5" Type="{relbase}styles" Target="styles.xml"/><Relationship Id="rId6" Type="{relbase}theme" Target="theme/theme1.xml"/></Relationships>')
        z.writestr('xl/styles.xml',styles_xml)
        z.writestr('xl/theme/theme1.xml',THEME)
        for i,s in enumerate(content,1):
            z.writestr(f'xl/worksheets/sheet{i}.xml',s)
            if i<=2:
                z.writestr(f'xl/worksheets/_rels/sheet{i}.xml.rels',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="{relbase}table" Target="../tables/table{i}.xml"/></Relationships>')
                z.writestr(f'xl/tables/table{i}.xml',_table(i,max(12,11+(len(records) if i==1 else len(days))),liquid_headers if i==2 else None))
    return buffer.getvalue()