"""Sensor platform for Countries Visited."""
from __future__ import annotations

from datetime import timedelta
import json
import logging
import os

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import event

from .const import CONF_PERSON, DOMAIN, ISO_TO_NAME

_LOGGER = logging.getLogger(__name__)

# Cache for loaded country data
_COUNTRIES_DATA_CACHE = None
_COUNTRIES_DATA_PATH = "www/community/countries-visited/dist/countries-data.json"


def _load_countries_data(hass):
    """Load country data from JSON file."""
    global _COUNTRIES_DATA_CACHE
    if _COUNTRIES_DATA_CACHE is not None:
        return _COUNTRIES_DATA_CACHE
    
    try:
        config_path = hass.config.path(_COUNTRIES_DATA_PATH)
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
            # Convert to dict for faster lookup: {code: {lat, lon, radius}}
            _COUNTRIES_DATA_CACHE = {
                c["id"]: {"lat": c["lat"], "lon": c["lon"], "radius": c["radius"]}
                for c in data
                if "lat" in c and "lon" in c and "radius" in c
            }
            _LOGGER.info("Loaded %d countries from data file", len(_COUNTRIES_DATA_CACHE))
            return _COUNTRIES_DATA_CACHE
    except Exception as err:
        _LOGGER.warning("Failed to load countries data from file: %s", err)
    
    return {}


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers using Haversine formula."""
    import math
    
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def get_country_from_coords(hass, lat, lon):
    """Determine country code from GPS coordinates using data from file."""
    country_boundaries = _load_countries_data(hass)
    if not country_boundaries:
        return None
    
    for code, data in country_boundaries.items():
        distance = haversine_distance(lat, lon, data["lat"], data["lon"])
        if distance <= data["radius"]:
            return code
    return None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Countries Visited sensor."""
    person_entity = entry.data[CONF_PERSON]
    
    sensor = CountriesVisitedSensor(hass, entry)
    async_add_entities([sensor])

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
            
        # Get country names for display
        country_names = [
            ISO_TO_NAME.get(code, code) for code in visited_countries
        ]
        
        # Get current location for current country detection
        current_country = await self._get_current_country(person_entity)
        
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
        
        return get_country_from_coords(self.hass, lat, lon)

    async def _detect_countries_from_history(self, person_entity):
        """Detect countries from device_tracker history."""
        detected = set()
        
        try:
            # Check if history component is available
            if not hasattr(self.hass, 'components') or not hasattr(self.hass.components, 'history'):
                _LOGGER.debug("History component not available")
                return list(detected)
            
            history_component = self.hass.components.history
            
            # Use async API if available (HA 2022.4+)
            if hasattr(history_component, 'async_get_state'):
                # Newer HA versions (2022.4+)
                state = await history_component.async_get_state(self.hass, None, person_entity)
                states = state if state else []
            else:
                # Legacy API fallback
                try:
                    states = await self.hass.async_add_executor_job(
                        lambda: history_component.get_state(self.hass, None, person_entity)
                    )
                    states = states.get(person_entity, []) if states else []
                except Exception:
                    _LOGGER.debug("Could not fetch history")
                    return list(detected)
            
            for state in states:
                # Check if state has GPS coordinates
                lat = state.attributes.get("latitude")
                lon = state.attributes.get("longitude")
                
                if lat is not None and lon is not None:
                    country_code = get_country_from_coords(self.hass, lat, lon)
                    if country_code:
                        detected.add(country_code)
                
                # Also check zone information
                if state.state and state.state.startswith("zone."):
                    zone_entity = state.state
                    zone_state = self.hass.states.get(zone_entity)
                    if zone_state:
                        zone_lat = zone_state.attributes.get("latitude")
                        zone_lon = zone_state.attributes.get("longitude")
                        if zone_lat is not None and zone_lon is not None:
                            country_code = get_country_from_coords(self.hass, zone_lat, zone_lon)
                            if country_code:
                                detected.add(country_code)
                                
        except Exception as err:
            _LOGGER.warning("Error detecting countries from history: %s", err)
        
        return list(detected)