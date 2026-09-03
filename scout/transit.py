"""Dynamic transit, mileage, and date-aware stay matching for any destination city."""
import math
from typing import Optional, List, Dict, Any

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in kilometers."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def resolve_stay_for_date(stays: List[Any], target_date: Optional[str]) -> Optional[Any]:
    """
    Select the active accommodation / hotel for a specific date.
    Enables switching hotels midway through a city stay!
    """
    if not stays:
        return None

    if not target_date or target_date == "todo":
        return stays[0]

    # Look for exact date range match
    for s in stays:
        if s.start_date and s.end_date:
            if s.start_date <= target_date <= s.end_date:
                return s

    # Fallback to closest or first stay
    return stays[0]

def calculate_transit_from_stay(
    stay: Optional[Any],
    venue_lat: Optional[float],
    venue_lon: Optional[float],
    city_name: str = "Lisbon"
) -> Dict[str, Any]:
    """
    Calculate accurate distance (km & miles) and transit recommendations
    relative to the specific hotel active on that date.
    """
    if not stay or stay.lat is None or stay.lon is None or venue_lat is None or venue_lon is None:
        return {
            "stay_name": stay.name if stay else "City Center",
            "miles": 1.0,
            "km": 1.6,
            "walk_time": "20 mins",
            "best_mode": f"Local {city_name} transit / walk",
            "summary": f"Check local transit directions from {stay.name if stay else city_name}."
        }

    km = haversine_km(stay.lat, stay.lon, venue_lat, venue_lon)
    # Walking route factor (roads aren't straight lines, approx 1.25x)
    walking_km = km * 1.25
    miles = round(walking_km * 0.621371, 1)
    km_rounded = round(walking_km, 1)

    # Average walking speed 4.8 km/h = 80 m/min = ~12.5 mins per km
    walk_mins = int(walking_km * 12.5)

    if walk_mins <= 5:
        walk_time_str = f"{walk_mins} min walk"
        best_mode = f"Direct Walk ({walk_mins} mins)"
        summary = f"Steps away from {stay.name} ({walk_mins} min walk)."
    elif walk_mins <= 25:
        walk_time_str = f"{walk_mins} min walk"
        best_mode = f"Scenic Walk ({walk_mins} mins)"
        summary = f"Pleasant {walk_mins} min walk ({miles} mi) through {city_name} from {stay.name}."
    else:
        hours = walk_mins // 60
        rem_mins = walk_mins % 60
        walk_time_str = f"{hours}h {rem_mins}m walk" if hours > 0 else f"{walk_mins} mins"

        if "Lisbon" in city_name:
            metro_mins = max(10, int(km * 3) + 6)
            best_mode = f"Lisbon Metro / Tram ({metro_mins} mins)"
            summary = f"Take Metro or Tram from near {stay.name} (~{metro_mins} mins total)."
        elif "Porto" in city_name:
            metro_mins = max(10, int(km * 3) + 5)
            best_mode = f"Metro do Porto / Uber ({metro_mins} mins)"
            summary = f"Direct Metro or quick Uber from {stay.name} across Gaia/Porto (~{metro_mins} mins)."
        elif "Bragança" in city_name:
            bus_mins = max(8, int(km * 4) + 4)
            best_mode = f"STUB Bus / Taxi ({bus_mins} mins)"
            summary = f"Quick 6-min drive or urban bus from {stay.name} to the citadel."
        else:
            best_mode = f"Transit / Rideshare ({max(10, int(km * 3))} mins)"
            summary = f"Take local transit or rideshare from {stay.name} ({miles} mi)."

    return {
        "stay_name": stay.name,
        "stay_address": stay.address,
        "miles": miles,
        "km": km_rounded,
        "walk_time": walk_time_str,
        "best_mode": best_mode,
        "summary": summary
    }
