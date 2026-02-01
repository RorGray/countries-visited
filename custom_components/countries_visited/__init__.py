"""Countries Visited component for Home Assistant."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS
from .frontend import CountriesVisitedCardRegistration
from .services import register_services

# Configure logger with a clear name for easy filtering
_LOGGER = logging.getLogger(f"custom_components.{DOMAIN}")

# Optional: Set up a file handler for separate log file (if desired)
# This creates a log file at: <config>/countries_visited.log
_log_file_handler = None


def _setup_file_logging(hass: HomeAssistant):
    """Set up file logging for Countries Visited.
    
    Creates two handlers:
    - File handler: DEBUG level (all logs to countries_visited.log)
    - Console filter: Suppresses INFO/DEBUG from console (WARNING+ only)
    """
    global _log_file_handler
    
    try:
        log_file = hass.config.path("countries_visited.log")
        
        # Get the root logger for the domain (this will catch all child loggers)
        root_logger = logging.getLogger(f"custom_components.{DOMAIN}")
        
        # Set logger level to DEBUG to capture all messages
        root_logger.setLevel(logging.DEBUG)
        
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Prevent duplicate handlers - remove any existing file handlers for this log file
        existing_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
        for handler in existing_handlers:
            try:
                if os.path.abspath(handler.baseFilename) == os.path.abspath(log_file):
                    root_logger.removeHandler(handler)
                    handler.close()
            except (AttributeError, OSError):
                pass
        
        # Clear the log file on restart by using write mode (truncates existing file)
        # This prevents the log file from growing indefinitely
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
            except OSError:
                pass  # If we can't delete it, the write mode will truncate it anyway
        
        # Create file handler - DEBUG level (all logs to file)
        # Use "w" mode to truncate the file on each restart
        file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="w")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        _log_file_handler = file_handler
        
        # Disable propagation to prevent duplicate logs in console
        # We'll handle console output ourselves with a WARNING+ handler
        root_logger.propagate = False
        
        # Add console handler for WARNING+ only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Write initial message to file
        root_logger.info(f"Countries Visited file logging initialized: {log_file}")
        root_logger.info("=" * 80)
        root_logger.info("Countries Visited Integration Log")
        root_logger.info("Full logs: countries_visited.log | Console: WARNING+ only")
        root_logger.info("=" * 80)
        
    except Exception as e:
        # Don't fail setup if logging can't be configured
        logging.getLogger(__name__).warning(f"Could not set up file logging: {e}")


def _remove_file_logging():
    """Remove file logging handler."""
    global _log_file_handler
    if _log_file_handler:
        _LOGGER.removeHandler(_log_file_handler)
        _log_file_handler.close()
        _log_file_handler = None


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
    
    # Path to icon files in repository root (relative to config directory)
    # When installed via HACS, the repo root is at custom_components/countries_visited/
    # So we need to go up two levels to find icon files
    repo_root = Path(frontend_source).parent.parent.parent
    icon_svg = repo_root / "icon.svg"
    icon_png = repo_root / "icon.png"

    try:
        if not os.path.exists(frontend_source):
            _LOGGER.error(f"Frontend source folder not found: {frontend_source}")
            return False

        # Copy all files and subdirectories
        if os.path.exists(frontend_dest):
            shutil.rmtree(frontend_dest)

        shutil.copytree(frontend_source, frontend_dest)
        _LOGGER.info(f"Copied frontend files from {frontend_source} to {frontend_dest}")
        
        # Copy icon files if they exist in the repository root
        try:
            if icon_svg.exists():
                shutil.copy2(icon_svg, frontend_dest / "icon.svg")
                _LOGGER.debug("Copied icon.svg to frontend directory")
            if icon_png.exists():
                shutil.copy2(icon_png, frontend_dest / "icon.png")
                _LOGGER.debug("Copied icon.png to frontend directory")
        except Exception as icon_error:
            _LOGGER.debug(f"Could not copy icon files: {icon_error}")

        return True
    except Exception as e:
        _LOGGER.error(f"Failed to copy Countries Visited frontend files: {e}")
        return False


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up a skeleton component."""
    # Set up optional file logging FIRST, before any other logging
    await hass.async_add_executor_job(_setup_file_logging, hass)
    
    # Get version from manifest
    try:
        manifest = hass.data.get("integrations", {}).get(DOMAIN, {}).manifest
        version = manifest.get("version", "unknown")
    except Exception:
        version = "unknown"
    
    _LOGGER.info("🌍 Setting up Countries Visited integration v%s (global setup)", version)
    _LOGGER.debug("File logging should now be active - check countries_visited.log")

    # Ensure frontend files exist on every Home Assistant startup
    await hass.async_add_executor_job(ensure_directory, hass)
    await hass.async_add_executor_job(copy_frontend_files, hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Countries Visited from a config entry."""
    # Get version from manifest
    try:
        manifest = hass.data.get("integrations", {}).get(DOMAIN, {}).manifest
        version = manifest.get("version", "unknown")
    except Exception:
        version = "unknown"
    
    _LOGGER.info("🌍 Setting up Countries Visited integration v%s for %s", version, entry.entry_id)

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
