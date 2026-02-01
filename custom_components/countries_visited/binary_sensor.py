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
    sensor_entity_id = f"sensor.countries_visited_{entry.entry_id}"
    
    @callback
    def handle_sensor_change(entity_id, old_state, new_state):
        if entity_id == sensor_entity_id:
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

    @property
    def is_on(self):
        """Return true if person has visited at least one country."""
        # Read from the sensor entity, not the person entity
        sensor_entity_id = f"sensor.countries_visited_{self._entry.entry_id}"
        state = self.hass.states.get(sensor_entity_id)
        if state:
            visited_countries = state.attributes.get("visited_countries", [])
            return len(visited_countries) > 0
        return False

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        # Read from the sensor entity, not the person entity
        person_entity = self._entry.data.get(CONF_PERSON)
        sensor_entity_id = f"sensor.countries_visited_{self._entry.entry_id}"
        state = self.hass.states.get(sensor_entity_id)
        if state:
            visited_countries = state.attributes.get("visited_countries", [])
            return {
                "visited_countries": visited_countries,
                "count": len(visited_countries),
                "person": person_entity,
            }
        return {}
    
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
