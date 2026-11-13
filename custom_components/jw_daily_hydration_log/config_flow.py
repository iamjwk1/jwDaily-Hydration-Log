"""UI config and options flow; names are normalized via HA's slugify."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.util import slugify
from homeassistant.core import callback
from .const import DOMAIN, UNITS


def _schema(existing: dict | None = None, with_name: bool = True):
    d=existing or {}
    fields={}
    if with_name:
        fields[vol.Required('name',default=d.get('name',''))]=str
    fields[vol.Required('age',default=d.get('age',30))]=selector.NumberSelector(selector.NumberSelectorConfig(min=1,max=120,step=1,mode='box'))
    fields[vol.Required('gender',default=d.get('gender','male'))]=selector.SelectSelector(selector.SelectSelectorConfig(options=['male','female'],mode='dropdown'))
    fields[vol.Required('unit',default=d.get('unit','mL'))]=selector.SelectSelector(selector.SelectSelectorConfig(options=[selector.SelectOptionDict(value='mL',label='Millilitres (mL)'),selector.SelectOptionDict(value='L',label='Litres (L)'),selector.SelectOptionDict(value='fl_oz',label='Fluid ounces (fl oz)')],mode='dropdown'))
    return vol.Schema(fields)


class DailyHydrationLogConfigFlow(config_entries.ConfigFlow,domain=DOMAIN):
    VERSION=1

    async def async_step_user(self,user_input=None):
        errors={}
        if user_input:
            normalized=slugify(user_input['name'])
            if not normalized:
                errors['name']='invalid_name'
            else:
                await self.async_set_unique_id(normalized)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input['name'],data=user_input)
        return self.async_show_form(step_id='user',data_schema=_schema(),errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return DailyHydrationLogOptionsFlow(config_entry)


class DailyHydrationLogOptionsFlow(config_entries.OptionsFlow):
    def __init__(self,config_entry):
        self._entry=config_entry
    async def async_step_init(self,user_input=None):
        if user_input is not None:
            return self.async_create_entry(title='',data=user_input)
        return self.async_show_form(step_id='init',data_schema=_schema({**self._entry.data,**self._entry.options},with_name=False))
