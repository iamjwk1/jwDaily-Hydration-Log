"""Per-profile editable drink records and durable source sample history."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import math
from uuid import uuid4
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util, slugify

from .const import DOMAIN, SIGNAL, LIQUID_TYPES, to_ml, target_ml, safe_amount


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
    if value > dt_util.now().astimezone(tz) + timedelta(minutes=5):
        raise ValueError('Drink time cannot be in the future')
    return value.isoformat(timespec='seconds')



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
        self.pregnancy = bool(cfg.get('pregnancy', False))
        self.lactation = bool(cfg.get('lactation', False))
        self.source_sensor = cfg.get('source_sensor') or None
        self.source_mode = cfg.get('source_mode', 'absolute')
        self.unit = cfg.get('unit', 'mL')
        self.target_override_ml = 0.0
        self.consumed_ml = 0.0
        self.manual_consumed_ml = 0.0
        self.last_reset_date = self._today()
        self._last_source_value: float | None = None
        self._source_baseline_ml: float = 0.0
        self.records: list[dict[str, Any]] = []
        self.source_readings: list[dict[str, Any]] = []
        self.daily_archive: dict[str, dict[str, Any]] = {}

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
        return round(self.target_override_ml) if self.target_override_ml > 0 else target_ml(self.age,self.gender,self.pregnancy,self.lactation)

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

    async def async_initialize(self) -> None:
        saved = await self._store.async_load()
        if saved:
            self.consumed_ml = float(saved.get('consumed_ml',0.0))
            self.manual_consumed_ml = float(saved.get('manual_consumed_ml',0.0))
            self.last_reset_date = saved.get('last_reset_date', self._today())
            self.target_override_ml = float(saved.get('target_override_ml',0.0))
            self._last_source_value = saved.get('last_source_value')
            self._source_baseline_ml = float(saved.get('source_baseline',0.0))
            self.records = list(saved.get('records',[]))
            for item in self.records:
                if item.get('kind') == 'drink':
                    item.setdefault('liquid_type', 'unknown')  # Historical v1.0.2, never assume water.
            self.source_readings = list(saved.get('source_readings',[]))
            self.daily_archive = dict(saved.get('daily_archive',{}))
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
                              clock: str | None = None) -> dict:
        amount_ml = safe_amount(amount, unit)
        if liquid_type not in LIQUID_TYPES:
            raise ValueError('Choose a liquid type explicitly')
        timestamp = _local_timestamp(self.hass, day, clock)
        async with self._lock:
            self._rolled()
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
            record['liquid_type'] = liquid_type
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
                               day: str, clock: str) -> dict:
        """Replace a drink in place, keeping its stable ID but no old values."""
        if liquid_type not in LIQUID_TYPES:
            raise ValueError('Choose a liquid type explicitly')
        amount_ml = safe_amount(amount, 'mL')
        timestamp = _local_timestamp(self.hass, day, clock)
        async with self._lock:
            self._rolled()
            record = next((r for r in self.records if r.get('id') == record_id
                           and r.get('kind') == 'drink'), None)
            if record is None:
                raise ValueError('Drink moment not found')
            previous_day = record['timestamp'][:10]
            previous_ml = float(record['volume_ml'])
            next_day = timestamp[:10]
            # Replace first so archive counts reflect the new timestamp/date.
            record.update(timestamp=timestamp, volume_ml=round(amount_ml, 4),
                          liquid_type=liquid_type, input_volume=float(amount), input_unit='mL')
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
        await self._store.async_save(dict(consumed_ml=self.consumed_ml,manual_consumed_ml=self.manual_consumed_ml,
            last_reset_date=self.last_reset_date,target_override_ml=self.target_override_ml,
            last_source_value=self._last_source_value,source_baseline=self._source_baseline_ml,
            records=self.records,source_readings=self.source_readings,daily_archive=self.daily_archive))

    @callback
    def _dispatch(self) -> None:
        async_dispatcher_send(self.hass,self.signal)

    def get_history(self, date: str | None = None) -> list[dict]:
        day = date or self._today()
        values = [dict(id=r['id'], timestamp=r['timestamp'], volume_ml=r['volume_ml'],
                       liquid_type=r.get('liquid_type', 'unknown'), origin=r.get('origin', ''))
                  for r in self.records if r['kind']=='drink' and r['timestamp'][:10]==day]
        return sorted(values, key=lambda r: (r['timestamp'],r['id']))

    def export_snapshot(self) -> dict:
        cfg = {key: getattr(self,key) for key in ('name','age','gender','pregnancy','lactation','source_sensor','source_mode','unit')}
        return dict(entry_id=self.entry_id,slug=self.slug,config=cfg,date=self.last_reset_date,
                    consumed_ml=self.consumed_ml,manual_consumed_ml=self.manual_consumed_ml,
                    target_ml=self.target_ml,source_contribution_ml=self.source_contribution_ml,
                    records=[dict(r) for r in self.records],source_readings=[dict(r) for r in self.source_readings],
                    daily_archive={key:dict(val) for key,val in self.daily_archive.items()})
