"""Lodging & Neighborhood Evaluator Agent for Travel Scout.

Evaluates booked hotels and prospective accommodations against the traveler's
wishlist and scheduled itinerary, scoring walkability, commute times, and neighborhood character.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from database.models import Trip, CitySegment, StayLocation, ItineraryItem
from scout.transit import haversine_km
from scout.geocoding import resolve_city_coordinates, resolve_venue_coordinates


def evaluate_stay_location(
    stay_name: str,
    stay_lat: float,
    stay_lon: float,
    city_name: str,
    items: List[ItineraryItem]
) -> Dict[str, Any]:
    """Evaluates a single accommodation against a set of city activities."""
    if not items:
        return {
            "stay_name": stay_name,
            "walkability_score": 75,
            "verdict": "👍 Ready for Explorations",
            "avg_distance_km": 0.0,
            "within_15min_walk": 0,
            "total_activities": 0,
            "summary": "No activities currently saved for this city segment."
        }

    distances: List[float] = []
    within_walk = 0

    for it in items:
        lat = it.lat
        lon = it.lon
        if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
            d = haversine_km(stay_lat, stay_lon, lat, lon)
            distances.append(d)
            if d <= 1.2:  # ~15 min walk
                within_walk += 1

    avg_d = round(sum(distances) / len(distances), 2) if distances else 0.0
    walk_pct = round((within_walk / max(1, len(distances))) * 100, 1)

    # Score calculation (0 - 100)
    # 100 points: avg distance <= 1km
    # Points decrease as avg distance increases
    base_score = max(20, min(100, int(100 - (avg_d * 12) + (walk_pct * 0.25))))

    if base_score >= 80:
        verdict = "🌟 Prime Cultural Base (Highly Walkable)"
    elif base_score >= 60:
        verdict = "👍 Solid Neighborhood Hub (Short Transit Required)"
    else:
        verdict = "⚠️ High Commute Location (Frequent Transit / Rideshare Needed)"

    return {
        "stay_name": stay_name,
        "walkability_score": base_score,
        "verdict": verdict,
        "avg_distance_km": avg_d,
        "within_15min_walk_count": within_walk,
        "within_15min_walk_pct": walk_pct,
        "total_activities": len(distances),
        "summary": f"{within_walk} of {len(distances)} spots ({walk_pct}%) are within a 15-minute walk. Average commute to activities is {avg_d} km."
    }


def evaluate_trip_lodging(
    db: Session,
    trip_id: str
) -> Dict[str, Any]:
    """Evaluates all current stays in a trip against the itinerary and wishlist."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}

    all_items = db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).all()
    evaluations: List[Dict[str, Any]] = []

    for seg in sorted(trip.city_segments, key=lambda s: s.order_index):
        seg_items = [it for it in all_items if it.city_segment_id == seg.id]
        stays = seg.stays or []

        if not stays:
            evaluations.append({
                "city_name": seg.city_name,
                "status": "No lodging booked yet",
                "message": f"Add a hotel or stay in {seg.city_name} to evaluate walkability and routes."
            })
            continue

        for stay in stays:
            lat = stay.lat
            lon = stay.lon
            if not lat or not lon or (lat == 0.0 and lon == 0.0):
                # Try to resolve stay coords
                lat, lon, _ = resolve_venue_coordinates(stay.name, seg.city_name, seg.country)

            eval_res = evaluate_stay_location(
                stay_name=stay.name,
                stay_lat=lat or 0.0,
                stay_lon=lon or 0.0,
                city_name=seg.city_name,
                items=seg_items
            )
            eval_res["city_name"] = seg.city_name
            eval_res["stay_id"] = stay.id
            eval_res["address"] = stay.address
            eval_res["dates"] = f"{stay.start_date or seg.start_date} to {stay.end_date or seg.end_date}"
            evaluations.append(eval_res)

    return {
        "trip_id": trip_id,
        "trip_title": trip.title,
        "stays_evaluated": len(evaluations),
        "evaluations": evaluations
    }
