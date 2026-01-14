"""Config flow for Countries Visited."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
import homeassistant.helpers.entity_registry as er

from .const import CONF_MAP_COLOR, CONF_PERSON, CONF_VISITED_COLOR, DOMAIN


class CountriesVisitedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Countries Visited."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return CountriesVisitedOptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        # Get list of person entities
        persons = [
            entity.entity_id
            for entity in self.hass.entity_registry.entities.values()
            if entity.domain == "person"
        ]

        if user_input is not None:
            return self.async_create_entry(title="Countries Visited", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_PERSON): vol.In(persons) if persons else str,
                vol.Optional(CONF_MAP_COLOR, default="#e0e0e0"): str,
                vol.Optional(CONF_VISITED_COLOR, default="#4CAF50"): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )


class CountriesVisitedOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Countries Visited."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        
        persons = [
            entity.entity_id
            for entity in self.hass.entity_registry.entities.values()
            if entity.domain == "person"
        ]

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_PERSON, default=self.config_entry.data.get(CONF_PERSON)): 
                    vol.In(persons) if persons else str,
                vol.Optional(CONF_MAP_COLOR, default=self.config_entry.data.get(CONF_MAP_COLOR, "#e0e0e0")): str,
                vol.Optional(CONF_VISITED_COLOR, default=self.config_entry.data.get(CONF_VISITED_COLOR, "#4CAF50")): str,
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=data_schema, errors=errors
        )
