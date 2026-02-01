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
        _LOGGER.debug("Using cached country for (%s, %s): %s", lat, lon, cached_result)
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
            _LOGGER.debug(f"Rate limiting: waiting {wait_time:.2f}s before API call")
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
                    else:
                        _LOGGER.debug(
                            "Invalid country code from geocoding: %s", country_code
                        )
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                _LOGGER.debug("Geocoding error for (%s, %s): %s", lat, lon, e)
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
        
        if country_code:
            _LOGGER.debug("Resolved (%s, %s) to country: %s", lat, lon, country_code)
        else:
            _LOGGER.debug("Could not resolve country for (%s, %s)", lat, lon)
        
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
        _LOGGER.debug(f"Manual countries from {person_entity}: {manual_countries}")
        
        # Detect countries from history
        history_countries = await self._detect_countries_from_history(person_entity)
        _LOGGER.info(f"Detected {len(history_countries)} countries from history: {history_countries}")
        
        # Merge countries (manual + detected)
        visited_countries = list(set(manual_countries + history_countries))
        visited_countries.sort()
        
        _LOGGER.info(
            f"Total visited countries for {person_entity}: {len(visited_countries)} "
            f"(manual: {len(manual_countries)}, detected: {len(history_countries)})"
        )
        
        # Update state only if changed
        if visited_countries != self._last_visited_countries:
            self._last_visited_countries = visited_countries
            _LOGGER.info(f"Countries list updated: {visited_countries}")
            
        # Get current location for current country detection
        current_country = await self._get_current_country(person_entity)
        if current_country:
            _LOGGER.debug(f"Current country for {person_entity}: {current_country}")
            # Add current country to visited list if not already there
            if current_country not in visited_countries:
                visited_countries.append(current_country)
                visited_countries.sort()
                _LOGGER.info(f"Added current country {current_country} to visited list")
        
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
        
        _LOGGER.debug(f"Sensor updated - state: {self._attr_native_value}, attributes: {self._attr_extra_state_attributes}")

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
        """Detect countries from device_tracker history."""
        detected = set()
        
        try:
            # Try multiple methods to access history component
            history_component = None
            
            # Method 1: Direct access via hass.components.history
            if hasattr(self.hass, 'components') and hasattr(self.hass.components, 'history'):
                history_component = self.hass.components.history
                _LOGGER.debug("Accessed history component via hass.components.history")
            
            # Method 2: Check if history is in loaded components and try to get it
            elif 'history' in self.hass.config.components:
                try:
                    from homeassistant.components import history as history_module
                    history_component = history_module
                    _LOGGER.debug("Accessed history component via import")
                except ImportError:
                    _LOGGER.debug("Could not import history component")
            
            # Method 3: Try to get from hass.data
            if history_component is None and 'history' in self.hass.data:
                try:
                    history_component = self.hass.data.get('history')
                    _LOGGER.debug("Accessed history component via hass.data")
                except Exception:
                    pass
            
            if history_component is None:
                _LOGGER.warning(
                    "History component not available. "
                    "Make sure 'history:' is in your configuration.yaml or history is enabled. "
                    "History is usually enabled by default."
                )
                return list(detected)
            
            # Try to get history states - use multiple API methods
            states = []
            
            # Method 1: Try async_get_state (HA 2022.4+) - works with hass.components.history
            if hasattr(history_component, 'async_get_state'):
                try:
                    _LOGGER.debug(f"Using async_get_state API for {person_entity}")
                    result = await history_component.async_get_state(self.hass, None, person_entity)
                    if result:
                        # async_get_state returns a dict with entity_id as key
                        if isinstance(result, dict):
                            states = result.get(person_entity, [])
                        elif isinstance(result, list):
                            states = result
                        else:
                            states = []
                    _LOGGER.debug(f"Retrieved {len(states)} history states via async_get_state")
                except Exception as e:
                    _LOGGER.debug(f"async_get_state failed: {e}, trying fallback")
            
            # Method 2: Try get_state (legacy API) - works with hass.components.history
            if not states and hasattr(history_component, 'get_state'):
                try:
                    _LOGGER.debug(f"Using get_state API for {person_entity}")
                    result = await self.hass.async_add_executor_job(
                        lambda: history_component.get_state(self.hass, None, person_entity)
                    )
                    if result:
                        if isinstance(result, dict):
                            states = result.get(person_entity, [])
                        elif isinstance(result, list):
                            states = result
                        else:
                            states = []
                    _LOGGER.debug(f"Retrieved {len(states)} history states via get_state")
                except Exception as e:
                    _LOGGER.debug(f"get_state failed: {e}")
            
            # Method 3: Try using recorder history API directly (when history module is imported)
            if not states:
                try:
                    from datetime import datetime, timedelta
                    from homeassistant.components.recorder import history as recorder_history
                    _LOGGER.debug(f"Trying recorder.history.get_significant_states API for {person_entity}")
                    # Get history from last 365 days
                    end_time = datetime.now()
                    start_time = end_time - timedelta(days=365)
                    
                    # Check if recorder is loaded
                    if 'recorder' not in self.hass.config.components:
                        _LOGGER.debug("Recorder component not loaded, skipping recorder.history API")
                    else:
                        result = await recorder_history.get_significant_states(
                            self.hass,
                            start_time,
                            end_time,
                            [person_entity],
                            significant_changes_only=False
                        )
                        if result and person_entity in result:
                            states = result[person_entity]
                            _LOGGER.info(f"Retrieved {len(states)} history states via recorder.history.get_significant_states")
                except ImportError as e:
                    _LOGGER.debug(f"recorder.history not available: {e}")
                except Exception as e:
                    _LOGGER.debug(f"recorder.history API failed: {e}", exc_info=True)
            
            # Method 4: Try using the state machine's history directly
            if not states:
                try:
                    _LOGGER.debug(f"Trying state machine history for {person_entity}")
                    # Use the history component's state machine access
                    if hasattr(history_component, 'get_significant_states'):
                        from datetime import datetime, timedelta
                        end_time = datetime.now()
                        start_time = end_time - timedelta(days=365)
                        result = await history_component.get_significant_states(
                            self.hass,
                            start_time,
                            end_time,
                            [person_entity],
                            significant_changes_only=False
                        )
                        if result and person_entity in result:
                            states = result[person_entity]
                            _LOGGER.debug(f"Retrieved {len(states)} history states via get_significant_states")
                except Exception as e:
                    _LOGGER.debug(f"get_significant_states failed: {e}")
            
            if not states:
                # Log detailed diagnostics
                available_methods = [m for m in dir(history_component) if not m.startswith('_')]
                _LOGGER.warning(
                    f"Could not retrieve history for {person_entity} using any method. "
                    f"History component type: {type(history_component)}, "
                    f"Available methods: {available_methods[:10]}..."  # Limit to first 10 to avoid huge logs
                )
                _LOGGER.info(
                    f"History component access: "
                    f"hasattr(hass.components, 'history')={hasattr(self.hass, 'components') and hasattr(self.hass.components, 'history')}, "
                    f"'history' in config.components={'history' in self.hass.config.components}, "
                    f"'recorder' in config.components={'recorder' in self.hass.config.components}"
                )
                return list(detected)
            
            # Process states in batches to avoid too many API calls
            coordinates_to_resolve = []
            
            for state in states:
                # Check if state has GPS coordinates
                lat = state.attributes.get("latitude")
                lon = state.attributes.get("longitude")
                
                if lat is not None and lon is not None:
                    coordinates_to_resolve.append((lat, lon))
                
                # Also check zone information
                if state.state and state.state.startswith("zone."):
                    zone_entity = state.state
                    zone_state = self.hass.states.get(zone_entity)
                    if zone_state:
                        zone_lat = zone_state.attributes.get("latitude")
                        zone_lon = zone_state.attributes.get("longitude")
                        if zone_lat is not None and zone_lon is not None:
                            coordinates_to_resolve.append((zone_lat, zone_lon))
            
            # Resolve coordinates to countries (with caching and rate limiting)
            # Process unique coordinates only to minimize API calls
            unique_coords = list(set(coordinates_to_resolve))
            _LOGGER.debug(
                "Processing %d unique coordinates from history (total: %d)",
                len(unique_coords),
                len(coordinates_to_resolve)
            )
            
            # Limit processing to avoid excessive API calls
            # Process max 100 coordinates per update to avoid timeouts
            max_coords = 100
            if len(unique_coords) > max_coords:
                _LOGGER.info(
                    "Limiting history processing to %d coordinates (found %d). "
                    "Consider running detection periodically rather than on every update.",
                    max_coords,
                    len(unique_coords)
                )
                unique_coords = unique_coords[:max_coords]
            
            detected_count = 0
            for lat, lon in unique_coords:
                country_code = await get_country_from_coords(self.hass, lat, lon)
                if country_code:
                    detected.add(country_code)
                    detected_count += 1
                    _LOGGER.debug(f"Detected country {country_code} from coordinates ({lat}, {lon})")
                # No additional delay needed - rate limiting is handled in get_country_from_coords
            
            _LOGGER.info(
                f"History processing complete for {person_entity}: "
                f"{detected_count} countries detected from {len(unique_coords)} coordinates, "
                f"total unique countries: {len(detected)}"
            )
                                
        except Exception as err:
            _LOGGER.warning("Error detecting countries from history: %s", err, exc_info=True)
        
        result = list(detected)
        _LOGGER.debug(f"Returning {len(result)} detected countries: {result}")
        return result


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