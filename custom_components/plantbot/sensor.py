import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.const import UnitOfPressure

_LOGGER = logging.getLogger(__name__)


from .const import DOMAIN

SENSOR_TYPES = {
    "temperature": {"name": "Temperatur", "unit": UnitOfTemperature.CELSIUS,"device_class":SensorDeviceClass.TEMPERATURE ,"state_class": SensorStateClass.MEASUREMENT, "optional": True,"ignore_zero": True},
    "humidity": {"name": "Feuchtigkeit", "unit": PERCENTAGE,"device_class":SensorDeviceClass.HUMIDITY,"state_class": SensorStateClass.MEASUREMENT, "optional": True,"ignore_zero": True},
    "pressure": {"name": "Luftdruck", "unit": UnitOfPressure.HPA,"device_class":None, "state_class": SensorStateClass.MEASUREMENT,"optional": True,"ignore_zero": True,"icon": "mdi:gauge"},
    "water_level": {"name": "Wasserstand", "unit": PERCENTAGE,"device_class":None,"state_class": SensorStateClass.MEASUREMENT, "optional": True},
    "jobs": {"name": "Jobs", "unit": "count","device_class":None  , "state_class": SensorStateClass.MEASUREMENT,"optional": True,"icon": "mdi:playlist-play","ignore_zero": False},
    "flow": {"name": "Flow", "unit": None,"device_class":None, "state_class": SensorStateClass.TOTAL,"optional": True,"icon": "mdi:water-pump"},
    "lastVolume": {"name": "Volume", "unit": 'ml',"device_class":None ,"state_class": SensorStateClass.MEASUREMENT, "optional": True,"icon": "mdi:water"},
    "status": {"name": "Status", "unit": None,"device_class":None, "optional": False,"icon": "mdi:information"},
    "wifi": {"name": "WIFI", "unit": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,"device_class":SensorDeviceClass.SIGNAL_STRENGTH,"state_class": SensorStateClass.MEASUREMENT, "optional": False},
    "runtime": {"name": "Runtime", "unit": "min" ,"device_class":SensorDeviceClass.DURATION,"state_class": SensorStateClass.MEASUREMENT, "optional": True},
    "water_runtime": {"name": "Wasser Runtime", "unit": "s" ,"device_class":SensorDeviceClass.DURATION,"state_class": SensorStateClass.MEASUREMENT, "optional": True,"icon": "mdi:timer-sand"},
    "last_reset_reason": {"name": "Letzter Reset Grund", "unit": None, "device_class": None, "optional": True,"icon": "mdi:restart"},
    "memory_usage": {"name": "Speicherauslastung", "unit": None,"device_class": None,"state_class": SensorStateClass.MEASUREMENT, "optional": True,"icon": "mdi:memory"},
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for station_id, station in coordinator.data.items():
        #Feste Sensoren
        for key, props in SENSOR_TYPES.items():
            value = station.get(key)
            if not props["optional"] or key in station:
                if props["optional"] and (props["ignore_zero"] == True) and (value is None or value == "" or value == "null"):
                    continue  # Überspringe leere Temperaturdaten
                _LOGGER.debug(
                "Füge Sensor hinzu: station_id=%s, typ=%s, name=%s",
                station_id, key, props["name"]
                )
                entities.append(PlantbotSensor(coordinator, station_id, key, props, station["name"]))

        #Modbus-Sensoren
        modbus_sens = station.get("modbusSens", {})
        for addr, values in modbus_sens.items():
            addr_str = str(addr)
            if "hum" in values:
                entities.append(
                    PlantbotSensor(
                        coordinator,
                        station_id,
                        f"soil_hum_{addr_str}",
                        {
                            "name": f"Bodenfeuchtigkeit {addr_str}",
                            "unit": PERCENTAGE,
                            "optional": True,
                            "device_class": SensorDeviceClass.HUMIDITY,
                            "state_class": SensorStateClass.MEASUREMENT,

                        },
                        station["name"]
                    )
                )
                _LOGGER.debug("Füge Modbus-Sensor hinzu: station_id=%s, addr=%s, typ=%s", station_id, addr_str, "temp")

            if "temp" in values:
                entities.append(
                    PlantbotSensor(
                        coordinator,
                        station_id,
                        f"soil_temp_{addr_str}",
                        {
                            "name": f"Bodentemperatur {addr_str}",
                            "unit": UnitOfTemperature.CELSIUS,
                            "optional": True,
                            "device_class": SensorDeviceClass.TEMPERATURE,
                            "state_class": SensorStateClass.MEASUREMENT,
                        },
                        station["name"]
                    )
                )              
                _LOGGER.debug("Füge Modbus-Sensor hinzu: station_id=%s, addr=%s, typ=%s", station_id, addr_str, "hum")

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
        self._attr_editable = False  # Das macht's read-only        
        self._attr_device_class = props["device_class"]
        self._attr_state_class = props.get("state_class")
        self.station_ip = coordinator.data[self.station_id].get("ip")
        self._attr_icon = props.get("icon")
        _LOGGER.debug("##### IP=%s", self.station_ip)


    @property
    def native_value(self):
        if not self.available:
            return None        
        if "soil_hum" in self.key or "soil_temp" in self.key:
            # Dynamische Modbus-Sensoren
            modbus = self.coordinator.data[self.station_id].get("modbusSens", {})
            parts = self.key.rsplit("_", 1)
            if len(parts) == 2:
                addr = parts[1]
                key_type = "hum" if "hum" in self.key else "temp"
                return modbus.get(addr, {}).get(key_type)
            return None
        else:
            value = self.coordinator.data[self.station_id].get(self.key)
            sensor_conf = SENSOR_TYPES.get(self.key, {})
            if value == 0:
                return None
            return value

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        info = {
            "identifiers": {(DOMAIN, f"station_{self.station_id}")},
            "name": self.station_name,
            "manufacturer": "PlantBot",
            "model": "Bewässerungsstation",
        }
        if self.station_ip:
            info["configuration_url"] = f"http://{self.station_ip}"
        return info

    async def async_update(self):
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        self.coordinator.async_add_listener(self.async_write_ha_state)