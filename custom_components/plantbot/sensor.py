import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.const import UnitOfPressure

_LOGGER = logging.getLogger(__name__)


from .const import DOMAIN

SENSOR_TYPES = {
    "temperature": {"name": "Temperatur", "unit": UnitOfTemperature.CELSIUS, "optional": True},
    "humidity": {"name": "Feuchtigkeit", "unit": PERCENTAGE, "optional": True},
    "pressure": {"name": "Luftdruck", "unit": UnitOfPressure.HPA, "optional": True},
    "water_level": {"name": "Wasserstand", "unit": PERCENTAGE, "optional": True},
    "jobs": {"name": "Jobs", "unit": None, "optional": True},
    "flow": {"name": "Flow", "unit": None, "optional": True},
    "lastVolume": {"name": "Volume", "unit": 'L', "optional": True},
    "status": {"name": "Status", "unit": None, "optional": False},
    "wifi": {"name": "WIFI", "unit": SIGNAL_STRENGTH_DECIBELS_MILLIWATT, "optional": False},
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for station_id, station in coordinator.data.items():
        #entities.append(PlantbotStatusSensor(coordinator, station_id, station["name"]))
        for key, props in SENSOR_TYPES.items():
            value = station.get(key)
            if not props["optional"] or key in station:
                if props["optional"] and (value is None or value == "" or value == "null"):
                    continue  # Überspringe leere Temperaturdaten
                _LOGGER.debug(
                "Füge Sensor hinzu: station_id=%s, typ=%s, name=%s",
                station_id, key, props["name"]
                )
                entities.append(PlantbotSensor(coordinator, station_id, key, props, station["name"]))

    async_add_entities(entities)

class PlantbotSensor(SensorEntity):
    def __init__(self, coordinator, station_id, key, props, station_name):
        self.coordinator = coordinator
        self.station_id = str(station_id)
        self.key = key
        self.station_name = station_name
        #self._attr_name = f"{station_name} – {props['name']}"
        self._attr_name = props['name']
        self._attr_unique_id = f"{station_id}_{key}"
        self._attr_native_unit_of_measurement = props["unit"]
        self._optional = props["optional"]
        if self.key == "temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        if self.key == "humidity":
            self._attr_device_class = SensorDeviceClass.HUMIDITY
        if key == "jobs":
            self._attr_device_class = None
            self._attr_native_unit_of_measurement = "Aufträge"
            self._attr_state_class = SensorStateClass.MEASUREMENT    
        if key == "flow":
            self._attr_state_class = SensorStateClass.TOTAL
        if key == "lastVolume":
            self._attr_state_class = SensorStateClass.MEASUREMENT   
        if key == "wifi":
            self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
            self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
        
        self._attr_editable = False  # Das macht's read-only        


    @property
    def native_value(self):
        value = self.coordinator.data[self.station_id].get(self.key)
        if value is None and not self._optional:
            return 0
        return value

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"station_{self.station_id}")},
            "name": self.station_name,
            "manufacturer": "PlantBot",
            "model": "Bewässerungsstation",
        }

    async def async_update(self):
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)


class PlantbotStatusSensor(SensorEntity):
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"station_{self.station_id}")},
            "name": self.station_name,
            "manufacturer": "PlantBot",
            "model": "Bewässerungsstation",
        }
    def __init__(self, coordinator, station_id, station_name):
        self.coordinator = coordinator
        self.station_id = str(station_id)
        self.station_name = station_name
        self._attr_name = "Status"
        self._attr_unique_id = f"plantbot_text_{self.station_id}_status"
        self._attr_editable = False  # Das macht's read-only        
        _LOGGER.debug("Alle registrierten Stati:\n%s", station_name)

    @property
    def native_value(self):
        return self.coordinator.data[self.station_id].get("status", "Unbekannt")

    @property
    def available(self):
        return self.coordinator.last_update_success

    async def async_update(self):
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)        