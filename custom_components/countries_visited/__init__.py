"""Countries Visited component for Home Assistant."""
from __future__ import annotations

import logging
import os
import shutil

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .frontend import CountriesVisitedCardRegistration
from .services import register_services

_LOGGER = logging.getLogger(__name__)


def ensure_directory(hass: HomeAssistant):
    """Ensure the frontend destination directory exists (blocking)."""
    frontend_dest = hass.config.path("www/community/countries-visited")

    if not os.path.exists(frontend_dest):
        os.makedirs(frontend_dest, exist_ok=True)
        _LOGGER.info(f"Created frontend destination folder: {frontend_dest}")


def copy_frontend_files(hass: HomeAssistant):
    """Copy frontend files synchronously from the integration folder to the www folder."""
    frontend_source = hass.config.path("custom_components/countries_visited/frontend")
    frontend_dest = hass.config.path("www/community/countries-visited")

    try:
        if not os.path.exists(frontend_source):
            _LOGGER.error(f"Frontend source folder not found: {frontend_source}")
            return False

        # Copy all files and subdirectories
        if os.path.exists(frontend_dest):
            shutil.rmtree(frontend_dest)

        shutil.copytree(frontend_source, frontend_dest)
        _LOGGER.info(f"Copied frontend files from {frontend_source} to {frontend_dest}")

        return True
    except Exception as e:
        _LOGGER.error(f"Failed to copy Countries Visited frontend files: {e}")
        return False


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up a skeleton component."""
    _LOGGER.info("Setting up Countries Visited integration (global setup)")

    # Ensure frontend files exist on every Home Assistant startup
    await hass.async_add_executor_job(ensure_directory, hass)
    await hass.async_add_executor_job(copy_frontend_files, hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Countries Visited from a config entry."""
    _LOGGER.info(f"Setting up Countries Visited integration for {entry.entry_id}")

    # Initialize domain data if not exists
    hass.data.setdefault(DOMAIN, {})

    # Store entry-specific data
    hass.data[DOMAIN][entry.entry_id] = {
        "person": entry.data.get("person"),
        **entry.data,
    }

    # Register services (only once, but safe to call multiple times)
    register_services(hass)

    # Ensure frontend files exist
    await hass.async_add_executor_job(ensure_directory, hass)
    await hass.async_add_executor_job(copy_frontend_files, hass)

    # Register frontend resources
    try:
        frontend_registration = CountriesVisitedCardRegistration(hass)
        await frontend_registration.async_register()
        _LOGGER.info("Countries Visited frontend registered successfully")
    except Exception as e:
        _LOGGER.error(f"Failed to register Countries Visited frontend: {e}")

    # Forward entry to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Countries Visited component setup completed")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info(f"Unloading Countries Visited integration for {entry.entry_id}")

    try:
        # Remove stored data for this entry
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id, None)
            _LOGGER.debug("Removed stored data for this entry")

        # Check if this is the last instance
        active_instances = sum(
            1
            for e in hass.config_entries.async_entries(DOMAIN)
            if not e.disabled_by
        )

        # If this is the last instance, unregister frontend and remove files
        if active_instances == 1:
            _LOGGER.info("Last instance removed. Cleaning up frontend resources.")

            frontend_registration = CountriesVisitedCardRegistration(hass)
            await frontend_registration.async_unregister()
            _LOGGER.info("Unregistered Countries Visited frontend.")

            # Remove the frontend files from www/community/countries-visited/
            frontend_dest = hass.config.path("www/community/countries-visited")

            def remove_frontend_files():
                """Delete the Countries Visited frontend directory."""
                if os.path.exists(frontend_dest):
                    _LOGGER.info(f"Removing frontend folder: {frontend_dest}")
                    shutil.rmtree(frontend_dest, ignore_errors=True)

            await hass.async_add_executor_job(remove_frontend_files)
            _LOGGER.info("Successfully removed frontend files.")

        # Unload platforms
        unload_result = await hass.config_entries.async_unload_platforms(
            entry, PLATFORMS
        )

        _LOGGER.info(f"Unloaded platforms: {unload_result}")
        return unload_result

    except Exception as e:
        _LOGGER.error(f"Error while unloading Countries Visited: {e}")
        return False
