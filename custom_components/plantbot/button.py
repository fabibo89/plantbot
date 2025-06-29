from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
import aiohttp
import logging

from .const import DOMAIN
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    buttons = []

    for station_id, station in coordinator.data.items():
            station_name = station.get("name", f"Station {station_id}")  # <- Hier zuerst holen
            buttons.append(ResetButton(coordinator,station_name, station_id))

    async_add_entities(buttons, True)


class ResetButton(ButtonEntity):
    def __init__(self, coordinator, station_name,station_id):
        self._coordinator = coordinator
        self.station_id = station_id  
        self.station_name = station_name
        self._attr_name = f"Reset Station {station_id}"
        self._attr_unique_id = f"{coordinator.server_url}_reset_{station_id}"
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_press(self):
        """Send a GET request to the device to trigger reset."""
        url = f"{self._coordinator.server_url}/HA/reset"
        _LOGGER.debug("Reset an %s",url) 

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status != 200:
                        raise Exception(f"Unexpected status: {response.status}")
            except Exception as e:
                _LOGGER.error(f"Reset failed: {e}")
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"station_{self.station_id}")},
            "name": self.station_name,
            "manufacturer": "PlantBot",
            "model": "Bewässerungsstation",
        }                
