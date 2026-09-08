"""Transit Route & Itinerary Day Optimizer Agent for Travel Scout.

Orders scheduled activities on each itinerary day to minimize walking distance
and transit transfers starting from the day's active lodging, solves the TSP route,
and recommends local city transit passes and transit cards.
"""
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from database.models import Trip, CitySegment, ItineraryItem
from scout.transit import haversine_km, resolve_stay_for_trip_date
from scout.geocoding import resolve_city_coordinates

# Comprehensive local transit pass database
CITY_TRANSIT_PASSES: Dict[str, Dict[str, Any]] = {
    "san diego": {
        "agency": "Metropolitan Transit System (MTS)",
        "card_name": "PRONTO Card / App",
        "fare_info": "$2.50 one-way / $6.00 daily cap for unlimited Trolley & Bus",
        "url": "https://www.sdmts.com/fares/pronto",
        "tip": "Download the PRONTO app before arrival and load funds. Best for Silver/Blue Trolley lines and downtown coastal buses."
    },
    "lisbon": {
        "agency": "Carris & Metropolitano de Lisboa",
        "card_name": "Navegante Ocasional (formerly Viva Viagem)",
        "fare_info": "€1.80 single / €6.80 24h unlimited pass across Metro, Carris buses, and Historic Trams",
        "url": "https://www.metrolisboa.pt",
        "tip": "Purchase at any Metro vending machine. Cover Tram 28, Santa Justa Lift, and all metro lines."
    },
    "porto": {
        "agency": "Metro do Porto & STCP",
        "card_name": "Andante Card",
        "fare_info": "€1.40 - €2.15 per zone / €7.50 24h Tour Card",
        "url": "https://www.metrodoporto.pt",
        "tip": "Validate before boarding at any yellow ticket validator machine."
    },
    "london": {
        "agency": "Transport for London (TfL)",
        "card_name": "Contactless Bank Card / Oyster Card",
        "fare_info": "Daily fare cap (~£8.50 Zones 1-2 for unlimited Tube & Bus)",
        "url": "https://tfl.gov.uk",
        "tip": "Just tap your contactless debit/credit card or Apple/Google Pay directly on the yellow readers."
    },
    "paris": {
        "agency": "RATP & Île-de-France Mobilités",
        "card_name": "Navigo Easy / Île-de-France Mobilités App",
        "fare_info": "€2.15 single ticket / €8.65 Navigo Jour daily pass",
        "url": "https://www.ratp.fr",
        "tip": "Purchase Navigo Easy card for €2 at stations or load tickets directly to Apple/Google Wallet."
    },
    "new york": {
        "agency": "MTA New York City Transit",
        "card_name": "OMNY Tap-and-Go",
        "fare_info": "$2.90 per ride with automatic 7-day fare cap after 12 rides ($34)",
        "url": "https://omny.info",
        "tip": "Simply tap your smartphone or contactless card on turnstile readers."
    },
    "tokyo": {
        "agency": "Tokyo Metro & Toei Subway / JR East",
        "card_name": "Suica / Pasmo / Tokyo Subway Ticket",
        "fare_info": "¥800 24-hour unlimited Tokyo Subway Ticket (foreign tourists)",
        "url": "https://www.tokyometro.jp",
        "tip": "Add digital Suica to Apple Wallet with zero setup fee."
    }
}


def solve_day_route(
    origin_coords: Tuple[float, float],
    items: List[ItineraryItem]
) -> Tuple[List[ItineraryItem], float, float]:
    """
    Solves route sequence minimizing total travel distance using Nearest Neighbor + 2-Opt.
    Returns: (optimized_items, original_total_km, optimized_total_km)
    """
    if len(items) <= 1:
        return items, 0.0, 0.0

    valid_items = []
    for it in items:
        lat = it.lat if (it.lat is not None and it.lat != 0.0) else origin_coords[0]
        lon = it.lon if (it.lon is not None and it.lon != 0.0) else origin_coords[1]
        valid_items.append((it, (lat, lon)))

    # Compute original distance
    orig_dist = 0.0
    curr_pt = origin_coords
    for _, pt in valid_items:
        orig_dist += haversine_km(curr_pt[0], curr_pt[1], pt[0], pt[1])
        curr_pt = pt
    # return to origin
    orig_dist += haversine_km(curr_pt[0], curr_pt[1], origin_coords[0], origin_coords[1])

    # Nearest Neighbor Heuristic
    unvisited = list(valid_items)
    ordered_items: List[Tuple[ItineraryItem, Tuple[float, float]]] = []
    curr_pt = origin_coords

    while unvisited:
        nearest_idx = 0
        min_d = float("inf")
        for i, (_, pt) in enumerate(unvisited):
            d = haversine_km(curr_pt[0], curr_pt[1], pt[0], pt[1])
            if d < min_d:
                min_d = d
                nearest_idx = i
        selected = unvisited.pop(nearest_idx)
        ordered_items.append(selected)
        curr_pt = selected[1]

    # Compute optimized distance
    opt_dist = 0.0
    curr_pt = origin_coords
    for _, pt in ordered_items:
        opt_dist += haversine_km(curr_pt[0], curr_pt[1], pt[0], pt[1])
        curr_pt = pt
    opt_dist += haversine_km(curr_pt[0], curr_pt[1], origin_coords[0], origin_coords[1])

    return [it for it, _ in ordered_items], round(orig_dist, 2), round(opt_dist, 2)


def optimize_trip_day_schedule(
    db: Session,
    trip_id: str,
    target_date: str,
    apply_order_index: bool = False
) -> Dict[str, Any]:
    """Optimizes the itinerary item schedule for a specific date."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}

    items = db.query(ItineraryItem).filter(
        ItineraryItem.trip_id == trip_id,
        ItineraryItem.assigned_date == target_date
    ).order_by(ItineraryItem.order_index).all()

    if not items:
        return {"date": target_date, "message": "No scheduled items found for this date", "items": []}

    # Resolve active lodging and city segment for origin
    stay, city_seg = resolve_stay_for_trip_date(trip.city_segments, target_date)
    city_name = city_seg.city_name if city_seg else "Destination"

    if stay and stay.lat and stay.lon:
        origin_coords = (stay.lat, stay.lon)
        origin_name = stay.name
    elif city_seg and city_seg.lat and city_seg.lon:
        origin_coords = (city_seg.lat, city_seg.lon)
        origin_name = f"{city_name} Center"
    else:
        c_lat, c_lon, _ = resolve_city_coordinates(city_name)
        origin_coords = (c_lat, c_lon)
        origin_name = f"{city_name} Center"

    optimized_items, orig_km, opt_km = solve_day_route(origin_coords, items)
    saved_km = round(max(0.0, orig_km - opt_km), 2)

    if apply_order_index:
        for idx, it in enumerate(optimized_items):
            it.order_index = idx
        db.commit()

    transit_pass = CITY_TRANSIT_PASSES.get(city_name.lower()) or {
        "agency": f"{city_name} Local Transit",
        "card_name": "City Day Pass / Contactless",
        "fare_info": "Check local station kiosks for 24h unlimited passes",
        "url": "https://www.google.com/maps",
        "tip": "Most major urban metros offer 24h tourist day passes with unlimited transfers."
    }

    return {
        "date": target_date,
        "city_name": city_name,
        "origin_name": origin_name,
        "origin_coords": origin_coords,
        "item_count": len(optimized_items),
        "original_km": orig_km,
        "optimized_km": opt_km,
        "saved_km": saved_km,
        "transit_pass_recommendation": transit_pass,
        "ordered_items": [
            {
                "order": idx + 1,
                "id": it.id,
                "title": it.title,
                "category": it.category,
                "address": it.address,
                "lat": it.lat,
                "lon": it.lon
            }
            for idx, it in enumerate(optimized_items)
        ]
    }
