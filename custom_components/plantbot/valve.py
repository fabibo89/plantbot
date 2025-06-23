# valve.py
from homeassistant.components.valve import ValveEntity, ValveDeviceClass
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
import asyncio
import voluptuous as vol
import logging
import aiohttp

from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.event import async_call_later
from homeassistant.components.persistent_notification import async_create as async_create_notification
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def get_device_info(device_id: str, name: str) -> dict:
    return {
        "identifiers": {(DOMAIN, device_id)},
        "name": name,
        "manufacturer": "PlantBot",
        "model": "Watering V3.1.0",
        "configuration_url": f"http://localhost:4000"
    }

class PlantBotValve(ValveEntity):
    def __init__(self, hass, station_id, valve_id, name, state, server_url, device_id, unique_id):
        self._attr_name = name.replace("_", " ").capitalize()
        self._attr_unique_id = unique_id
        self._attr_is_closed = state == "closed"
        self._station_id = station_id
        self._valve_id = valve_id
        self._server_url = server_url
        self._hass = hass
        self._name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)}
        }

        self._attr_reports_position = False
        self._attr_device_class = ValveDeviceClass.WATER
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_supported_features = 0
        self._read_only = True

    async def async_open_valve(self, **kwargs):
        if self._read_only:
            _LOGGER.debug(f"Read-only: Öffnen nicht erlaubt für {self._name}")
            return

    async def async_close_valve(self, **kwargs):
        if self._read_only:
            _LOGGER.debug(f"Read-only: Schließen nicht erlaubt für {self._name}")
            return

    @property
    def is_closed(self):
        return self._attr_is_closed

    async def async_update(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._server_url}/HA/stations", ssl=False) as response:
                    data = await response.json()
                    stations = data.get("data", [[]])[0]
                    for station in stations:
                        if station["id"] == self._station_id:
                            for valve in station.get("valves", []):
                                if valve["id"] == self._valve_id:
                                    self._attr_is_closed = valve["state"] == "closed"
                                    break
        except Exception as e:
            _LOGGER.warning(f"PlantBot update fehlgeschlagen für {self._name}: {e}")

class PlantBotTemperatureSensor(SensorEntity):
    def __init__(self, station_id, device_id, unique_id, name, station_name, initial_value=None):
        self._attr_name = f"{name} Temperatur"
        self._attr_unique_id = f"{station_id}_temperature"
        self._station_id = station_id
        self._attr_native_unit_of_measurement = "°C"
        self._attr_state_class = "measurement"
        self._attr_device_info = get_device_info(device_id, station_name)
        self._state = initial_value
        self._attr_device_class = "temperature"


    @property
    def native_value(self):
        return self._state

    def set_temperature(self, temp):
        self._state = temp
        self.async_write_ha_state()

class PlantBotQueueSensor(SensorEntity):
    def __init__(self, station_id, device_id, unique_id, name, station_name, initial_value=None):
        self._attr_name = f"{name} Warteschlange"
        self._attr_unique_id = f"{station_id}_queue"
        self._station_id = station_id
        self._attr_device_info = get_device_info(device_id, station_name)
        self._attr_state_class = "measurement"
        self._state = initial_value

    @property
    def native_value(self):
        return self._state

    def set_queue_length(self, value):
        self._state = value
        self.async_write_ha_state()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    server_url = hass.data[DOMAIN]["server_url"]
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server_url}/HA/stations", ssl=False) as response:
                data = await response.json()
                stations = data.get("data", [[]])[0]
    except Exception as e:
        _LOGGER.error(f"Fehler beim Laden der Stationen: {e}")
        return

    entities = []
    device_registry = dr.async_get(hass)

    for station in stations:
        station_id = station["id"]
        station_name = station["name"].strip()
        device_id = f"plantbot_station_{station_id}"

        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_id)},
            name=station_name,
            manufacturer="PlantBot",
            model="Watering Station"
        )

        temp_sensor = PlantBotTemperatureSensor(
            station_id=station_id,
            device_id=device_id,
            unique_id=device_id,
            name=station_name,
            station_name=station_name,
            initial_value=20.0
        )
        queue_sensor = PlantBotQueueSensor(
            station_id=station_id,
            device_id=device_id,
            unique_id=device_id,
            name=station_name,
            station_name=station_name,
            initial_value=0
        )
        entities.extend([temp_sensor, queue_sensor])
        hass.data[DOMAIN].setdefault("entities", {})[temp_sensor.unique_id] = temp_sensor
        hass.data[DOMAIN]["entities"][queue_sensor.unique_id] = queue_sensor

        for valve in station.get("valves", []):
            name_raw = valve.get("name")
            if not name_raw:
                name_raw = f"valve_{valve.get('id', 'unknown')}"
            valve_name = name_raw.strip()#.lower().replace(" ", "_")

            unique_id = f"plantbot_{valve['id']}"  # NUR ventPlantBotTemperatureSensoril-ID als unique_id

            entity = PlantBotValve(
                hass=hass,
                station_id=station_id,
                valve_id=valve["id"],
                name=valve_name,
                state=valve["state"],
                server_url=server_url,
                device_id=device_id,
                unique_id=unique_id
            )
            entities.append(entity)
            hass.data[DOMAIN].setdefault("entities", {})[unique_id] = entity

    async_add_entities(entities)

    @callback
    async def handle_set_temperature(call):
        station_id = call.data["station"]
        temperature = call.data["temperature"]

        for entity in hass.data[DOMAIN]["entities"].values():
            if isinstance(entity, PlantBotTemperatureSensor) and entity._station_id == station_id:
                entity.set_temperature(temperature)
                _LOGGER.info(f"Temperatur aktualisiert für Station {station_id}: {temperature}°C")

    @callback
    async def handle_set_queue_length(call):
        station_id = call.data["station"]
        queue = call.data["queue"]

        for entity in hass.data[DOMAIN]["entities"].values():
            if isinstance(entity, PlantBotQueueSensor) and entity._station_id == station_id:
                entity.set_queue_length(queue)
                _LOGGER.info(f"Warteschlange aktualisiert für Station {station_id}: {queue}")

    @callback
    async def handle_water_service(call):
        entity_id = call.data["valve"]
        registry = async_get(hass)
        reg_entry = registry.async_get(entity_id)

        if not reg_entry:
            _LOGGER.warning(f"Unbekanntes Ventil: {entity_id} (nicht im Entity-Registry)")
            return

        unique_id = reg_entry.unique_id
        entity = hass.data[DOMAIN]["entities"].get(unique_id)

        if not entity:
            _LOGGER.warning(f"Unbekanntes Ventil: {entity_id} (nicht in hass.data)")
            return

        volume = call.data["volume"]
        station_id = entity._station_id
        valve_id = entity._valve_id

        async def post_water():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{server_url}/HA/water", json={
                        "station": station_id,
                        "valve": valve_id,
                        "volume": volume
                    }, ssl=False) as response:
                        if response.status == 200:
                            _LOGGER.info(f"Ventil {valve_id} erfolgreich bewässert mit {volume}ml")
                            async_create_notification(
                                hass,
                                f"Ventil {valve_id} wurde erfolgreich mit {volume}ml bewässert.",
                                title="PlantBot Benachrichtigung"
                            )
                        else:
                            _LOGGER.warning(f"Fehlerhafte Antwort beim Bewässern von Ventil {valve_id}: {response.status}")
                            async_create_notification(
                                hass,
                                f"Fehler beim Bewässern von Ventil {valve_id}: HTTP {response.status}",
                                title="PlantBot Fehler"
                            )
            except Exception as e:
                _LOGGER.warning(f"PlantBot water service failed: {e}")
                async_create_notification(
                    hass,
                    f"Fehler beim Bewässern von Ventil {valve_id}: {str(e)}",
                    title="PlantBot Fehler"
                )

        hass.async_create_task(post_water())

    @callback
    async def handle_set_valve_state(call):
        valve_id = call.data["valve"]
        new_state = call.data["state"]
        unique_id = f"plantbot_{valve_id}"

        entity = hass.data[DOMAIN]["entities"].get(unique_id)

        if not entity:
            _LOGGER.warning(f"Valve nicht gefunden: {unique_id}")
            return

        entity._attr_is_closed = (new_state == "closed")
        entity.async_write_ha_state()
        _LOGGER.info(f"Ventil-Zustand gesetzt: {unique_id} => {new_state}")
        async_create_notification(
            hass,
            f"Ventil {valve_id} wurde auf {new_state} gesetzt.",
            title="PlantBot Zustand aktualisiert"
        )

    hass.services.async_register(
        DOMAIN,
        "set_temperature",
        handle_set_temperature,
        schema=vol.Schema({
            vol.Required("station"): vol.Coerce(int),
            vol.Required("temperature"): vol.Coerce(float)
        })
    )

    hass.services.async_register(
        DOMAIN,
        "set_queue_length",
        handle_set_queue_length,
        schema=vol.Schema({
            vol.Required("station"): vol.Coerce(int),
            vol.Required("queue"): vol.Coerce(int)
        })
    )

    hass.services.async_register(
        # action: plantbot.set_valve_state
        # data:
        #   valve: 35
        #   state: open        
        DOMAIN,
        "set_valve_state",
        handle_set_valve_state,
        schema=vol.Schema({
            vol.Required("valve"): vol.Coerce(int),
            vol.Required("state"): vol.In(["open", "closed"])
        })
    )

    hass.services.async_register(
        DOMAIN,
        "water_station",
        handle_water_service,
        schema=vol.Schema({
            vol.Required("valve"): cv.entity_id,
            vol.Required("volume"): vol.All(vol.Coerce(int), vol.Range(min=1))
        })
    )