"""Create a standards-compliant Excel .xlsx with only the Python standard library.

All data stays in memory and is returned only to an authenticated WebSocket caller.
No public /local URL, temporary exported file or extra pip dependency is needed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
import math
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile
from zoneinfo import ZoneInfo

SHEETS = ["Profiles", "Drink Moments", "Daily Totals", "Source Readings", "Adjustments", "Export Info", "Daily Breakdown", "Liquid Types"]
VERSION = "1.1.0-beta.3"


def _xml(value: object) -> str:
    return escape(str(value), {'"': '&quot;', "'": '&apos;'})


def _column(number: int) -> str:
    label = ""
    while number:
        number, digit = divmod(number - 1, 26)
        label = chr(65 + digit) + label
    return label


def _timestamp(value: str | None, tz: ZoneInfo) -> float | str:
    if not value:
        return ""
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        date = date.astimezone(tz).replace(tzinfo=None)
        return (date - datetime(1899, 12, 30)).total_seconds() / 86400
    except (TypeError, ValueError, OverflowError):
        return value


def _cell(row: int, col: int, value: object, header: bool = False, datetime_value: bool = False, date_value: bool = False) -> str:
    position = f"{_column(col)}{row}"
    style = 1 if header else (4 if date_value and isinstance(value,(int,float)) else (2 if datetime_value and isinstance(value, (int, float)) else (3 if row % 2 == 0 else 0)))
    if value is None:
        return f'<c r="{position}" s="{style}"/>'
    if isinstance(value, bool):
        return f'<c r="{position}" s="{style}" t="b"><v>{int(value)}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        return f'<c r="{position}" s="{style}"><v>{value}</v></c>'
    # Excel formula injection protection: all external text is stored as inline text.
    # Excel does not evaluate inline strings as formulas; prefix for CSV re-export safety.
    string = str(value)
    if string.startswith(("=", "+", "-", "@", "\t", "\r")):
        string = "'" + string
    return f'<c r="{position}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{_xml(string)}</t></is></c>'


def _worksheet(rows: list[list[object]], datetime_cols: set[int] | None = None, date_cols: set[int] | None = None) -> bytes:
    if not rows:
        rows = [["No data"]]
    datetime_cols = datetime_cols or set()
    date_cols = date_cols or set()
    cols = max(len(row) for row in rows)
    last = f"{_column(cols)}{len(rows)}"
    widths = []
    for i in range(cols):
        estimate = max((len(str(r[i])) if i < len(r) and r[i] is not None else 0) for r in rows[:150])
        widths.append(min(48, max(11, estimate + 2)))
    xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
           f'<dimension ref="A1:{last}"/>',
           '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>',
           '<sheetFormatPr defaultRowHeight="17"/>',
           '<cols>']
    xml += [f'<col min="{i}" max="{i}" width="{width}" customWidth="1"/>' for i, width in enumerate(widths, 1)]
    xml.append('</cols><sheetData>')
    for row_index, values in enumerate(rows, 1):
        xml.append(f'<row r="{row_index}">')
        for col_index, value in enumerate(values, 1):
            xml.append(_cell(row_index, col_index, value, row_index == 1, col_index in datetime_cols, col_index in date_cols))
        xml.append('</row>')
    xml.append('</sheetData>')
    if cols > 0:
        xml.append(f'<autoFilter ref="A1:{last}"/>')
    xml.append('<pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.3" footer="0.3"/></worksheet>')
    return ''.join(xml).encode('utf-8')


STYLES = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="2"><numFmt numFmtId="164" formatCode="dd-mm-yyyy hh:mm:ss"/><numFmt numFmtId="165" formatCode="dd-mm-yyyy"/></numFmts>
<fonts count="2"><font><sz val="11"/><name val="Aptos"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Aptos"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF144A73"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="5"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFill="1" applyFont="1"/><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''


def _date_serial(day: str) -> int:
    """Excel date number; visible format set to DD-MM-YYYY."""
    parsed = datetime.strptime(day, '%Y-%m-%d')
    return (parsed - datetime(1899, 12, 30)).days


def export_xlsx(profiles: list[dict], timezone_name: str = "Europe/Amsterdam") -> bytes:
    """Export full retained records for all selected profiles; never truncate rows."""
    try:
        tz = ZoneInfo(timezone_name)
    except (KeyError, ValueError):
        tz = ZoneInfo('UTC')

    profile_rows = [["Profile ID", "Name", "Slug", "Age", "Gender", "Pregnancy", "Lactation",
                     "Source sensor", "Source mode", "Display unit",
                     "Target mL", "Today consumed mL", "Today manual mL", "Today remaining mL", "Progress %"]]
    drink_rows = [["Record ID", "Timestamp (local)", "Profile", "Volume mL", "Entered volume", "Entered unit",
                   "Liquid type", "Liquid name", "Origin", "Details"]]
    day_rows = [["Date", "Profile", "Manual mL", "Source mL", "Consumed mL", "Target mL", "Drink count",
                 "Closed at (local)", "Record type"]]
    source_rows = [["Record ID", "Timestamp (local)", "Profile", "Sensor", "Raw value", "Raw unit",
                    "Value mL", "Change mL", "Consumed after mL"]]
    correction_rows = [["Record ID", "Timestamp (local)", "Profile", "Action", "Value mL", "Before mL",
                        "After mL", "Origin", "Details"]]
    breakdown_rows = [["Date", "Profile", "Water mL", "Coffee mL", "Tea mL", "Milk mL", "Soup mL", "Wine mL", "Other mL", "Unknown legacy mL", "Custom types mL", "Total mL", "Drink count"]]
    type_rows = [["Profile", "Liquid ID", "Name", "MDI Icon", "SVG Image", "Default volume mL"]]
    for p in profiles:
        cfg = p["config"]
        catalog = {x["id"]:x for x in p.get("custom_liquid_types", [])}
        for typ in catalog.values():
            type_rows.append([cfg["name"], typ["id"], typ["name"], typ.get("icon_mdi", ""),
                              typ.get("icon_svg", ""), typ.get("default_volume_ml")])
        profile_rows.append([p["entry_id"], cfg["name"], p["slug"], cfg["age"], cfg["gender"],
                             cfg["pregnancy"], cfg["lactation"],
                             cfg["source_sensor"], cfg["source_mode"], cfg["unit"], p["target_ml"],
                             p["consumed_ml"], p["manual_consumed_ml"], max(0, p["target_ml"] - p["consumed_ml"]),
                             round(p["consumed_ml"] / max(1,p["target_ml"]) * 100, 2)])
        for record in p["records"]:
            moment = _timestamp(record.get("timestamp"), tz)
            if record["kind"] == "drink":
                drink_rows.append([record["id"], moment, cfg["name"], record.get("volume_ml", 0),
                                   record.get("input_volume", 0), record.get("input_unit", "mL"),
                                   record.get("liquid_type", "unknown"),
                                   catalog.get(record.get("liquid_type", ""), {}).get("name",
                                       record.get("liquid_type", "unknown")), record.get("origin", ""),
                                   json.dumps(record.get("details", {}), ensure_ascii=False)])
            if record["kind"] in ("reset", "set_consumed", "set_target"):
                correction_rows.append([record["id"], moment, cfg["name"], record["kind"],
                                        record.get("volume_ml", 0), record.get("before_ml", 0),
                                        record.get("after_ml", 0), record.get("origin", ""),
                                        json.dumps(record.get("details", {}), ensure_ascii=False)])
        daily_types = {}
        for record in p["records"]:
            if record["kind"] != "drink":
                continue
            date = record.get("timestamp", "")[:10]
            typ = record.get("liquid_type", "unknown")
            if typ not in ("water", "coffee", "tea", "milk", "soup", "wine", "other"):
                typ = "custom" if typ in catalog else "unknown"
            key = (date, typ)
            daily_types[key] = daily_types.get(key, 0.0) + float(record.get("volume_ml", 0))
        for day in sorted({date for date, typ in daily_types}):
            row = [round(daily_types.get((day, typ), 0.0), 3)
                   for typ in  ("water", "coffee", "tea", "milk", "soup", "wine", "other", "unknown", "custom")]
            breakdown_rows.append([_date_serial(day), cfg["name"], *row,
                                   round(sum(row), 3), sum(1 for r in p["records"]
                                     if r["kind"] == "drink" and r["timestamp"][:10] == day)])
        for record in p["source_readings"]:
            source_rows.append([record["id"], _timestamp(record["timestamp"], tz), cfg["name"], record["sensor"],
                                record["raw_value"], record["unit"], record["value_ml"],
                                record["change_ml"], record["consumed_after_ml"]])
        for day, snapshot in sorted(p["daily_archive"].items()):
            day_rows.append([_date_serial(day), cfg["name"], snapshot["manual_ml"], snapshot["source_ml"], snapshot["consumed_ml"],
                             snapshot["target_ml"], snapshot["drink_count"],
                             _timestamp(snapshot.get("closed_at"), tz), "Closed"])
        day = p["date"]
        day_rows.append([_date_serial(day), cfg["name"], p["manual_consumed_ml"],
                         p.get("source_contribution_ml", 0), p["consumed_ml"], p["target_ml"],
                         sum(1 for r in p["records"] if r["kind"] == "drink" and r["timestamp"][:10] == p["date"]),
                         "", "Current"])
    now = datetime.now(tz).isoformat(timespec="seconds")
    info_rows = [["Field", "Value"], ["Integration", "jwDaily Hydration Log"], ["Version", VERSION],
                 ["Generated (local)", now], ["Timezone", str(tz)], ["Number of profiles", len(profiles)],
                 ["Drink event rows", len(drink_rows)-1], ["Daily total rows", len(day_rows)-1],
                 ["Source reading rows", len(source_rows)-1], ["Correction rows", len(correction_rows)-1],
                 ["Data scope", "Current saved drink records (edits replace; deletions are permanent) and source history"],
                 ["Legacy data", "Individual drink moments before installation were not stored by the original integration"],
                 ["Timestamp format", "Excel numeric local datetime; HH:MM:SS, Europe/Amsterdam unless configured otherwise"],
                 ["Data integrity", "Each drink is stored before UI refresh; no event limit or export truncation"]]
    contents = [profile_rows, drink_rows, day_rows, source_rows, correction_rows, info_rows, breakdown_rows, type_rows]
    datetime_columns = [set(), {2}, {8}, {2}, {2}, set(), set(), set()]
    date_columns = [set(), set(), {1}, set(), set(), set(), {1}, set()]
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(SHEETS) + 1)) + '</Types>')
        archive.writestr('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr('xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><bookViews><workbookView activeTab="0"/></bookViews><sheets>' + ''.join(f'<sheet name="{_xml(name)}" sheetId="{i}" r:id="rId{i}"/>' for i, name in enumerate(SHEETS, 1)) + '</sheets></workbook>')
        archive.writestr('xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(SHEETS) + 1)) + '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        archive.writestr('xl/styles.xml', STYLES)
        for i, rows in enumerate(contents, 1):
            archive.writestr(f'xl/worksheets/sheet{i}.xml', _worksheet(rows, datetime_columns[i-1], date_columns[i-1]))
    return buffer.getvalue()
