"""Constants for Countries Visited."""
import json
from pathlib import Path

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

# Get version from manifest.json (single source of truth)
def _get_version():
    """Get version from manifest.json."""
    try:
        manifest_path = Path(__file__).parent / "manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
            version = manifest.get("version", "0.1")
            # Remove 'v' prefix if present (manifest has "v0.1", we want "0.1")
            return version.lstrip("v")
    except Exception:
        return "0.1"  # Fallback version

FRONTEND_VERSION = _get_version()

# Frontend constants
URL_BASE = "/hacsfiles/countries-visited"
COUNTRIES_VISITED_CARDS = [
    {
        "name": "Countries Map Data",
        "filename": "map-data.js",
        "version": FRONTEND_VERSION,
    },
    {
        "name": "Countries Map Card",
        "filename": "countries-map-card.js",
        "version": FRONTEND_VERSION,
    },
    {
        "name": "Countries Map Card CSS",
        "filename": "countries-map-card.css",
        "version": FRONTEND_VERSION,
    },
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
