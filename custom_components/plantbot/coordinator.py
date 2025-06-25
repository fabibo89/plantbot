import logging
from datetime import timedelta
import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class PlantbotCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, server_url):
        self.hass = hass
        self.server_url = server_url
        self.session = aiohttp.ClientSession()
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self):
        try:
            async with self.session.get(f"{self.server_url}/HA/stations",ssl=False) as response:
                if response.status != 200:
                    _LOGGER.error("HTTP-Fehler beim Abrufen der Daten: %s", response.status)
                    raise UpdateFailed(f"Status {response.status}")
                raw = await response.json()
                if raw["status"] != "success":
                    _LOGGER.error("PlantBot-API-Fehler: %s", raw)
                    raise UpdateFailed("Antwortstatus war nicht 'success'")
                stations = raw["data"][0]
                #_LOGGER.debug("Empfangene Daten vom Server: %s", raw)
                return {f"station_{station['id']}": station for station in stations}
        except Exception as err:
            _LOGGER.exception("Fehler bei der Kommunikation mit PlantBot:")
            raise UpdateFailed(f"Fehler: {err}")