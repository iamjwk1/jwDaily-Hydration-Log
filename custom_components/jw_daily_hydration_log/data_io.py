"""Strict schema-v2 data transfer and ZIP full-profile restore; no Home Assistant imports.

No import writes anything. All validation/preview is performed before the coordinator
acquires its write lock. Stable IDs, original drink quantities and timestamps survive.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, date
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile
import base64
import hashlib
import json
import math
import re

DATA_FORMAT = 'jwDaily-Hydration-Log-data'
DATA_SCHEMA = 2
FULL_FORMAT = 'jwDaily-Hydration-Log-full-backup'
FULL_SCHEMA = 1
MAX_DATA_BYTES = 12_000_000
MAX_ZIP_BYTES = 14_000_000
MAX_RECORDS = 100_000
MAX_SOURCE = 120_000
RECORD_TYPES = {'drink', 'reset', 'set_target', 'set_consumed'}
FIELDS = ('records', 'source_readings', 'daily_archive', 'consumed_ml',
          'manual_consumed_ml', 'last_reset_date', 'last_source_value',
          'source_baseline')
IDENT = re.compile(r'^[A-Za-z0-9_-]{8,80}$')
LIQUID = re.compile(r'^[A-Za-z0-9_-]{1,80}$')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _pairs(kv):
    result = {}
    for key, value in kv:
        if key in result:
            raise ValueError('Duplicate JSON field: ' + str(key)[:30])
        result[key] = value
    return result


def parse(contents):
    if not isinstance(contents, str) or len(contents.encode('utf-8')) > MAX_DATA_BYTES:
        raise ValueError('Data JSON exceeds the 12 MB limit')
    try:
        return json.loads(contents, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON number')))
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError('Invalid data JSON') from exc


def _number(value, title, *, zero=True):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or value > 1_000_000 or (not zero and value == 0):
        raise ValueError('Invalid ' + title)
    return float(value)


def _iso(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('Invalid timestamp')
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('Invalid timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Timestamp must include an offset')
    if parsed.year < 2000 or parsed.date() > date.today():
        raise ValueError('Historical timestamp outside supported dates')
    return value


def _date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d\d-\d\d', value):
        raise ValueError('Invalid calendar date')
    try:
        day = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('Invalid calendar date') from exc
    if day.year < 2000 or day > date.today():
        raise ValueError('Future calendar dates are not accepted')
    return value


def extract(coordinator):
    return {key: deepcopy(getattr(coordinator, '_source_baseline_ml' if key == 'source_baseline' else
                                 '_last_source_value' if key == 'last_source_value' else key)) for key in FIELDS}


def export_payload(coordinator):
    return {'format': DATA_FORMAT, 'schema': DATA_SCHEMA,
            'source_profile': {'name': coordinator.name, 'slug': coordinator.slug},
            'data': extract(coordinator)}


def validate(raw, *, liquids, cups):
    """Strictly validate an independent data exchange against the selected settings."""
    if not isinstance(raw, dict) or raw.get('format') != DATA_FORMAT or raw.get('schema') != DATA_SCHEMA:
        raise ValueError('Unsupported data file; use a schema-v2 export')
    payload = raw.get('data')
    if not isinstance(payload, dict) or set(payload) != set(FIELDS):
        raise ValueError('Incomplete or unknown data fields')
    if len(canonical(raw)) > MAX_DATA_BYTES:
        raise ValueError('Data file exceeds 12 MB')
    records = payload['records']
    if not isinstance(records, list) or len(records) > MAX_RECORDS:
        raise ValueError('Too many data records')
    valid_liquids, valid_cups = set(liquids), set(cups)
    seen = set()
    clean = deepcopy(payload)
    for item in clean['records']:
        if not isinstance(item, dict) or len(canonical(item)) > 4096:
            raise ValueError('Oversized or invalid record')
        ident = item.get('id')
        if not isinstance(ident, str) or not IDENT.fullmatch(ident) or ident in seen:
            raise ValueError('Missing, invalid or duplicate record ID')
        seen.add(ident)
        kind = item.get('kind')
        if kind not in RECORD_TYPES:
            raise ValueError('Unsupported ledger event: ' + str(kind)[:24])
        _iso(item.get('timestamp'))
        _number(item.get('volume_ml'), 'logged volume')
        if kind == 'drink':
            if item['volume_ml'] <= 0 or item['volume_ml'] > 100_000:
                raise ValueError('Drink volume must be positive')
            liquid = item.get('liquid_type_id') or item.get('liquid_type')
            if not isinstance(liquid, str) or not LIQUID.fullmatch(liquid) or liquid not in valid_liquids:
                raise ValueError('Data import references unknown Liquid ID: ' + str(liquid)[:50])
            if item.get('liquid_type') and item['liquid_type'] != liquid:
                raise ValueError('Contradictory Liquid IDs')
            cup = item.get('cup_type_id')
            if cup is not None and (not isinstance(cup, str) or cup not in valid_cups):
                raise ValueError('Data import references unknown Cup ID')
            item['liquid_type_id'] = liquid
            item.pop('liquid_type', None)
            item.pop('source_legacy_liquid_id', None)
            item['cup_type_id'] = cup  # None is explicitly unknown; never guess based on volume.
            if item.get('cup_default_volume_ml_at_log') is not None:
                _number(item['cup_default_volume_ml_at_log'], 'historical Cup volume', zero=False)
            if item.get('quick_button_id') is not None and not isinstance(item['quick_button_id'], str):
                raise ValueError('Invalid Quick ID')
            historic_label = item.get('quick_button_label_at_log')
            if historic_label is not None and (not isinstance(historic_label, str)
                                                or len(historic_label) > 100
                                                or any(ord(ch) < 32 for ch in historic_label)):
                raise ValueError('Invalid historic Quick button label')
        if item.get('details') is not None and not isinstance(item['details'], dict):
            raise ValueError('Invalid record details')
    daily = clean['daily_archive']
    if not isinstance(daily, dict) or len(daily) > 7000:
        raise ValueError('Invalid daily archive')
    for day, snapshot in daily.items():
        _date(day)
        if not isinstance(snapshot, dict) or len(canonical(snapshot)) > 4096:
            raise ValueError('Invalid daily snapshot')
        for field in ('manual_ml', 'source_ml', 'consumed_ml', 'target_ml'):
            if field in snapshot:
                _number(snapshot[field], 'daily ' + field)
        if 'drink_count' in snapshot and (type(snapshot['drink_count']) is not int or snapshot['drink_count'] < 0):
            raise ValueError('Invalid daily drink count')
    readings = clean['source_readings']
    if not isinstance(readings, list) or len(readings) > MAX_SOURCE:
        raise ValueError('Invalid source readings')
    for reading in readings:
        if not isinstance(reading, dict) or len(canonical(reading)) > 2048:
            raise ValueError('Invalid source reading')
    for field in ('consumed_ml', 'manual_consumed_ml', 'source_baseline'):
        _number(clean[field], field)
    if clean['last_source_value'] is not None:
        _number(clean['last_source_value'], 'last source value')
    _date(clean['last_reset_date'])
    return clean


def import_plan(current, incoming, mode, *, default_target_ml=0):
    if mode not in ('merge', 'update', 'replace'):
        raise ValueError('Unknown import mode')
    old = {r['id']: r for r in current['records'] if r.get('kind') == 'drink'}
    new = {r['id']: r for r in incoming['records'] if r.get('kind') == 'drink'}
    collisions = set(old) & set(new)
    new_ids = set(new) - set(old)
    modified = sum(1 for ident in collisions if old[ident] != new[ident])
    if mode == 'replace':
        result = deepcopy(incoming)
    else:
        result = deepcopy(current)
        if mode == 'merge':
            result['records'].extend(deepcopy(new[x]) for x in new if x in new_ids)
        else:
            result['records'] = [(deepcopy(new[r['id']]) if r.get('kind') == 'drink' and r['id'] in new else r)
                                 for r in result['records']]
            result['records'].extend(deepcopy(new[x]) for x in new if x in new_ids)
        # Keep sensor history, existing daily snapshot targets and non-drink audit events.
        before_by_day, after_by_day = {}, {}
        for row, dest in ((current, before_by_day), (result, after_by_day)):
            for r in row['records']:
                if r.get('kind') == 'drink':
                    key = r['timestamp'][:10]
                    total, count = dest.get(key, (0.0, 0))
                    dest[key] = (round(total + float(r['volume_ml']), 4), count + 1)
        for day in set(before_by_day) | set(after_by_day):
            prev, prev_n = before_by_day.get(day, (0, 0))
            nxt, nxt_n = after_by_day.get(day, (0, 0))
            delta = round(nxt - prev, 4)
            if day == result['last_reset_date']:
                result['manual_consumed_ml'] = round(max(0, float(result['manual_consumed_ml']) + delta), 4)
                result['consumed_ml'] = round(max(0, float(result['consumed_ml']) + delta), 4)
            else:
                snap = result['daily_archive'].setdefault(day, {
                    'manual_ml': 0, 'source_ml': 0, 'consumed_ml': 0,
                    'target_ml': default_target_ml, 'drink_count': 0, 'closed_at': None})
                snap['manual_ml'] = round(max(0, float(snap.get('manual_ml', 0)) + delta), 4)
                snap['consumed_ml'] = round(max(0, float(snap.get('consumed_ml', 0)) + delta), 4)
                snap['drink_count'] = nxt_n
    counts = {'existing_drinks': len(old), 'incoming_drinks': len(new),
              'matching_ids': len(collisions), 'new_ids': len(new_ids),
              'changed_matching_ids': modified,
              'imported': len(new) if mode == 'replace' else len(new_ids) + (modified if mode == 'update' else 0),
              'total_result_drinks': sum(r.get('kind') == 'drink' for r in result['records'])}
    if len({r['id'] for r in result['records']}) != len(result['records']):
        raise ValueError('Data import would create duplicate event IDs')
    return result, counts


def build_full(settings_document, data_document):
    configs = {'settings.json': canonical(settings_document), 'data.json': canonical(data_document)}
    manifest = {'format': FULL_FORMAT, 'schema': FULL_SCHEMA,
                'files': {name: {'size': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
                          for name, content in configs.items()}}
    configs['manifest.json'] = canonical(manifest)
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(configs):
            archive.writestr(path, configs[path])
    return output.getvalue()


def parse_full(contents_b64):
    if not isinstance(contents_b64, str) or len(contents_b64) > MAX_ZIP_BYTES * 2:
        raise ValueError('Full backup too large')
    try:
        raw = base64.b64decode(contents_b64, validate=True)
        if len(raw) > MAX_ZIP_BYTES:
            raise ValueError('Full backup exceeds size limit')
        with ZipFile(BytesIO(raw)) as zipfile:
            if set(zipfile.namelist()) != {'settings.json', 'data.json', 'manifest.json'}:
                raise ValueError('Unexpected full backup entries')
            for info in zipfile.infolist():
                if info.file_size > MAX_DATA_BYTES or info.is_dir():
                    raise ValueError('Invalid full backup member')
            if zipfile.testzip() is not None:
                raise ValueError('Full backup ZIP CRC check failed')
            parts = {name: zipfile.read(name) for name in zipfile.namelist()}
        manifest = parse(parts['manifest.json'].decode('utf-8'))
        if manifest.get('format') != FULL_FORMAT or manifest.get('schema') != FULL_SCHEMA:
            raise ValueError('Unknown full backup format')
        if set(manifest.get('files', {})) != {'settings.json', 'data.json'}:
            raise ValueError('Full backup manifest incomplete')
        for name in ('settings.json', 'data.json'):
            item = manifest['files'][name]
            if item['size'] != len(parts[name]) or item['sha256'] != hashlib.sha256(parts[name]).hexdigest():
                raise ValueError('Full backup checksum mismatch')
        return (parse(parts['settings.json'].decode('utf-8')),
                parse(parts['data.json'].decode('utf-8')), hashlib.sha256(raw).hexdigest())
    except (BadZipFile, UnicodeError, KeyError, TypeError, ValueError, base64.binascii.Error) as exc:
        raise ValueError('Invalid or corrupt full profile backup: ' + str(exc)) from exc
