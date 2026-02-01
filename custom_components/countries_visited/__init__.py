"""Countries Visited component for Home Assistant."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .frontend import JSModuleRegistration
from .services import register_services

# Store registration instance
_frontend_registration: JSModuleRegistration | None = None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Countries Visited from a config entry."""
    # Register services
    register_services(hass)
    
    # Register frontend resources
    global _frontend_registration
    _frontend_registration = JSModuleRegistration(hass)
    await _frontend_registration.async_register()
    
    # Forward entry to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unregister frontend resources
    global _frontend_registration
    if _frontend_registration:
        await _frontend_registration.async_unregister()
        _frontend_registration = None
    
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
