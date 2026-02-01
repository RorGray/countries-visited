# Countries Visited for Home Assistant

![GitHub release (latest by date)](https://img.shields.io/github/v/release/RorGray/countries-visited?style=for-the-badge)
![HACS validated](https://img.shields.io/badge/HACS-Default-orange?style=for-the-badge)

A Home Assistant integration to track and visualize countries visited by family members on an interactive world map.

## Features

- 🌍 **Full World Map** - Interactive SVG map with 250+ countries and territories
- 👤 **Multi-Person Support** - Track visits for multiple people independently
- 🎨 **Customizable Colors** - Configure map, visited, and current location colors
- 🔧 **Manual Management** - Add/remove countries via services
- 📊 **Automatic Tracking** - Detects countries from device_tracker history using reverse geocoding
- 🗺️ **Reverse Geocoding** - Converts GPS coordinates to country codes using Nominatim (OpenStreetMap)
- 📈 **Cache Statistics** - Monitor geocoding cache performance with dedicated sensor
- 🎯 **Current Location** - Highlights user's current country with animated border
- 💬 **Tooltips** - Hover over countries to see names
- ✨ **Smooth Animations** - CSS transitions for all interactions
- 🎯 **ISO 3166-1 alpha-2** - Standard country codes (US, GB, DE, FR, etc.)

## Installation

### HACS

1. Add this repository to HACS:
   - Go to **HACS** → **Integrations** → **⋮** → **Add custom repository**
   - Repository: `https://github.com/RorGray/countries-visited`
   - Category: **Integration**
2. Install "Countries Visited" from HACS
3. Restart Home Assistant

## Configuration

### Via UI

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Countries Visited"
4. Select the person to track
5. Configure colors (optional)
6. **Access Token** (optional but recommended):
   - Create a long-lived access token: **Profile** → **Long-Lived Access Tokens** → **Create Token**
   - Copy the token and paste it in the integration configuration
   - **Required for automatic history detection** - Without it, the integration will still work for:
     - Current location detection (based on person's current GPS coordinates)
     - Manual country management (via services)
   - History detection from past locations will be skipped without a token

## Lovelace Card

The JavaScript file is loaded automatically via the integration's frontend configuration.

Add the card to your dashboard:

```yaml
type: custom:countries-map-card
entity: sensor.countries_visited_person_your_name
visited_color: '#4CAF50'
map_color: '#d0d0d0'
```

**Note**: The card accepts either the sensor entity (`sensor.countries_visited_*`) or the person entity (`person.*`). If you provide a person entity, the card will automatically find the corresponding sensor entity.

### Card Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | Required | Sensor entity ID (`sensor.countries_visited_*`) or person entity ID (`person.*`) |
| `person` | string | Optional | Alias for entity (deprecated, use `entity` instead) |
| `visited_color` | string | `#4CAF50` | Color for visited countries |
| `current_color` | string | `#FF5722` | Color for current location |
| `map_color` | string | `#d0d0d0` | Color for non-visited countries |
| `title` | string | `Countries Visited` | Card title |

## Sensors

The integration creates two sensor entities for each configured person:

### `sensor.countries_visited_{person_name}`

Main sensor tracking visited countries.

**State**: Number of visited countries

**Attributes**:
- `visited_countries`: List of ISO country codes (e.g., `["US", "GB", "DE"]`)
- `visited_countries_names`: List of country names (e.g., `["United States", "United Kingdom", "Germany"]`)
- `person`: Person entity ID being tracked
- `detected_from_history`: Countries automatically detected from history
- `manual_countries`: Countries manually added via services
- `current_country`: Current country code based on person's GPS location

### `sensor.geocoding_cache_statistics_{entry_id}`

Cache performance sensor for reverse geocoding.

**State**: Cache hit rate (percentage)

**Attributes**:
- `cache_size`: Number of cached coordinate entries
- `cache_hits`: Number of times cache was used (no API call needed)
- `cache_misses`: Number of times API was called
- `api_calls`: Total API calls made to Nominatim
- `total_requests`: Total geocoding requests processed
- `hit_rate`: Cache hit rate percentage

**Example**: A hit rate of 85% means 85% of geocoding requests were served from cache, reducing API calls by 85%.

## Services

### `countries_visited.add_country`

Add a country to a person's visited list.

```yaml
service: countries_visited.add_country
data:
  person: person.your_name
  country_code: US
```

### `countries_visited.remove_country`

Remove a country from a person's visited list.

```yaml
service: countries_visited.remove_country
data:
  person: person.your_name
  country_code: US
```

### `countries_visited.set_countries`

Set the complete list of visited countries (replaces existing).

```yaml
service: countries_visited.set_countries
data:
  person: person.your_name
  country_codes:
    - US
    - GB
    - DE
    - FR
```

## Automatic Tracking

The integration can automatically detect countries from:
- `device_tracker` history with GPS coordinates
- Home Assistant zones with latitude/longitude
- Current GPS location from person entities

### Reverse Geocoding

The integration uses **reverse geocoding** to convert GPS coordinates (latitude/longitude) into country codes. This is powered by:

- **Nominatim** (OpenStreetMap) - Free, open-source geocoding service
- **No API key required** - Works out of the box
- **Intelligent caching** - Coordinates are cached to minimize API calls
- **Rate limiting** - Respects Nominatim's 1 request/second limit

#### How it works:

1. The integration extracts GPS coordinates from:
   - Device tracker history states
   - Zone coordinates when a person enters a zone
   - Current location from person entity attributes
2. Coordinates are rounded to ~1km precision for efficient caching
3. Each unique coordinate is reverse geocoded to determine the country code
4. Results are cached to avoid redundant API calls

### Setting up automatic tracking

1. **Create a long-lived access token** (required for history detection):
   - Go to **Profile** → **Long-Lived Access Tokens** → **Create Token**
   - Give it a name (e.g., "Countries Visited")
   - Copy the token
   - Add it in the integration settings: **Settings** → **Devices & Services** → **Countries Visited** → **Configure** → **Access Token**
2. Ensure your person entities have GPS coordinates (latitude/longitude attributes)
3. The integration will automatically process history and detect countries
4. Country codes are resolved from coordinates using reverse geocoding
5. Results are cached for future use

**Note**: 
- **Without an access token**: The integration will still work for current location detection and manual country management, but history detection will be skipped.
- Processing large amounts of history may take time due to rate limiting. The integration processes up to 100 unique coordinates per update to prevent timeouts.

## Country Codes

Use ISO 3166-1 alpha-2 country codes:
- `US` - United States
- `GB` - United Kingdom
- `DE` - Germany
- `FR` - France
- ... and more

## Multiple Cards

You can create multiple cards for different people:

```yaml
# Card for person 1
type: custom:countries-map-card
entity: sensor.countries_visited_person_alice
title: Alice's Travels

# Card for person 2  
type: custom:countries-map-card
entity: sensor.countries_visited_person_bob
title: Bob's Travels
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## Credits

This project uses the following open-source resources:

- **Base Project**: Based on [suxarik/ha-countries-visited-plugin](https://github.com/suxarik/ha-countries-visited-plugin) (MIT License)
- **World Map**: World vector map from [mapsvg.com](https://mapsvg.com). Any use, including commercial, is allowed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Country Data**: Country information from [raphaellepuschitz/SVG-World-Map](https://github.com/raphaellepuschitz/SVG-World-Map/) (MIT License)

## License

This project is licensed under the [MIT License](https://opensource.org/license/MIT).

## Support

- [GitHub Issues](https://github.com/RorGray/countries-visited/issues)
- [Home Assistant Community](https://community.home-assistant.io/)