"""jwDaily Hydration Log, standalone integration with XLSX export."""
from __future__ import annotations

import base64
import json
import hashlib
import logging
import math
from copy import deepcopy
from homeassistant.helpers.storage import Store
from .settings_io import (FORMAT as SETTINGS_FORMAT, export_payload, parse_settings_json,
                          validate_payload, settings_preview, extract, digest, canonical)
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
from .excel import export_xlsx, export_filename
from .frontend import async_register_frontend

_LOGGER=logging.getLogger(__name__)

CONFIG_SCHEMA=cv.config_entry_only_config_schema(DOMAIN)

_DRINK_SCHEMA=vol.Schema({vol.Required('profile'):cv.string,vol.Required('volume'):vol.Coerce(float),
                           vol.Optional('unit',default='mL'):vol.In(UNITS),
                           vol.Optional('origin',default='service'):cv.string,
                           vol.Required('liquid_type'):cv.string,
                           vol.Optional('date'):cv.string,vol.Optional('time'):cv.string,
                           vol.Optional('cup_type_id'):cv.string,vol.Optional('quick_button_id'):cv.string})
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
                                    call.data['liquid_type'],call.data.get('date'),call.data.get('time'),
                                    call.data.get('cup_type_id'),call.data.get('quick_button_id'))
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
    websocket_api.async_register_command(hass,ws_manage_cup)
    websocket_api.async_register_command(hass,ws_manage_quick)
    websocket_api.async_register_command(hass,ws_legacy_preview)
    websocket_api.async_register_command(hass,ws_migration_backup)
    websocket_api.async_register_command(hass,ws_legacy_mapping)
    websocket_api.async_register_command(hass,ws_set_target)
    websocket_api.async_register_command(hass,ws_settings_export)
    websocket_api.async_register_command(hass,ws_settings_preview)
    websocket_api.async_register_command(hass,ws_settings_apply)
    websocket_api.async_register_command(hass,ws_conversion_preview)
    websocket_api.async_register_command(hass,ws_conversion_apply)
    websocket_api.async_register_command(hass,ws_profiles_list)
    websocket_api.async_register_command(hass,ws_profile_edit)
    websocket_api.async_register_command(hass,ws_profile_create)
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
                                      'edit_drink':True,'custom_liquid_types':True,'builtin_liquid_visibility':True,
                                      'cup_types':True,'quick_buttons':True,'legacy_mapping':True,'central_settings':True,
                                      'settings_transfer':True,'conversion_wizard':True,'profile_management':True})


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
        'cup_types':c.get_cup_types(), 'quick_buttons':c.get_quick_buttons(),
        'profile_settings':dict(name=c.name,age=c.age,gender=c.gender,unit=c.unit,
                                source_mode=c.source_mode),
        'migration_active':bool(c.legacy_mappings),
        'conversion_applied':bool(c.conversion_state.get('applied')), 
        'backend_version':VERSION,
    })


@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/add_drink',
                                  probatio.Required('profile'):str,
                                  probatio.Required('volume_ml'):float,
                                  probatio.Required('liquid_type'):str,
                                  probatio.Optional('date'):str,
                                  probatio.Optional('time'):str,
                                  probatio.Optional('cup_type_id'):str,
                                  probatio.Optional('quick_button_id'):str})
@websocket_api.async_response
async def ws_add_drink(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    """Add a new drink and return the saved ID so Undo never guesses."""
    try:
        c=_resolve(hass,msg['profile'])
        saved=await c.async_add_drink(msg['volume_ml'],'mL','dashboard',msg['liquid_type'],
                                      msg.get('date'),msg.get('time'),
                                      msg.get('cup_type_id'),msg.get('quick_button_id'))
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
                                  probatio.Required('time'):str,
                                  probatio.Optional('cup_type_id'):str,
                                  probatio.Optional('quick_button_id'):str})
@websocket_api.async_response
async def ws_edit_drink(hass:HomeAssistant, connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        c=_resolve(hass,msg['profile'])
        updated=await c.async_edit_drink(msg['record_id'],msg['volume_ml'],
                                         msg['liquid_type'],msg['date'],msg['time'],
                                         msg.get('cup_type_id'),msg.get('quick_button_id'))
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
                                  probatio.Optional('default_volume_ml'):float,
                                  probatio.Optional('color'):str})
@websocket_api.async_response
async def ws_add_liquid_type(hass:HomeAssistant, connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        c=_resolve(hass,msg['profile'])
        item=await c.async_add_liquid_type(msg['name'],msg.get('icon_mdi',''),
                                           msg.get('icon_svg',''),msg.get('default_volume_ml'),msg.get('color',''))
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
                                  probatio.Optional('default_volume_ml'):float,
                                  probatio.Optional('color'):str})
@websocket_api.async_response
async def ws_update_liquid_type(hass:HomeAssistant,connection:websocket_api.ActiveConnection,msg:dict)->None:
    try:
        item=await _resolve(hass,msg['profile']).async_update_liquid_type(
            msg['liquid_type'],msg['name'],msg.get('icon_mdi',''),
            msg.get('icon_svg',''),msg.get('default_volume_ml'),msg.get('color'))
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


# Central-settings APIs: all changes remain admin-gated, profile scoped and validated.
@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/manage_cup',
                                  probatio.Required('profile'):str,
                                  probatio.Required('action'):str,
                                  probatio.Optional('cup_id'):str,
                                  probatio.Optional('name'):str,
                                  probatio.Optional('volume_ml'):float,
                                  probatio.Optional('icon_mdi'):str,
                                  probatio.Optional('order'):[str]})
@websocket_api.async_response
async def ws_manage_cup(hass, connection, msg):
    try:
        c=_resolve(hass,msg['profile'])
        result=await c.async_manage_cup(msg['action'],msg.get('cup_id',''),msg.get('name',''),
                                        msg.get('volume_ml'),msg.get('icon_mdi',''),msg.get('order'))
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_cup',str(exc));return
    connection.send_result(msg['id'],{'cup_types':result})


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/manage_quick',
                                  probatio.Required('profile'):str,
                                  probatio.Required('action'):str,
                                  probatio.Optional('quick_id'):str,
                                  probatio.Optional('liquid_type_id'):str,
                                  probatio.Optional('cup_type_id'):str,
                                  probatio.Optional('label_mode'):str,
                                  probatio.Optional('custom_label'):str,
                                  probatio.Optional('order'):[str]})
@websocket_api.async_response
async def ws_manage_quick(hass, connection, msg):
    try:
        c=_resolve(hass,msg['profile'])
        result=await c.async_manage_quick(msg['action'],msg.get('quick_id',''),
                                          msg.get('liquid_type_id',''),msg.get('cup_type_id',''),
                                          msg.get('label_mode','automatic'),msg.get('custom_label',''),
                                          msg.get('order'))
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_quick',str(exc));return
    connection.send_result(msg['id'],{'quick_buttons':result})


@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/migration_preview',
                                  probatio.Required('profile'):str})
@callback
def ws_legacy_preview(hass, connection, msg):
    try:
        result=_resolve(hass,msg['profile']).migration_preview()
    except ServiceValidationError as exc:
        connection.send_error(msg['id'],'not_found',str(exc));return
    connection.send_result(msg['id'],result)


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/migration_backup',
                                  probatio.Required('profile'):str})
@websocket_api.async_response
async def ws_migration_backup(hass, connection, msg):
    """Return the unmodified persisted profile store for a user-held rollback.

    This is a read-only operation. It deliberately does not write any HA file,
    change the Store schema, or silently enable a migration.
    """
    try:
        c=_resolve(hass,msg['profile'])
        saved=await c._store.async_load()
        if not isinstance(saved,dict):
            raise ValueError('No stored profile snapshot to back up')
        data=json.dumps(saved,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        digest=hashlib.sha256(data).hexdigest()
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'backup_error',str(exc));return
    connection.send_result(msg['id'],{
        'filename':f'jwDaily Hydration Log {c.slug} pre-beta28-conversion.json',
        'base64':base64.b64encode(data).decode('ascii'),
        'sha256':digest,'bytes':len(data),'version':VERSION})


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/legacy_mapping',
                                  probatio.Required('profile'):str,
                                  probatio.Required('action'):str,
                                  probatio.Required('legacy_id'):str,
                                  probatio.Optional('liquid_type_id'):str,
                                  probatio.Optional('cup_type_id'):str})
@websocket_api.async_response
async def ws_legacy_mapping(hass, connection, msg):
    try:
        c=_resolve(hass,msg['profile'])
        if msg['action']=='apply':
            result=await c.async_set_legacy_mapping(msg['legacy_id'],msg.get('liquid_type_id',''),msg.get('cup_type_id',''))
        elif msg['action']=='clear':
            result=await c.async_clear_legacy_mapping(msg['legacy_id'])
        else:
            raise ValueError('Unknown legacy mapping action')
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_mapping',str(exc));return
    connection.send_result(msg['id'],result)


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/set_target',
                                  probatio.Required('profile'):str,
                                  probatio.Required('target_ml'):float})
@websocket_api.async_response
async def ws_set_target(hass, connection, msg):
    try:
        c=_resolve(hass,msg['profile'])
        target=float(msg['target_ml'])
        if not math.isfinite(target) or target<0 or target>100000:
            raise ValueError('Daily target must be 0 (automatic) or at most 100000 mL')
        await c.async_set_target(target)
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'invalid_target',str(exc));return
    connection.send_result(msg['id'],{'target_ml':c.target_ml,'target_override_ml':c.target_override_ml})



# Settings export excludes history, manual totals, source readings and entity IDs.
@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/settings_export',
                                  probatio.Required('profile'):str})
@websocket_api.async_response
async def ws_settings_export(hass, connection, msg):
    try:
        c=_resolve(hass,msg['profile']);raw=canonical(export_payload(c))
        connection.send_result(msg['id'], dict(filename=f'jwDaily Hydration Log {c.slug} Settings.json',
            base64=base64.b64encode(raw).decode('ascii'),size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
            schema=1,profile=c.name,revision=c.settings_revision()))
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'settings_export_failed',str(exc))


def _settings_candidate(c,content,with_mappings=False):
    payload=parse_settings_json(content)
    history_ids={str(r.get('liquid_type') or 'unknown') for r in c.records if r.get('kind')=='drink'}
    if with_mappings and (payload.get('source_profile') or {}).get('slug') != c.slug:
        raise ValueError('Historical mappings can only be restored to their original profile')
    cleaned=validate_payload(payload,existing_legacy_ids=history_ids,include_mappings=with_mappings)
    return cleaned, payload


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/settings_import_preview',
                                  probatio.Required('profile'):str,
                                  probatio.Required('content'):str,
                                  probatio.Optional('include_mappings'):bool})
@callback
def ws_settings_preview(hass, connection, msg):
    try:
        c=_resolve(hass,msg['profile'])
        source=parse_settings_json(msg['content'])
        include=bool(msg.get('include_mappings',(source.get('source_profile') or {}).get('slug')==c.slug))
        new, payload=_settings_candidate(c,msg['content'],include)
        preview=settings_preview(c,new)
        preview.update(source_profile=(payload.get('source_profile') or {}).get('name','Unknown'),
                       import_sha256=digest(new),exclude_history=True,
                       include_mappings=include)
        connection.send_result(msg['id'],preview)
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'settings_validation_failed',str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/settings_import_apply',
                                  probatio.Required('profile'):str,
                                  probatio.Required('content'):str,
                                  probatio.Required('expected_revision'):str,
                                  probatio.Required('import_sha256'):str,
                                  probatio.Required('confirm'):bool,
                                  probatio.Optional('include_mappings'):bool})
@websocket_api.async_response
async def ws_settings_apply(hass, connection, msg):
    try:
        if msg['confirm'] is not True:raise ValueError('Explicit confirmation required')
        c=_resolve(hass,msg['profile'])
        source=parse_settings_json(msg['content'])
        include=bool(msg.get('include_mappings',(source.get('source_profile') or {}).get('slug')==c.slug))
        new,_=_settings_candidate(c,msg['content'],include)
        if digest(new)!=msg['import_sha256']:raise ValueError('Import contents changed after preview')
        result=await c.async_import_settings(new,msg['expected_revision'],include)
        connection.send_result(msg['id'],dict(applied=True,**result))
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'settings_import_failed',str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/conversion_preview',
                                  probatio.Required('profile'):str})
@callback
def ws_conversion_preview(hass, connection, msg):
    try:connection.send_result(msg['id'],_resolve(hass,msg['profile']).conversion_preview())
    except ServiceValidationError as exc:connection.send_error(msg['id'],'not_found',str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/conversion_apply',
                                  probatio.Required('profile'):str,
                                  probatio.Required('plan'):dict,
                                  probatio.Required('expected_revision'):str,
                                  probatio.Required('confirm'):bool})
@websocket_api.async_response
async def ws_conversion_apply(hass, connection, msg):
    try:
        if msg['confirm'] is not True:raise ValueError('Explicit confirmation required')
        result=await _resolve(hass,msg['profile']).async_apply_conversion(msg['plan'],msg['expected_revision'])
        connection.send_result(msg['id'],result)
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'conversion_failed',str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/profiles_list'})
@callback
def ws_profiles_list(hass, connection, msg):
    connection.send_result(msg['id'],{'profiles':[dict(entry_id=c.entry_id,slug=c.slug,
            name=c.name,age=c.age,gender=c.gender,unit=c.unit,
            pregnancy=c.pregnancy,lactation=c.lactation,
            source_sensor=c.source_sensor or '',source_mode=c.source_mode,
            daily_target_ml=c.target_ml) for c in _profiles(hass).values()]})


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/profile_edit',
                                  probatio.Required('profile'):str,
                                  probatio.Required('name'):str,
                                  probatio.Required('age'):int,
                                  probatio.Required('gender'):str,
                                  probatio.Required('unit'):str,
                                  probatio.Optional('pregnancy'):bool,
                                  probatio.Optional('lactation'):bool,
                                  probatio.Optional('source_sensor'):str,
                                  probatio.Optional('source_mode'):str})
@websocket_api.async_response
async def ws_profile_edit(hass, connection, msg):
    try:
        c=_resolve(hass,msg['profile'])
        if not 1<=msg['age']<=120 or msg['gender'] not in ('male','female') or msg['unit'] not in UNITS:
            raise ValueError('Invalid age, gender or measurement unit')
        mode=msg.get('source_mode',c.source_mode)
        if mode not in ('absolute','delta','sum'):raise ValueError('Invalid source mode')
        name=c._catalog_name(msg['name'],'Profile name')
        await c.async_set_display_name(name)
        old={**c.entry.data,**c.entry.options}
        opts={**c.entry.options,**{key:msg[key] for key in
            ('age','gender','unit','pregnancy','lactation','source_sensor') if key in msg},
            'source_mode':mode}
        if any(old.get(k)!=v for k,v in opts.items()):
            hass.config_entries.async_update_entry(c.entry,options=opts,title=name)
        else:
            hass.config_entries.async_update_entry(c.entry,title=name)
        connection.send_result(msg['id'],dict(updated=True,name=name,slug=c.slug,
                                                stable_entry_id=c.entry_id))
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'profile_edit_failed',str(exc))


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required('type'):f'{DOMAIN}/profile_create',
                                  probatio.Required('name'):str,
                                  probatio.Required('age'):int,
                                  probatio.Required('gender'):str,
                                  probatio.Required('unit'):str,
                                  probatio.Optional('copy_from'):str,
                                  probatio.Optional('pregnancy'):bool,
                                  probatio.Optional('lactation'):bool})
@websocket_api.async_response
async def ws_profile_create(hass, connection, msg):
    try:
        name=msg['name'].strip()
        slug=slugify(name)
        if not name or len(name)>48 or not slug or any(c.slug==slug for c in _profiles(hass).values()):
            raise ValueError('Invalid or duplicate profile name')
        if not 1<=msg['age']<=120 or msg['gender'] not in ('male','female') or msg['unit'] not in UNITS:
            raise ValueError('Invalid profile age, gender or unit')
        template=_resolve(hass,msg['copy_from']) if msg.get('copy_from') else None
        data=dict(name=name,age=msg['age'],gender=msg['gender'],unit=msg['unit'],
                  pregnancy=bool(msg.get('pregnancy',False)),lactation=bool(msg.get('lactation',False)),
                  source_mode='absolute')
        # Home Assistant's native config flow owns config-entry registration.
        result=await hass.config_entries.flow.async_init(DOMAIN,
                    context={'source':'user'},data=data)
        if result.get('type')!='create_entry' or not result.get('result'):
            raise ValueError('Could not create profile through Home Assistant config flow')
        entry=result['result']
        if template:
            settings=extract(template)
            mapped_legacy_ids=set(settings['legacy_mappings'])
            settings['legacy_mappings']={}  # Never copy historic aliases between people.
            settings['legacy_cup_defaults']={}
            settings['conversion_state']={}
            # Exclude old alias-only custom liquids; the new profile has no
            # legacy drink history for which those IDs would be meaningful.
            settings['custom_liquid_types']=[item for item in settings['custom_liquid_types']
                                             if item['id'] not in mapped_legacy_ids]
            settings['liquid_colors']={key:value for key,value in settings['liquid_colors'].items()
                                       if key not in mapped_legacy_ids}
            settings['liquid_order']=[key for key in settings['liquid_order']
                                      if key not in mapped_legacy_ids]
            settings['quick_buttons']=[item for item in settings['quick_buttons']
                                        if item['liquid_type_id'] not in mapped_legacy_ids]
            # A fresh profile has no history; each profile owns its own settings copy.
            store=Store(hass,1,f'{DOMAIN}.{entry.entry_id}')
            current=await store.async_load() or {}
            if current.get('records') or current.get('source_readings'):
                raise ValueError('New profile already contains observations; not copying settings')
            current.update(deepcopy(settings))
            current['target_override_ml']=0.0  # Personal target never copied.
            await store.async_save(current)
            # Load the copied setup if the new entry was already initialized.
            if entry.entry_id in _profiles(hass):
                await hass.config_entries.async_reload(entry.entry_id)
        connection.send_result(msg['id'],dict(created=True,slug=slug,
            entry_id=entry.entry_id,copied_settings=bool(template),history_copied=False))
    except (ValueError,ServiceValidationError) as exc:
        connection.send_error(msg['id'],'profile_create_failed',str(exc))


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
    connection.send_result(msg['id'],{'filename':export_filename(hass.config.time_zone),
                                      'mime_type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                      'base64':base64.b64encode(workbook).decode('ascii'),
                                      'bytes':len(workbook), 'version':VERSION})
