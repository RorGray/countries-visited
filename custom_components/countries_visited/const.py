"""Constants for Countries Visited."""
DOMAIN = "countries_visited"
PLATFORMS = ["sensor", "binary_sensor"]

# Configuration keys
CONF_PERSON = "person"
CONF_MAP_COLOR = "map_color"
CONF_VISITED_COLOR = "visited_color"
CONF_ACCESS_TOKEN = "access_token"

# Default colors
DEFAULT_MAP_COLOR = "#e0e0e0"
DEFAULT_VISITED_COLOR = "#4CAF50"

# Frontend constants
URL_BASE = "/hacsfiles/countries-visited"
COUNTRIES_VISITED_CARDS = [
    {
        "name": "Countries Map Data",
        "filename": "map-data.js",
        "version": "0.1.0",
    },
    {
        "name": "Countries Map Card",
        "filename": "countries-map-card.js",
        "version": "0.1.0",
    }
]

# ISO country code mapping (partial - for key countries)
ISO_TO_NAME = {
    "US": "United States",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "ES": "Spain",
    "IT": "Italy",
    "RU": "Russia",
    "CN": "China",
    "JP": "Japan",
    "AU": "Australia",
    "CA": "Canada",
    "BR": "Brazil",
    "MX": "Mexico",
    "IN": "India",
    "KR": "South Korea",
    "NL": "Netherlands",
    "BE": "Belgium",
    "CH": "Switzerland",
    "AT": "Austria",
    "PT": "Portugal",
    "SE": "Sweden",
    "NO": "Norway",
    "FI": "Finland",
    "DK": "Denmark",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "HU": "Hungary",
    "GR": "Greece",
    "TR": "Turkey",
    "EG": "Egypt",
    "ZA": "South Africa",
    "AE": "United Arab Emirates",
    "TH": "Thailand",
    "SG": "Singapore",
    "MY": "Malaysia",
    "ID": "Indonesia",
    "PH": "Philippines",
    "VN": "Vietnam",
    "NZ": "New Zealand",
    "IL": "Israel",
    "SA": "Saudi Arabia",
    "Qatar": "QA",
    "KU": "KW",
}
