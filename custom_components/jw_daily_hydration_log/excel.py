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

VERSION = '1.1.0-beta.46'
SHEETS = ['Hydration log', 'Daily intake', 'Settings - Liquid Types', 'Settings - Cup types', 'Settings - Quick buttons', 'Settings - Profiles']

# Compressed styles and Office theme (visual metadata only, no user profile data)
# extracted from the supplied Excel reference. Values contain no workbook cells.
_STYLES_Z = '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'
_THEME_Z = 'eNrtWluLGzcUfi/0P4h5d+Zijy8hTvC1abKbLLublDzKY9mjWDMaJHl3TQmU9KkvhUJb+lLoWx9KaaCBhr70xwQSevkR1WjG45Gt6Sbtphe6a1iPNN939Enn6Oh47Gs3ziICThDjmMZdy73iWADFAZ3ieN617h2Pa20LcAHjKSQ0Rl1rhbh14/rbb12DV0WIIgQkP+ZXYdcKhUiu2jYPZDfkV2iCYnlvRlkEhWyyuT1l8FTajYjtOU7TjiCOLRDDSJq9O5vhAIHj1KR1fW18ROS/WPC0IyDsKFAjlhkKO1246Rtf8QFh4ASSriXHmdLTY3QmLEAgF/JG13LUn2Vfv2YXJCIquCXeWP3lvJwwXXiKx+aTguiMvHbDLex7mf1d3Kidvgp7CgCDQM7U3cG6ftNpezm2BMouDbY7Lbeu40v267v2O82+19Dw9Q2+sTvHcWc09DV8Y4P3d/A9x+t36hre3+CbO/jGqNfyRhpegUKC48Uuutlqt5s5uoDMKLlphHeaTac1zOEblF2Krowfi6pYi+BDysYSoJwLBY6BWCVoBgOJ6yWCcjDEPCFwZYEExpTLbsdzXRl4DccrXmrF4VUES+ysK+A7XakewAOGE9G1bkmrVgny4tmz54+fPn/8w/MPP3z++Duwh+ehMPBuwnhe5v369Se/ffkB+OX7r3799DMznpfxL7/96OWPP/2ReaHJ+vzJy6dPXnzx8c/ffGqA9xiclOHHOEIc3EGn4JBGcoKGAdCEvR7jOIRYY8BQIg3AkQg14J0VJCZcH+lLeJ/JTGECvrN8qGk9CtlSYAPwdhhpwH1KSZ8y43Rup2OVp7OM5+bB2bKMO4TwxDT2YMvBo2UiQx6bTA5CpMk8INLbcI5iJEB6jy4QMtAeYKyt6z4OGOV0JsADDPoQG5fkGE+EmXQTR9IvK2h2tbY2+/dBnxKT+SE60ZFyW0BiMomItozvwKWAkVExjEgZuQdFaBJ5tGKBtuBcSE/PEaFgNEWcmzh32UqTexvKlGV0+z5ZRTqSCbwwIfcgpWXkkC4GIYwSo2Ych2Xsu3whQxSCAyqMIqi+Q9K29AOMK919HyPxetv6nsxA5gBJ7yyZaUsgqu/HFZlBFBvzUqRl1x7DxujoL+daaO8hROApnCIE7r1rwtOEmkXfCmVWuYlMa3ML6rGatmPEZZmU1jUGx2KuhewRmtMKPfurrcSzgnEEWZXlOws9ZEYTho2p9C4JFloqxSzdtGYRd3kEX8nqQQi1sErbPKnYY/Hr7jHJefgnOOi1OTKxv/LaHEOCzAFzDDHYQ2bK0kxJt5OiLY28mb5pN26wt+qdCMfnFT93IGNp8fxP1D5vrOq5+HqnKq9sVzlVuP9gbTOEy/gAyePksrS5LG3+j6VN1V6+LGguC5rLguZvK2g2NYxdftSjrESVz31mmJAjsSJoj6vqh8u9Px3LTtVQpOIxUxLKy3w4DTdnUF0DRsV7WIRHIUzkMK4aYc5z03MOEspl6WRV2lb11zLap9P8KZ67frIpCVBs+h2/6JfVmsh6m63NY9DCvGrNeVmAr4y+uojSYLqIukFEq/5qIlznolR0DCra7h+psEtekYcTgOlDcb+RKZLhJkN6mvop46+9e+GerlpMfdqeYXqdxoV5WhNRCjddRCkMQ3l4bHdfsK87HbOrPaOMVvtN+NrezQ0k1lvgNNXUSu0EMOlaM/nRSV5GiTTI01QFyTzuWoHIV/rPpJaEcTGEPMxg6la2ABEWiAGCIxnsZT+QuCSuIzfNv1Wclzrh3ybO3vYyms1QICp6Nk15LzNivPsXwWmDLqXoo3B6CiZkyQ6hXCi/5abenWIuCldPMStF92YVt/JVvhe1L4A2exSSJIT5kVLO5hlcXRdySvNQSrdnZZuWcDIfX8Sxez5pK2tWnCCtyjT25k75kqq6WZVvTHad9jnHxF8/EUrS2mZpdbO0qsPjAiuC0nDN+jmHxEUfB9tRa5cKS9Xa+W6bTh7KyB/KcnVJsh4Sy5aSnBwwpX1Cp6v8kvBsl2RzWqcBEh+iGcDTM5kyTYuTf3lcJLHDbID08CqIzvnEHL9JPAXZPZ9cMNY1e0FWZbnJgDgrRs7wmcOKrJGvlG1aRfnZj8HB+qvdLJ2q3nWKPhNgyXDXet/xe42B5w9qTtsf1Rr1hlNr+716ref7dXfku86w7z2S8kQYuX7mwDGMMFnlv39Q/Tu/gYjWH1iuBDSyqfo0YSuy+g2E61X/BkKuipTljdyG1/MGtcHQbdYa3rBZa7fqvdrAaw69nszkzXHvkQVOFNjtD4fjse/VmgOJazg9v9br1we1ZnvU98buqDF0JDh3xJlYv69jVOm6/julQGAc'
STYLES = zlib.decompress(base64.b64decode(_STYLES_Z))
THEME = zlib.decompress(base64.b64decode(_THEME_Z))

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


def _cols(widths: list[float | tuple[float,bool]]) -> str:
    """Fixed widths except Daily intake liquid columns flagged as best-fit."""
    def tag(i, value):
        width, auto = value if isinstance(value, tuple) else (value, False)
        return (f'<col min="{i}" max="{i}" width="{width:.4f}"'
                + (' bestFit="1"' if auto else '') + ' customWidth="1"/>')
    return '<cols>' + ''.join(tag(i,w) for i,w in enumerate(widths,1)) + '</cols>'

def _liquid_width(name: str, unit_label: str) -> tuple[float, bool]:
    # Excel has no stored "autofit" operation. Calculate a fitted width and
    # mark bestFit=1 for ONLY the liquid column, never the fixed metadata columns.
    longest=max((len(part) for part in str(name).splitlines()),default=0)
    return (float(max(8,min(30,max(longest,len(unit_label)+2)+2))), True)



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
              _cols(widths),'<sheetData>']
    for row in sorted(rows):
        if row >= header_row:
            if row == header_row:
                height = 38 if index == 1 else (44 if index == 2 else 43.75)
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


def _table(table_number: int, bottom: int, liquid_headers: list[str] | None = None, unit: str = 'mL', mixed: bool = False) -> bytes:
    """Structured Excel tables, including table filters and header layout."""
    if table_number==1:
        label='tblHydrationLog'; right='K' if mixed else 'I'
        headers=['Date+time','Profile','Age','Gender',f'Target_x000a_({_unit_label(unit)})',
                 'Liquid name',f'Volume_x000a_({_unit_label(unit)})','Cup used']
        if mixed:headers+=['Profile unit','Volume (profile unit)']
        attrs='headerRowDxfId="15" dataDxfId="26" headerRowBorderDxfId="24" tableBorderDxfId="25" totalsRowBorderDxfId="23"'
    else:
        label='tblDailyIntake'
        assert liquid_headers is not None
        right=_col(10+len(liquid_headers)+(2 if mixed else 0))
        headers=['Date','Profile','Age','Gender','Full day',f'Target_x000a_({_unit_label(unit)})','Drink_x000a_count',f'Volume_x000a_({_unit_label(unit)})','%']
        if mixed:headers+=['Profile unit','Volume (profile unit)']
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
        parsed = ET.fromstring(original)
        color_fills = parsed.find(ns + 'fills')
        color_xfs = parsed.find(ns + 'cellXfs')
        fill_id, style_id = len(color_fills), len(color_xfs)
        fill = (f'<fill><patternFill patternType="solid"><fgColor rgb="FF{color[1:]}"/>'
                '<bgColor indexed="64"/></patternFill></fill>')
        # Sheet 3's original settings cells are style 0. Reuse its exact format,
        # changing only the fill reference.
        template = ET.tostring(color_xfs[0], encoding='unicode')
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
    """Match the supplied four-sheet reference, retaining ALL drink records.

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
        rows={2:[(2, title, 1, None)],
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
                           'Nr of cup types',len(unique_cups))
    header(cupsrows,9,['Profile','Cup Type ID','Name','Default volume\n(mL)',
                       'MDI icon','Icon graphic','SVG Image','Order','Visible'])
    for rownum,(p,pos,cup) in enumerate(unique_cups,10):
        vals=['All profiles' if len(profiles)>0 else p['config']['name'],
              cup.get('id',''),cup.get('name',''),cup.get('default_volume_ml'),
              cup.get('icon_mdi',''),'', 'Yes' if cup.get('icon_svg') else '',
              pos,'No' if cup.get('hidden',False) else 'Yes']
        cupsrows[rownum]=[(col,val,11,None) for col,val in enumerate(vals,2)]
    if not unique_cups:cupsrows[10]=[]

    # Settings - Quick buttons: B9:N9; the saved per-profile order and
    # effective label are exported exactly as used by the cards.
    quick_rows=settings_meta('Home Assistant jwDaily Hydration Log  - Settings - Quick buttons',
                             'Nr of quick buttons',sum(len(p.get('quick_buttons') or []) for p in profiles))
    header(quick_rows,9,['Profile','Button ID','Effective button label','Label mode',
                         'Default volume\n(mL)','Visible','Custom label','MDI icon',
                         'Order','Liquid ID','Liquid name','Cup ID','Cup name'])
    rownum=9
    for p in profiles:
        cups={c.get('id'):c for c in p.get('cup_types') or []}
        liquids={l.get('id'):l.get('name',l.get('id')) for l in p.get('liquid_definitions') or []}
        for pos,q in enumerate(p.get('quick_buttons') or [],1):
            rownum+=1
            cid=q.get('cup_type_id','');lid=q.get('liquid_type_id','')
            cup_name=cups.get(cid,{}).get('name',cid)
            liquid_name=liquids.get(lid,lid)
            label=q.get('label') or q.get('custom_label') or f'{liquid_name} ({cup_name})'
            vals=[p['config'].get('name',''),q.get('id',''),label,
                  q.get('label_mode','automatic'),cups.get(cid,{}).get('default_volume_ml'),
                  'No' if q.get('hidden') else 'Yes',q.get('custom_label',''),
                  q.get('icon_mdi',''),pos,lid,liquid_name,cid,cup_name]
            quick_rows[rownum]=[(col,val,11,None) for col,val in enumerate(vals,2)]
    if rownum==9:quick_rows[10]=[]

    # Settings - Profiles: B8:I8; identities and targets from HA snapshots.
    profrows=settings_meta('Home Assistant jwDaily Hydration Log  - Settings - Profiles')
    header(profrows,8,['Profile','Profile ID','Age','Gender','Unit',
                       'Daily target mL','Target override mL','Quick button count'])
    for rownum,p in enumerate(profiles,9):
        cfg=p.get('config') or {}
        vals=[cfg.get('name'),p.get('slug') or p.get('entry_id') or cfg.get('slug') or '',
              cfg.get('age'),cfg.get('gender'),_unit(p),
              p.get('target_ml'),p.get('target_override_ml'),
              len(p.get('quick_buttons') or [])]
        profrows[rownum]=[(col,val,11,None) for col,val in enumerate(vals,2)]
    if not profiles:profrows[9]=[]
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
                 f'M{max(10,liquid_row)}',max(10,liquid_row)),
      _worksheet(4,cupsrows,[3.71,16,16,16.29,12,18.64,7.21,7.71,9.79,10.64],
                 f'J{max(10,9+len(unique_cups))}',max(10,9+len(unique_cups))),
      _worksheet(5,quick_rows,[3.71,16,21.5,23,14.64,11.21,10.64,15.64,17.42,9.79,22,18.07,19,13.43],
                 f'N{max(10,rownum)}',max(10,rownum)),
      _worksheet(6,profrows,[3.71,16,16,8,11.14,8.43,17.5,20.5,21.14],
                 f'I{max(9,8+len(profiles))}',max(9,8+len(profiles))),
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
          +''.join(f'<Override PartName="/xl/tables/table{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>' for i in range(1,3))
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
            if i<=2:
                z.writestr(f'xl/worksheets/_rels/sheet{i}.xml.rels',
                  '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                  f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                  f'<Relationship Id="rId1" Type="{relbase}table" Target="../tables/table{i}.xml"/>'
                  '</Relationships>')
                z.writestr(f'xl/tables/table{i}.xml',
                    _table(i,max(12,11+(len(records) if i==1 else len(days))),
                           liquid_headers if i==2 else None,export_unit,mixed))
    return buffer.getvalue()
