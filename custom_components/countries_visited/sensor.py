"""Sensor platform for Countries Visited."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import event

from .const import CONF_PERSON, DOMAIN, ISO_TO_NAME

# Use consistent logger name for easy filtering
_LOGGER = logging.getLogger(f"custom_components.{DOMAIN}.sensor")

# Callbacks for cache statistics sensors to update
_cache_stats_callbacks = []

# Cache for reverse geocoding results (lat,lon -> country_code)
_COORDINATE_CACHE = {}

# Cache statistics
_CACHE_STATS = {
    "cache_hits": 0,
    "cache_misses": 0,
    "api_calls": 0,
    "total_requests": 0,
}

# Reverse geocoder instance (lazy loaded)
_reverse_geocoder = None

# Rate limiting: track last API call time
_last_api_call_time = 0.0
RATE_LIMIT_SECONDS = 1.1  # Nominatim allows 1 request per second, use 1.1 for safety


def _get_reverse_geocoder():
    """Get or create reverse geocoder instance."""
    global _reverse_geocoder
    if _reverse_geocoder is None:
        try:
            from geopy.geocoders import Nominatim
            from geopy.exc import GeocoderTimedOut, GeocoderServiceError
            
            # Use Nominatim (OpenStreetMap) - free, no API key required
            _reverse_geocoder = Nominatim(user_agent="home-assistant-countries-visited")
            _LOGGER.info("Initialized reverse geocoder for country detection")
        except ImportError:
            _LOGGER.error(
                "geopy library not installed. Install it with: pip install geopy"
            )
            _reverse_geocoder = False  # Mark as unavailable
        except Exception as err:
            _LOGGER.warning("Failed to initialize reverse geocoder: %s", err)
            _reverse_geocoder = False
    
    return _reverse_geocoder if _reverse_geocoder is not False else None


def _notify_cache_stats_updated(hass: HomeAssistant):
    """Notify all cache statistics sensors to update."""
    for callback_func in _cache_stats_callbacks:
        try:
            callback_func()
        except Exception as err:
            _LOGGER.debug("Error notifying cache stats sensor: %s", err)


def get_cache_stats():
    """Get current cache statistics."""
    cache_size = len(_COORDINATE_CACHE)
    total_requests = _CACHE_STATS["total_requests"]
    cache_hits = _CACHE_STATS["cache_hits"]
    cache_misses = _CACHE_STATS["cache_misses"]
    api_calls = _CACHE_STATS["api_calls"]
    
    # Calculate hit rate (percentage)
    hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0.0
    
    return {
        "cache_size": cache_size,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "api_calls": api_calls,
        "total_requests": total_requests,
        "hit_rate": round(hit_rate, 2),
    }


async def get_country_from_coords(hass, lat, lon):
    """Determine country code from GPS coordinates using reverse geocoding.
    
    Uses caching to avoid excessive API calls. Coordinates are rounded to ~1km
    precision for caching efficiency.
    
    Note: Nominatim (OpenStreetMap) has rate limits:
    - 1 request per second (free tier)
    - Please be respectful of their service
    """
    global _last_api_call_time
    
    # Round coordinates to ~1km precision for caching (0.01° ≈ 1km)
    cache_key = (round(lat, 2), round(lon, 2))
    
    # Update statistics
    _CACHE_STATS["total_requests"] += 1
    
    # Check cache first - NO DELAY for cache hits!
    if cache_key in _COORDINATE_CACHE:
        cached_result = _COORDINATE_CACHE[cache_key]
        _CACHE_STATS["cache_hits"] += 1
        # Notify cache statistics sensors to update
        _notify_cache_stats_updated(hass)
        return cached_result
    
    # Cache miss - will need API call
    _CACHE_STATS["cache_misses"] += 1
    
    geocoder = _get_reverse_geocoder()
    if not geocoder:
        _LOGGER.debug("Reverse geocoder not available, cannot determine country")
        # Notify cache statistics sensors to update (even though no API call was made)
        _notify_cache_stats_updated(hass)
        return None
    
    try:
        # Rate limiting: only wait if we need to make an API call
        import time
        current_time = time.time()
        time_since_last_call = current_time - _last_api_call_time
        
        if time_since_last_call < RATE_LIMIT_SECONDS:
            wait_time = RATE_LIMIT_SECONDS - time_since_last_call
            await asyncio.sleep(wait_time)
        
        # Update last API call time
        _last_api_call_time = time.time()
        
        # Use async executor to avoid blocking
        from geopy.exc import GeocoderTimedOut, GeocoderServiceError
        
        def reverse_geocode():
            try:
                location = geocoder.reverse((lat, lon), exactly_one=True, timeout=10)
                if location and location.raw:
                    address = location.raw.get("address", {})
                    country_code = address.get("country_code", "").upper()
                    if country_code and len(country_code) == 2:
                        return country_code
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                pass  # Geocoding errors are expected and don't need logging
                return None
            except Exception as e:
                _LOGGER.warning("Unexpected geocoding error: %s", e)
                return None
            return None
        
        country_code = await hass.async_add_executor_job(reverse_geocode)
        
        # Track API call
        _CACHE_STATS["api_calls"] += 1
        
        # Cache the result (both success and failure)
        _COORDINATE_CACHE[cache_key] = country_code
        
        
        # Notify cache statistics sensors to update
        _notify_cache_stats_updated(hass)
        
        return country_code
            
    except Exception as err:
        _LOGGER.warning("Error reverse geocoding coordinates (%s, %s): %s", lat, lon, err)
        # Track API call attempt
        _CACHE_STATS["api_calls"] += 1
        # Cache the error to avoid retrying immediately
        _COORDINATE_CACHE[cache_key] = None
        # Notify cache statistics sensors to update
        _notify_cache_stats_updated(hass)
        return None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Countries Visited sensor."""
    person_entity = entry.data[CONF_PERSON]
    
    sensor = CountriesVisitedSensor(hass, entry)
    cache_stats_sensor = CacheStatisticsSensor(hass, entry)
    async_add_entities([sensor, cache_stats_sensor])
    
    # Trigger initial update to check history immediately
    # This ensures history is processed on setup/reload
    await sensor.async_update()
    await cache_stats_sensor.async_update()

    # Listen for person state changes to detect new locations
    @callback
    def handle_person_change(entity_id, old_state, new_state):
        if entity_id == person_entity and new_state:
            sensor.async_schedule_update_ha_state(True)

    entry.async_on_unload(
        event.async_track_state_change_event(hass, person_entity, handle_person_change)
    )


class CountriesVisitedSensor(SensorEntity):
    """Sensor to track visited countries for a person."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self._entry = entry
        self._attr_native_unit_of_measurement = "countries"
        self._attr_icon = "mdi:map-marker-multiple"
        self._attr_extra_state_attributes = {}
        self._last_visited_countries = []
        
    @property
    def name(self):
        """Return the name of the sensor."""
        person_name = self._entry.data.get(CONF_PERSON, "Unknown")
        return f"Countries Visited ({person_name})"

    @property
    def unique_id(self):
        """Return unique ID."""
        return f"countries_visited_{self._entry.entry_id}"

    async def async_update(self):
        """Update the sensor state."""
        person_entity = self._entry.data.get(CONF_PERSON)
        
        state = self.hass.states.get(person_entity)
        if not state:
            _LOGGER.warning(f"Person entity {person_entity} not found")
            return
        
        # Get manually tracked countries from entity attributes
        manual_countries = list(state.attributes.get("visited_countries", []))
        
        # Detect countries from history
        history_countries = await self._detect_countries_from_history(person_entity)
        
        # Merge countries (manual + detected)
        visited_countries = list(set(manual_countries + history_countries))
        visited_countries.sort()
        
        # Update state only if changed
        if visited_countries != self._last_visited_countries:
            self._last_visited_countries = visited_countries
            _LOGGER.info(
                f"Countries list updated for {person_entity}: {len(visited_countries)} countries "
                f"(manual: {len(manual_countries)}, detected: {len(history_countries)})"
            )
            
        # Get current location for current country detection
        current_country = await self._get_current_country(person_entity)
        if current_country:
            # Add current country to visited list if not already there
            if current_country not in visited_countries:
                visited_countries.append(current_country)
                visited_countries.sort()
                _LOGGER.info(f"Added current country {current_country} to visited list for {person_entity}")
        
        # Get country names for display (after adding current country)
        country_names = [
            ISO_TO_NAME.get(code, code) for code in visited_countries
        ]
        
        self._attr_native_value = len(visited_countries)
        self._attr_extra_state_attributes = {
            "visited_countries": visited_countries,
            "visited_countries_names": country_names,
            "person": person_entity,
            "detected_from_history": history_countries,
            "manual_countries": manual_countries,
            "current_country": current_country,
        }

    async def _get_current_country(self, person_entity):
        """Get the current country based on person's current GPS location."""
        state = self.hass.states.get(person_entity)
        if not state:
            return None
        
        lat = state.attributes.get("latitude")
        lon = state.attributes.get("longitude")
        
        if lat is None or lon is None:
            return None
        
        return await get_country_from_coords(self.hass, lat, lon)

    async def _detect_countries_from_history(self, person_entity):
        """Detect countries from person entity history using REST API."""
        detected = set()
        
        try:
            # Check if recorder component is loaded
            if 'recorder' not in self.hass.config.components:
                _LOGGER.debug(
                    "Recorder component not loaded. "
                    "History detection requires the recorder component to be enabled."
                )
                return list(detected)
            
            # Use REST API to get entity history (avoids blocking call issues)
            from datetime import datetime, timedelta
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            from urllib.parse import quote
            import json
            
            # Get history from last 365 days
            end_time = datetime.now()
            start_time = end_time - timedelta(days=365)
            
            # Format timestamps for API (ISO 8601 format)
            start_time_str = start_time.isoformat()
            end_time_str = end_time.isoformat()
            
            # Use internal API mechanism to bypass authentication
            # Call the history API handler directly through hass.http.app
            from aiohttp import web
            from homeassistant.components.history import HistoryPeriodView
            
            # Build API path with timestamp
            api_path = f"/api/history/period/{quote(start_time_str)}"
            
            # Build query parameters
            query_params = {
                "filter_entity_id": person_entity,
                "end_time": end_time_str,
            }
            
            try:
                # Create internal request object for the history API handler
                # This bypasses authentication for internal calls
                internal_request = web.Request(
                    method="GET",
                    path=api_path,
                    headers={},
                    match_info={"timestamp": start_time_str},
                    query=query_params,
                )
                
                # Set the app reference so the handler can access hass
                internal_request._app = self.hass.http.app
                
                # Call the HistoryPeriodView handler directly
                # This is an internal call that bypasses HTTP authentication
                handler = HistoryPeriodView()
                response = await handler.get(internal_request)
                
                # Extract JSON from response
                if response.status == 200:
                    data = await response.json()
                else:
                    _LOGGER.warning(
                        f"History API returned status {response.status} for {person_entity}"
                    )
                    return list(detected)
                    
            except Exception as internal_error:
                _LOGGER.warning(
                    f"Internal API call failed: {internal_error}. "
                    "History detection will be skipped. "
                    "This may require a long-lived access token for REST API calls."
                )
                return list(detected)
            
            if not data or not isinstance(data, list) or len(data) == 0:
                return list(detected)
            
            # Extract states for our entity (first array in response)
            entity_states = data[0] if data else []
            
            # Extract GPS coordinates from history states
            # API returns dict objects, not State objects
            coordinates_to_resolve = []
            
            for state_dict in entity_states:
                # Check if state has GPS coordinates in attributes
                attributes = state_dict.get("attributes", {})
                lat = attributes.get("latitude")
                lon = attributes.get("longitude")
                
                if lat is not None and lon is not None:
                    coordinates_to_resolve.append((lat, lon))
                
                # Also check zone information
                state_value = state_dict.get("state")
                if state_value and state_value.startswith("zone."):
                    zone_entity = state_value
                    zone_state = self.hass.states.get(zone_entity)
                    if zone_state:
                        zone_lat = zone_state.attributes.get("latitude")
                        zone_lon = zone_state.attributes.get("longitude")
                        if zone_lat is not None and zone_lon is not None:
                            coordinates_to_resolve.append((zone_lat, zone_lon))
            
            # Resolve coordinates to countries (with caching and rate limiting)
            # Process unique coordinates only to minimize API calls
            unique_coords = list(set(coordinates_to_resolve))
            
            # Limit processing to avoid excessive API calls
            # Process max 100 coordinates per update to avoid timeouts
            max_coords = 100
            if len(unique_coords) > max_coords:
                _LOGGER.warning(
                    "Limiting history processing to %d coordinates (found %d) for %s. "
                    "Consider running detection periodically rather than on every update.",
                    max_coords,
                    len(unique_coords),
                    person_entity
                )
                unique_coords = unique_coords[:max_coords]
            
            detected_count = 0
            for lat, lon in unique_coords:
                country_code = await get_country_from_coords(self.hass, lat, lon)
                if country_code:
                    detected.add(country_code)
                    detected_count += 1
                # No additional delay needed - rate limiting is handled in get_country_from_coords
            
            if detected_count > 0:
                _LOGGER.info(
                    f"Detected {len(detected)} countries from history for {person_entity}: {sorted(detected)}"
                )
                                
        except Exception as err:
            _LOGGER.warning("Error detecting countries from history: %s", err, exc_info=True)
        
        return list(detected)


class CacheStatisticsSensor(SensorEntity):
    """Sensor to track geocoding cache statistics."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self._entry = entry
        self._attr_icon = "mdi:chart-line"
        self._attr_extra_state_attributes = {}
        
        # Register callback for cache updates
        def update_callback():
            self.async_schedule_update_ha_state(True)
        
        _cache_stats_callbacks.append(update_callback)
        
        # Store callback for cleanup
        self._update_callback = update_callback
        
    @property
    def name(self):
        """Return the name of the sensor."""
        return "Geocoding Cache Statistics"
    
    @property
    def unique_id(self):
        """Return unique ID."""
        return f"geocoding_cache_stats_{self._entry.entry_id}"
    
    async def async_will_remove_from_hass(self):
        """Clean up callback when entity is removed."""
        if self._update_callback in _cache_stats_callbacks:
            _cache_stats_callbacks.remove(self._update_callback)
    
    async def async_update(self):
        """Update the sensor state with cache statistics."""
        stats = get_cache_stats()
        
        # Use hit rate as the main value
        self._attr_native_value = stats["hit_rate"]
        self._attr_native_unit_of_measurement = "%"
        
        self._attr_extra_state_attributes = {
            "cache_size": stats["cache_size"],
            "cache_hits": stats["cache_hits"],
            "cache_misses": stats["cache_misses"],
            "api_calls": stats["api_calls"],
            "total_requests": stats["total_requests"],
            "hit_rate": stats["hit_rate"],
        }