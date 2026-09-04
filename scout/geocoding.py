"""Dynamic city geocoding and coordinate resolver for Travel Scout.

Provides instant offline coordinate lookup for 70+ global destinations, with
graceful live fallback to OpenStreetMap's free Nominatim Geocoding API (no API key required).
"""
import json
import re
import urllib.parse
import urllib.request
from typing import Tuple, Dict, Any, Optional

# Extensive offline city registry covering major global destinations
GLOBAL_CITY_COORDINATES: Dict[str, Dict[str, Any]] = {
    # Portugal
    "lisbon": {"lat": 38.7223, "lon": -9.1393, "country": "Portugal"},
    "lisboa": {"lat": 38.7223, "lon": -9.1393, "country": "Portugal"},
    "porto": {"lat": 41.1579, "lon": -8.6291, "country": "Portugal"},
    "bragança": {"lat": 41.8061, "lon": -6.7567, "country": "Portugal"},
    "braganca": {"lat": 41.8061, "lon": -6.7567, "country": "Portugal"},
    "coimbra": {"lat": 40.2033, "lon": -8.4103, "country": "Portugal"},
    "faro": {"lat": 37.0194, "lon": -7.9322, "country": "Portugal"},
    "sintra": {"lat": 38.8029, "lon": -9.3817, "country": "Portugal"},
    "funchal": {"lat": 32.6669, "lon": -16.9241, "country": "Portugal"},
    
    # Europe
    "paris": {"lat": 48.8566, "lon": 2.3522, "country": "France"},
    "nice": {"lat": 43.7102, "lon": 7.2620, "country": "France"},
    "lyon": {"lat": 45.7640, "lon": 4.8357, "country": "France"},
    "london": {"lat": 51.5074, "lon": -0.1278, "country": "United Kingdom"},
    "edinburgh": {"lat": 55.9533, "lon": -3.1883, "country": "United Kingdom"},
    "rome": {"lat": 41.9028, "lon": 12.4964, "country": "Italy"},
    "florence": {"lat": 43.7696, "lon": 11.2558, "country": "Italy"},
    "venice": {"lat": 45.4408, "lon": 12.3155, "country": "Italy"},
    "milan": {"lat": 45.4642, "lon": 9.1900, "country": "Italy"},
    "madrid": {"lat": 40.4168, "lon": -3.7038, "country": "Spain"},
    "barcelona": {"lat": 41.3879, "lon": 2.1699, "country": "Spain"},
    "seville": {"lat": 37.3891, "lon": -5.9845, "country": "Spain"},
    "berlin": {"lat": 52.5200, "lon": 13.4050, "country": "Germany"},
    "munich": {"lat": 48.1351, "lon": 11.5820, "country": "Germany"},
    "amsterdam": {"lat": 52.3676, "lon": 4.9041, "country": "Netherlands"},
    "vienna": {"lat": 48.2082, "lon": 16.3738, "country": "Austria"},
    "prague": {"lat": 50.0755, "lon": 14.4378, "country": "Czech Republic"},
    "budapest": {"lat": 47.4979, "lon": 19.0402, "country": "Hungary"},
    "athens": {"lat": 37.9838, "lon": 23.7275, "country": "Greece"},
    "dublin": {"lat": 53.3498, "lon": -6.2603, "country": "Ireland"},
    "zurich": {"lat": 47.3769, "lon": 8.5417, "country": "Switzerland"},
    "copenhagen": {"lat": 55.6761, "lon": 12.5683, "country": "Denmark"},
    "stockholm": {"lat": 59.3293, "lon": 18.0686, "country": "Sweden"},
    "oslo": {"lat": 59.9139, "lon": 10.7522, "country": "Norway"},
    "helsinki": {"lat": 60.1699, "lon": 24.9384, "country": "Finland"},

    # North America
    "new york": {"lat": 40.7128, "lon": -74.0060, "country": "United States"},
    "new york city": {"lat": 40.7128, "lon": -74.0060, "country": "United States"},
    "washington, d.c.": {"lat": 38.9072, "lon": -77.0369, "country": "United States"},
    "washington dc": {"lat": 38.9072, "lon": -77.0369, "country": "United States"},
    "washington": {"lat": 38.9072, "lon": -77.0369, "country": "United States"},
    "los angeles": {"lat": 34.0522, "lon": -118.2437, "country": "United States"},
    "san francisco": {"lat": 37.7749, "lon": -122.4194, "country": "United States"},
    "chicago": {"lat": 41.8781, "lon": -87.6298, "country": "United States"},
    "seattle": {"lat": 47.6062, "lon": -122.3321, "country": "United States"},
    "miami": {"lat": 25.7617, "lon": -80.1918, "country": "United States"},
    "boston": {"lat": 42.3601, "lon": -71.0589, "country": "United States"},
    "austin": {"lat": 30.2672, "lon": -97.7431, "country": "United States"},
    "new orleans": {"lat": 29.9511, "lon": -90.0715, "country": "United States"},
    "las vegas": {"lat": 36.1699, "lon": -115.1398, "country": "United States"},
    "honolulu": {"lat": 21.3069, "lon": -157.8583, "country": "United States"},
    "toronto": {"lat": 43.6532, "lon": -79.3832, "country": "Canada"},
    "vancouver": {"lat": 49.2827, "lon": -123.1207, "country": "Canada"},
    "montreal": {"lat": 45.5017, "lon": -73.5673, "country": "Canada"},
    "mexico city": {"lat": 19.4326, "lon": -99.1332, "country": "Mexico"},
    "cancun": {"lat": 21.1619, "lon": -86.8515, "country": "Mexico"},

    # Asia & Pacific
    "tokyo": {"lat": 35.6762, "lon": 139.6503, "country": "Japan"},
    "kyoto": {"lat": 35.0116, "lon": 135.7681, "country": "Japan"},
    "osaka": {"lat": 34.6937, "lon": 135.5023, "country": "Japan"},
    "seoul": {"lat": 37.5665, "lon": 126.9780, "country": "South Korea"},
    "beijing": {"lat": 39.9042, "lon": 116.4074, "country": "China"},
    "shanghai": {"lat": 31.2304, "lon": 121.4737, "country": "China"},
    "hong kong": {"lat": 22.3193, "lon": 114.1694, "country": "Hong Kong"},
    "taipei": {"lat": 25.0330, "lon": 121.5654, "country": "Taiwan"},
    "singapore": {"lat": 1.3521, "lon": 103.8198, "country": "Singapore"},
    "bangkok": {"lat": 13.7563, "lon": 100.5018, "country": "Thailand"},
    "chiang mai": {"lat": 18.7883, "lon": 98.9853, "country": "Thailand"},
    "hanoi": {"lat": 21.0285, "lon": 105.8542, "country": "Vietnam"},
    "ho chi minh city": {"lat": 10.8231, "lon": 106.6297, "country": "Vietnam"},
    "bali": {"lat": -8.3405, "lon": 115.0920, "country": "Indonesia"},
    "sydney": {"lat": -33.8688, "lon": 151.2093, "country": "Australia"},
    "melbourne": {"lat": -37.8136, "lon": 144.9631, "country": "Australia"},
    "auckland": {"lat": -36.8485, "lon": 174.7633, "country": "New Zealand"},

    # Middle East, Latin America, Africa
    "dubai": {"lat": 25.2048, "lon": 55.2708, "country": "United Arab Emirates"},
    "istanbul": {"lat": 41.0082, "lon": 28.9784, "country": "Turkey"},
    "cairo": {"lat": 30.0444, "lon": 31.2357, "country": "Egypt"},
    "cape town": {"lat": -33.9249, "lon": 18.4241, "country": "South Africa"},
    "marrakech": {"lat": 31.6295, "lon": -7.9811, "country": "Morocco"},
    "rio de janeiro": {"lat": -22.9068, "lon": -43.1729, "country": "Brazil"},
    "buenos aires": {"lat": -34.6037, "lon": -58.3816, "country": "Argentina"},
    "santiago": {"lat": -33.4489, "lon": -70.6693, "country": "Chile"},
    "lima": {"lat": -12.0464, "lon": -77.0428, "country": "Peru"},
}

def resolve_city_coordinates(city_name: str, country: Optional[str] = None) -> Tuple[float, float, str]:
    """
    Resolve accurate latitude, longitude, and country for any city in the world.
    
    1. Checks offline global registry first for instant response.
    2. Falls back to free OpenStreetMap Nominatim lookup (no API key required).
    3. Caches lookup dynamically.
    """
    if not city_name:
        return (0.0, 0.0, country or "")

    key = city_name.strip().lower()

    # 1. Check presets
    if key in GLOBAL_CITY_COORDINATES:
        c = GLOBAL_CITY_COORDINATES[key]
        return (c["lat"], c["lon"], country or c.get("country", ""))

    # Normalize name (remove punctuation)
    clean_key = re.sub(r"[^\w\s]", "", key)
    if clean_key in GLOBAL_CITY_COORDINATES:
        c = GLOBAL_CITY_COORDINATES[clean_key]
        return (c["lat"], c["lon"], country or c.get("country", ""))

    # 2. Live geocode using OpenStreetMap Nominatim (Free, no API key required)
    try:
        query = f"{city_name}, {country}" if country else city_name
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "TravelScoutApp/2.0 (collaborative-travel-planner)"}
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                raw_bytes = resp.read()
                data = json.loads(raw_bytes.decode("utf-8"))
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    resolved_country = country or ""
                    # Cache for future calls
                    GLOBAL_CITY_COORDINATES[key] = {
                        "lat": lat,
                        "lon": lon,
                        "country": resolved_country
                    }
                    return (lat, lon, resolved_country)
    except Exception as err:
        print(f"Notice: Nominatim geocoding lookup for '{city_name}' skipped: {err}")

    # 3. Default fallback if geocoding is unavailable
    return (0.0, 0.0, country or "")
