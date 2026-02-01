"""Countries Visited component for Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .frontend import CountriesVisitedCardRegistration
from .services import register_services

# Store registration instance
_frontend_registration: CountriesVisitedCardRegistration | None = None


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up a skeleton component."""
    # Register custom cards
    global _frontend_registration
    _frontend_registration = CountriesVisitedCardRegistration(hass)
    await _frontend_registration.async_register()
    
    # Return boolean to indicate that initialization was successfully.
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Countries Visited from a config entry."""
    # Register services
    register_services(hass)
    
    # Forward entry to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Frontend resources remain registered at component level
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
