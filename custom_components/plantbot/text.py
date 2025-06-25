from homeassistant.components.sensor import SensorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for station_id, station in coordinator.data.items():
        entities.append(PlantbotStatusSensor(coordinator, station_id, station["name"]))

    async_add_entities(entities)

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
        self._attr_name = f"{station_name} – Status"
        self._attr_unique_id = f"plantbot_text_{self.station_id}_status"

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