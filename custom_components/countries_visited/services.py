"""Services for Countries Visited."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.core import ServiceCall
from homeassistant.helpers import config_validation as cv

DOMAIN = "countries_visited"

# Service schemas
ADD_COUNTRY_SCHEMA = vol.Schema(
    {
        vol.Required("person"): cv.entity_id,
        vol.Required("country_code"): vol.Length(min=2, max=2),
    }
)

REMOVE_COUNTRY_SCHEMA = vol.Schema(
    {
        vol.Required("person"): cv.entity_id,
        vol.Required("country_code"): vol.Length(min=2, max=2),
    }
)

SET_COUNTRIES_SCHEMA = vol.Schema(
    {
        vol.Required("person"): cv.entity_id,
        vol.Required("country_codes"): vol.All(cv.ensure_list, [vol.Length(min=2, max=2)]),
    }
)


async def async_add_country(hass, person: str, country_code: str):
    """Add a country to a person's visited list."""
    state = hass.states.get(person)
    if state is None:
        return False
    
    visited = list(state.attributes.get("visited_countries", []))
    country_code = country_code.upper()
    
    if country_code not in visited:
        visited.append(country_code)
        visited.sort()
    
        # Set the new attribute directly
        hass.states.async_set(
            person,
            state.state,
            {
                **state.attributes,
                "visited_countries": visited,
            }
        )
        return True
    
    return False


async def async_remove_country(hass, person: str, country_code: str):
    """Remove a country from a person's visited list."""
    state = hass.states.get(person)
    if state is None:
        return False
    
    visited = list(state.attributes.get("visited_countries", []))
    country_code = country_code.upper()
    
    if country_code in visited:
        visited.remove(country_code)
    
        # Set the new attribute directly
        hass.states.async_set(
            person,
            state.state,
            {
                **state.attributes,
                "visited_countries": visited,
            }
        )
        return True
    
    return False


async def async_set_countries(hass, person: str, country_codes: list):
    """Set the complete list of visited countries."""
    state = hass.states.get(person)
    if state is None:
        return False
    
    country_codes = [code.upper() for code in country_codes]
    country_codes.sort()
    
    # Set the new attribute directly
    hass.states.async_set(
        person,
        state.state,
        {
            **state.attributes,
            "visited_countries": country_codes,
        }
    )
    return True


def register_services(hass):
    """Register services for Countries Visited."""
    
    async def add_visited_country(call: ServiceCall):
        """Add a country to visited list."""
        person = call.data["person"]
        country_code = call.data["country_code"]
        await async_add_country(hass, person, country_code)

    async def remove_visited_country(call: ServiceCall):
        """Remove a country from visited list."""
        person = call.data["person"]
        country_code = call.data["country_code"]
        await async_remove_country(hass, person, country_code)

    async def set_visited_countries(call: ServiceCall):
        """Set the complete list of visited countries."""
        person = call.data["person"]
        country_codes = call.data["country_codes"]
        await async_set_countries(hass, person, country_codes)

    hass.services.async_register(
        DOMAIN, "add_country", add_visited_country, schema=ADD_COUNTRY_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "remove_country", remove_visited_country, schema=REMOVE_COUNTRY_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, "set_countries", set_visited_countries, schema=SET_COUNTRIES_SCHEMA
    )