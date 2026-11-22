"""Export jwDaily Hydration Log in the six-sheet reference workbook layout.

Six worksheets match the user-supplied 20261120-1703 workbook: data rows
are 18 pt and vertically centered, with the log header 38 pt, Daily intake
liquid-only column auto sizing and fully separate Settings tabs. Profile data, drink
history and UI settings come exclusively from Home Assistant snapshots.

The generated XLSX is in memory, with no public URL, temporary files, macros,
third-party dependencies, embedded personal records, or network access.
"""
from __future__ import annotations

import base64
import collections
import copy
from datetime import datetime, date, timezone
from dataclasses import dataclass
from io import BytesIO
import math
import xml.etree.ElementTree as ET
import zlib
from xml.sax.saxutils import escape
from zipfile import ZipFile, ZIP_DEFLATED
from zoneinfo import ZoneInfo
from .const import default_liquid_color, from_ml
from .excel_icons import png_icon

VERSION = '1.5.1-beta.3'
SHEETS = ['Hydration log', 'Daily intake', 'Settings - Liquid Types', 'Settings - Cup types', 'Settings - Quick buttons', 'Settings - Profiles']

# Compressed styles and Office theme (visual metadata only, no user profile data)
# extracted from the supplied Excel reference. Values contain no workbook cells.
from .excel_reference_format import REFERENCE_STYLES as STYLES, REFERENCE_THEME as THEME, REFERENCE_COLS, REFERENCE_LIQUID_WIDTHS

_BUILTIN = ('water', 'coffee', 'tea', 'milk', 'soup', 'wine', 'other')


def export_filename(timezone_name: str = 'Europe/Amsterdam', when: datetime | None = None,
                    profile_name: str | None = None) -> str:
    try:
        tz = ZoneInfo(timezone_name)
    except (KeyError, ValueError):
        tz = ZoneInfo('UTC')
    local = when.astimezone(tz) if when is not None else datetime.now(tz)
    invalid=set('<>:"/|?*')
    scope=(''.join(ch for ch in str(profile_name)
                    if ch not in invalid and ch!=chr(92) and ord(ch)>=32).strip()
           if profile_name else 'All Data')
    return f'{local:%Y%m%d-%H%M} jwDaily Hydration Log - {scope or "Profile"}.xlsx'


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


@dataclass(frozen=True)
class InCellImage:
    """Native Excel Place in Cell image, referenced via rich value metadata."""
    number: int


def _cell(address: str, value, style: int = 0, formula: str | None = None) -> str:
    attrs = f' r="{address}" s="{style}"'
    if isinstance(value, InCellImage):
        if value.number < 1:raise ValueError('Invalid Place in Cell image index')
        # Excel's own saved Place in Cell representation uses a cached #VALUE!
        # and vm=index. The rich-value metadata supplies the actual image and
        # Excel displays the image, not the cached fallback error.
        return f'<c{attrs} t="e" vm="{value.number}"><v>#VALUE!</v></c>'
    if value is None:
        return f'<c{attrs}/>'
    if isinstance(value, bool):
        # Excel's ordinary UI shows Boolean cells as TRUE/FALSE; the report
        # contract uses Yes/No for all exported settings and Boolean data.
        return f'<c{attrs} t="inlineStr"><is><t>{"Yes" if value else "No"}</t></is></c>'
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


def _cols(widths: list[float | tuple[float,bool]]) -> str:
    """Fixed widths except Daily intake liquid columns flagged as best-fit."""
    def tag(i, value):
        width, auto = value if isinstance(value, tuple) else (value, False)
        return (f'<col min="{i}" max="{i}" width="{width:.4f}"'
                + (' bestFit="1"' if auto else '') + ' customWidth="1"/>')
    return '<cols>' + ''.join(tag(i,w) for i,w in enumerate(widths,1)) + '</cols>'

def _liquid_width(name: str, unit_label: str) -> tuple[float, bool]:
    """Fitted columns only for Liquid types; base widths match approved workbook."""
    canonical=str(name).strip().casefold()
    width=(REFERENCE_LIQUID_WIDTHS.get(canonical)
           if unit_label=='mL' else None)
    if width is None:
        header=f'{name}\n({unit_label})'
        width=float(max(8, min(38,max(len(x) for x in header.splitlines())+2.25)))
    return (float(width),True)


def _fit_reference_columns(index: int, source: str, rows: dict) -> str:
    """Content-fit technical IDs and MDI paths, preserving other reference cols.

    OOXML bestFit alone is not a reliable recalculation request on Excel open;
    generate actual safe content-derived widths plus bestFit metadata.
    """
    import re
    targets={3:(5,),4:(3,6),5:(9,)}.get(index,())
    if not targets:return source

    def measured_width(position):
        values=[]
        for row, cells in rows.items():
            if row < 9:continue
            for col, value, _style, _formula in cells:
                if col==position and value is not None and isinstance(value,str):
                    values.extend(value.splitlines())
        longest=max((len(v) for v in values),default=0)
        return float(max(13, min(72, longest+3)))

    def boundary(tag,lo,hi):
        tag=re.sub(r'\bmin="\d+"',f'min="{lo}"',tag,count=1)
        return re.sub(r'\bmax="\d+"',f'max="{hi}"',tag,count=1)

    result=[]
    for original in re.findall(r'<col\b[^>]*/>',source):
        low=int(re.search(r'\bmin="(\d+)"',original).group(1))
        high=int(re.search(r'\bmax="(\d+)"',original).group(1))
        affected=[p for p in targets if low<=p<=high]
        if not affected:
            result.append(original)
            continue
        start=low
        for p in sorted(affected):
            if start<p:result.append(boundary(original,start,p-1))
            fitted=boundary(original,p,p)
            fitted=re.sub(r'\bwidth="[^"]+"',f'width="{measured_width(p):g}"',fitted,count=1)
            if 'bestFit=' in fitted:
                fitted=re.sub(r'\bbestFit="[^"]+"','bestFit="1"',fitted,count=1)
            else:
                fitted=fitted.replace(' customWidth=', ' bestFit="1" customWidth=',1)
            result.append(fitted)
            start=p+1
        if start<=high:result.append(boundary(original,start,high))
    return '<cols>'+''.join(result)+'</cols>'


def _reference_columns(index: int, widths: list[float | tuple[float,bool]], rows: dict | None = None) -> str:
    """Original exact column geometry; only Daily intake Liquid types are dynamic."""
    if index==2:
        # Preserve the ten fixed metadata columns byte-for-byte from the
        # supplied reference. Dynamic Liquid columns are the ONLY fitted ones.
        import re
        fixed=[]
        for col in re.findall(r'<col\b[^>]*/>', REFERENCE_COLS[2]):
            n=re.search(r'\bmin="(\d+)"',col)
            if n and int(n.group(1))<=10:
                fixed.append(col)
        variable=[]
        for position,width in enumerate(widths[10:],11):
            value, fit = width if isinstance(width,tuple) else (width,False)
            variable.append(f'<col min="{position}" max="{position}" width="{value}"'
                            + (' bestFit="1"' if fit else '') + ' customWidth="1"/>')
        return '<cols>'+''.join(fixed)+''.join(variable)+'</cols>'
    if index==5:
        # Keep every existing column width, shifting the Order+ columns right
        # by one; new J holds the native Place in Cell icon graphics.
        import re
        original=re.findall(r'<col\b[^>]*/>', REFERENCE_COLS[5])
        moved=[]
        for raw in original:
            match=re.search(r'\bmin="(\d+)"\s+max="(\d+)"',raw)
            if match is None:raise ValueError('Malformed reference column XML')
            minimum,maximum=int(match.group(1)),int(match.group(2))
            if minimum>=10:
                raw=raw[:match.start()]+f'min="{minimum+1}" max="{maximum+1}"'+raw[match.end():]
            moved.append((minimum if minimum<10 else minimum+1,raw))
        moved.append((10,'<col min="10" max="10" width="11.5" customWidth="1"/>'))
        return _fit_reference_columns(index,'<cols>'+''.join(raw for _,raw in sorted(moved))+'</cols>',rows or {})
    cols=REFERENCE_COLS[index]
    if index in (3,4):
        return _fit_reference_columns(index,cols,rows or {})
    if index==6 and len(widths)>9:
        # Extend the approved Profiles columns; keep all existing widths intact.
        extras=''.join(f'<col min="{i}" max="{i}" width="{w:g}" customWidth="1"/>'
                       for i,w in enumerate(widths[9:],10))
        return cols.replace('</cols>',extras+'</cols>')
    if index==1 and len(widths)>9:
        extras=''.join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
                       for i,w in enumerate(widths[9:],10))
        return cols.replace('</cols>',extras+'</cols>')
    return cols


# Indexed exactly as in the approved 20261120-1703 reference workbook.
# Only user-requested differences: all data rows 18pt, all cells vertical center,
# full native IDs and current data from HA, and Liquid types dynamic widths.
_REFERENCE_HEADERS = {
 1:[5,6,6,6,6,8,9,9],
 2:[24,25,25,25,26,23,23,23,23],
 3:[54,48,47,47,47,47,47,47,47,47,47,49],
 4:[46,54,47,48,47,47,47,47,49],
 5:[46,47,47,47,48,47,47,47,47,47,47,47,47,50],
 6:[51,55,52,52,52,52,52,52,52,53],
}
_REFERENCE_BODY = {
 1:[10,11,11,11,11,11,12,11],
 2:[17,7,11,11,19,7,7,7,18],
 3:[30,30,11,11,11,11,11,11,20,11,11,12],
 4:[43,43,11,11,11,11,11,11,45],
 5:[43,11,11,11,11,19,11,12,11,11,11,11,11,11],
 6:[43,43,11,11,11,11,11,11,11,12],
}
_REFERENCE_LAST = {
 1:[13,14,14,14,14,14,15,14],
 3:[31,31,14,14,14,14,14,14,29,14,14,15],
 4:[44,44,14,14,14,14,14,14,45],
 5:[44,14,14,14,14,19,14,15,14,14,14,14,14,14],
 6:[44,44,14,14,14,14,14,14,14,15],
}

def _apply_reference_styles(index, rows):
    """Preserve approved cell fonts, fills, borders, number formats and position."""
    header=11 if index in (1,2) else 8 if index==6 else 9
    data_rows=[r for r in rows if r>header and rows[r]]
    last=max(data_rows) if data_rows else None
    for row, items in rows.items():
        revised=[]
        for col,value,style,formula in items:
            if row==2: target=1
            elif row==4: target=(2 if col==2 else 16 if index==1 else 4)
            elif row==7 and index in (3,4,5): target=(2 if col==2 else 3)
            elif row in (5,6,7,8) and row!=header:
                target=3 if col==3 and (row==6 and index>2 or row in (7,8) and index in (1,2)) else 0
            elif row==header:
                heads=_REFERENCE_HEADERS[index]
                if index==2 and col>=11:
                    target=22 if col==max(x[0] for x in rows[row]) else 21
                else: target=heads[min(col-2,len(heads)-1)]
            elif row>header:
                arr=_REFERENCE_LAST.get(index) if last==row else None
                if arr is None:arr=_REFERENCE_BODY[index]
                target=arr[min(col-2,len(arr)-1)]
                if index==2 and col>=11:target=11
                if index==3 and col==11:target=style  # Dynamic HA color swatch.
            else:target=style
            revised.append((col,value,target,formula))
        rows[row]=revised


def _worksheet(index: int, rows: dict[int,list[tuple[int, object, int, str | None]]],
               widths: list[float | tuple[float,bool]], last_cell: str, last_row: int,
               table: bool = False, drawing: bool = False) -> bytes:
    """Reference worksheet positions B2/B4; proper 18pt body and centered text.

    B11 is the header for the two data tables; settings have B9, profiles B8.
    """
    header_row = 11 if index in (1,2) else (8 if index == 6 else 9)
    parts=['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
      '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
      f'<dimension ref="B2:{last_cell}"/>',
      '<sheetViews><sheetView workbookViewId="0"'+(' tabSelected="1"' if index==1 else '')+'>']
    if index in (1,2):
        parts.append('<pane ySplit="11" topLeftCell="A12" activePane="bottomLeft" state="frozen"/>')
    parts += ['</sheetView></sheetViews><sheetFormatPr defaultRowHeight="14.6"/>',
              _reference_columns(index,widths,rows),'<sheetData>']
    for row in sorted(rows):
        if row >= header_row:
            if row == header_row:
                height = 38 if index == 1 else (44.05 if index == 2 else 43.75)
            else:
                height = 18
            rowheight = f' ht="{height}" customHeight="1"'
        elif row == 2:
            rowheight=' ht="18.45" customHeight="1"'
        else:
            rowheight=''
        parts.append(f'<row r="{row}"{rowheight}>')
        for col,value,style,formula in sorted(rows[row],key=lambda x:x[0]):
            parts.append(_cell(f'{_col(col)}{row}',value,style,formula))
        parts.append('</row>')
    parts.append('</sheetData>')
    # Order follows ECMA-376: margins before drawing/tableParts.
    parts.append('<pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>')
    if drawing:parts.append('<drawing r:id="rId1"/>')
    if table:parts.append('<tableParts count="1"><tablePart r:id="rId1"/></tableParts>')
    parts.append('</worksheet>')
    return ''.join(parts).encode('utf-8')


def _in_cell_image_parts(images: list[bytes]) -> dict[str, bytes]:
    """OOXML native *Place in Cell*, not a floating DrawingML shape.

    Schema and relationships mirror a Microsoft Excel 365 workbook saved with
    Insert → Pictures → Place in Cell (rich value / XLRICHVALUE metadata).
    """
    count=len(images)
    if not count:return {}
    def xml(text):return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+text).encode('utf-8')
    metadata=(''
      '<metadata xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:xlrd="http://schemas.microsoft.com/office/spreadsheetml/2017/richdata">'
      '<metadataTypes count="1"><metadataType name="XLRICHVALUE" minSupportedVersion="120000" '
      'copy="1" pasteAll="1" pasteValues="1" merge="1" splitFirst="1" '
      'rowColShift="1" clearFormats="1" clearComments="1" assign="1" coerce="1"/></metadataTypes>'
      f'<futureMetadata name="XLRICHVALUE" count="{count}">'
      +''.join('<bk><extLst><ext uri="{3e2802c4-a4d2-4d8b-9148-e3be6c30e623}">'
               f'<xlrd:rvb i="{i}"/></ext></extLst></bk>' for i in range(count))
      +f'</futureMetadata><valueMetadata count="{count}">'
      +''.join(f'<bk><rc t="1" v="{i}"/></bk>' for i in range(count))
      +'</valueMetadata></metadata>')
    rv_structure=(''
      '<rvStructures xmlns="http://schemas.microsoft.com/office/spreadsheetml/2017/richdata" count="1">'
      '<s t="_localImage"><k n="_rvRel:LocalImageIdentifier" t="i"/>'
      '<k n="CalcOrigin" t="i"/></s></rvStructures>')
    rv_data=(''
      f'<rvData xmlns="http://schemas.microsoft.com/office/spreadsheetml/2017/richdata" count="{count}">'
      +''.join(f'<rv s="0"><v>{i}</v><v>5</v></rv>' for i in range(count))
      +'</rvData>')
    types=(''
      '<rvTypesInfo xmlns="http://schemas.microsoft.com/office/spreadsheetml/2017/richdata2" '
      'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
      'mc:Ignorable="x" xmlns:x="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
      '<global><keyFlags>'
      +''.join(f'<key name="{name}"><flag name="ExcludeFromCalcComparison" value="1"/></key>'
               for name in ('_DisplayString','_Flags','_Format','_SubLabel','_Attribution',
                            '_Icon','_Display','_CanonicalPropertyNames','_ClassificationId'))
      +'<key name="_Self"><flag name="ExcludeFromFile" value="1"/>'
      '<flag name="ExcludeFromCalcComparison" value="1"/></key>'
      '</keyFlags></global></rvTypesInfo>')
    rel_list=(''
      '<richValueRels xmlns="http://schemas.microsoft.com/office/spreadsheetml/2022/richvaluerel" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
      +''.join(f'<rel r:id="rId{i+1}"/>' for i in range(count))
      +'</richValueRels>')
    rels=(''
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
      +''.join(f'<Relationship Id="rId{i+1}" '
               'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
               f'Target="../media/image{i+1}.png"/>' for i in range(count))
      +'</Relationships>')
    parts={
      'xl/metadata.xml':xml(metadata),
      'xl/richData/rdrichvaluestructure.xml':xml(rv_structure),
      'xl/richData/rdrichvalue.xml':xml(rv_data),
      'xl/richData/rdRichValueTypes.xml':xml(types),
      'xl/richData/richValueRel.xml':xml(rel_list),
      'xl/richData/_rels/richValueRel.xml.rels':xml(rels),
    }
    parts.update({f'xl/media/image{i+1}.png':png for i,png in enumerate(images)})
    return parts


def _table(table_number: int, bottom: int, liquid_headers: list[str] | None = None,
           unit: str = 'mL', mixed: bool = False,
           settings_headers: list[str] | None = None) -> bytes:
    """Reference-style structured tables, usable filters on all six sheets."""
    if table_number==1:
        label='tblHydrationLog'; right='K' if mixed else 'I'; first=11
        headers=['Date+time','Profile','Age','Gender',f'Target_x000a_({_unit_label(unit)})',
                 'Liquid name',f'Volume_x000a_({_unit_label(unit)})','Cup used']
        if mixed:headers+=['Profile unit','Volume (profile unit)']
        attrs='headerRowDxfId="15" dataDxfId="26" headerRowBorderDxfId="24" tableBorderDxfId="25" totalsRowBorderDxfId="23"'
    elif table_number==2:
        label='tblDailyIntake';first=11
        assert liquid_headers is not None
        right=_col(10+len(liquid_headers)+(2 if mixed else 0))
        headers=['Date','Profile','Age','Gender','Full day',f'Target_x000a_({_unit_label(unit)})','Drink_x000a_count',f'Volume_x000a_({_unit_label(unit)})','%']
        if mixed:headers+=['Profile unit','Volume (profile unit)']
        headers += [name.replace('\n','_x000a_') for name in liquid_headers]
        attrs='headerRowDxfId="0" dataDxfId="32" headerRowBorderDxfId="30" tableBorderDxfId="31" totalsRowBorderDxfId="29"'
    elif 3<=table_number<=6:
        label=f'Table{table_number-2}'; first=8 if table_number==6 else 9
        if settings_headers is None:raise ValueError('Settings table headers missing')
        headers=[str(h).replace('\n','_x000a_') for h in settings_headers]
        right=_col(len(headers)+1)
        attrs=''
    else:
        raise ValueError('Invalid table number')
    # A table range always contains at least one data row (can be blank).
    rng=f'B{first}:{right}{max(first+1,bottom)}'
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
       '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
       f'id="{table_number}" name="{label}" displayName="{label}" ref="{rng}" totalsRowShown="0" {attrs}>'
       f'<autoFilter ref="{rng}"/>'
       f'<tableColumns count="{len(headers)}">' + ''.join(f'<tableColumn id="{i}" name="{_xml(head)}"/>' for i,head in enumerate(headers,1))
       + '</tableColumns><tableStyleInfo showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/></table>').encode('utf-8')


def _styles_with_colored_liquid_cells(colors: list[str] | None = None) -> tuple[bytes,int,dict[str,int]]:
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
    # Only sheet 3 uses these additive solid-fill cell styles. The original
    # styles, workbook themes, table formatting and formulas remain intact.
    color_style_ids = {}
    for color in dict.fromkeys(colors or []):
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}', color):
            continue
        color = color.upper()
        if color in color_style_ids:
            continue
        # Reuse the exact approved Excel color+border style where available.
        # This retains the original Liquid swatches and bottom-row borders.
        approved = None
        for i, style in enumerate(xfs):
            fill_at = int(style.get('fillId','0'))
            if fill_at >= len(fills):continue
            pigment = fills[fill_at].find('.//'+ns+'fgColor')
            if pigment is not None and pigment.get('rgb','').upper() == 'FF'+color[1:]:
                approved=i
                break
        if approved is not None:
            color_style_ids[color]=approved
            continue
        parsed = ET.fromstring(original)
        color_fills = parsed.find(ns + 'fills')
        color_xfs = parsed.find(ns + 'cellXfs')
        fill_id, style_id = len(color_fills), len(color_xfs)
        fill = (f'<fill><patternFill patternType="solid"><fgColor rgb="FF{color[1:]}"/>'
                '<bgColor indexed="64"/></patternFill></fill>')
        # Sheet 3's original settings cells are style 0. Reuse its exact format,
        # changing only the fill reference.
        template = ET.tostring(color_xfs[11], encoding='unicode')
        template = template.replace('ns0:', '').replace(' xmlns:ns0="http://schemas.openxmlformats.org/spreadsheetml/2006/main"', '')
        template = re.sub(r'\bfillId="[^"]*"', f'fillId="{fill_id}"', template)
        if 'fillId=' not in template:
            template = template.replace('<xf ', f'<xf fillId="{fill_id}" ', 1)
        if 'applyFill=' in template:
            template = re.sub(r'\bapplyFill="[^"]*"', 'applyFill="1"', template)
        else:
            template = template.replace('<xf ', '<xf applyFill="1" ', 1)
        xmatch = re.search(r'<cellXfs([^>]*)>(.*?)</cellXfs>', original, re.S)
        original = original[:xmatch.start()] + inject(xmatch, ('cellXfs', template), style_id + 1) + original[xmatch.end():]
        fmatch = re.search(r'<fills([^>]*)>(.*?)</fills>', original, re.S)
        original = original[:fmatch.start()] + inject(fmatch, ('fills', fill), fill_id + 1) + original[fmatch.end():]
        color_style_ids[color] = style_id
    # Preserve the existing date/time number format while overriding alignment
    # only for the first worksheet's export date (C4).
    parsed = ET.fromstring(original)
    current_xfs = parsed.find(ns+'cellXfs')
    left_date_style_id = len(current_xfs)
    left_xf = copy.deepcopy(xfs[4])
    left_xf.set('applyAlignment','1')
    alignment=left_xf.find(ns+'alignment')
    if alignment is None:
        alignment=ET.SubElement(left_xf,ns+'alignment')
    alignment.set('horizontal','left')
    left_style = ET.tostring(left_xf,encoding='unicode').replace('ns0:','').replace(
        ' xmlns:ns0="http://schemas.openxmlformats.org/spreadsheetml/2006/main"','')
    match=re.search(r'<cellXfs([^>]*)>(.*?)</cellXfs>', original, re.S)
    original=original[:match.start()]+inject(match,('cellXfs',left_style),left_date_style_id+1)+original[match.end():]
    # All exported cells must be vertically centered, including styled
    # table-body cells, header text and the reference's date/percentage styles.
    # Replace only <cellXfs> content so Excel's original mc/xr prefixes survive.
    match=re.search(r'<cellXfs([^>]*)>(.*?)</cellXfs>', original, re.S)
    if match is None:raise ValueError('Missing cell style collection')
    def center_xf(raw: str) -> str:
        if raw.endswith('/>'):
            return raw[:-2]+'><alignment vertical="center"/></xf>'
        if '<alignment' in raw:
            return re.sub(r'<alignment\b([^>]*?)/>',lambda m:
                '<alignment'+re.sub(r'\svertical="[^"]*"', '', m.group(1))
                +' vertical="center"/>',raw,count=1)
        return raw.replace('</xf>','<alignment vertical="center"/></xf>')
    xfs_xml=re.sub(r'<xf\b[^>]*?/>|<xf\b[^>]*>.*?</xf>',
                   lambda m:center_xf(m.group(0)), match.group(2),flags=re.S)
    original=original[:match.start(2)]+xfs_xml+original[match.end(2):]
    ET.fromstring(original)
    return original.encode('utf-8'),new_style_id,color_style_ids,left_date_style_id


def _outline_all_tables(styles_xml: bytes, sheet_rows: list[dict]) -> bytes:
    """Add thin auto-black outside borders without changing internal line styles.

    Every style is cloned only if an outside edge is necessary. Original
    fonts, fills (including HA liquid colors), number formats and alignment
    remain untouched. All table rectangles B:LastColumn get all four edges.
    """
    import re
    source=styles_xml.decode('utf-8')
    ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    tree=ET.fromstring(source)
    borders=tree.find(ns+'borders');xfs=tree.find(ns+'cellXfs')
    if borders is None or xfs is None:raise ValueError('Missing Excel styles')
    border_cache={};style_cache={};extra_borders=[];extra_styles=[]
    def raw_xml(element):
        text=ET.tostring(element,encoding='unicode')
        return text.replace(' xmlns:ns0="http://schemas.openxmlformats.org/spreadsheetml/2006/main"','').replace('ns0:','')
    def new_style(base_style: int, sides: tuple[str,...]) -> int:
        if not sides:return base_style
        key=(base_style,sides)
        if key in style_cache:return style_cache[key]
        parent=xfs[base_style]
        base_border=int(parent.get('borderId','0'))
        borderkey=(base_border,sides)
        if borderkey not in border_cache:
            border=copy.deepcopy(borders[base_border])
            for side in sides:
                edge=border.find(ns+side)
                if edge is None:edge=ET.SubElement(border,ns+side)
                edge.set('style','thin')
                for child in list(edge):edge.remove(child)
                ET.SubElement(edge,ns+'color',{'indexed':'64'})
            border_cache[borderkey]=len(borders)+len(extra_borders)
            extra_borders.append(raw_xml(border))
        style=copy.deepcopy(parent)
        style.set('borderId',str(border_cache[borderkey]))
        style.set('applyBorder','1')
        index=len(xfs)+len(extra_styles)
        extra_styles.append(raw_xml(style))
        style_cache[key]=index
        return index
    for sheet_number, rows in enumerate(sheet_rows,1):
        head=11 if sheet_number<=2 else 8 if sheet_number==6 else 9
        last=max((r for r in rows if r>head),default=head+1)
        end=max((x[0] for x in rows[head]),default=2)
        # Even when there is no drink, show the complete bordered empty table.
        if not rows.get(last):rows[last]=[(c,None,11,None) for c in range(2,end+1)]
        for row in (r for r in sorted(rows) if head<=r<=last):
            updated=[]
            for col,value,style,formula in rows[row]:
                sides=tuple(side for needed,side in (
                    (row==head,'top'),(row==last,'bottom'),
                    (col==2,'left'),(col==end,'right')) if needed)
                updated.append((col,value,new_style(style,sides),formula))
            rows[row]=updated
    def extend(tag,body):
        nonlocal source
        pattern=fr'<{tag}([^>]*)>(.*?)</{tag}>'
        match=re.search(pattern,source,re.S)
        if match is None:raise ValueError('Could not extend '+tag)
        attrs=re.sub(r'\bcount="[^"]+"',f'count="{len(borders)+len(extra_borders) if tag=="borders" else len(xfs)+len(extra_styles)}"',match.group(1))
        source=source[:match.start()]+f'<{tag}{attrs}>{match.group(2)}'+''.join(body)+f'</{tag}>'+source[match.end():]
    if extra_borders:extend('borders',extra_borders)
    if extra_styles:extend('cellXfs',extra_styles)
    ET.fromstring(source)
    return source.encode('utf-8')


def _record_table(profiles: list[dict], tz: ZoneInfo):
    """Actual logged drinks with user-editable liquid display names; no artificial records."""
    result=[]
    for p in profiles:
        cfg=p['config']; target=p.get('target_ml',0)
        definitions={v['id']:v.get('name',v['id']) for v in p.get('liquid_definitions',[])}
        cup_details={c['id']:c for c in p.get('cup_types',[])}
        cups={ident:item.get('name',ident) for ident,item in cup_details.items()}
        quick={q['id']:q.get('label',q['id']) for q in p.get('quick_buttons',[])}
        for record in p.get('records', []):
            if record.get('kind') != 'drink':continue
            local=_local_dt(record.get('timestamp'),tz)
            if local is None:continue
            day=local.date().isoformat()
            target_day=p.get('daily_archive',{}).get(day,{}).get('target_ml') or target
            liquid=record.get('liquid_type_id')
            if liquid not in definitions:
                raise ValueError('Excel export blocked: historical record has no valid native Liquid')
            cup_id=record.get('cup_type_id')
            if cup_id and cup_id not in cup_details:
                raise ValueError('Excel export blocked: unknown native Cup reference')
            quick_id=record.get('quick_button_id') or ''
            result.append((p,_serial(local),cfg['name'],cfg.get('age'),cfg.get('gender'),
                           target_day,definitions[liquid],float(record['volume_ml']),day,liquid,
                           cups.get(cup_id,'') if cup_id else '',
                           record.get('cup_default_volume_ml_at_log', cup_details.get(cup_id,{}).get('default_volume_ml')) if cup_id else None,
                           record.get('quick_button_label_at_log') or quick.get(quick_id,quick_id)))
    # Chronological presentation, independent of the original storage order.
    # Stable sorting preserves input order for exact ties.
    result.sort(key=lambda row: (row[1], str(row[2]), str(row[9])))
    return result


def _unit(p):
    u=p.get('config',{}).get('unit','mL')
    return u if u in ('mL','L','fl_oz') else 'mL'

def _unit_label(unit):
    return 'fl oz' if unit=='fl_oz' else unit

def _volume(ml,unit):
    result = round(from_ml(float(ml or 0),unit), 6)
    return int(result) if result.is_integer() else result

def export_xlsx(profiles: list[dict], timezone_name: str='Europe/Amsterdam', when: datetime | None = None) -> bytes:
    """Match the supplied six-sheet reference, retaining ALL drink records.

    All native Liquid IDs receive Daily intake columns, never merged into Other.
    """
    try: tz=ZoneInfo(timezone_name)
    except (KeyError,ValueError): tz=ZoneInfo('UTC')
    now=when.astimezone(tz) if when is not None else datetime.now(tz)
    today=now.date().isoformat()
    mixed=len({_unit(profile) for profile in profiles})>1
    export_unit=(_unit(profiles[0]) if not mixed and profiles else 'mL')
    unit_label=_unit_label(export_unit)
    records=_record_table(profiles,tz)
    current={}
    for profile in profiles:
        for typ in (profile.get('liquid_definitions') or profile.get('custom_liquid_types') or []):
            lid=str(typ.get('id') or '').strip()
            if lid and lid not in current:
                current[lid]=str(typ.get('name') or lid)
    ordered_types=[(lid,name,False) for lid,name in current.items() if lid != 'other']
    if 'other' in current:
        ordered_types.append(('other',current['other'],False))
    if not current:
        ordered_types=[(lid,lid.title(),False) for lid in _BUILTIN]
    liquid_headers=[f'{name}\n({unit_label if not mixed else "mL"})' for _,name,_ in ordered_types]
    # Resolve one effective color per (profile, stable ID), including old IDs
    # that occur only in that profile's historical records.
    export_types = []
    for p in profiles:
        defs = list(p.get('liquid_definitions') or p.get('custom_liquid_types') or [])
        colors = p.get('liquid_colors') or {}
        for position, typ in enumerate(defs, 1):
            ident = str(typ.get('id') or '')
            raw = colors.get(ident) or typ.get('color_override') or typ.get('color')
            color = (str(raw).upper() if isinstance(raw,str) and
                     __import__('re').fullmatch(r'#[0-9A-Fa-f]{6}', raw)
                     else default_liquid_color(ident, str(typ.get('name') or ident)))
            export_types.append((p, position, typ, color))
    styles_xml,fallback_header_style,color_styles,left_date_style = _styles_with_colored_liquid_cells(
        [color for _, _, _, color in export_types])
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
                       (3,value,(9 if second else left_date_style) if row==4 else (8 if row==7 else 0),None)]
        rows[8]=[(2,count_label,0,None),(3,count_value,8,None)]
        return rows

    logrows=summary('Home Assistant jwDaily Hydration log - Hydration log','Drink log rows',len(records))
    heads=['Date+time','Profile','Age','Gender',f'Target\n({unit_label})','Liquid name',f'Volume\n({unit_label})','Cup used']
    if mixed:heads+=['Profile unit','Volume (profile unit)']
    hstyles=[10,11,11,11,11,23,24,24]+([11,24] if mixed else [])
    logrows[11]=[(col,h,sty,None) for col,(h,sty) in enumerate(zip(heads,hstyles),2)]
    for rownum,r in enumerate(records,12):
        _,stamp,name,age,gender,target,liquid,volume,_,_,cup_name,cup_default,button_label=r
        rowunit=_unit(r[0]);cup_used=(f'{cup_name} ({_volume(cup_default,rowunit if not mixed else "mL"):g} {_unit_label(rowunit if not mixed else "mL")})' if cup_name and isinstance(cup_default,(int,float)) else cup_name)
        sty=[25,26,27,27,27,26,28,26]+([26,28] if mixed else [])
        if rownum==len(records)+11:
            sty=[29,30,31,31,31,30,32,30]+([30,32] if mixed else [])
        vals=[stamp,name,age,gender,_volume(target,export_unit),liquid,_volume(volume,export_unit),cup_used]
        if mixed:vals+=[_unit_label(rowunit),_volume(volume,rowunit)]
        logrows[rownum]=[(col,value,sty[col-2],None) for col,value in enumerate(vals,2)]
    if not records:
        logrows[12]=[]

    drows=summary('Home Assistant jwDaily Hydration Log  - Daily totals','Daily total rows',len(days),second=True)
    dheads=['Date','Profile','Age','Gender','Full day',f'Target\n({unit_label})','Drink\ncount',f'Volume\n({unit_label})','%']+(['Profile unit','Volume (profile unit)'] if mixed else [])+liquid_headers
    dhstyles=[10,11,11,11,12,13,13,13,14]+([11,13] if mixed else [])+[fallback_header_style if legacy else 6 for _,_,legacy in ordered_types]
    drows[11]=[(col,h,sty,None) for col,(h,sty) in enumerate(zip(dheads,dhstyles),2)]
    for rnum,row in enumerate(days,12):
        values=[_serial(date.fromisoformat(row['day'])),row['cfg']['name'],row['cfg'].get('age'),
                row['cfg'].get('gender'),'Yes' if row['day']<today else 'No',
                _volume(row['target'],export_unit),row['count'],_volume(row['consumed'],export_unit),
                round(row['consumed']/row['target']*100,12) if row['target']>0 else 0]
        if mixed:values += [_unit_label(_unit(row['p'])),_volume(row['consumed'],_unit(row['p']))]
        values += [_volume(row['types'].get(lid,0),export_unit) for lid,_,_ in ordered_types]
        styles=[15,16,27,27,17,16,16,16,18]+([16,16] if mixed else [])+[0]*len(ordered_types)
        if rnum==len(days)+11:
            styles=[19,20,27,27,21,20,20,20,22]+([20,20] if mixed else [])+[0]*len(ordered_types)
        drows[rnum]=[(col,value,styles[col-2],f'I{rnum}/G{rnum}*100' if col==10 and row['target']>0 else None)
                     for col,value in enumerate(values,2)]
    if not days:drows[12]=[]

    # All three settings catalogs and profile metadata are separate sheets,
    # matching the supplied six-sheet workbook (not the older combined sheet).
    def settings_meta(title, count_label=None, count_value=None):
        rows={2:[(2, title, 1, None),(3,None,1,None)],
              4:[(2,'Export date',2,None),(3,_serial(now),left_date_style,None)],
              5:[(2,'Integration version',0,None),(3,VERSION,0,None)],
              6:[(2,'Number of profiles',0,None),(3,len(profiles),3,None)]}
        if count_label is not None:
            rows[7]=[(2,count_label,2,None),(3,count_value,3,None)]
        return rows

    def header(rows, row_number, names):
        rows[row_number]=[(i,h,6,None) for i,h in enumerate(names,2)]

    # Settings - Liquid Types: B9:M9, one row per profile and type.
    typesrows=settings_meta('Home Assistant jwDaily Hydration Log  - Settings - Defined liquid types',
                            'Nr of liquid types',sum(len(p.get('liquid_definitions') or []) for p in profiles))
    header(typesrows,9,['Profile','Liquid ID','Name','MDI Icon','Icon graphic','SVG Image',
                        'Custom','Liquid order','Visible in picker','Color','Status','Nr of times used'])
    icon_images=[]
    used=collections.Counter((str(p.get('config',{}).get('name','')),str(rec.get('liquid_type_id','')))
          for p in profiles for rec in p.get('records',[]) if rec.get('kind')=='drink')
    liquid_row=9
    for p,pos,typ,color in export_types:
        liquid_row+=1
        ident=str(typ.get('id') or '')
        p_name=str(p.get('config',{}).get('name',''))
        svg=typ.get('icon_svg') or ''
        # An actual embedded icon is rendered in F; no error-prone IMAGE formula.
        vals=[p_name,ident,typ.get('name',ident),typ.get('icon_mdi',''),
              InCellImage(len(icon_images)+1),'Yes' if svg else '',bool(typ.get('custom',False)),pos,
              not bool(typ.get('hidden',False)),color,
              'Hidden' if typ.get('hidden') else 'Active',used[(p_name,ident)]]
        typesrows[liquid_row]=[(col,val,color_styles.get(color.upper(),11) if col==11 else 11,None)
                               for col,val in enumerate(vals,2)]
        icon_images.append(png_icon(typ.get('icon_mdi',''),typ.get('icon_color') or color))
    if liquid_row==9:typesrows[10]=[]

    # Settings - Cup types: B9:J9. Shared definitions are not repeated per
    # profile; profile-specific definitions (if any) retain their owner.
    unique_cups=[]
    seen=set()
    for p in profiles:
        for pos,cup in enumerate(p.get('cup_types') or [],1):
            ident=str(cup.get('id',''))
            if ident in seen:continue
            seen.add(ident)
            unique_cups.append((p,pos,cup))
    cupsrows=settings_meta('Home Assistant jwDaily Hydration Log  - Settings - Cup types',
                           'Nr of liquid types',len(export_types))
    header(cupsrows,9,['Profile','Cup Type ID','Name','Default volume\n(mL)',
                       'MDI icon','Icon graphic','SVG Image','Order','Visible'])
    for rownum,(p,pos,cup) in enumerate(unique_cups,10):
        vals=['All profiles' if len(profiles)>0 else p['config']['name'],
              cup.get('id',''),cup.get('name',''),cup.get('default_volume_ml'),
              cup.get('icon_mdi',''),InCellImage(len(icon_images)+1),
               'Yes' if cup.get('icon_svg') else '',
              pos,'No' if cup.get('hidden',False) else 'Yes']
        cupsrows[rownum]=[(col,val,11,None) for col,val in enumerate(vals,2)]
        icon_images.append(png_icon(cup.get('icon_mdi') or 'mdi:cup',
                                    cup.get('icon_color') or '#172A35'))
    if not unique_cups:cupsrows[10]=[]

    # Settings - Quick buttons: B9:O9, native icon in J; per-profile order and
    # effective label are exported exactly as used by the cards.
    quick_rows=settings_meta('Home Assistant jwDaily Hydration Log  - Settings - Quick buttons',
                             'Nr of liquid types',len(export_types))
    header(quick_rows,9,['Profile','Button ID','Effective button label','Label mode',
                         'Default volume\n(mL)','Visible','Custom label','MDI icon',
                         'Icon graphic','Order','Liquid ID','Liquid name','Cup ID','Cup name'])
    rownum=9
    for p in profiles:
        cups={c.get('id'):c for c in p.get('cup_types') or []}
        liquid_defs={l.get('id'):l for l in p.get('liquid_definitions') or []}
        liquids={lid:l.get('name',lid) for lid,l in liquid_defs.items()}
        for pos,q in enumerate(p.get('quick_buttons') or [],1):
            rownum+=1
            cid=q.get('cup_type_id','');lid=q.get('liquid_type_id','')
            cup_name=cups.get(cid,{}).get('name',cid)
            liquid_name=liquids.get(lid,lid)
            label=q.get('label') or q.get('custom_label') or f'{liquid_name} ({cup_name})'
            source=liquid_defs.get(lid,{})
            icon_mdi=(q.get('icon_mdi') or source.get('icon_mdi') or
                      cups.get(cid,{}).get('icon_mdi') or 'mdi:cup')
            icon_color=(q.get('icon_color') or source.get('icon_color') or '#172A35')
            vals=[p['config'].get('name',''),q.get('id',''),label,
                  q.get('label_mode','automatic'),cups.get(cid,{}).get('default_volume_ml'),
                  'No' if q.get('hidden') else 'Yes',q.get('custom_label',''),
                  icon_mdi,InCellImage(len(icon_images)+1),pos,lid,liquid_name,cid,cup_name]
            quick_rows[rownum]=[(col,val,11,None) for col,val in enumerate(vals,2)]
            icon_images.append(png_icon(icon_mdi,icon_color))
    if rownum==9:quick_rows[10]=[]
    quick_last_row=max(10,rownum)

    # Settings - Profiles: append profile-scoped Add drink visibility options.
    # These are persisted per HA profile, unlike Lovelace card layout options.
    profrows=settings_meta('Home Assistant jwDaily Hydration Log  - Settings - Profiles')
    header(profrows,8,['Profile','Profile ID','Age','Gender','Unit',
                       'Daily target mL','Target override mL','Quick button count',
                       'Show Quick buttons','Show Liquid types and Cup types'])
    for rownum,p in enumerate(profiles,9):
        cfg=p.get('config') or {}
        vals=[cfg.get('name'),p.get('slug') or p.get('entry_id') or cfg.get('slug') or '',
              cfg.get('age'),cfg.get('gender'),_unit(p),
              p.get('target_ml'),p.get('target_override_ml'),
              len(p.get('quick_buttons') or []),
              'Yes' if cfg.get('show_add_quick_buttons') is not False else 'No',
              'Yes' if cfg.get('show_add_liquid_cup_types') is not False else 'No']
        profrows[rownum]=[(col,val,11,None) for col,val in enumerate(vals,2)]
    if not profiles:profrows[9]=[]
    all_rows=[logrows,drows,typesrows,cupsrows,quick_rows,profrows]
    for sheet_index, sheet_rows in enumerate(all_rows,1):
        _apply_reference_styles(sheet_index,sheet_rows)
    styles_xml=_outline_all_tables(styles_xml,all_rows)
    rich_parts=_in_cell_image_parts(icon_images)
    content=[
      _worksheet(1,logrows,[4,19,16,6,9,9,17,11,25]+([17,20] if mixed else []),
                 f'{"K" if mixed else "I"}{max(12,11+len(records))}',max(12,11+len(records)),True),
      _worksheet(2,drows,[4.285,16,15,7,9,6,10,9,11,6]+([16,21] if mixed else [])
                 +[_liquid_width(name,_unit_label(export_unit if not mixed else 'mL'))
                   for _,name,_ in ordered_types],
                 f'{_col(10+len(ordered_types)+(2 if mixed else 0))}{max(12,11+len(days))}',
                 max(12,11+len(days)),True),
      _worksheet(3,typesrows,[3.21,16,16,17.42,16.21,7.71,12,13,8.21,8.21,9.21,8.29,7.64],
                 f'M{max(10,liquid_row)}',max(10,liquid_row),True),
      _worksheet(4,cupsrows,[3.71,16,16,16.29,12,18.64,7.21,7.71,9.79,10.64],
                 f'J{max(10,9+len(unique_cups))}',max(10,9+len(unique_cups)),True),
      _worksheet(5,quick_rows,[3.71,16,21.5,23,14.64,11.21,10.64,15.64,17.42,11.5,9.79,22,18.07,19,13.43],
                 f'O{quick_last_row}',quick_last_row,True),
      _worksheet(6,profrows,[3.71,16,16,8,11.14,8.43,17.5,20.5,21.14,24,31],
                 f'K{max(9,8+len(profiles))}',max(9,8+len(profiles)),True),
    ]
    # Standard OOXML container. In-cell images are native rich-value metadata
    # (the same representation as in the user's six-tab reference workbook).
    buffer=BytesIO()
    with ZipFile(buffer,'w',ZIP_DEFLATED,compresslevel=6) as z:
        main='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        relbase='http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        parts=(
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          +('<Default Extension="png" ContentType="image/png"/>' if icon_images else '')
          +'<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          '<Override PartName="/xl/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
          +''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,7))
          +''.join(f'<Override PartName="/xl/tables/table{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>' for i in range(1,7))
        )
        if icon_images:
            parts+=(
              '<Override PartName="/xl/metadata.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheetMetadata+xml"/>'
              '<Override PartName="/xl/richData/richValueRel.xml" ContentType="application/vnd.ms-excel.richvaluerel+xml"/>'
              '<Override PartName="/xl/richData/rdrichvalue.xml" ContentType="application/vnd.ms-excel.rdrichvalue+xml"/>'
              '<Override PartName="/xl/richData/rdrichvaluestructure.xml" ContentType="application/vnd.ms-excel.rdrichvaluestructure+xml"/>'
              '<Override PartName="/xl/richData/rdRichValueTypes.xml" ContentType="application/vnd.ms-excel.rdrichvaluetypes+xml"/>'
            )
        z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+parts+'</Types>')
        z.writestr('_rels/.rels',
          '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
          f'<Relationship Id="rId1" Type="{relbase}officeDocument" Target="xl/workbook.xml"/>'
          '</Relationships>')
        z.writestr('xl/workbook.xml',
          '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          f'<workbook xmlns="{main}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<bookViews><workbookView activeTab="0"/></bookViews><sheets>'
          +''.join(f'<sheet name="{_xml(name)}" sheetId="{i}" r:id="rId{i}"/>' for i,name in enumerate(SHEETS,1))
          +'</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
        relation=(
          '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
          +''.join(f'<Relationship Id="rId{i}" Type="{relbase}worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,7))
          +f'<Relationship Id="rId7" Type="{relbase}styles" Target="styles.xml"/>'
          +f'<Relationship Id="rId8" Type="{relbase}theme" Target="theme/theme1.xml"/>'
        )
        if icon_images:
            relation+=(
              '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sheetMetadata" Target="metadata.xml"/>'
              '<Relationship Id="rId10" Type="http://schemas.microsoft.com/office/2022/10/relationships/richValueRel" Target="richData/richValueRel.xml"/>'
              '<Relationship Id="rId11" Type="http://schemas.microsoft.com/office/2017/06/relationships/rdRichValue" Target="richData/rdrichvalue.xml"/>'
              '<Relationship Id="rId12" Type="http://schemas.microsoft.com/office/2017/06/relationships/rdRichValueStructure" Target="richData/rdrichvaluestructure.xml"/>'
              '<Relationship Id="rId13" Type="http://schemas.microsoft.com/office/2017/06/relationships/rdRichValueTypes" Target="richData/rdRichValueTypes.xml"/>'
            )
        z.writestr('xl/_rels/workbook.xml.rels',
          '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'+relation+'</Relationships>')
        z.writestr('xl/styles.xml',styles_xml)
        z.writestr('xl/theme/theme1.xml',THEME)
        for path,contents in rich_parts.items():
            z.writestr(path,contents)
        for i,xml in enumerate(content,1):
            z.writestr(f'xl/worksheets/sheet{i}.xml',xml)
            z.writestr(f'xl/worksheets/_rels/sheet{i}.xml.rels',
              '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              f'<Relationship Id="rId1" Type="{relbase}table" Target="../tables/table{i}.xml"/>'
              '</Relationships>')
            if i<=2:
                bottom=max(12,11+(len(records) if i==1 else len(days)))
                z.writestr(f'xl/tables/table{i}.xml',
                    _table(i,bottom,liquid_headers if i==2 else None,export_unit,mixed))
            else:
                header_row=8 if i==6 else 9
                headers=[cell[1] for cell in sorted(({
                    3:typesrows,4:cupsrows,5:quick_rows,6:profrows}[i])[header_row],
                    key=lambda x:x[0])]
                bottom={3:max(10,liquid_row),4:max(10,9+len(unique_cups)),
                        5:quick_last_row,6:max(9,8+len(profiles))}[i]
                z.writestr(f'xl/tables/table{i}.xml',
                    _table(i,bottom,settings_headers=headers))
    return buffer.getvalue()