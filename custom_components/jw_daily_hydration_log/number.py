"""Editable daily target override, isolated from upstream."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN, ENTITY_PREFIX, from_ml, to_ml

async def async_setup_entry(hass,entry,async_add_entities):
    async_add_entities([TargetOverride(hass.data[DOMAIN]['profiles'][entry.entry_id])])

class TargetOverride(NumberEntity):
    _attr_has_entity_name=True
    _attr_name='Target override'
    _attr_icon='mdi:tune-vertical'
    _attr_mode=NumberMode.BOX
    def __init__(self,c):
        self.c=c
        self._attr_unique_id=f'{c.entry_id}_target_override'
        self.entity_id=f'number.{ENTITY_PREFIX}_{c.slug}_target_override'
        self._attr_device_info=DeviceInfo(identifiers={(DOMAIN,c.entry_id)},name=c.name,
                                          manufacturer='jwDaily Hydration Log Contributors',model='jwDaily Hydration Log')
    @property
    def native_unit_of_measurement(self):return 'fl oz' if self.c.unit=='fl_oz' else self.c.unit
    @property
    def native_min_value(self):return 0
    @property
    def native_max_value(self):return round(from_ml(10000,self.c.unit),2)
    @property
    def native_step(self):return 0.01 if self.c.unit!='mL' else 1
    @property
    def native_value(self):return round(from_ml(self.c.target_override_ml,self.c.unit),2)
    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(self.hass,self.c.signal,self._refresh))
    @callback
    def _refresh(self):self.async_write_ha_state()
    async def async_set_native_value(self,value):await self.c.async_set_target(to_ml(float(value),self.c.unit))
