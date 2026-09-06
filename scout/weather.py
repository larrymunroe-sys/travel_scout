"""Free Open-Meteo Weather Integration for Travel Scout Itinerary Days.

Fetches 7-14 day high-resolution weather forecasts for itinerary cities without
requiring any API keys, provides WMO weather condition icons, temperatures, rain
probabilities, and automated indoor swap suggestions for rainy days.
"""
import json
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional, List

# WMO Weather interpretation code mapping
WMO_WEATHER_MAP: Dict[int, Dict[str, Any]] = {
    0: {"icon": "☀️", "condition": "Clear Sky", "rain_risk": False},
    1: {"icon": "🌤️", "condition": "Mainly Sunny", "rain_risk": False},
    2: {"icon": "⛅", "condition": "Partly Cloudy", "rain_risk": False},
    3: {"icon": "☁️", "condition": "Overcast", "rain_risk": False},
    45: {"icon": "🌫️", "condition": "Foggy", "rain_risk": False},
    48: {"icon": "🌫️", "condition": "Depositing Rime Fog", "rain_risk": False},
    51: {"icon": "🌦️", "condition": "Light Drizzle", "rain_risk": False},
    53: {"icon": "🌦️", "condition": "Moderate Drizzle", "rain_risk": False},
    55: {"icon": "🌧️", "condition": "Dense Drizzle", "rain_risk": True},
    61: {"icon": "🌧️", "condition": "Slight Rain", "rain_risk": True},
    63: {"icon": "🌧️", "condition": "Moderate Rain", "rain_risk": True},
    65: {"icon": "🌧️", "condition": "Heavy Rain", "rain_risk": True},
    71: {"icon": "🌨️", "condition": "Slight Snow", "rain_risk": True},
    73: {"icon": "🌨️", "condition": "Moderate Snow", "rain_risk": True},
    75: {"icon": "❄️", "condition": "Heavy Snow", "rain_risk": True},
    80: {"icon": "🌦️", "condition": "Slight Rain Showers", "rain_risk": True},
    81: {"icon": "🌧️", "condition": "Moderate Rain Showers", "rain_risk": True},
    82: {"icon": "⛈️", "condition": "Violent Rain Showers", "rain_risk": True},
    95: {"icon": "⛈️", "condition": "Thunderstorm", "rain_risk": True},
    96: {"icon": "⛈️", "condition": "Thunderstorm with Hail", "rain_risk": True},
    99: {"icon": "⛈️", "condition": "Severe Thunderstorm with Hail", "rain_risk": True},
}

_WEATHER_CACHE: Dict[str, Any] = {}

def fetch_open_meteo_forecast(lat: float, lon: float, days: int = 14) -> Dict[str, Any]:
    """Fetch real-time daily forecast from Open-Meteo (free, no API key)."""
    if lat == 0.0 and lon == 0.0:
        return {}

    cache_key = f"{round(lat, 2)}_{round(lon, 2)}"
    if cache_key in _WEATHER_CACHE:
        return _WEATHER_CACHE[cache_key]

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&daily="
        f"weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum&"
        f"timezone=auto&forecast_days={days}"
    )

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "TravelScoutApp/2.0 (itinerary-weather-forecast)"}
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                daily = data.get("daily", {})
                dates = daily.get("time", [])
                codes = daily.get("weathercode", [])
                max_temps = daily.get("temperature_2m_max", [])
                min_temps = daily.get("temperature_2m_min", [])
                rain_probs = daily.get("precipitation_probability_max", [])

                result_by_date = {}
                for idx, dt in enumerate(dates):
                    code = codes[idx] if idx < len(codes) else 0
                    mapping = WMO_WEATHER_MAP.get(code, {"icon": "🌤️", "condition": "Fair", "rain_risk": False})
                    rain_prob = rain_probs[idx] if idx < len(rain_probs) else 0
                    is_rain_alert = mapping["rain_risk"] or (rain_prob is not None and rain_prob >= 50)
                    max_c = round(max_temps[idx], 1) if idx < len(max_temps) and max_temps[idx] is not None else None
                    min_c = round(min_temps[idx], 1) if idx < len(min_temps) and min_temps[idx] is not None else None
                    max_f = round((max_c * 9/5) + 32, 1) if max_c is not None else None
                    min_f = round((min_c * 9/5) + 32, 1) if min_c is not None else None
                    advisory = (
                        "💡 High chance of rain: Perfect day to swap outdoor walks with indoor museums, wine lodges, or covered markets!"
                        if is_rain_alert
                        else f"Pleasant conditions for exploring ({mapping['condition']})"
                    )

                    result_by_date[dt] = {
                        "date": dt,
                        "temp_max": max_c,
                        "temp_min": min_c,
                        "temp_max_c": max_c,
                        "temp_min_c": min_c,
                        "temp_max_f": max_f,
                        "temp_min_f": min_f,
                        "rain_prob": rain_prob if rain_prob is not None else 0,
                        "precipitation_probability_max": rain_prob if rain_prob is not None else 0,
                        "weather_code": code,
                        "icon": mapping["icon"],
                        "condition": mapping["condition"],
                        "rain_alert": is_rain_alert,
                        "is_rainy": is_rain_alert,
                        "suggestion": advisory,
                        "advisory": advisory
                    }

                _WEATHER_CACHE[cache_key] = result_by_date
                return result_by_date
    except Exception as err:
        print(f"Notice: Open-Meteo forecast skipped for ({lat}, {lon}): {err}")

    return {}


def get_trip_weather(city_segments: List[Any]) -> Dict[str, Any]:
    """Build a consolidated date-keyed weather lookup across all trip destination stops."""
    consolidated: Dict[str, Any] = {}

    for city in city_segments:
        if city.lat and city.lon:
            forecast = fetch_open_meteo_forecast(city.lat, city.lon)
            for dt, w_info in forecast.items():
                if dt not in consolidated:
                    info_copy = dict(w_info)
                    info_copy["city_name"] = city.city_name
                    consolidated[dt] = info_copy

    return consolidated
