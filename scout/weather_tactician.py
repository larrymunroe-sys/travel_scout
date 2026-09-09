"""Smart Weather Re-Scheduler & Packing Tactical Agent for Travel Scout.

Monitors real-time Open-Meteo forecasts for trip dates, issues rain advisories,
proactively suggests swapping outdoor activities with indoor cultural gems,
and generates customized trip packing checklists.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import Trip, CitySegment, ItineraryItem
from scout.weather import fetch_open_meteo_forecast, WMO_WEATHER_MAP
from scout.geocoding import resolve_city_coordinates

OUTDOOR_KEYWORDS = [
    "park", "beach", "garden", "walk", "outdoor", "rooftop", "trail", "hike",
    "market", "flea", "street", "fair", "festival", "carnival", "square",
    "plaza", "pier", "harbor", "zoo", "botanic", "courtyard", "open air"
]

INDOOR_CATEGORIES = [
    "art", "museums", "records", "cafes", "dining", "press",
    "bookstores", "vintage-fashion", "vintage-gear", "home-design", "culinary-goods"
]


def generate_packing_checklist(
    min_temp: float,
    max_temp: float,
    rain_days_count: int,
    total_days: int
) -> List[Dict[str, str]]:
    """Generate dynamic packing checklist based on actual forecasted conditions."""
    checklist: List[Dict[str, str]] = []

    # Rain & weather protection
    if rain_days_count > 0:
        checklist.append({
            "item": "Compact Windproof Umbrella",
            "category": "Weather Protection",
            "reason": f"Rain forecasted on {rain_days_count} day(s) during your stay."
        })
        checklist.append({
            "item": "Lightweight Waterproof Shell / Rain Jacket",
            "category": "Weather Protection",
            "reason": "Allows staying dry during outdoor neighborhood transitions."
        })

    # Cold / Cool weather
    if min_temp < 12.0:
        checklist.append({
            "item": "Warm Layering Pieces (Sweater / Fleece)",
            "category": "Clothing",
            "reason": f"Morning/evening lows dipping to {round(min_temp, 1)}°C."
        })
    if min_temp < 6.0:
        checklist.append({
            "item": "Beanie & Thermal Base Layer",
            "category": "Clothing",
            "reason": "Chilly weather expected."
        })

    # Warm / Hot weather
    if max_temp > 25.0:
        checklist.append({
            "item": "UV-Protection Sunglasses & Sunscreen (SPF 50+)",
            "category": "Sun Protection",
            "reason": f"Warm highs reaching {round(max_temp, 1)}°C."
        })
        checklist.append({
            "item": "Breathable Linen / Lightweight Cottons",
            "category": "Clothing",
            "reason": "Optimal comfort for daytime city walking in the heat."
        })

    # Universal travel items
    checklist.append({
        "item": "Supportive Broken-in Walking Shoes",
        "category": "Footwear",
        "reason": "Essential for cobblestones, transit transfers, and walking tours."
    })
    checklist.append({
        "item": "Portable Power Bank (10,000mAh)",
        "category": "Tech & Gear",
        "reason": "Keeps your phone charged for navigation and digital transit tickets."
    })

    return checklist


def evaluate_trip_weather_advisory(
    db: Session,
    trip_id: str
) -> Dict[str, Any]:
    """
    Evaluates weather risk across all itinerary dates and generates tactical swap recommendations.
    """
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found", "advisories": [], "packing_checklist": []}

    itinerary_items = db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).all()
    wishlist_items = [it for it in itinerary_items if it.assigned_date == "todo"]

    day_advisories: List[Dict[str, Any]] = []
    all_temps_min: List[float] = []
    all_temps_max: List[float] = []
    rain_days = 0

    for seg in sorted(trip.city_segments, key=lambda s: s.order_index):
        lat = seg.lat
        lon = seg.lon
        if not lat or not lon or (lat == 0.0 and lon == 0.0):
            lat, lon, _ = resolve_city_coordinates(seg.city_name, seg.country)

        if not lat or not lon or (lat == 0.0 and lon == 0.0):
            continue

        forecast = fetch_open_meteo_forecast(lat, lon, days=14)
        daily = forecast.get("daily", {})
        dates = daily.get("time", [])
        wcodes = daily.get("weathercode", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precip_probs = daily.get("precipitation_probability_max", [])
        precip_sums = daily.get("precipitation_sum", [])

        for idx, date_str in enumerate(dates):
            # Check if this date falls within segment range or if items are scheduled on it
            assigned_today = [it for it in itinerary_items if it.assigned_date == date_str]
            in_range = (seg.start_date and seg.end_date and seg.start_date <= date_str <= seg.end_date)
            if not in_range and not assigned_today:
                continue

            wcode = wcodes[idx] if idx < len(wcodes) else 0
            t_max = max_temps[idx] if idx < len(max_temps) else 20.0
            t_min = min_temps[idx] if idx < len(min_temps) else 12.0
            p_prob = precip_probs[idx] if idx < len(precip_probs) else 0
            p_sum = precip_sums[idx] if idx < len(precip_sums) else 0.0

            all_temps_min.append(t_min)
            all_temps_max.append(t_max)

            w_info = WMO_WEATHER_MAP.get(wcode, {"icon": "🌤️", "condition": "Partly Cloudy", "rain_risk": False})
            is_rainy = w_info.get("rain_risk", False) or (p_prob is not None and p_prob >= 45) or (p_sum is not None and p_sum >= 2.5)

            if is_rainy:
                rain_days += 1

            # Check outdoor items scheduled today
            outdoor_at_risk: List[Dict[str, Any]] = []
            if is_rainy and assigned_today:
                for it in assigned_today:
                    title_lower = it.title.lower()
                    cat_lower = it.category.lower()
                    is_outdoor = (
                        cat_lower in ["festivals", "markets"] or
                        any(kw in title_lower for kw in OUTDOOR_KEYWORDS)
                    )
                    if is_outdoor:
                        outdoor_at_risk.append({
                            "id": it.id,
                            "title": it.title,
                            "category": it.category,
                            "neighborhood": it.neighborhood
                        })

            # Suggest indoor wishlist swaps if outdoor activities are compromised
            suggested_indoor_swaps: List[Dict[str, Any]] = []
            if outdoor_at_risk and wishlist_items:
                for w in wishlist_items:
                    w_cat = w.category.lower()
                    w_title = w.title.lower()
                    if w_cat in INDOOR_CATEGORIES or "museum" in w_title or "gallery" in w_title:
                        suggested_indoor_swaps.append({
                            "id": w.id,
                            "title": w.title,
                            "category": w.category,
                            "neighborhood": w.neighborhood
                        })
                        if len(suggested_indoor_swaps) >= 3:
                            break

            day_advisories.append({
                "date": date_str,
                "city_name": seg.city_name,
                "icon": w_info["icon"],
                "condition": w_info["condition"],
                "temp_max": t_max,
                "temp_min": t_min,
                "rain_prob": p_prob,
                "precip_mm": p_sum,
                "is_rainy": is_rainy,
                "scheduled_count": len(assigned_today),
                "outdoor_at_risk": outdoor_at_risk,
                "suggested_indoor_swaps": suggested_indoor_swaps
            })

    # Compute packing list
    overall_min = min(all_temps_min) if all_temps_min else 12.0
    overall_max = max(all_temps_max) if all_temps_max else 22.0
    packing_list = generate_packing_checklist(
        min_temp=overall_min,
        max_temp=overall_max,
        rain_days_count=rain_days,
        total_days=len(day_advisories)
    )

    return {
        "trip_id": trip_id,
        "trip_title": trip.title,
        "total_days_evaluated": len(day_advisories),
        "rain_days_count": rain_days,
        "temp_range": {"min_c": round(overall_min, 1), "max_c": round(overall_max, 1)},
        "day_advisories": day_advisories,
        "packing_checklist": packing_list
    }
