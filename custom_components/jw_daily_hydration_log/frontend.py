"""Register one Lovelace module loader, isolated from upstream PHM."""
from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_when_setup
from .const import DOMAIN,VERSION

_LOGGER=logging.getLogger(__name__)
BASE=f'/{DOMAIN}_static'
CARD_FILE='jwdaily-hydration-log-card.js'
URL=f'{BASE}/{CARD_FILE}'
LEGACY_CARD_URL=f'{BASE}/jw-daily-hydration-log-card.js'  # v1.0.1 only
VERSIONED=f'{URL}?v={VERSION}'

async def async_register_frontend(hass:HomeAssistant)->None:
    directory=Path(__file__).parent/'www'
    if not (directory/CARD_FILE).is_file():
        _LOGGER.error('jwDaily Hydration Log card missing: %s', directory/CARD_FILE)
        return
    static_key=f'{DOMAIN}_static_registered'
    if not hass.data.get(static_key):
        try:
            await hass.http.async_register_static_paths([StaticPathConfig(BASE,str(directory),cache_headers=False)])
        except RuntimeError:
            pass
        hass.data[static_key]=True
    if hass.data.get('lovelace') is not None:
        await _register_loader(hass)
    elif not hass.data.get(f'{DOMAIN}_waiting_lovelace'):
        hass.data[f'{DOMAIN}_waiting_lovelace']=True
        async def ready(_hass,_component):
            _hass.data.pop(f'{DOMAIN}_waiting_lovelace',None)
            await _register_loader(_hass)
        async_when_setup(hass,'lovelace',ready)

async def _register_loader(hass:HomeAssistant)->None:
    lovelace=hass.data.get('lovelace')
    resources=getattr(lovelace,'resources',None)
    if resources is None or not hasattr(resources,'async_create_item'):
        key=f'{DOMAIN}_extra_loader'
        if not hass.data.get(key):
            add_extra_js_url(hass,VERSIONED)
            hass.data[key]=True
        return
    lock=hass.data.setdefault(f'{DOMAIN}_frontend_lock',asyncio.Lock())
    async with lock:
        try:
            if hasattr(resources,'async_load') and not getattr(resources,'loaded',True):
                await resources.async_load()
            existing=[item for item in resources.async_items()
                      if item.get('url','').split('?',1)[0] in (URL, LEGACY_CARD_URL)]
            payload={'res_type':'module','url':VERSIONED}
            if not existing:
                await resources.async_create_item(payload)
            else:
                primary,*duplicates=existing
                if primary.get('url')!=VERSIONED or primary.get('res_type')!='module':
                    await resources.async_update_item(primary['id'],payload)
                for duplicate in duplicates:
                    await resources.async_delete_item(duplicate['id'])
        except Exception as exc:
            _LOGGER.warning('Could not register jwDaily Hydration Log card resource: %s',exc)
