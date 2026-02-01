# Countries Visited for Home Assistant

![GitHub release (latest by date)](https://img.shields.io/github/v/release/RorGray/ha-countries-visited-plugin)
![HACS validated](https://img.shields.io/badge/HACS-Default-orange)

This project is based on [suxarik/ha-countries-visited-plugin](https://github.com/suxarik/ha-countries-visited-plugin).

A Home Assistant integration to track and visualize countries visited by family members on an interactive world map.

## Features

- 🌍 **Full World Map** - Interactive SVG map with 250+ countries and territories
- 👤 **Multi-Person Support** - Track visits for multiple people independently
- 🎨 **Customizable Colors** - Configure map, visited, and current location colors
- 🔧 **Manual Management** - Add/remove countries via services
- 📊 **Automatic Tracking** - Detects countries from device_tracker history
- 🎯 **Current Location** - Highlights user's current country with animated border
- 💬 **Tooltips** - Hover over countries to see names
- ✨ **Smooth Animations** - CSS transitions for all interactions
- 🎯 **ISO 3166-1 alpha-2** - Standard country codes (US, GB, DE, FR, etc.)

## Installation

### HACS (Recommended)

1. Add this repository to HACS:
   - Go to **HACS** → **Integrations** → **⋮** → **Add custom repository**
   - Repository: `https://github.com/RorGray/ha-countries-visited-plugin`
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

## Lovelace Card

Add the resource first:

**Configuration** → **Lovelace Dashboards** → **Resources** → **+ Add Resource**

```
URL: /local/community/countries-visited/dist/countries-visited.js
Resource type: JavaScript Module
```

Then add the card to your dashboard:

```yaml
type: custom:countries-map-card
entity: person.your_name
visited_color: '#4CAF50'
map_color: '#d0d0d0'
```

### Card Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | Required | Person entity ID to track |
| `person` | string | Optional | Alias for entity |
| `visited_color` | string | `#4CAF50` | Color for visited countries |
| `current_color` | string | `#FF5722` | Color for current location |
| `map_color` | string | `#d0d0d0` | Color for non-visited countries |
| `title` | string | `Countries Visited` | Card title |

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

### Setting up automatic tracking

1. Ensure you have zones defined for each location
2. The integration will automatically detect when a person enters a zone
3. Country codes are resolved from zone coordinates

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
entity: person.alice
title: Alice's Travels

# Card for person 2  
type: custom:countries-map-card
entity: person.bob
title: Bob's Travels
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

- [GitHub Issues](https://github.com/RorGray/ha-countries-visited-plugin/issues)
- [Home Assistant Community](https://community.home-assistant.io/)