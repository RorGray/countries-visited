"""Countries Visited Frontend"""
import logging
import os

from homeassistant import core
from homeassistant.helpers.event import async_call_later
from homeassistant.components.http import StaticPathConfig

from ..const import URL_BASE, COUNTRIES_VISITED_CARDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class CountriesVisitedCardRegistration:
    def __init__(self, hass: core.HomeAssistant):
        self.hass = hass

    async def async_register(self):
        """Register Countries Visited frontend in Lovelace."""
        _LOGGER.info("Registering Countries Visited frontend in Lovelace")

        try:
            await self.async_register_countries_visited_path()

            # Only proceed if Lovelace is in "storage" mode
            if self.hass.data["lovelace"].mode == "storage":
                await self.async_wait_for_lovelace_resources()
        except Exception as e:
            _LOGGER.error(f"Failed to register Countries Visited frontend: {e}", exc_info=True)

    async def async_register_countries_visited_path(self):
        """Register custom cards path if not already registered."""
        try:
            # HACS serves files from www/community/ at /hacsfiles/ paths
            frontend_path = self.hass.config.path("www/community/countries-visited")

            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(URL_BASE, frontend_path, False)]
            )

            _LOGGER.debug("Registered countries_visited path from %s", frontend_path)
        except RuntimeError:
            _LOGGER.debug("Countries visited static path already registered")

    async def async_wait_for_lovelace_resources(self) -> None:
        """Wait for Lovelace resources to load before registering cards."""
        retries = 10  # Max retries to prevent infinite loop
        delay = 5  # Wait time in seconds

        async def check_lovelace_resources_loaded(now):
            nonlocal retries
            if retries <= 0:
                _LOGGER.error(
                    "Lovelace resources failed to load after multiple attempts."
                )
                return

            if self.hass.data["lovelace"].resources.loaded:
                await self.async_register_countries_visited_cards()
            else:
                _LOGGER.debug(
                    "Lovelace resources not loaded yet, retrying in %d seconds...",
                    delay,
                )
                retries -= 1
                async_call_later(self.hass, delay, check_lovelace_resources_loaded)

        await check_lovelace_resources_loaded(0)

    async def async_register_countries_visited_cards(self):
        """Register Countries Visited cards in Lovelace resources."""
        _LOGGER.info("Installing Lovelace resources for countries_visited cards")

        resources = self.hass.data["lovelace"].resources

        # Get resources already registered
        countries_visited_resources = [
            resource
            for resource in resources.async_items()
            if resource["url"].startswith(URL_BASE)
        ]

        # Prevent duplicate registrations
        existing_urls = {res.get("url") for res in resources.async_items()}

        for card in COUNTRIES_VISITED_CARDS:
            url = f"{URL_BASE}/{card.get('filename')}"
            versioned_url = f"{url}?v={card.get('version')}"

            if not url.endswith(".js"):
                _LOGGER.debug("Skipping non-JS file: %s", url)
                continue

            # Check if already registered with correct version
            if versioned_url in existing_urls:
                _LOGGER.debug(
                    "%s already registered as version %s",
                    card.get("name"),
                    card.get("version"),
                )
                continue

            card_registered = False

            for res in countries_visited_resources:
                if self.get_resource_path(res["url"]) == url:
                    card_registered = True
                    # check version
                    if self.get_resource_version(res["url"]) != card.get("version"):
                        # Update card version
                        _LOGGER.debug(
                            "Updating %s to version %s",
                            card.get("name"),
                            card.get("version"),
                        )
                        await resources.async_update_item(
                            res.get("id"),
                            {
                                "res_type": "module",
                                "url": versioned_url,
                            },
                        )
                        # Remove old gzipped files
                        await self.async_remove_gzip_files()
                    else:
                        _LOGGER.debug(
                            "%s already registered as version %s",
                            card.get("name"),
                            card.get("version"),
                        )

            if not card_registered:
                _LOGGER.info(
                    "Registering %s as version %s",
                    card.get("name"),
                    card.get("version"),
                )
                await resources.async_create_item(
                    {"res_type": "module", "url": versioned_url}
                )

    def get_resource_path(self, url: str):
        return url.split("?")[0]

    def get_resource_version(self, url: str):
        try:
            return url.split("?")[1].replace("v=", "")
        except Exception:
            return 0

    async def async_unregister(self):
        """Remove Lovelace resources when integration is removed."""
        _LOGGER.info("Unregistering Countries Visited frontend resources")

        if (
            "lovelace" in self.hass.data
            and self.hass.data["lovelace"].mode == "storage"
        ):
            resources = self.hass.data["lovelace"].resources

            for card in COUNTRIES_VISITED_CARDS:
                url = f"{URL_BASE}/{card.get('filename')}"
                countries_visited_resources = [
                    resource
                    for resource in list(resources.async_items())
                    if str(resource["url"]).startswith(url)
                ]
                for resource in countries_visited_resources:
                    _LOGGER.debug(f"Removing Lovelace resource: {resource['url']}")
                    await resources.async_delete_item(resource.get("id"))

    async def async_remove_gzip_files(self):
        """Remove outdated gzip-compressed files."""
        await self.hass.async_add_executor_job(self.remove_gzip_files)

    def remove_gzip_files(self):
        """Remove outdated gzip-compressed files."""
        path = self.hass.config.path("www/community/countries-visited")

        if not os.path.exists(path):
            _LOGGER.warning("Frontend path does not exist: %s", path)
            return

        try:
            gzip_files = [
                filename
                for filename in os.listdir(path)
                if filename and filename.endswith(".gz")
            ]

            for file in gzip_files:
                original_file = file.replace(".gz", "")
                original_file_path = os.path.join(path, original_file)

                if os.path.exists(original_file_path) and os.path.getmtime(
                    original_file_path
                ) > os.path.getmtime(os.path.join(path, file)):
                    _LOGGER.debug(f"Removing outdated gzip file: {file}")
                    os.remove(os.path.join(path, file))
        except Exception as e:
            _LOGGER.error("Failed to remove gzip file: %s", e)
