"""Binary sensor platform for Countries Visited."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import event

from .const import CONF_PERSON, CONF_VISITED_COLOR, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Countries Visited binary sensors."""
    person_entity = entry.data[CONF_PERSON]
    
    # Create a binary sensor for the person
    sensor = PersonVisitedAnywhereSensor(hass, entry)
    async_add_entities([sensor])
    
    # Listen for sensor entity changes to update binary sensor
    # Find the sensor entity first, then track it
    def find_sensor_entity():
        """Find the sensor entity for this person."""
        # First try: Use entry_id (standard format)
        sensor_entity_id = f"sensor.countries_visited_{entry.entry_id}"
        state = hass.states.get(sensor_entity_id)
        if state and state.attributes.get("person") == person_entity:
            return sensor_entity_id
        
        # Fallback: Search all countries_visited sensors by person attribute
        for entity_id in hass.states.async_entity_ids("sensor"):
            if entity_id.startswith("sensor.countries_visited_"):
                state = hass.states.get(entity_id)
                if state and state.attributes.get("person") == person_entity:
                    return entity_id
        return None
    
    sensor_entity_id = find_sensor_entity()
    
    if sensor_entity_id:
        @callback
        def handle_sensor_change(event):
            """Handle state change for the sensor entity."""
            if event.data.get("entity_id") == sensor_entity_id:
                sensor.async_schedule_update_ha_state(True)
        
        entry.async_on_unload(
            event.async_track_state_change_event(hass, sensor_entity_id, handle_sensor_change)
        )


class PersonVisitedAnywhereSensor(BinarySensorEntity):
    """Binary sensor to indicate if person has visited any countries."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self._entry = entry
        self._attr_icon = "mdi:map-check"
        
    @property
    def name(self):
        """Return the name of the sensor."""
        person_name = self._entry.data.get(CONF_PERSON, "Unknown")
        return f"Has Visited Countries ({person_name})"

    @property
    def unique_id(self):
        """Return unique ID."""
        return f"countries_visited_anywhere_{self._entry.entry_id}"

    def _find_sensor_entity(self):
        """Find the sensor entity for this person."""
        person_entity = self._entry.data.get(CONF_PERSON)
        
        # First try: Use entry_id (standard format)
        sensor_entity_id = f"sensor.countries_visited_{self._entry.entry_id}"
        state = self.hass.states.get(sensor_entity_id)
        if state and state.attributes.get("person") == person_entity:
            return sensor_entity_id
        
        # Fallback: Search all countries_visited sensors by person attribute
        for entity_id in self.hass.states.async_entity_ids("sensor"):
            if entity_id.startswith("sensor.countries_visited_"):
                state = self.hass.states.get(entity_id)
                if state and state.attributes.get("person") == person_entity:
                    return entity_id
        
        return None

    @property
    def is_on(self):
        """Return true if person has visited at least one country."""
        # Find the sensor entity (with fallback)
        sensor_entity_id = self._find_sensor_entity()
        if not sensor_entity_id:
            return False
        
        state = self.hass.states.get(sensor_entity_id)
        if state:
            visited_countries = state.attributes.get("visited_countries", [])
            return len(visited_countries) > 0
        return False

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        # Find the sensor entity (with fallback)
        person_entity = self._entry.data.get(CONF_PERSON)
        sensor_entity_id = self._find_sensor_entity()
        if not sensor_entity_id:
            return {
                "person": person_entity,
                "sensor_entity": None,
            }
        
        state = self.hass.states.get(sensor_entity_id)
        if state:
            visited_countries = state.attributes.get("visited_countries", [])
            return {
                "visited_countries": visited_countries,
                "count": len(visited_countries),
                "person": person_entity,
                "sensor_entity": sensor_entity_id,
            }
        return {
            "person": person_entity,
            "sensor_entity": sensor_entity_id,
        }
    
    async def async_update(self):
        """Update the binary sensor state."""
        # Trigger state update to refresh is_on property
        self.async_schedule_update_ha_state()


# Individual country binary sensors factory
class CountryVisitedSensor(BinarySensorEntity):
    """Binary sensor for a specific country."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, country_code: str, country_name: str):
        self.hass = hass
        self._entry = entry
        self._country_code = country_code
        self._country_name = country_name
        self._attr_icon = "mdi:map-marker"

    @property
    def name(self):
        """Return the name of the sensor."""
        person_name = self._entry.data.get(CONF_PERSON, "Unknown")
        return f"Visited {self._country_name} ({person_name})"

    @property
    def unique_id(self):
        """Return unique ID."""
        return f"visited_{self._country_code}_{self._entry.entry_id}"

    @property
    def is_on(self):
        """Return true if person has visited this country."""
        # Read from the sensor entity, not the person entity
        sensor_entity_id = f"sensor.countries_visited_{self._entry.entry_id}"
        state = self.hass.states.get(sensor_entity_id)
        if state:
            visited_countries = state.attributes.get("visited_countries", [])
            return self._country_code in visited_countries
        return False
