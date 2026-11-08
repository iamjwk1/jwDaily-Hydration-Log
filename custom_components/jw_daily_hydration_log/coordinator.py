"""Per-profile state, immutable drink ledger and source sample history."""
from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta
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

from .const import DOMAIN, SIGNAL, DEFAULT_START, DEFAULT_END, SOURCE_MODES, to_ml, target_ml, safe_amount


def _parse_clock(text: str, fallback: str) -> time:
    try:
        return time.fromisoformat((text or fallback))
    except (TypeError, ValueError):
        return time.fromisoformat(fallback)


class HydrationCoordinator:
    """One persisted profile; every user-visible add is a distinct ledger event."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass, self.entry = hass, entry
        self.entry_id = entry.entry_id
        self._store = Store(hass, 1, f'{DOMAIN}.{entry.entry_id}')
        self._lock = asyncio.Lock()
        self._unsub_reset = self._unsub_source = self._unsub_pace = None
        cfg = {**entry.data, **entry.options}
        self.name = cfg.get('name', 'Hydration')
        self.slug = slugify(self.name)
        self.age = int(cfg.get('age', 30))
        self.gender = cfg.get('gender', 'male')
        self.pregnancy = bool(cfg.get('pregnancy', False))
        self.lactation = bool(cfg.get('lactation', False))
        self.day_start = _parse_clock(cfg.get('day_start'), DEFAULT_START)
        self.day_end = _parse_clock(cfg.get('day_end'), DEFAULT_END)
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
    def hourly_pace_ml(self) -> float:
        now = self._now()
        start = now.replace(hour=self.day_start.hour,minute=self.day_start.minute,second=self.day_start.second,microsecond=0)
        end = now.replace(hour=self.day_end.hour,minute=self.day_end.minute,second=self.day_end.second,microsecond=0)
        if end <= start or now >= end:
            return round(self.remaining_ml,1)
        if now < start:
            return round(self.remaining_ml / max(0.25, (end-start).total_seconds()/3600),1)
        return round(self.remaining_ml / max(0.25, (end-now).total_seconds()/3600),1)

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
            self.source_readings = list(saved.get('source_readings',[]))
            self.daily_archive = dict(saved.get('daily_archive',{}))
        if self.last_reset_date != self._today():
            self._rolled()
            await self._save()
        self._unsub_reset = async_track_time_change(self.hass,self._scheduled_reset,hour=0,minute=0,second=0)
        self._unsub_pace = async_track_time_change(self.hass,self._tick,second=0)
        if self.source_sensor:
            self._unsub_source = self.hass.bus.async_listen(EVENT_STATE_CHANGED,self._handle_source_change)
        self._dispatch()

    async def async_shutdown(self) -> None:
        for func in (self._unsub_reset,self._unsub_pace,self._unsub_source):
            if func:
                func()
        async with self._lock:
            await self._save()

    @callback
    def _scheduled_reset(self, _now: datetime) -> None:
        self.hass.async_create_task(self.async_maybe_reset())

    @callback
    def _tick(self, _now: datetime) -> None:
        self._dispatch()

    async def async_maybe_reset(self) -> None:
        async with self._lock:
            if self.last_reset_date == self._today():
                return
            self._rolled()
            await self._save()
            self._dispatch()

    async def async_add_drink(self, amount: float, unit: str = 'mL', origin: str = 'service') -> dict:
        amount_ml = safe_amount(amount, unit)
        async with self._lock:
            self._rolled()
            before = self.consumed_ml
            self.manual_consumed_ml += amount_ml
            if self.source_mode == 'sum':
                self.consumed_ml = self.manual_consumed_ml + self.source_contribution_ml
            else:
                self.consumed_ml += amount_ml
            record = self._entry('drink',origin,before,amount_ml,float(amount),unit)
            self.records.append(record)
            await self._save()
            self._dispatch()
            return record

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
        return [dict(id=r['id'],timestamp=r['timestamp'],volume_ml=r['volume_ml'],origin=r['origin'])
                for r in self.records if r['kind']=='drink' and r['timestamp'][:10]==day]

    def export_snapshot(self) -> dict:
        cfg = {key: getattr(self,key) for key in ('name','age','gender','pregnancy','lactation','source_sensor','source_mode','unit')}
        cfg['day_start']=self.day_start.isoformat()
        cfg['day_end']=self.day_end.isoformat()
        return dict(entry_id=self.entry_id,slug=self.slug,config=cfg,date=self.last_reset_date,
                    consumed_ml=self.consumed_ml,manual_consumed_ml=self.manual_consumed_ml,
                    target_ml=self.target_ml,source_contribution_ml=self.source_contribution_ml,
                    records=[dict(r) for r in self.records],source_readings=[dict(r) for r in self.source_readings],
                    daily_archive={key:dict(val) for key,val in self.daily_archive.items()})
