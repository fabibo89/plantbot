import logging
from datetime import timedelta
import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN
import json
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import asyncio

_LOGGER = logging.getLogger(__name__)

class PlantbotCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, server_url):
        self.hass = hass
        self.server_url = server_url
        self.session = async_get_clientsession(hass)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self):
        try:
            async with self.session.get(f"{self.server_url}/HA/stations",ssl=False) as response:
                _LOGGER.debug("Empfangene Daten vom Server: %s", f"{self.server_url}/HA/stations")
                if response.status != 200:
                    _LOGGER.error("HTTP-Fehler beim Abrufen der Daten: %s", response.status)
                    raise UpdateFailed(f"Status {response.status}")
                raw = await response.json()
                if raw["status"] != "success":
                    _LOGGER.error("PlantBot-API-Fehler: %s", raw)
                    raise UpdateFailed("Antwortstatus war nicht 'success'")
                basis_data = raw["data"]
                #_LOGGER.debug("Empfangene Daten vom Server: %s", raw)
                #return {f"station_{station['id']}": station for station in stations}
                result = {f"station_{station['id']}": station for station in basis_data}

                for station in basis_data:
                    source = station.get("source", "server")
                    ip = station.get("ip")
                    station_id = station['id']
                    station_name = station['name']
                    result = {f"station_{station['id']}": station for station in basis_data}
                    #_LOGGER.debug(" Data:\n%s", json.dumps(result, indent=2))
                    #_LOGGER.debug("Folgende station wird angeschut %s - %s ", station_id, ip)
                    
                    if source == "server":
                        _LOGGER.debug(" wir gehen rein für IP %s über %s", ip,f"http://{ip}/HA/stations")
                        try:
                            async with self.session.get(f"http://{ip}/HA/stations", timeout=5) as dev_resp:
                                if dev_resp.status == 200:
                                    device_raw = await dev_resp.json()
                                    device_data = device_raw["data"][0]
                                    if raw["status"] != "success":
                                        _LOGGER.error("PlantBot-API-Fehler (Device): %s", device_raw)
                                    _LOGGER.debug("Statusdaten von Gerät %s für %s aktualisiert", ip, station_id)
                                    key_station_id=f"station_{station['id']}"
                                    result[key_station_id].update({
                                        "wifi": device_data.get("wifi"),
                                        "temperature": device_data.get("temperature"),
                                        "humidity": device_data.get("humidity") or {} ,
                                        "status": device_data.get("status"),
                                        "current_version": device_data.get("current_version"),
                                        "latestVersion": device_data.get("latestVersion"),
                                        "update_needed": device_data.get("update_needed"),                                        
                                        "modbusSens": device_data.get("modbusSens") or {} ,                                     
                                        "runtime": int(device_data.get("runtime", 0) / 1000)
                                    })

                                    #_LOGGER.debug("Device Data:\n%s", json.dumps(device_data, indent=2))

                                else:
                                    self.last_update_success = False
                                    _LOGGER.warning("Gerät %s antwortet nicht wie erwartet (%s)", ip, dev_resp.status)
                        except Exception as e:
                            _LOGGER.warning("Fehler beim Statusabruf von Gerät %s: %s", ip, e)
                            self.last_update_success = False

                return result
        

        except asyncio.CancelledError:
            _LOGGER.warning("Abbruch während Datenabruf – vermutlich durch Shutdown oder Timeout")
            self.last_update_success = False
            raise
        except aiohttp.ClientError as err:
            _LOGGER.error("Verbindung zu PlantBot fehlgeschlagen: %s", err)
            self.last_update_success = False
            raise UpdateFailed from err
        except Exception as err:
            _LOGGER.exception("Fehler bei der Kommunikation mit PlantBot:")
            self.last_update_success = False
            raise UpdateFailed(f"Fehler: {err}")

