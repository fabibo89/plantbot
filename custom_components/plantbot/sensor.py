from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from .const import DOMAIN

SENSOR_TYPES = {
    "temperature": {"name": "Temperatur", "unit": UnitOfTemperature.CELSIUS, "optional": True},
    "water_level": {"name": "Wasserstand", "unit": PERCENTAGE, "optional": True},
    "jobs": {"name": "Jobs", "unit": None, "optional": False},
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for station_id, station in coordinator.data.items():
        for key, props in SENSOR_TYPES.items():
            if not props["optional"] or key in station:
                entities.append(PlantbotSensor(coordinator, station_id, key, props, station["name"]))

    async_add_entities(entities)

class PlantbotSensor(SensorEntity):
    def __init__(self, coordinator, station_id, key, props, station_name):
        self.coordinator = coordinator
        self.station_id = str(station_id)
        self.key = key
        self.station_name = station_name
        self._attr_name = f"{station_name} – {props['name']}"
        self._attr_unique_id = f"{station_id}_{key}"
        self._attr_native_unit_of_measurement = props["unit"]
        self._optional = props["optional"]

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