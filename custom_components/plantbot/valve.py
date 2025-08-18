import logging
from homeassistant.components.valve import ValveEntity,ValveEntityFeature
from .const import DOMAIN
from homeassistant.core import callback
from homeassistant.components.valve import ValveDeviceClass
from homeassistant.exceptions import HomeAssistantError
import aiohttp
import asyncio

_LOGGER = logging.getLogger(__name__)
ENTITIES: dict[str, "PlantbotValve"] = {}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    _LOGGER.debug("Initialisiere Valve-Plattform mit Daten: %s", coordinator.data)

    for station_id, station in coordinator.data.items():
        for valve in station.get("valves", []):
            entity = PlantbotValve(coordinator, station_id, station["name"], valve)
            ENTITIES[entity.unique_id] = entity
            entities.append(entity)
            _LOGGER.debug("Registriere Ventil: %s", entity.name or "kein Name")

    async_add_entities(entities)

class PlantbotValve(ValveEntity):
    def __init__(self, coordinator, station_id, station_name, valve_data):
        self.valve_name = valve_data["name"]
        self._attr_name = self.valve_name.replace("_", " ").capitalize() #f"{station_name} – {self.valve_name}"
        self.coordinator = coordinator
        self.station_id = str(station_id)
        self.station_name = station_name
        self.valve_id = str(valve_data["id"])
        self._attr_unique_id = f"plantbot_{self.valve_id}" 
        self._attr_reports_position = False
        self._attr_supported_features = 0
        self._read_only = False
        self._attr_should_poll = False
        self._attr_supported_features = (
            ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
        )
        self.station_ip = coordinator.data[self.station_id].get("ip")

        #self._attr_available = True        
        self._attr_device_class = ValveDeviceClass.WATER

        _LOGGER.debug("Erstelle Ventil-Entität %s (station: %s)", self.valve_id, self.station_id)

    @property
    def available(self):
        #_LOGGER.debug("Ist die Entität verfügbar? %s", self.valve_id)
        return self.coordinator.last_update_success and self._get_valve() is not None

    def _get_valve(self):
        station = self.coordinator.data.get(self.station_id, {})
        valves = station.get("valves", [])
        #_LOGGER.debug("Station %s – verfügbare Ventile: %s", self.station_id, [v['id'] for v in valves])

        for v in valves:
            if str(v["id"]) == str(self.valve_id):
                #_LOGGER.debug("Valve %s gefunden mit state: %s", self.valve_id, v.get("state"))
                return v

        _LOGGER.warning("Valve %s NICHT gefunden in Station %s", self.valve_id, self.station_id)
        return None

    async def async_open_valve(self, **kwargs):
        if self._read_only:
            _LOGGER.debug(f"Read-only: Öffnen nicht erlaubt für {self._name}")
            return        
        await self._send_command("open")

    async def async_close_valve(self, **kwargs):
        if self._read_only:
            _LOGGER.debug(f"Read-only: Schließen nicht erlaubt für {self._name}")
            return
        await self._send_command("close")

    async def async_added_to_hass(self):
        #self.coordinator.async_add_listener(self.async_write_ha_state)
        self.coordinator.async_add_listener(self._handle_coordinator_update)
        self.async_write_ha_state()

        await super().async_added_to_hass()
        _LOGGER.debug("async_added_to_hass %s", self.entity_id)
        if self.entity_id:
            ENTITIES[self.entity_id] = self
            _LOGGER.debug("Registriere Valve: %s → entity_id: %s", self.valve_name, self.entity_id)




    
    async def _send_command(self, state):
        url = f"{self.coordinator.server_url}/HA/valve/{state}?id={self.valve_id}"
        _LOGGER.debug(url)
        async with self.coordinator.session.get(url) as resp:
            if resp.status == 200:
                await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self):
        valve = self._get_valve()
        if valve:
            state = valve.get("state")
            #_LOGGER.debug("Valve %s hat state: %s", self.valve_id, state)
            self._attr_is_closed = state == "closed"
        else:
            _LOGGER.warning("no Valve")
            self._attr_is_closed = None
        self.async_write_ha_state()

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"station_{self.station_id}")},
            "name": self.station_name,
            "manufacturer": "PlantBot",
            "model": "Bewässerungsstation",
            "configuration_url": f"http://{self.station_ip}"
        }
    
    async def open_for_seconds(self, duration):
        url = f"{self.coordinator.server_url}/HA/valve/open?id={self.valve_id}&duration={duration}"

        _LOGGER.warning(url)

        try:
            async with self.coordinator.session.get(url, ssl=False, timeout=10) as resp:
                if resp.status != 200:
                    raise HomeAssistantError(f"Fehler vom Server: HTTP {resp.status}")
                _LOGGER.debug("Serverantwort (%s): %s", resp.status, await resp.text())
                await self.coordinator.async_request_refresh()

        except aiohttp.ClientConnectionError:
            raise HomeAssistantError("Verbindung zum PlantBot-Server fehlgeschlagen (nicht erreichbar)")

        except aiohttp.ClientResponseError as e:
            raise HomeAssistantError(f"Antwortfehler: {e.status} {e.message}")

        except asyncio.TimeoutError:
            raise HomeAssistantError("Zeitüberschreitung beim Warten auf Antwort vom Server")

        except Exception as e:
            _LOGGER.exception("Unerwarteter Fehler bei Kommunikation mit dem Server:")
            raise HomeAssistantError(f"Unerwarteter Fehler: {e}")    

    async def open_for_volume(self,volume):
        url = f"{self.coordinator.server_url}/HA/valve/open?id={self.valve_id}&volume={volume}"
        #http://192.168.10.77/HA/valve/open?id=1&volume=300
        _LOGGER.debug(url)
        try:
            async with self.coordinator.session.get(url, ssl=False, timeout=10) as resp:
                if resp.status != 200:
                    raise HomeAssistantError(f"Fehler vom Server: HTTP {resp.status}")
                _LOGGER.debug("Serverantwort (%s): %s", resp.status, await resp.text())
                await self.coordinator.async_request_refresh()

        except aiohttp.ClientConnectionError:
            raise HomeAssistantError("Verbindung zum PlantBot-Server fehlgeschlagen (nicht erreichbar)")

        except aiohttp.ClientResponseError as e:
            raise HomeAssistantError(f"Antwortfehler: {e.status} {e.message}")

        except asyncio.TimeoutError:
            raise HomeAssistantError("Zeitüberschreitung beim Warten auf Antwort vom Server")

        except Exception as e:
            _LOGGER.exception("Unerwarteter Fehler bei Kommunikation mit dem Server:")
            raise HomeAssistantError(f"Unerwarteter Fehler: {e}")        
            















