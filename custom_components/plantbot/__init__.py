from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.discovery import async_load_platform

import logging
_LOGGER = logging.getLogger(__name__)
_LOGGER.info("PlantBot setup_entry läuft...")

DOMAIN = "plantbot"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["server_url"] = entry.data["server_url"]

    await hass.config_entries.async_forward_entry_setups(entry, ["valve"])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Entfernt alle Komponenten dieser Config-Entry."""
    return await hass.config_entries.async_unload_platforms(entry, ["valve"])

