"""jwDaily Hydration Log, standalone integration with XLSX export."""
from __future__ import annotations

import base64
import logging
import math
import voluptuous as vol
import probatio
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.components import websocket_api
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import slugify

from .const import DOMAIN, EVENT_DRINK, PLATFORMS, UNITS, LIQUID_TYPES, VERSION
from .coordinator import HydrationCoordinator
from .excel import export_xlsx
from .frontend import async_register_frontend

_LOGGER=logging.getLogger(__name__)

CONFIG_SCHEMA=cv.config_entry_only_config_schema(DOMAIN)

_DRINK_SCHEMA=vol.Schema({vol.Required('profile'):cv.string,vol.Required('volume'):vol.Coerce(float),
                           vol.Optional('unit',default='mL'):vol.In(UNITS),
                           vol.Optional('origin',default='service'):cv.string,
                           vol.Required('liquid_type'):cv.string,
                           vol.Optional('date'):cv.string,vol.Optional('time'):cv.string})
_RESET_SCHEMA=vol.Schema({vol.Required('profile'):cv.string})
_SET_SCHEMA=vol.Schema({vol.Required('profile'):cv.string,vol.Required('volume'):vol.Coerce(float),
                        vol.Optional('unit',default='mL'):vol.In(UNITS)})


def _profiles(hass):
    return hass.data.get(DOMAIN,{}).get('profiles',{})


def _resolve(hass, profile):
    profiles=_profiles(hass)
    if profile in profiles:
        return profiles[profile]
    wanted=slugify(profile)
    for coordinator in profiles.values():
        if coordinator.slug == wanted:
            return coordinator
    raise ServiceValidationError(f'Unknown jwDaily Hydration Log profile: {profile}')


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN,{'profiles':{}})
    await async_register_frontend(hass)

    async def log_drink(call):
        c=_resolve(hass,call.data['profile'])
        try:
            await c.async_add_drink(call.data['volume'],call.data['unit'],call.data.get('origin','service'),
                                    call.data['liquid_type'],call.data.get('date'),call.data.get('time'))
        except ValueError as exc:
            raise ServiceValidationError(str(exc)) from exc

    async def reset_today(call):
        await _resolve(hass,call.data['profile']).async_reset_today()

    async def set_consumed(call):
        c=_resolve(hass,call.data['profile'])
        try:
            await c.async_set_consumed(call.data['volume'],call.data['unit'])
        except ValueError as exc:
            raise ServiceValidationError(str(exc)) from exc

    hass.services.async_register(DOMAIN,'log_drink',log_drink,schema=_DRINK_SCHEMA)
    hass.services.async_register(DOMAIN,'reset_today',reset_today,schema=_RESET_SCHEMA)
    hass.services.async_register(DOMAIN,'set_consumed',set_consumed,schema=_SET_SCHEMA)

    @callback
    def on_drink_event(event):
        try:
            c=_resolve(hass,str(event.data['profile']))
            volume=float(event.data['volume'])
            unit=event.data.get('unit','mL')
            if not math.isfinite(volume):
                raise ValueError('Invalid volume')
        except (ValueError,KeyError,ServiceValidationError) as exc:
            _LOGGER.warning('Invalid drink event ignored: %s',exc)
            return
        liquid_type=event.data.get('liquid_type')
        if not c._valid_liquid_type(liquid_type):
            _LOGGER.warning('Drink event ignored: valid liquid_type is required')
            return
        hass.async_create_task(c.async_add_drink(volume,unit,'event',liquid_type))

    hass.bus.async_listen(EVENT_DRINK,on_drink_event)
    websocket_api.async_register_command(hass,ws_capabilities)
    websocket_api.async_register_command(hass,ws_add_drink)
    websocket_api.async_register_command(hass,ws_edit_drink)
    websocket_api.async_register_command(hass,ws_delete_drink)
    websocket_api.async_register_command(hass,ws_history)
    websocket_api.async_register_command(hass,ws_add_liquid_type)
    websocket_api.async_register_command(hass,ws_delete_liquid_type)
    websocket_api.async_register_command(hass,ws_update_liquid_type)
    websocket_api.async_register_command(hass,ws_set_builtin_liquid_visibility)
    websocket_api.async_register_command(hass,ws_set_liquid_order)
    websocket_api.async_register_command(hass,ws_set_volume_buttons)
    websocket_api.async_register_command(hass,ws_export)
    return True


async def async_setup_entry(hass:HomeAssistant,entry:ConfigEntry)->bool:
    await async_register_frontend(hass)
    c=HydrationCoordinator(hass,entry)
    await c.async_initialize()
    _profiles(hass)[entry.entry_id]=c
    # Retire only the old v1.0.2 pace entity for this exact config entry.
    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(hass)
    obsolete = registry.async_get_entity_id('sensor', DOMAIN, f'{entry.entry_id}_hourly_pace')
    if obsolete:
        registry.async_remove(obsolete)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass:HomeAssistant,entry:ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass:HomeAssistant,entry:ConfigEntry)->bool:
    ok=await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        coordinator=_profiles(hass).pop(entry.entry_id,None)
        if coordinator:
            await coordinator.async_shutdown()
    return ok


@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/capabilities'})
@callback
def ws_capabilities(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    """Confirm that the Python backend matches the frontend before any write."""
    connection.send_result(msg['id'],{'version':VERSION,'add_drink':True,
                                      'edit_drink':True,'custom_liquid_types':True,'builtin_liquid_visibility':True})


@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/history',probatio.Required('profile'):str,
                                  probatio.Optional('date'):str})
@callback
def ws_history(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    """History is for authenticated HA users; none is published in sensor attrs."""
    try:
        c=_resolve(hass,msg['profile'])
    except ServiceValidationError as exc:
        connection.send_error(msg['id'],'not_found',str(exc))
        return
    day=msg.get('date') or c._today()
    try:
        summary=c.day_summary(day)
    except ValueError as exc:
        connection.send_error(msg['id'],'invalid_date',str(exc))
        return
    records=c.get_history(day)
    connection.send_result(msg['id'],{
        'profile':c.slug,'date':day, 'entries':records,
        'day_summary':summary,
        'count':len(records),'total_ml':round(sum(x['volume_ml'] for x in records),2),
        'consumed_ml':round(c.consumed_ml,2),'target_ml':c.target_ml,
        'liquid_types':c.get_liquid_definitions(),
        'volume_buttons':None if c.volume_buttons is None else list(c.volume_buttons),
        'today_breakdown':c.today_breakdown(),
        'backend_version':VERSION,
    })


@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/add_drink',
                                  probatio.Required('profile'):str,
                                  probatio.Required('volume_ml'):float,
                                  probatio.Required('liquid_type'):str,
                                  probatio.Optional('date'):str,
                                  probatio.Optional('time'):str})
@websocket_api.async_response
async def ws_add_drink(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    """Add a new drink and return the saved ID so Undo never guesses."""
    try:
        c=_resolve(hass,msg['profile'])
        saved=await c.async_add_drink(msg['volume_ml'],'mL','dashboard',msg['liquid_type'],
                                      msg.get('date'),msg.get('time'))
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_drink',str(exc))
        return
    connection.send_result(msg['id'],{'record_id':saved['id']})


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/edit_drink',
                                  probatio.Required('profile'):str,
                                  probatio.Required('record_id'):str,
                                  probatio.Required('volume_ml'):float,
                                  probatio.Required('liquid_type'):str,
                                  probatio.Required('date'):str,
                                  probatio.Required('time'):str})
@websocket_api.async_response
async def ws_edit_drink(hass:HomeAssistant, connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        c=_resolve(hass,msg['profile'])
        updated=await c.async_edit_drink(msg['record_id'],msg['volume_ml'],
                                         msg['liquid_type'],msg['date'],msg['time'])
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_drink',str(exc))
        return
    connection.send_result(msg['id'],{'id':updated['id'],'saved':True})


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/delete_drink',
                                  probatio.Required('profile'):str,
                                  probatio.Required('record_id'):str})
@websocket_api.async_response
async def ws_delete_drink(hass:HomeAssistant, connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        c=_resolve(hass,msg['profile'])
        await c.async_delete_drink(msg['record_id'])
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_drink',str(exc))
        return
    connection.send_result(msg['id'],{'deleted':True})



@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/add_liquid_type',
                                  probatio.Required('profile'):str,
                                  probatio.Required('name'):str,
                                  probatio.Optional('icon_mdi'):str,
                                  probatio.Optional('icon_svg'):str,
                                  probatio.Optional('default_volume_ml'):float})
@websocket_api.async_response
async def ws_add_liquid_type(hass:HomeAssistant, connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        c=_resolve(hass,msg['profile'])
        item=await c.async_add_liquid_type(msg['name'],msg.get('icon_mdi',''),
                                           msg.get('icon_svg',''),msg.get('default_volume_ml'))
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_liquid_type',str(exc))
        return
    connection.send_result(msg['id'],item)


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/delete_liquid_type',
                                  probatio.Required('profile'):str,
                                  probatio.Required('liquid_type'):str})
@websocket_api.async_response
async def ws_delete_liquid_type(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        await _resolve(hass,msg['profile']).async_delete_liquid_type(msg['liquid_type'])
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_liquid_type',str(exc))
        return
    connection.send_result(msg['id'],{'deleted':True})

@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/update_liquid_type',
                                  probatio.Required('profile'):str,
                                  probatio.Required('liquid_type'):str,
                                  probatio.Required('name'):str,
                                  probatio.Optional('icon_mdi'):str,
                                  probatio.Optional('icon_svg'):str,
                                  probatio.Optional('default_volume_ml'):float})
@websocket_api.async_response
async def ws_update_liquid_type(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        item=await _resolve(hass,msg['profile']).async_update_liquid_type(
            msg['liquid_type'],msg['name'],msg.get('icon_mdi',''),
            msg.get('icon_svg',''),msg.get('default_volume_ml'))
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_liquid_type',str(exc))
        return
    connection.send_result(msg['id'],item)


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/set_builtin_liquid_visibility',
                                  probatio.Required('profile'):str,
                                  probatio.Required('liquid_type'):str,
                                  probatio.Required('visible'):bool})
@websocket_api.async_response
async def ws_set_builtin_liquid_visibility(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        item=await _resolve(hass,msg['profile']).async_set_builtin_liquid_visibility(
            msg['liquid_type'],msg['visible'])
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_builtin_visibility',str(exc))
        return
    connection.send_result(msg['id'],item)


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/set_liquid_order',
                                  probatio.Required('profile'):str,
                                  probatio.Required('order'):[str]})
@websocket_api.async_response
async def ws_set_liquid_order(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        order=await _resolve(hass,msg['profile']).async_set_liquid_order(msg['order'])
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_liquid_order',str(exc))
        return
    connection.send_result(msg['id'],{'order':order})


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/set_volume_buttons',
                                  probatio.Required('profile'):str,
                                  probatio.Required('volumes'):[float]})
@websocket_api.async_response
async def ws_set_volume_buttons(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        volumes=await _resolve(hass,msg['profile']).async_set_volume_buttons(msg['volumes'])
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_volume_buttons',str(exc))
        return
    connection.send_result(msg['id'],{'volumes':volumes})


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/export',probatio.Optional('profile'):str})
@websocket_api.async_response
async def ws_export(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    """Admin-only complete export as base64 XLSX over the authenticated WS."""
    try:
        selected=[_resolve(hass,msg['profile'])] if msg.get('profile') else list(_profiles(hass).values())
    except ServiceValidationError as exc:
        connection.send_error(msg['id'],'not_found',str(exc))
        return
    snapshots=[c.export_snapshot() for c in selected]
    try:
        workbook=await hass.async_add_executor_job(export_xlsx,snapshots,hass.config.time_zone)
    except Exception:
        _LOGGER.exception('Failed to create hydration Excel workbook')
        connection.send_error(msg['id'],'export_failed','Excel export failed; see Home Assistant logs')
        return
    connection.send_result(msg['id'],{'filename':'jwDaily Hydration Log - All Data.xlsx',
                                      'mime_type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                      'base64':base64.b64encode(workbook).decode('ascii'),
                                      'bytes':len(workbook), 'version':VERSION})
