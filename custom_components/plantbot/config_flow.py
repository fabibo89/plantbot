import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class PlantBotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            url = user_input["server_url"]

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/HA/stations", ssl=False, timeout=5) as resp:
                        if resp.status != 200:
                            raise ValueError("Ungültiger Statuscode")
            except Exception as e:
                _LOGGER.warning(f"Verbindung zum Server fehlgeschlagen: {e}")
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Plant Bot", data={"server_url": url})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("server_url"): str
            }),
            errors=errors
        )
