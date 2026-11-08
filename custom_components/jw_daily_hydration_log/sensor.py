"""Per-person hydration sensors; unique IDs deliberately distinct from PHM."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, ENTITY_PREFIX, from_ml

async def async_setup_entry(hass, entry, async_add_entities):
    c = hass.data[DOMAIN]['profiles'][entry.entry_id]
    async_add_entities([DailyTarget(c), ConsumedToday(c), ManualConsumed(c), Remaining(c), Progress(c), DrinkCount(c)])

class _Sensor(SensorEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True
    def __init__(self, coordinator, key, name):
        self.coordinator=coordinator
        self._attr_unique_id=f'{coordinator.entry_id}_{key}'
        self._attr_name=name
        self.entity_id=f'sensor.{ENTITY_PREFIX}_{coordinator.slug}_{key}'
        self._attr_device_info=DeviceInfo(identifiers={(DOMAIN,coordinator.entry_id)},name=coordinator.name,
                                          manufacturer='jwDaily Hydration Log Contributors',model='jwDaily Hydration Log')

    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(self.hass,self.coordinator.signal,self._refresh))

    @callback
    def _refresh(self):
        self.async_write_ha_state()

class _Volume(_Sensor):
    @property
    def native_unit_of_measurement(self):
        return 'fl oz' if self.coordinator.unit=='fl_oz' else self.coordinator.unit

    def volume(self, v):
        return round(from_ml(v,self.coordinator.unit),2)

class DailyTarget(_Volume):
    _attr_icon='mdi:target'
    _attr_state_class=SensorStateClass.TOTAL
    def __init__(self,c):super().__init__(c,'daily_target','Daily target')
    @property
    def native_value(self):return self.volume(self.coordinator.target_ml)
    @property
    def extra_state_attributes(self):return {'target_ml':self.coordinator.target_ml}

class ConsumedToday(_Volume):
    _attr_icon='mdi:cup-water'
    _attr_state_class=SensorStateClass.TOTAL_INCREASING
    def __init__(self,c):super().__init__(c,'consumed_today','Consumed today')
    @property
    def native_value(self):return self.volume(self.coordinator.consumed_ml)
    @property
    def extra_state_attributes(self):return {'consumed_ml':round(self.coordinator.consumed_ml,2)}

class ManualConsumed(_Volume):
    _attr_icon='mdi:water-plus'
    _attr_state_class=SensorStateClass.TOTAL_INCREASING
    def __init__(self,c):super().__init__(c,'manual_consumed','Manual consumed')
    @property
    def native_value(self):return self.volume(self.coordinator.manual_consumed_ml)
    @property
    def extra_state_attributes(self):return {'manual_consumed_ml':round(self.coordinator.manual_consumed_ml,2)}

class Remaining(_Volume):
    _attr_icon='mdi:cup-outline'
    def __init__(self,c):super().__init__(c,'remaining','Remaining')
    @property
    def native_value(self):return self.volume(self.coordinator.remaining_ml)

class Progress(_Sensor):
    _attr_icon='mdi:chart-donut'
    _attr_native_unit_of_measurement=PERCENTAGE
    _attr_state_class=SensorStateClass.MEASUREMENT
    def __init__(self,c):super().__init__(c,'progress','Progress')
    @property
    def native_value(self):return self.coordinator.progress_percent

class DrinkCount(_Sensor):
    _attr_icon='mdi:counter'
    _attr_state_class=SensorStateClass.MEASUREMENT
    def __init__(self,c):super().__init__(c,'drink_count_today','Drink moments today')
    @property
    def native_value(self):return len(self.coordinator.get_history())
