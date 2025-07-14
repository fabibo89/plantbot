from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import logging

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Konfigurierbare Button-Typen
BUTTON_TYPES = {
    "reset": {
        "name": "Reset",
        "url_path": "/HA/reset",
        "icon": "mdi:restart",
        "use_server": False
    },
    "start_irrigation": {
        "name": "Start Bewässerung",
        "url_path": "/HA/startQueue/{id}",
        "icon": "mdi:water-pump",
        "use_server": True
    }
    # Weitere Buttons kannst du hier ergänzen ...
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("button.py gestartet – verfügbare Stationsdaten: %s", coordinator.data)
    buttons = []

    for station_id, station in coordinator.data.items():
        station_name = station.get("name", f"Station {station_id}")
        station_ip = station.get("ip", f"Station {station_id}")

        for button_key, button_conf in BUTTON_TYPES.items():
            button_name = f"{button_conf['name']} {station_name}"
            if button_key == "start_irrigation" and station.get("source") != "server":
                _LOGGER.debug("Überspringe %s für %s (nicht 'server')", button_key, station_id)
                continue
            server_url = entry.data["server"] 
            _LOGGER.debug("Erzeuge Button: %s (station_id=%s, type=%s)", button_name, station_id, button_key)

            buttons.append(
                    PlantBotButton(
                        coordinator,
                        hass,
                        station_name,
                        station_id,
                        station_ip,
                        button_key,
                        button_conf,
                        server_url
                    )
                )

    async_add_entities(buttons, True)


class PlantBotButton(ButtonEntity):
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"station_{self.station_id}")},
            "name": self.station_name,
            "manufacturer": "PlantBot",
            "model": "Bewässerungsstation",
            "configuration_url": f"http://{self.station_ip}"

        }    
    def __init__(self, coordinator, hass, station_name, station_id, station_ip, button_key, config, server_url):
        self._coordinator = coordinator
        self._session = async_get_clientsession(hass)
        self.station_id = station_id
        self.station_name = station_name
        self.station_ip = station_ip
        self.button_key = button_key
        self._config = config
        self._server_url = server_url

        self._use_server = config.get("use_server", False)
        self._attr_name = f"{config['name']} {station_name}"
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_icon = config.get("icon", "mdi:gesture-tap-button")
        self._attr_unique_id = f"{station_ip}_{button_key}_{station_id}"

    async def async_press(self):
        url_path_template = self._config["url_path"]
        station_id_clean = self.station_id.replace("station_", "")
        url_path = url_path_template.format(id=station_id_clean)

        if self._use_server:
            url = f"{self._server_url}{url_path}"
        else:
            url = f"http://{self.station_ip}{url_path}"        

        _LOGGER.debug("Sende Button-Befehl an %s", url)

        try:
            async with self._session.get(url, timeout=5,ssl=False) as response:
                if response.status != 200:
                    _LOGGER.warning("Button-Request fehlgeschlagen (%s): %s", self._attr_name, response.status)
        except Exception as e:
            _LOGGER.error("Fehler beim Senden des Button-Requests an %s: %s", self._attr_name, e)
