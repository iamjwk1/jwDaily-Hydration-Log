"""Per-profile editable drink records and durable source sample history."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from .settings_io import extract, digest, validate_payload, settings_preview
from . import data_io
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
import math
import re
import xml.etree.ElementTree as ET
from uuid import uuid4
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util, slugify

from .const import DOMAIN, SIGNAL, LIQUID_TYPES, to_ml, target_ml, safe_amount, default_liquid_color, historical_default_target_ml


def _local_timestamp(hass: HomeAssistant, day: str | None, clock: str | None) -> str:
    """Validate dd-mm-yyyy and 24-hour HH:MM in the HA local timezone."""
    if day is None and clock is None:
        return dt_util.now().isoformat(timespec='microseconds')
    if not day or not clock:
        raise ValueError('Date and time must both be supplied')
    try:
        local_day = datetime.strptime(day, '%d-%m-%Y')
        clock_format = '%H:%M:%S' if len(clock) == 8 else '%H:%M'
        local_clock = datetime.strptime(clock, clock_format)
        if local_day.strftime('%d-%m-%Y') != day or local_clock.strftime(clock_format) != clock:
            raise ValueError('Incorrect date or 24-hour time format')
        tz = ZoneInfo(hass.config.time_zone)
        value = datetime(local_day.year, local_day.month, local_day.day,
                         local_clock.hour, local_clock.minute, local_clock.second, tzinfo=tz)
    except (ValueError, KeyError, AttributeError) as exc:
        raise ValueError('Use DD-MM-YYYY and HH:MM or HH:MM:SS (24-hour local time)') from exc
    # Reject spring-forward wall times that never happened in this timezone.
    if value.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != value.replace(tzinfo=None):
        raise ValueError('This time does not exist because of daylight saving time')
    # The calendar DAY cannot be in the future, but any valid time TODAY is
    # allowed, including a time later than the current HA-local clock.
    if value.date() > dt_util.now().astimezone(tz).date():
        raise ValueError('Drink date cannot be in the future')
    return value.isoformat(timespec='seconds')




# Personal SVG uploads are stored as inert images (never inline DOM), restricted to
# a small set of vector-only elements. This rejects scripts, links and remote assets.
_SVG_ELEMENTS = {'svg', 'g', 'path', 'circle', 'ellipse', 'rect', 'line',
                 'polyline', 'polygon', 'defs', 'linearGradient', 'stop'}
_SVG_ATTRS = {'xmlns', 'viewBox', 'width', 'height', 'd', 'points', 'cx', 'cy',
              'r', 'rx', 'ry', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'fill', 'stroke',
              'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit',
              'fill-rule', 'clip-rule', 'opacity', 'fill-opacity', 'stroke-opacity',
              'transform', 'id', 'offset', 'stop-color', 'stop-opacity',
              'gradientUnits', 'gradientTransform'}
_BUILTIN_LIQUIDS = (
    ('water', 'Water', 'mdi:water'), ('coffee', 'Coffee', 'mdi:coffee'),
    ('tea', 'Tea', 'mdi:tea'), ('milk', 'Milk', 'mdi:cow'),
    ('soup', 'Soup', 'mdi:bowl-mix'), ('wine', 'Wine', 'mdi:glass-wine'),
    ('other', 'Other', 'mdi:glass-water'),
)


def _safe_svg(svg: str) -> str:
    if not isinstance(svg, str) or not (0 < len(svg.encode('utf-8')) <= 16000):
        raise ValueError('SVG must be a nonempty file up to 16 KB')
    if re.search(r'<!DOCTYPE|<!ENTITY|<\?xml-stylesheet', svg, re.I):
        raise ValueError('SVG must not contain declarations or entities')
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise ValueError('Invalid SVG file') from exc
    if root.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError('SVG root needs the standard SVG namespace')
    if len(list(root.iter())) > 400:
        raise ValueError('Too many SVG elements')
    for element in root.iter():
        tag = element.tag.rsplit('}', 1)[-1]
        if tag not in _SVG_ELEMENTS:
            raise ValueError('SVG contains unsupported elements')
        for raw_key, value in element.attrib.items():
            key = raw_key.rsplit('}', 1)[-1]
            if key not in _SVG_ATTRS or raw_key.startswith('{http://www.w3.org/1999/xlink}'):
                raise ValueError('SVG contains unsafe attributes')
            if re.search(r'url\s*\(|javascript:|data:|https?:|@import|expression\s*\(', value, re.I):
                raise ValueError('SVG cannot load external or embedded resources')
        if element.text and element.text.strip():
            raise ValueError('SVG cannot contain text nodes')
    return svg


def _hex_color(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}', value):
        raise ValueError('Color must be a 6-digit hex code such as #3A87B2')
    return value.upper()


def _color_override(value: str | None) -> str | None:
    """Empty text resets; absent WS field is handled by the caller."""
    return _hex_color(value) if value else None


def _default_volume(value):
    if value is None or value == '':
        return None
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError('Default volume must be numeric') from exc
    if not math.isfinite(v) or v <= 0 or v > 100000:
        raise ValueError('Default volume must be between 0 and 100000 mL')
    return round(v, 2)

class HydrationCoordinator:
    """One persisted profile; every user-visible add is a distinct ledger event."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass, self.entry = hass, entry
        self.entry_id = entry.entry_id
        self._store = Store(hass, 1, f'{DOMAIN}.{entry.entry_id}')
        self._lock = asyncio.Lock()
        self._unsub_reset = self._unsub_source = None
        cfg = {**entry.data, **entry.options}
        self.name = cfg.get('name', 'Hydration')
        self.slug = slugify(self.name)
        self.age = int(cfg.get('age', 30))
        self.gender = cfg.get('gender', 'male')
        # These legacy attributes are inert during Release 1 and are not exposed
        # as settings. Historical source data stays available for rollback.
        self.pregnancy = False
        self.lactation = False
        self.source_sensor = None
        self.source_mode = 'delta'
        self.unit = cfg.get('unit', 'mL')
        self.target_override_ml = 0.0
        self._target_v3_initialized = False
        self.consumed_ml = 0.0
        self.manual_consumed_ml = 0.0
        self.last_reset_date = self._today()
        self._last_source_value: float | None = None
        self._source_baseline_ml: float = 0.0
        self.records: list[dict[str, Any]] = []
        self.source_readings: list[dict[str, Any]] = []
        self.daily_archive: dict[str, dict[str, Any]] = {}
        self.custom_liquid_types: list[dict[str, Any]] = []
        # Profile-scoped settings; stable liquid IDs preserve all old drink records.
        self.liquid_overrides: dict[str, dict[str, Any]] = {}
        # Non-destructive additive storage, scoped to this HA config entry.
        # Overrides are keyed by stable IDs, independent of name and order.
        self.liquid_colors: dict[str, str] = {}
        self.hidden_builtin_liquids: list[str] = []
        self.liquid_order: list[str] = []
        # Native v2 profile-scoped Cup and Quick catalogs.
        self.cup_types: list[dict[str, Any]] = []
        self.quick_buttons: list[dict[str, Any]] = []
        self._global_catalog_v3 = None
        self._global_catalog_sha256 = None
        self.data_model_version: int = 2
        self.profile_display_name: str = self.name

    def _now(self) -> datetime:
        return dt_util.now()

    def _today(self) -> str:
        return self._now().date().isoformat()

    def _stamp(self) -> str:
        return self._now().isoformat(timespec='microseconds')

    @property
    def signal(self) -> str:
        return SIGNAL.format(self.entry_id)

    @property
    def target_ml(self) -> int:
        return round(self.target_override_ml) if self.target_override_ml > 0 else 2000

    @property
    def remaining_ml(self) -> float:
        return max(0.0, self.target_ml - self.consumed_ml)

    @property
    def progress_percent(self) -> float:
        return min(100.0, round(100*self.consumed_ml/max(1,self.target_ml),1))

    @property
    def source_contribution_ml(self) -> float:
        if self.source_mode == 'sum':
            return max(0.0,(self._last_source_value or 0.0)-self._source_baseline_ml)
        if self.source_mode == 'absolute':
            return max(0.0,self._last_source_value or 0.0)
        return max(0.0,self.consumed_ml-self.manual_consumed_ml)

    def _entry(self, kind: str, origin: str, before: float, value_ml: float, input_amount: float = 0,
               input_unit: str = 'mL', details: dict | None = None) -> dict[str, Any]:
        return dict(id=uuid4().hex, timestamp=self._stamp(),kind=kind,origin=origin,
                    volume_ml=round(value_ml,4),input_volume=input_amount,input_unit=input_unit,
                    before_ml=round(before,4),after_ml=round(self.consumed_ml,4),
                    manual_after_ml=round(self.manual_consumed_ml,4),details=details or {})

    def _snapshot(self, closed_at: str | None = None) -> dict[str, Any]:
        return dict(manual_ml=round(self.manual_consumed_ml,4),source_ml=round(self.source_contribution_ml,4),
                    consumed_ml=round(self.consumed_ml,4),target_ml=self.target_ml,
                    drink_count=sum(1 for r in self.records if r['kind']=='drink' and
                                    r['timestamp'][:10]==self.last_reset_date), closed_at=closed_at)

    def _reset_without_write(self, today: str) -> None:
        """A snapshot is archived before resetting; never deletes the ledger."""
        if today == self.last_reset_date:
            return
        previous = self.last_reset_date
        self.daily_archive[previous] = self._snapshot(self._stamp())
        before = self.consumed_ml
        self.last_reset_date = today
        self.consumed_ml = self.manual_consumed_ml = 0.0
        if self.source_mode == 'sum':
            self._source_baseline_ml = self._last_source_value or 0.0
        else:
            self._last_source_value = None
            self._source_baseline_ml = 0.0
        self.records.append(self._entry('reset', 'calendar_midnight', before, 0, details={'date':today}))

    def _rolled(self) -> None:
        self._reset_without_write(self._today())

    def _assert_native_ledger(self) -> None:
        """Refuse writes if ANY historic drink is not independently addressable."""
        liquids = set(LIQUID_TYPES) | {x['id'] for x in self.custom_liquid_types}
        cups = {x['id'] for x in self.cup_types}
        ids = set()
        for r in self.records:
            rid = r.get('id')
            if not isinstance(rid, str) or not rid or rid in ids:
                raise ValueError('Native ledger has invalid or duplicate record IDs')
            ids.add(rid)
            if r.get('kind') != 'drink':
                continue
            if r.get('liquid_type_id') not in liquids:
                raise ValueError('Unmigrated/unknown Liquid in record '+rid+'; restore beta.29 and finalize migration')
            if r.get('cup_type_id') not in (None, *cups):
                raise ValueError('Unknown Cup in record '+rid+'; repair before cleanup')
            volume = r.get('volume_ml')
            if type(volume) not in (float,int) or not math.isfinite(volume) or volume <= 0:
                raise ValueError('Invalid historical volume in '+rid)
            if not isinstance(r.get('timestamp'), str) or len(r['timestamp']) < 10:
                raise ValueError('Invalid historical timestamp in '+rid)
        self.data_model_version = 2

    async def _validated_native_store(self, raw: dict) -> dict:
        """One-time isolated pre-beta30 archive and fail-closed native cleanup."""
        if not isinstance(raw, dict) or int(raw.get('data_model_version', 1)) != 2:
            raise ValueError('beta.30 requires finalized data model 2. Reinstall beta.29, export Full Backup and finalize data first.')
        from copy import deepcopy
        original = deepcopy(raw)
        liquid_ids = set(LIQUID_TYPES) | {x['id'] for x in raw.get('custom_liquid_types', [])}
        cups = {c['id'] for c in raw.get('cup_types', [])}
        ids = set()
        for r in raw.get('records', []):
            ident = r.get('id')
            if not isinstance(ident,str) or not ident or ident in ids:
                raise ValueError('Native cleanup blocked: invalid/duplicate record ID')
            ids.add(ident)
            if r.get('kind') != 'drink': continue
            lid = r.get('liquid_type_id')
            if lid not in liquid_ids or (r.get('liquid_type') and r['liquid_type'] != lid):
                raise ValueError('Native cleanup blocked: incomplete/contradictory Liquid reference')
            cup = r.get('cup_type_id')
            if cup is not None and cup not in cups:
                raise ValueError('Native cleanup blocked: orphaned Cup ID')
            vol = r.get('volume_ml')
            if type(vol) not in (int,float) or not math.isfinite(vol) or vol <= 0:
                raise ValueError('Native cleanup blocked: invalid drink volume')
            if not isinstance(r.get('timestamp'),str) or len(r['timestamp']) < 10:
                raise ValueError('Native cleanup blocked: invalid timestamp')
        clean = deepcopy(raw)
        legacy_keys=('volume_buttons','legacy_mappings','legacy_cup_defaults','conversion_state')
        for key in legacy_keys:clean.pop(key,None)
        obsolete = set((raw.get('legacy_mappings') or {}).keys())
        used = {r['liquid_type_id'] for r in raw.get('records', []) if r.get('kind') == 'drink'}
        quick = {q.get('liquid_type_id') for q in raw.get('quick_buttons', [])}
        obsolete -= used | quick
        # Only obsolete custom definitions already mapped away; not user-owned active types.
        clean['custom_liquid_types'] = [dict((k,v) for k,v in typ.items() if k != 'default_volume_ml')
            for typ in raw.get('custom_liquid_types', []) if typ.get('id') not in obsolete]
        clean['liquid_overrides'] = {key:{k:v for k,v in override.items() if k!='default_volume_ml'}
            for key,override in (raw.get('liquid_overrides') or {}).items()}
        clean['liquid_order'] = [x for x in raw.get('liquid_order', []) if x not in obsolete]
        clean['liquid_colors'] = {k:v for k,v in (raw.get('liquid_colors') or {}).items() if k not in obsolete}
        for r in clean.get('records', []):
            if r.get('kind') != 'drink':continue
            for k in ('liquid_type','source_legacy_liquid_id'):r.pop(k,None)
            r.setdefault('cup_type_id',None)
        clean['data_model_version'] = 2
        if clean == raw:
            return clean
        # The separate Store archive is intentionally not deleted automatically.
        archive = Store(self.hass,1,f'{DOMAIN}.{self.entry_id}.pre_beta30')
        archived = await archive.async_load()
        if archived is None:
            import hashlib
            from .settings_io import canonical
            archived = {'format':'jwDaily-pre-beta30-backup','sha256':hashlib.sha256(canonical(original)).hexdigest(),
                        'profile_entry_id':self.entry_id,'payload':original}
            await archive.async_save(archived)
        if archived.get('format') != 'jwDaily-pre-beta30-backup' or archived.get('profile_entry_id') != self.entry_id:
            raise ValueError('Native cleanup blocked: unexpected archive payload')
        from .settings_io import canonical
        import hashlib
        if hashlib.sha256(canonical(archived['payload'])).hexdigest() != archived['sha256']:
            raise ValueError('Native cleanup blocked: invalid original backup checksum')
        if archived['payload'] != original:
            # It may contain a previous authoritative cleanup backup; do not overwrite it.
            if clean == archived['payload']:
                return clean
            # Updating data since the archived snapshot is valid; preserve oldest recoverable backup.
        await self._store.async_save(clean)
        verified = await self._store.async_load()
        if verified != clean:
            raise ValueError('Native cleanup blocked: HA storage readback mismatch')
        return clean

    async def async_initialize(self) -> None:
        saved = await self._store.async_load()
        if saved:
            saved = await self._validated_native_store(saved)
            self.consumed_ml = float(saved.get('consumed_ml',0.0))
            self.manual_consumed_ml = float(saved.get('manual_consumed_ml',0.0))
            self.last_reset_date = saved.get('last_reset_date', self._today())
            self.target_override_ml = float(saved.get('target_override_ml',0.0))
            self._target_v3_initialized = bool(saved.get('profile_target_model_v3',False))
            if not self._target_v3_initialized and self.target_override_ml == 0:
                cfg={**self.entry.data,**self.entry.options}
                old_goal=historical_default_target_ml(
                    self.age,self.gender,
                    bool(cfg.get('pregnancy',False)),bool(cfg.get('lactation',False)))
                # Original HA Store has already been copied into the immutable
                # v3 migration archive before coordinator initialization.
                self.target_override_ml=float(old_goal)
                self._target_v3_initialized=True
                saved['target_override_ml']=self.target_override_ml
                saved['profile_target_model_v3']=True
                await self._store.async_save(saved)
                verified=await self._store.async_load()
                if verified != saved:
                    raise ValueError('Historical target migration readback failed')
            self._last_source_value = saved.get('last_source_value')
            self._source_baseline_ml = float(saved.get('source_baseline',0.0))
            self.records = list(saved.get('records',[]))
            self.source_readings = list(saved.get('source_readings',[]))
            self.daily_archive = dict(saved.get('daily_archive',{}))
            self.custom_liquid_types = list(saved.get('custom_liquid_types', []))
            self.liquid_overrides = dict(saved.get('liquid_overrides') or {})
            # Preserve only valid values, never rewrite historic entries.
            self.liquid_colors = {str(k): _hex_color(v) for k, v in
                                  (saved.get('liquid_colors') or {}).items()
                                  if isinstance(k, str) and isinstance(v, str)
                                  and re.fullmatch(r'#[0-9a-fA-F]{6}', v)}
            self.hidden_builtin_liquids = [ident for ident in (saved.get('hidden_builtin_liquids') or [])
                                           if ident in LIQUID_TYPES]
            self.liquid_order = list(saved.get('liquid_order') or [])
            self.cup_types = list(saved.get('cup_types') or [])
            self.quick_buttons = list(saved.get('quick_buttons') or [])
            self.data_model_version = 2
            self.profile_display_name = saved.get('profile_display_name') or self.name
            self.name = self.profile_display_name
        if self.last_reset_date != self._today():
            self._rolled()
            await self._save()
        self._unsub_reset = async_track_time_change(self.hass,self._scheduled_reset,hour=0,minute=0,second=0)
        if self.source_sensor:
            self._unsub_source = self.hass.bus.async_listen(EVENT_STATE_CHANGED,self._handle_source_change)
        self._dispatch()

    async def async_shutdown(self) -> None:
        for func in (self._unsub_reset,self._unsub_source):
            if func:
                func()
        async with self._lock:
            await self._save()

    @callback
    def _scheduled_reset(self, _now: datetime) -> None:
        self.hass.async_create_task(self.async_maybe_reset())

    async def async_maybe_reset(self) -> None:
        async with self._lock:
            if self.last_reset_date == self._today():
                return
            self._rolled()
            await self._save()
            self._dispatch()

    async def async_add_drink(self, amount: float, unit: str = 'mL', origin: str = 'service',
                              liquid_type: str | None = None, day: str | None = None,
                              clock: str | None = None, cup_type_id: str | None = None,
                              quick_button_id: str | None = None) -> dict:
        amount_ml = safe_amount(amount, unit)
        if not self._valid_liquid_type(liquid_type):
            raise ValueError('Choose a valid liquid type explicitly')
        timestamp = _local_timestamp(self.hass, day, clock)
        if cup_type_id and not self.valid_cup(cup_type_id):
            raise ValueError('Choose a valid cup type')
        if quick_button_id and not self.valid_quick(quick_button_id, liquid_type, cup_type_id):
            raise ValueError('Quick button does not match selected liquid and cup')
        async with self._lock:
            self._rolled()
            if not self._valid_liquid_type(liquid_type):
                raise ValueError('Liquid type was removed before saving the drink')
            before = self.consumed_ml
            is_today = timestamp[:10] == self.last_reset_date
            if is_today:
                self.manual_consumed_ml += amount_ml
                if self.source_mode == 'sum':
                    self.consumed_ml = self.manual_consumed_ml + self.source_contribution_ml
                else:
                    self.consumed_ml += amount_ml
            record = self._entry('drink',origin,before,amount_ml,float(amount),unit)
            record['timestamp'] = timestamp
            record['liquid_type_id'] = liquid_type
            record['cup_default_volume_ml_at_log'] = next((float(c['default_volume_ml']) for c in self.cup_types if c['id'] == cup_type_id), None)
            if cup_type_id:
                record['cup_type_id'] = cup_type_id
            if quick_button_id:
                record['quick_button_id'] = quick_button_id
                # Preserve the button's label as it was at logging time.
                record['quick_button_label_at_log'] = next(
                    q['label'] for q in self.get_quick_buttons() if q['id'] == quick_button_id)
            self.records.append(record)
            if not is_today:
                self._adjust_archive(timestamp[:10], amount_ml)
            await self._save()
            self._dispatch()
            return record

    def _adjust_archive(self, day: str, delta_ml: float) -> None:
        """Correct historical snapshots in place; no separate edit/delete ledger."""
        snapshot = self.daily_archive.get(day)
        if snapshot is None:
            # A backdated day that was not yet in storage. It has no external sensor history.
            snapshot = dict(manual_ml=0.0, source_ml=0.0, consumed_ml=0.0,
                            target_ml=self.target_ml, drink_count=0, closed_at=None)
            self.daily_archive[day] = snapshot
        snapshot['manual_ml'] = round(max(0.0, float(snapshot.get('manual_ml', 0)) + delta_ml), 4)
        snapshot['consumed_ml'] = round(max(0.0, float(snapshot.get('consumed_ml', 0)) + delta_ml), 4)
        snapshot['drink_count'] = sum(1 for r in self.records if r.get('kind') == 'drink'
                                      and r.get('timestamp', '')[:10] == day)

    def _adjust_current(self, delta_ml: float) -> None:
        self.manual_consumed_ml = round(max(0.0, self.manual_consumed_ml + delta_ml), 4)
        if self.source_mode == 'sum':
            self.consumed_ml = self.manual_consumed_ml + self.source_contribution_ml
        else:
            self.consumed_ml = max(0.0, self.consumed_ml + delta_ml)

    async def async_edit_drink(self, record_id: str, amount: float, liquid_type: str,
                               day: str, clock: str, cup_type_id: str | None = None,
                               quick_button_id: str | None = None) -> dict:
        """Replace a drink in place, keeping its stable ID but no old values."""
        if not self._valid_liquid_type(liquid_type):
            raise ValueError('Choose a valid liquid type explicitly')
        amount_ml = safe_amount(amount, 'mL')
        if cup_type_id and not self.valid_cup(cup_type_id):
            raise ValueError('Choose a valid cup type')
        if quick_button_id and not self.valid_quick(quick_button_id, liquid_type, cup_type_id):
            raise ValueError('Quick button does not match the liquid and cup')
        timestamp = _local_timestamp(self.hass, day, clock)
        async with self._lock:
            self._rolled()
            if not self._valid_liquid_type(liquid_type):
                raise ValueError('Liquid type was removed before saving the edit')
            record = next((r for r in self.records if r.get('id') == record_id
                           and r.get('kind') == 'drink'), None)
            if record is None:
                raise ValueError('Drink moment not found')
            previous_day = record['timestamp'][:10]
            previous_ml = float(record['volume_ml'])
            next_day = timestamp[:10]
            # Replace first so archive counts reflect the new timestamp/date.
            record.update(timestamp=timestamp, volume_ml=round(amount_ml, 4),
                          liquid_type_id=liquid_type, input_volume=float(amount), input_unit='mL',
                          cup_default_volume_ml_at_log=next((float(c['default_volume_ml']) for c in self.cup_types if c['id'] == cup_type_id), None))
            # An explicit user edit may change the cup; never infer it from volume.
            if cup_type_id:
                record['cup_type_id'] = cup_type_id
            else:
                record.pop('cup_type_id', None)
            if quick_button_id:
                record['quick_button_id'] = quick_button_id
                record['quick_button_label_at_log'] = next(
                    q['label'] for q in self.get_quick_buttons() if q['id'] == quick_button_id)
            else:
                record.pop('quick_button_id', None)
                record.pop('quick_button_label_at_log', None)
            if previous_day == self.last_reset_date:
                self._adjust_current(-previous_ml)
            else:
                self._adjust_archive(previous_day, -previous_ml)
            if next_day == self.last_reset_date:
                self._adjust_current(amount_ml)
            else:
                self._adjust_archive(next_day, amount_ml)
            # Remove stale event-relative snapshots; they are no longer historic truth.
            record.pop('before_ml', None)
            record.pop('after_ml', None)
            record.pop('manual_after_ml', None)
            await self._save()
            self._dispatch()
            return dict(record)

    async def async_delete_drink(self, record_id: str) -> None:
        """Permanently delete a drink and correct its day's totals."""
        async with self._lock:
            self._rolled()
            record = next((r for r in self.records if r.get('id') == record_id
                           and r.get('kind') == 'drink'), None)
            if record is None:
                raise ValueError('Drink moment not found')
            old_day = record['timestamp'][:10]
            delta = -float(record['volume_ml'])
            self.records.remove(record)
            if old_day == self.last_reset_date:
                self._adjust_current(delta)
            else:
                self._adjust_archive(old_day, delta)
            await self._save()
            self._dispatch()

    async def async_set_consumed(self, amount: float, unit: str = 'mL', origin: str = 'service') -> dict:
        requested = float(amount)
        if not math.isfinite(requested) or requested < 0 or to_ml(requested,unit) > 100000:
            raise ValueError('Total must be finite and between 0 and 100000 mL')
        if unit not in ('mL','L','fl_oz'):
            raise ValueError('Unsupported unit')
        new_ml = to_ml(requested,unit)
        async with self._lock:
            self._rolled()
            before = self.consumed_ml
            if self.source_mode == 'sum':
                self.manual_consumed_ml = max(0,new_ml-self.source_contribution_ml)
                self.consumed_ml = self.manual_consumed_ml+self.source_contribution_ml
            else:
                self.consumed_ml = new_ml
            rec = self._entry('set_consumed',origin,before,new_ml,requested,unit)
            self.records.append(rec)
            await self._save()
            self._dispatch()
            return rec

    async def async_reset_today(self, origin: str = 'service') -> dict:
        async with self._lock:
            self._rolled()
            before = self.consumed_ml
            self.daily_archive[self.last_reset_date] = self._snapshot(self._stamp())
            self.consumed_ml = self.manual_consumed_ml = 0.0
            if self.source_mode == 'sum':
                self._source_baseline_ml = self._last_source_value or 0.0
            else:
                self._last_source_value = None
                self._source_baseline_ml = 0
            rec = self._entry('reset',origin,before,0,details={'date':self.last_reset_date})
            self.records.append(rec)
            await self._save()
            self._dispatch()
            return rec

    async def async_set_target(self, amount_ml: float) -> None:
        if not math.isfinite(float(amount_ml)) or float(amount_ml)<0:
            raise ValueError('Invalid target')
        async with self._lock:
            old = self.target_ml
            self.target_override_ml = float(amount_ml)
            self.records.append(self._entry('set_target','number_entity',self.consumed_ml,self.target_override_ml,
                                           details={'old_target_ml':old,'new_target_ml':self.target_ml}))
            await self._save()
            self._dispatch()

    async def _handle_source_change(self, event) -> None:
        if event.data.get('entity_id') != self.source_sensor:
            return
        state = event.data.get('new_state')
        if state is None or state.state in ('unknown','unavailable',None):
            return
        try:
            raw = float(state.state)
        except (ValueError,TypeError):
            return
        unit = str(state.attributes.get('unit_of_measurement','mL'))
        if unit.lower() in ('l','liter','liters','litre','litres'):
            value_ml = raw*1000
        elif unit.lower() in ('fl_oz','floz','oz'):
            value_ml = raw*29.5735
        else:
            value_ml = raw
        if not math.isfinite(value_ml) or value_ml<0:
            return
        async with self._lock:
            self._rolled()
            old = self._last_source_value
            before = self.consumed_ml
            if self.source_mode == 'absolute':
                self.consumed_ml = value_ml
            elif self.source_mode == 'sum':
                if value_ml < self._source_baseline_ml:
                    self._source_baseline_ml = 0.0
                self.consumed_ml = self.manual_consumed_ml+max(0.0,value_ml-self._source_baseline_ml)
            else:
                if old is not None and value_ml>=old:
                    self.consumed_ml += value_ml-old
            self._last_source_value=value_ml
            change=self.consumed_ml-before
            self.source_readings.append(dict(id=uuid4().hex,timestamp=self._stamp(),sensor=self.source_sensor,
                                            raw_value=raw,unit=unit,value_ml=value_ml,change_ml=change,
                                            consumed_after_ml=self.consumed_ml))
            await self._save()
            self._dispatch()

    async def _save(self) -> None:
        payload=dict(consumed_ml=self.consumed_ml,manual_consumed_ml=self.manual_consumed_ml,
            last_reset_date=self.last_reset_date,target_override_ml=self.target_override_ml,
            last_source_value=self._last_source_value,source_baseline=self._source_baseline_ml,
            records=self.records,source_readings=self.source_readings,daily_archive=self.daily_archive,
            custom_liquid_types=self.custom_liquid_types,
            liquid_overrides=self.liquid_overrides,
            liquid_colors=self.liquid_colors,
            liquid_order=self.liquid_order,
            hidden_builtin_liquids=self.hidden_builtin_liquids,
            cup_types=self.cup_types, quick_buttons=self.quick_buttons,
            data_model_version=self.data_model_version,
            profile_display_name=self.profile_display_name,
            profile_target_model_v3=True)
        # Preserve unknown legacy profile fields during Release 1. Only the
        # subsequent cleanup release may retire these after successful migration.
        original=await self._store.async_load()
        if original is not None:
            if not isinstance(original,dict):
                raise ValueError('Profile storage has an unexpected format')
            payload={**original,**payload}
        # Release 1 retains every legacy field/copy for reversible migration.
        catalog=getattr(self, '_global_catalog_v3', None)
        if catalog is None:
            await self._store.async_save(payload)
        else:
            await catalog.async_save(self,payload)

    @callback
    def _dispatch(self) -> None:
        async_dispatcher_send(self.hass,self.signal)

    def liquid_color(self, liquid_id: str, name: str = '') -> str:
        return self.liquid_colors.get(liquid_id, default_liquid_color(liquid_id, name))

    def liquid_color_map(self) -> dict[str, str]:
        """Current catalog plus remembered historic color overrides."""
        defs = {t['id']: self.liquid_color(t['id'], t['name'])
                for t in self.get_liquid_definitions()}
        for ident, color in self.liquid_colors.items():
            defs.setdefault(ident, color)
        return defs

    def get_liquid_definitions(self) -> list[dict]:
        """Ordered definitions, merging built-in display overrides with stable IDs."""
        base = [dict(id=key, name=name, icon_mdi=icon, icon_svg='',
                     custom=False, hidden=key in self.hidden_builtin_liquids)
                for key, name, icon in _BUILTIN_LIQUIDS]
        for item in base:
            item.update(self.liquid_overrides.get(item['id'], {}))
        items = base + [dict(item, hidden=bool(item.get('hidden',False))) for item in self.custom_liquid_types]
        for item in items:
            mgr=self._global_catalog_v3
            if mgr:
                item['drink_count_all_profiles']=mgr.liquid_use_count(item['id'])
                item['can_delete']=bool(item.get('custom')) and item['drink_count_all_profiles']==0
            ident = item['id']
            item['color_override'] = self.liquid_colors.get(ident)
            item['color'] = self.liquid_color(ident, item['name'])
        priority = {ident: index for index, ident in enumerate(self.liquid_order)}
        fallback = {item['id']: index for index, item in enumerate(items)}
        return sorted(items, key=lambda item: priority.get(item['id'], len(priority) + fallback[item['id']]))

    def _valid_liquid_type(self, liquid_type: str | None) -> bool:
        return isinstance(liquid_type, str) and (
            liquid_type in LIQUID_TYPES or
            any(liquid_type == item['id'] for item in self.custom_liquid_types))

    async def async_add_liquid_type(self, name: str, icon_mdi: str = '',
                                    icon_svg: str = '', color: str = '') -> dict:
        if not isinstance(name, str):
            raise ValueError('Liquid name is required')
        name = name.strip()
        if not 1 <= len(name) <= 48 or any(ord(c) < 32 for c in name):
            raise ValueError('Liquid name must be 1-48 characters')
        if icon_mdi and icon_svg:
            raise ValueError('Choose an MDI icon or an SVG, not both')
        if icon_mdi and not re.fullmatch(r'mdi:[a-z0-9-]{2,70}', icon_mdi):
            raise ValueError('Invalid MDI icon (example: mdi:coffee)')
        if icon_svg:
            icon_svg = _safe_svg(icon_svg)
        selected_color = _color_override(color)
        async with self._lock:
            if len(self.custom_liquid_types) >= 30:
                raise ValueError('Maximum of 30 custom liquids reached')
            if any(x['name'].casefold() == name.casefold() for x in self.get_liquid_definitions()):
                raise ValueError('Liquid name already exists')
            item = dict(id='custom_' + uuid4().hex[:12], name=name,
                        icon_mdi=icon_mdi or ('mdi:glass-mug-variant' if not icon_svg else ''),
                        icon_svg=icon_svg, custom=True, hidden=False)
            self.custom_liquid_types.append(item)
            if selected_color:
                self.liquid_colors[item['id']] = selected_color
            if self.liquid_order:
                self.liquid_order.append(item['id'])
            await self._save()
            self._dispatch()
            return dict(item)

    async def async_set_custom_liquid_visibility(self, liquid_type: str,
                                                visible: bool) -> dict:
        if type(visible) is not bool:
            raise ValueError('Expected boolean visibility')
        async with self._lock:
            item=next((t for t in self.custom_liquid_types if t['id']==liquid_type),None)
            if item is None:
                raise ValueError('Custom liquid type not found')
            item['hidden']=not visible
            await self._save()
            self._dispatch()
            return next(t for t in self.get_liquid_definitions() if t['id']==liquid_type)

    async def async_delete_liquid_type(self, liquid_type: str) -> None:
        async with self._lock:
            item = next((x for x in self.custom_liquid_types if x['id'] == liquid_type), None)
            if item is None:
                raise ValueError('Custom liquid not found')
            if any(x.get('kind') == 'drink' and x.get('liquid_type_id') == liquid_type for x in self.records):
                raise ValueError('This liquid is used in drink history and cannot be deleted')
            if self._global_catalog_v3 is None and any(q.get('liquid_type_id') == liquid_type for q in self.quick_buttons):
                raise ValueError('This liquid is used by Quick buttons; hide it instead')
            self.custom_liquid_types.remove(item)
            self.liquid_order = [key for key in self.liquid_order if key != liquid_type]
            await self._save()
            self._dispatch()

    async def async_update_liquid_type(self, liquid_type: str, name: str,
                                      icon_mdi: str = '', icon_svg: str = '',
                                      color: str | None = None) -> dict:
        """Update any liquid's display metadata. Never rewrite its historical ID."""
        if not isinstance(name, str):
            raise ValueError('Liquid name is required')
        name = name.strip()
        if not 1 <= len(name) <= 48 or any(ord(c) < 32 for c in name):
            raise ValueError('Liquid name must be 1-48 characters')
        if icon_mdi and icon_svg:
            raise ValueError('Choose an MDI icon or an SVG, not both')
        if icon_mdi and not re.fullmatch(r'mdi:[a-z0-9-]{2,70}', icon_mdi):
            raise ValueError('Invalid MDI icon (example: mdi:coffee)')
        if icon_svg:
            icon_svg = _safe_svg(icon_svg)
        selected_color = _color_override(color) if color is not None else None
        async with self._lock:
            definitions = self.get_liquid_definitions()
            existing = next((item for item in definitions if item['id'] == liquid_type), None)
            if existing is None:
                raise ValueError('Liquid type not found')
            if any(item['id'] != liquid_type and item['name'].casefold() == name.casefold()
                   for item in definitions):
                raise ValueError('Liquid name already exists')
            props = dict(name=name,
                         icon_mdi=icon_mdi or ('mdi:glass-water' if not icon_svg else ''),
                         icon_svg=icon_svg)
            if existing['custom']:
                next(item for item in self.custom_liquid_types if item['id'] == liquid_type).update(props)
            else:
                self.liquid_overrides[liquid_type] = props
            if color is not None:
                if selected_color is None:
                    self.liquid_colors.pop(liquid_type, None)
                else:
                    self.liquid_colors[liquid_type] = selected_color
            await self._save()
            self._dispatch()
            return next(item for item in self.get_liquid_definitions() if item['id'] == liquid_type)

    async def async_set_builtin_liquid_visibility(self, liquid_type: str, visible: bool) -> dict:
        """Remove or restore a built-in button without deleting historical records.

        Built-in IDs are part of historical drink data and service contracts. Hiding
        removes the type from the picker only, while preserving the definition for
        past records, the today chart, Excel and explicit recovery.
        """
        if liquid_type not in LIQUID_TYPES or type(visible) is not bool:
            raise ValueError('Expected a built-in liquid and a boolean visibility')
        async with self._lock:
            hidden = set(self.hidden_builtin_liquids)
            if visible:
                hidden.discard(liquid_type)
            else:
                hidden.add(liquid_type)
            self.hidden_builtin_liquids = [key for key, _, _ in _BUILTIN_LIQUIDS if key in hidden]
            await self._save()
            self._dispatch()
            return next(item for item in self.get_liquid_definitions() if item['id'] == liquid_type)

    async def async_set_liquid_order(self, ordered_ids: list[str]) -> list[str]:
        """Replace the entire catalog order atomically, rejecting stale lists."""
        async with self._lock:
            known = [item['id'] for item in self.get_liquid_definitions()]
            if (not isinstance(ordered_ids, list)
                    or any(not isinstance(ident, str) for ident in ordered_ids)
                    or len(ordered_ids) != len(known)
                    or len(set(ordered_ids)) != len(known)
                    or set(ordered_ids) != set(known)):
                raise ValueError('Liquid order must contain each existing type exactly once')
            self.liquid_order = list(ordered_ids)
            await self._save()
            self._dispatch()
            return list(self.liquid_order)


    # Native Liquid and Cup catalogs (no legacy aliases).
    @staticmethod
    def _catalog_name(value: str, label: str = 'Name') -> str:
        if not isinstance(value, str) or not (1 <= len(value.strip()) <= 48):
            raise ValueError(f'{label} must contain 1-48 characters')
        value = value.strip()
        if any(ord(ch) < 32 for ch in value):
            raise ValueError(f'{label} contains an invalid control character')
        return value

    def valid_cup(self, cup_id: str | None, include_hidden: bool = False) -> bool:
        return bool(cup_id) and any(c['id'] == cup_id and (include_hidden or not c.get('hidden'))
                                     for c in self.cup_types)

    def valid_quick(self, quick_id: str | None, liquid_id: str | None,
                    cup_id: str | None) -> bool:
        return bool(quick_id) and any(q['id'] == quick_id and not q.get('hidden')
                                      and q['liquid_type_id'] == liquid_id
                                      and q['cup_type_id'] == cup_id
                                      for q in self.quick_buttons)

    def get_cup_types(self) -> list[dict]:
        mgr=self._global_catalog_v3
        result=[]
        for cup in self.cup_types:
            item=dict(cup)
            item['drink_count_all_profiles']=(mgr.cup_use_count(cup['id']) if mgr
                else sum(r.get('kind')=='drink' and r.get('cup_type_id')==cup['id']
                         for r in self.records))
            item['can_delete']=item['drink_count_all_profiles']==0
            result.append(item)
        return result

    def get_quick_buttons(self) -> list[dict]:
        liquid_names = {x['id']: x['name'] for x in self.get_liquid_definitions()}
        cup_names = {x['id']: x['name'] for x in self.cup_types}
        result = []
        for q in self.quick_buttons:
            item = dict(q)
            item['label'] = (q.get('custom_label', '') if q.get('label_mode') == 'custom'
                             else f"{liquid_names.get(q['liquid_type_id'], q['liquid_type_id'])} "
                                  f"({cup_names.get(q['cup_type_id'], q['cup_type_id'])})")
            item['default_volume_ml'] = next((x['default_volume_ml'] for x in self.cup_types
                                             if x['id'] == q['cup_type_id']), None)
            item['available'] = (self._valid_liquid_type(q['liquid_type_id'])
                                 and not any(x['id'] == q['liquid_type_id'] and x.get('hidden')
                                             for x in self.get_liquid_definitions())
                                 and self.valid_cup(q['cup_type_id']) and not q.get('hidden'))
            result.append(item)
        return result

    async def async_manage_cup(self, action: str, cup_id: str = '', name: str = '',
                               volume_ml: float | None = None, icon_mdi: str = '',
                               order: list[str] | None = None) -> list[dict]:
        if action not in ('add', 'update', 'hide', 'restore', 'reorder', 'delete'):
            raise ValueError('Invalid cup action')
        async with self._lock:
            if action == 'delete':
                cup = next((c for c in self.cup_types if c['id'] == cup_id), None)
                if cup is None:
                    raise ValueError('Cup type not found')
                if any(r.get('kind')=='drink' and r.get('cup_type_id')==cup_id
                       for r in self.records):
                    raise ValueError('Cup is used in drink history; hide it')
                if self._global_catalog_v3 is None and any(q.get('cup_type_id')==cup_id for q in self.quick_buttons):
                    raise ValueError('Cup is used by Quick buttons; hide it')
                self.cup_types = [c for c in self.cup_types if c['id'] != cup_id]
            elif action == 'reorder':
                if not isinstance(order, list) or set(order) != {c['id'] for c in self.cup_types} or len(order) != len(self.cup_types):
                    raise ValueError('Cup order must include every cup exactly once')
                lookup = {c['id']: c for c in self.cup_types}
                self.cup_types = [lookup[x] for x in order]
            elif action in ('hide', 'restore'):
                cup = next((c for c in self.cup_types if c['id'] == cup_id), None)
                if cup is None:
                    raise ValueError('Cup type not found')
                cup['hidden'] = action == 'hide'
            else:
                name = self._catalog_name(name, 'Cup name')
                valid_volume = _default_volume(volume_ml)
                if valid_volume is None:
                    raise ValueError('Cup volume must be between 0 and 100000 mL')
                if icon_mdi and not re.fullmatch(r'mdi:[a-z0-9-]{2,70}', icon_mdi):
                    raise ValueError('Invalid Cup MDI icon')
                cup = next((c for c in self.cup_types if c['id'] == cup_id), None)
                if action == 'update' and cup is None:
                    raise ValueError('Cup type not found')
                if action == 'add' and len(self.cup_types) >= 40:
                    raise ValueError('Maximum 40 cup types')
                if any(c['name'].casefold() == name.casefold() and c is not cup for c in self.cup_types):
                    raise ValueError('Cup name already exists')
                props = dict(name=name, default_volume_ml=valid_volume,
                             icon_mdi=icon_mdi or 'mdi:cup', hidden=False)
                if action == 'add':
                    self.cup_types.append(dict(id='cup_' + uuid4().hex[:12], **props))
                else:
                    cup.update(props)
            await self._save()
            self._dispatch()
            return self.get_cup_types()

    async def async_manage_quick(self, action: str, quick_id: str = '',
                                 liquid_type_id: str = '', cup_type_id: str = '',
                                 label_mode: str = 'automatic', custom_label: str = '',
                                 order: list[str] | None = None, icon_mdi: str = '') -> list[dict]:
        if action not in ('add','update','hide','restore','reorder','delete'):
            raise ValueError('Invalid quick-button action')
        async with self._lock:
            if action == 'delete':
                item = next((q for q in self.quick_buttons if q['id'] == quick_id), None)
                if item is None:
                    raise ValueError('Quick button not found')
                # Historical ledger is immutable. A retired shortcut ID may
                # remain referenced by an older drink; that is provenance,
                # not an active profile preference.
                previous_buttons = deepcopy(self.quick_buttons)
                previous_records_digest = digest(self.records)
                try:
                    self.quick_buttons = [q for q in self.quick_buttons if q['id'] != quick_id]
                    await self._save()
                except Exception:
                    self.quick_buttons = previous_buttons
                    raise
                if digest(self.records) != previous_records_digest:
                    raise ValueError('Quick deletion unexpectedly modified drink history')
                self._dispatch()
                return self.get_quick_buttons()
            if action == 'reorder':
                if not isinstance(order, list) or set(order) != {q['id'] for q in self.quick_buttons} or len(order) != len(self.quick_buttons):
                    raise ValueError('Quick-button order must include every button exactly once')
                lookup = {q['id']: q for q in self.quick_buttons}
                self.quick_buttons = [lookup[x] for x in order]
            elif action in ('hide','restore'):
                item = next((q for q in self.quick_buttons if q['id'] == quick_id), None)
                if item is None:
                    raise ValueError('Quick button not found')
                item['hidden'] = action == 'hide'
            else:
                if not self._valid_liquid_type(liquid_type_id):
                    raise ValueError('Choose an active liquid type')
                if not self.valid_cup(cup_type_id):
                    raise ValueError('Choose an active cup type')
                if icon_mdi and not re.fullmatch(r'mdi:[a-z0-9-]{2,70}',icon_mdi):
                    raise ValueError('Invalid Quick button MDI icon')
                if label_mode not in ('automatic','custom'):
                    raise ValueError('Label mode must be automatic or custom')
                if label_mode == 'custom':
                    if not isinstance(custom_label,str) or not custom_label.strip() or any(ord(ch)<32 for ch in custom_label):
                        raise ValueError('Custom button label is required')
                    custom_label=custom_label.strip()
                    if len(custom_label) > 60:
                        raise ValueError('Label must be at most 60 characters')
                else:
                    custom_label = ''
                item = next((q for q in self.quick_buttons if q['id'] == quick_id), None)
                if action == 'update' and item is None:
                    raise ValueError('Quick button not found')
                if action == 'add' and len(self.quick_buttons) >= 48:
                    raise ValueError('Maximum 48 quick buttons')
                if any(q is not item and q['liquid_type_id'] == liquid_type_id and
                       q['cup_type_id'] == cup_type_id for q in self.quick_buttons):
                    raise ValueError('A Quick button already uses this Liquid and Cup combination')
                props = dict(liquid_type_id=liquid_type_id,cup_type_id=cup_type_id,
                             label_mode=label_mode,custom_label=custom_label,icon_mdi=icon_mdi,hidden=False)
                if action == 'add':
                    self.quick_buttons.append(dict(id='quick_' + uuid4().hex[:12], **props))
                else:
                    item.update(props)
            await self._save()
            self._dispatch()
            return self.get_quick_buttons()






    # Strict native Settings import; the drink ledger remains independent.
    def settings_revision(self) -> str:
        return digest(extract(self))

    async def async_import_settings(self, settings: dict, expected_revision: str,
                                    include_mappings: bool = False) -> dict:
        cleaned = validate_payload(dict(format='jwDaily-Hydration-Log-settings',
            schema=2, settings=settings))
        # A settings-only import must not orphan any persisted drink references.
        allowable = set(('water','coffee','tea','milk','soup','wine','other')) | {t['id'] for t in cleaned['custom_liquid_types']}
        available_cups = {cup['id'] for cup in cleaned['cup_types']}
        for record in self.records:
            if record.get('kind') != 'drink':
                continue
            lid = record['liquid_type_id']
            cup = record.get('cup_type_id')
            if lid not in allowable or (cup and cup not in available_cups):
                raise ValueError('Settings import would orphan existing Liquid/Cup references; restore matching Data or use Full Backup')
        # Imported user SVGs require the same security filter as direct uploads.
        for item in cleaned['custom_liquid_types']:
            if item.get('icon_svg'): _safe_svg(item['icon_svg'])
        for item in cleaned['liquid_overrides'].values():
            if item.get('icon_svg'): _safe_svg(item['icon_svg'])
        async with self._lock:
            if self.settings_revision() != expected_revision:
                raise ValueError('Settings have changed since preview. Refresh before importing.')
            old = extract(self)
            unchanged_records = [(r.get('id'), r.get('timestamp'), r.get('volume_ml'))
                                 for r in self.records]
            try:
                for k,v in cleaned.items():setattr(self,k,deepcopy(v))
                await self._save()
            except Exception:
                for k,v in old.items():setattr(self,k,v)
                raise
            assert unchanged_records == [(r.get('id'), r.get('timestamp'), r.get('volume_ml'))
                                         for r in self.records]
            self._dispatch()
            return settings_preview(self,cleaned)

    async def async_update_profile_identity_target(self, name: str, target: float) -> dict:
        """Commit display name and personal goal in one recoverable profile write.

        Existing drink records and archived daily target snapshots are preserved.
        """
        name=self._catalog_name(name,'Profile display name')
        if not isinstance(target,(int,float)) or not math.isfinite(target) or not 1<=target<=100000:
            raise ValueError('Invalid daily target')
        async with self._lock:
            old_name=self.name
            old_target=self.target_override_ml
            old_records=deepcopy(self.records)
            old_sha=digest(old_records)
            try:
                self.name=self.profile_display_name=name
                if round(target)!=self.target_ml:
                    self.target_override_ml=float(target)
                    self.records.append(self._entry('set_target','profile_settings',
                        self.consumed_ml,self.target_override_ml,
                        details={'old_target_ml':round(old_target) if old_target>0 else 2000,
                                 'new_target_ml':self.target_ml}))
                await self._save()
            except Exception:
                self.name=self.profile_display_name=old_name
                self.target_override_ml=old_target
                self.records=old_records
                raise
            self._dispatch()
            return {'name':name,'target_ml':self.target_ml,
                    'old_history_sha256':old_sha,
                    'records_before':len(old_records),'records_after':len(self.records)}

    async def async_set_display_name(self, name: str) -> dict:
        label=self._catalog_name(name,'Profile display name')
        async with self._lock:
            before=self.name
            self.name=self.profile_display_name=label
            try:await self._save()
            except Exception:
                self.name=self.profile_display_name=before
                raise
            self._dispatch()
            return dict(name=self.name, slug=self.slug)






    def get_history(self, date: str | None = None) -> list[dict]:
        day = date or self._today()
        values = [dict(id=r['id'],timestamp=r['timestamp'],volume_ml=r['volume_ml'],
                       liquid_type=r['liquid_type_id'],
                       cup_type_id=r.get('cup_type_id'),
                       cup_default_volume_ml_at_log=r.get('cup_default_volume_ml_at_log'),
                       quick_button_id=r.get('quick_button_id'),
                       quick_button_label_at_log=r.get('quick_button_label_at_log'),
                       origin=r.get('origin', ''))
                  for r in self.records if r['kind']=='drink' and r['timestamp'][:10]==day]
        return sorted(values, key=lambda r: (r['timestamp'],r['id']))

    def liquid_breakdown(self, day: str) -> list[dict]:
        """Recorded drinks grouped for ONE selected date, including hidden types.

        Source-sensor measurements cannot be assigned a liquid type and are not
        silently included in the typed breakdown.
        """
        totals: dict[str, float] = {}
        for record in self.records:
            if record.get('kind') != 'drink' or record.get('timestamp', '')[:10] != day:
                continue
            liquid = record['liquid_type_id']
            totals[liquid] = totals.get(liquid, 0.0) + float(record.get('volume_ml', 0))
        return [dict(liquid_type=key, volume_ml=round(volume, 3))
                for key, volume in sorted(totals.items()) if volume > 0]

    def today_breakdown(self) -> list[dict]:
        """Backward-compatible current-day breakdown."""
        return self.liquid_breakdown(self._today())

    def day_summary(self, day: str) -> dict:
        """Consistent historic or live totals for the selected HA-local date.

        Closed days use their stored daily_archive snapshots, including past
        sensor contribution and the target in force on that day. Dates without
        a snapshot cannot reconstruct historic sensor readings: use their
        manually logged drinks without inventing missing external volumes.
        """
        try:
            parsed = datetime.strptime(day, '%Y-%m-%d').date()
            if parsed.isoformat() != day:
                raise ValueError()
        except (TypeError, ValueError) as exc:
            raise ValueError('History date must be YYYY-MM-DD') from exc
        if day > self._today():
            raise ValueError('History date cannot be in the future')
        entries = self.get_history(day)
        if day == self._today():
            consumed = self.consumed_ml
            target = self.target_ml
            source = self.source_contribution_ml
        else:
            archived = self.daily_archive.get(day)
            if archived is not None:
                consumed = float(archived.get('consumed_ml', 0.0))
                target = float(archived.get('target_ml') or self.target_ml)
                source = float(archived.get('source_ml', 0.0))
            else:
                consumed = sum(float(item['volume_ml']) for item in entries)
                target = self.target_ml
                source = 0.0
        return dict(date=day, consumed_ml=round(max(0.0, consumed), 3),
                    target_ml=round(max(1.0, target), 3),
                    source_ml=round(max(0.0, source), 3),
                    drink_count=len(entries),
                    liquid_breakdown=self.liquid_breakdown(day))

    def chart_hourly_today(self) -> dict:
        """24 local-clock hour buckets, typed drink records only.

        Two physical hours during the autumn DST transition share the same
        labelled 02:00 local bucket. Source sensors cannot be typed per hour
        and are explicitly excluded to avoid misattribution.
        """
        day=self._today()
        tz=ZoneInfo(getattr(self.hass.config, 'time_zone', 'Europe/Amsterdam'))
        buckets=[]
        for hour in range(24):
            start=datetime.combine(date.fromisoformat(day),time(hour=hour),tzinfo=tz)
            buckets.append(dict(hour=f'{hour:02d}:00',start=start.isoformat(timespec='seconds'),
                                total_ml=0.0,liquids={}))
        for record in self.records:
            if record.get('kind')!='drink' or record.get('timestamp','')[:10]!=day:
                continue
            try:
                hour=int(record['timestamp'][11:13])
                volume=float(record.get('volume_ml',0))
                if not 0<=hour<=23 or not math.isfinite(volume) or volume<=0: continue
            except (TypeError,ValueError,IndexError):
                continue
            bucket=buckets[hour]
            liquid=record['liquid_type_id']
            bucket['total_ml']+=volume
            bucket['liquids'][liquid]=bucket['liquids'].get(liquid,0.0)+volume
        for bucket in buckets:
            bucket['total_ml']=round(bucket['total_ml'],3)
            bucket['liquids']={k:round(v,3) for k,v in bucket['liquids'].items()}
        return dict(date=day,total_logged_ml=round(sum(b['total_ml'] for b in buckets),3),
                    buckets=buckets,coverage='typed_logged_drinks_only',
                    liquid_names={t['id']:t['name'] for t in self.get_liquid_definitions()},
                    liquid_colors=self.liquid_color_map())

    def chart_last_7_days(self) -> dict:
        """Exactly seven HA-local calendar days, including today, by stable type ID."""
        today=date.fromisoformat(self._today())
        rows=[]
        for offset in range(6,-1,-1):
            day=(today-timedelta(days=offset)).isoformat()
            summary=self.day_summary(day)
            typed={part['liquid_type']:part['volume_ml'] for part in summary['liquid_breakdown']}
            # 'No data' is not the same as a tracked day with zero logged drinks.
            # Today is an active tracking day; historical days require an archive
            # snapshot or actual drink records. This is read-only metadata.
            has_data = (day == self._today() or day in self.daily_archive
                        or any(r.get('kind') == 'drink' and r.get('timestamp', '')[:10] == day
                               for r in self.records))
            rows.append(dict(date=day,total_logged_ml=round(sum(typed.values()),3),
                             consumed_ml=summary['consumed_ml'],target_ml=summary['target_ml'],
                             drink_count=summary['drink_count'],liquids=typed,has_data=has_data))
        return dict(days=rows,total_logged_ml=round(sum(r['total_logged_ml'] for r in rows),3),
                    coverage='typed_logged_drinks_only',
                    liquid_names={t['id']:t['name'] for t in self.get_liquid_definitions()},
                    liquid_colors=self.liquid_color_map())



    def data_revision(self) -> str:
        return data_io.sha(data_io.extract(self))

    def export_data(self) -> dict:
        return data_io.export_payload(self)

    def _validate_import_data(self, raw: dict, *, settings: dict | None = None) -> dict:
        from .settings_io import BUILTINS
        catalog = settings or extract(self)
        liquid_ids = set(BUILTINS) | {t['id'] for t in catalog['custom_liquid_types']}
        cup_ids = {c['id'] for c in catalog['cup_types']}
        return data_io.validate(raw, liquids=liquid_ids, cups=cup_ids)

    def data_import_preview(self, raw: dict, mode: str) -> dict:
        if mode == 'replace' and (raw.get('source_profile') or {}).get('slug') != self.slug:
            raise ValueError('Replace all requires a Data export of this same profile')
        clean = self._validate_import_data(raw)
        proposed, counts = data_io.import_plan(data_io.extract(self), clean, mode, default_target_ml=self.target_ml)
        return dict(profile=self.slug, mode=mode, counts=counts,
                    settings_revision=self.settings_revision(), data_revision=self.data_revision(),
                    import_sha256=data_io.sha(raw), expected_result_sha256=data_io.sha(proposed),
                    warning='Merge/update retains existing source measurements; replace restores full data.')

    async def async_import_data(self, raw: dict, mode: str, preview: dict) -> dict:
        async with self._lock:
            if self.settings_revision() != preview.get('settings_revision') or self.data_revision() != preview.get('data_revision'):
                raise ValueError('Data or settings changed after preview; recheck import')
            if data_io.sha(raw) != preview.get('import_sha256') or preview.get('mode') != mode:
                raise ValueError('Import contents changed after preview')
            clean = self._validate_import_data(raw)
            result, counts = data_io.import_plan(data_io.extract(self), clean, mode, default_target_ml=self.target_ml)
            if data_io.sha(result) != preview.get('expected_result_sha256'):
                raise ValueError('Import result no longer matches preview')
            old = data_io.extract(self)
            try:
                for k, v in result.items():
                    setattr(self, '_source_baseline_ml' if k=='source_baseline' else
                            '_last_source_value' if k=='last_source_value' else k, deepcopy(v))
                self._assert_native_ledger()
                await self._save()
            except Exception:
                for k, v in old.items():
                    setattr(self, '_source_baseline_ml' if k=='source_baseline' else
                            '_last_source_value' if k=='last_source_value' else k, v)
                raise
            self._dispatch()
            return dict(applied=True, **counts, data_revision=self.data_revision())

    def full_backup(self) -> bytes:
        from .settings_io import export_payload
        return data_io.build_full(export_payload(self), self.export_data())

    def _validate_restored_preferences(self, raw: dict) -> dict:
        if not isinstance(raw, dict):
            raise ValueError('Full backup is missing profile preferences')
        value = {key: raw.get(key) for key in ('age','gender','unit')}
        if type(value['age']) is not int or not 1 <= value['age'] <= 120:
            raise ValueError('Invalid profile age')
        if value['gender'] not in ('male', 'female') or value['unit'] not in ('mL','L','fl_oz'):
            raise ValueError('Invalid profile gender or unit')
        return value

    def full_restore_preview(self, raw_settings: dict, raw_data: dict, archive_digest: str) -> dict:
        if (raw_settings.get('source_profile') or {}).get('slug') != self.slug or \
           (raw_data.get('source_profile') or {}).get('slug') != self.slug:
            raise ValueError('Full restore is restricted to the same profile ID')
        settings = validate_payload(raw_settings)
        for item in settings['custom_liquid_types']:
            if item.get('icon_svg'):_safe_svg(item['icon_svg'])
        for item in settings['liquid_overrides'].values():
            if item.get('icon_svg'):_safe_svg(item['icon_svg'])
        preferences = self._validate_restored_preferences(raw_settings.get('profile_preferences'))
        data = self._validate_import_data(raw_data, settings=settings)
        counts = dict(records=sum(r.get('kind') == 'drink' for r in data['records']),
                      cups=len(settings['cup_types']), quick_buttons=len(settings['quick_buttons']),
                      current_records=sum(r.get('kind') == 'drink' for r in self.records))
        return dict(profile=self.slug, archive_sha256=archive_digest,
                    settings_revision=self.settings_revision(), data_revision=self.data_revision(),
                    counts=counts, target_settings_sha256=digest(settings),
                    target_data_sha256=data_io.sha(data), preferences_sha256=data_io.sha(preferences))

    async def async_restore_full(self, settings: dict, data: dict, preview: dict, preferences: dict | None = None) -> dict:
        async with self._lock:
            if (self.settings_revision() != preview.get('settings_revision') or
                self.data_revision() != preview.get('data_revision') or
                digest(settings) != preview.get('target_settings_sha256') or
                data_io.sha(data) != preview.get('target_data_sha256') or
                data_io.sha(preferences) != preview.get('preferences_sha256')):
                raise ValueError('Full backup or profile changed since preview')
            old_settings, old_data = extract(self), data_io.extract(self)
            old_version = self.data_model_version
            old_pref = {k:getattr(self,k) for k in ('age','gender','unit')}
            old_options = dict(self.entry.options)
            try:
                for k,v in preferences.items():setattr(self,k,v)
                for k, v in settings.items():
                    setattr(self, k, deepcopy(v))
                for k, v in data.items():
                    setattr(self, '_source_baseline_ml' if k=='source_baseline' else
                            '_last_source_value' if k=='last_source_value' else k, deepcopy(v))
                self._assert_native_ledger()
                await self._save()
                # Native Home Assistant options are the durable owner of profile preferences.
                options={**self.entry.options,**preferences}
                self.hass.config_entries.async_update_entry(self.entry, options=options)
            except Exception:
                for k,v in old_pref.items():setattr(self,k,v)
                for k, v in old_settings.items():setattr(self,k,v)
                for k, v in old_data.items():
                    setattr(self, '_source_baseline_ml' if k=='source_baseline' else
                            '_last_source_value' if k=='last_source_value' else k,v)
                self.data_model_version = old_version
                try:await self._save()
                except Exception:pass  # Preserve original exception; HA Store uses atomic writes.
                raise
            self._dispatch()
            return dict(restored=True, count=preview['counts']['records'],
                        settings_revision=self.settings_revision(), data_revision=self.data_revision())

    def export_snapshot(self) -> dict:
        cfg = {key: getattr(self,key) for key in ('name','age','gender','unit')}
        return dict(entry_id=self.entry_id,slug=self.slug,config=cfg,date=self.last_reset_date,
                    consumed_ml=self.consumed_ml,manual_consumed_ml=self.manual_consumed_ml,
                    target_ml=self.target_ml,source_contribution_ml=self.source_contribution_ml,
                    records=[dict(r) for r in self.records],source_readings=[dict(r) for r in self.source_readings],
                    daily_archive={key:dict(val) for key,val in self.daily_archive.items()},
                    custom_liquid_types=[dict(item) for item in self.custom_liquid_types],
                    liquid_definitions=self.get_liquid_definitions(),
                    liquid_colors=dict(self.liquid_colors),
                    hidden_builtin_liquids=list(self.hidden_builtin_liquids),
                    cup_types=self.get_cup_types(),quick_buttons=self.get_quick_buttons())