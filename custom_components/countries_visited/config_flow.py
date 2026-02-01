"""Config flow for Countries Visited."""
from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import CONF_MAP_COLOR, CONF_PERSON, CONF_VISITED_COLOR, DOMAIN

_LOGGER = logging.getLogger(__name__)


def get_person_entities(hass):
    """Get list of person entity IDs."""
    try:
        return [
            entity_id
            for entity_id, entity in hass.entity_registry.entities.items()
            if entity.domain == "person"
        ]
    except Exception:
        return []


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
        
        persons = get_person_entities(self.hass)

        if user_input is not None:
            return self.async_create_entry(title="Countries Visited", data=user_input)

        if persons:
            schema = {
                vol.Required(CONF_PERSON, default=persons[0]): vol.In(persons),
                vol.Optional(CONF_MAP_COLOR, default="#e0e0e0"): str,
                vol.Optional(CONF_VISITED_COLOR, default="#4CAF50"): str,
            }
        else:
            schema = {
                vol.Required(CONF_PERSON): str,
                vol.Optional(CONF_MAP_COLOR, default="#e0e0e0"): str,
                vol.Optional(CONF_VISITED_COLOR, default="#4CAF50"): str,
            }

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(schema), errors=errors
        )


class CountriesVisitedOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Countries Visited."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        
        try:
            # Access hass - OptionsFlow should have self.hass available
            # Try multiple ways to access hass for compatibility
            hass = None
            if hasattr(self, 'hass'):
                hass = self.hass
            elif hasattr(self.config_entry, 'hass'):
                hass = self.config_entry.hass
            elif hasattr(self.config_entry, '_hass'):
                hass = self.config_entry._hass
            
            if hass is None:
                _LOGGER.error("Could not access hass in options flow")
                errors["base"] = "hass_not_available"
                # Return a simple form without person selection
                schema = {
                    vol.Required(CONF_PERSON, default=self.config_entry.data.get(CONF_PERSON, "")): str,
                    vol.Optional(CONF_MAP_COLOR, default=self.config_entry.data.get(CONF_MAP_COLOR, "#e0e0e0")): str,
                    vol.Optional(CONF_VISITED_COLOR, default=self.config_entry.data.get(CONF_VISITED_COLOR, "#4CAF50")): str,
                }
                return self.async_show_form(
                    step_id="init", data_schema=vol.Schema(schema), errors=errors
                )
            
            persons = get_person_entities(hass)
            current_person = self.config_entry.data.get(CONF_PERSON, "")
        except Exception as e:
            errors["base"] = "unknown_error"
            _LOGGER.error(f"Error in options flow: {e}", exc_info=True)
            # Return a simple form on error
            schema = {
                vol.Required(CONF_PERSON, default=self.config_entry.data.get(CONF_PERSON, "")): str,
                vol.Optional(CONF_MAP_COLOR, default=self.config_entry.data.get(CONF_MAP_COLOR, "#e0e0e0")): str,
                vol.Optional(CONF_VISITED_COLOR, default=self.config_entry.data.get(CONF_VISITED_COLOR, "#4CAF50")): str,
            }
            return self.async_show_form(
                step_id="init", data_schema=vol.Schema(schema), errors=errors
            )

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        if persons:
            schema = {
                vol.Required(CONF_PERSON, default=current_person or persons[0]): 
                    vol.In(persons),
                vol.Optional(CONF_MAP_COLOR, default=self.config_entry.data.get(CONF_MAP_COLOR, "#e0e0e0")): str,
                vol.Optional(CONF_VISITED_COLOR, default=self.config_entry.data.get(CONF_VISITED_COLOR, "#4CAF50")): str,
            }
        else:
            schema = {
                vol.Required(CONF_PERSON, default=current_person): str,
                vol.Optional(CONF_MAP_COLOR, default=self.config_entry.data.get(CONF_MAP_COLOR, "#e0e0e0")): str,
                vol.Optional(CONF_VISITED_COLOR, default=self.config_entry.data.get(CONF_VISITED_COLOR, "#4CAF50")): str,
            }

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(schema), errors=errors
        )
