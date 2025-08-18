import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN
from .coordinator import PlantbotCoordinator
from .valve import ENTITIES

import asyncio

PLATFORMS = ["valve", "sensor","update","button"]
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    coordinator = PlantbotCoordinator(hass, entry.data["server"])
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    hass.services.async_register(DOMAIN, "open_for_seconds", handle_open_for_seconds)
    hass.services.async_register(DOMAIN, "open_for_volume", handle_open_for_volume)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def handle_open_for_seconds(call):
    valve_id = call.data["valve"]
    duration = call.data["duration"]
    entity = ENTITIES.get(valve_id)
    #_LOGGER.debug("Alle registrierten Plantbot-Ventile:\n%s", "\n".join(ENTITIES.keys()))
    if entity:
        _LOGGER.debug("Komponente gefunden %s", entity.valve_id)
        await entity.open_for_seconds(duration)
    else:
        _LOGGER.error("Komponente nicht gefunden %s ",valve_id)

async def handle_open_for_volume(call):
    valve_id = call.data["valve"]
    volume = call.data["volume"]
    entity = ENTITIES.get(valve_id)
    #_LOGGER.debug("Alle registrierten Plantbot-Ventile:\n%s", "\n".join(ENTITIES.keys()))
    if entity:
        _LOGGER.debug("Komponente gefunden %s", entity.valve_id)
        await entity.open_for_volume(volume)
    else:
        _LOGGER.error("Komponente nicht gefunden %s ",valve_id)