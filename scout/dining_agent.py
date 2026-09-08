"""Culinary & Hidden Gems Scout Agent for Travel Scout.

Discovers authentic neighborhood eateries, bakeries, third-wave coffee roasters,
iconic local specialties, and craft cocktail bars, avoiding generic tourist traps.
"""
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session

from database.models import CitySegment, ItineraryItem
from scout.web_search import live_city_search
from scout.geocoding import resolve_venue_coordinates
from scout.transit import generate_directions_url
from scout.backup import compute_item_hash, is_item_deleted_and_unchanged, auto_backup_on_change

DINING_SCAN_QUERIES: Dict[str, Dict[str, Any]] = {
    "coffee": {
        "category": "cafes",
        "channel": "cafes",
        "queries": [
            "specialty coffee roasters third wave cafe best espresso",
            "independent neighborhood coffee shop pour over"
        ]
    },
    "bakeries": {
        "category": "cafes",
        "channel": "cafes",
        "queries": [
            "artisan sourdough bakery morning pastries croissants",
            "traditional neighborhood pastry shop bakery"
        ]
    },
    "casual": {
        "category": "dining",
        "channel": "dining",
        "queries": [
            "essential neighborhood casual eats street food local favorite",
            "iconic casual dining sandwich shop tacos noodles"
        ]
    },
    "dinner": {
        "category": "dining",
        "channel": "dining",
        "queries": [
            "best neighborhood restaurants Eater 38 Bib Gourmand local food",
            "acclaimed independent bistro farm to table dinner"
        ]
    },
    "cocktails": {
        "category": "gems",
        "channel": "nightlife",
        "queries": [
            "craft cocktail bar speakeasy natural wine bar intimate",
            "best neighborhood aperitivo cocktail lounge"
        ]
    }
}


def hunt_dining_spots(
    city_name: str,
    country: Optional[str] = None,
    categories: Optional[List[str]] = None,
    max_per_type: int = 3,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    """Subagent 1: Culinary Hunter (Parallel Category Web Search)."""
    types_to_scan = categories or list(DINING_SCAN_QUERIES.keys())
    discovered: List[Dict[str, Any]] = []
    seen_titles = set()

    def _scan_category(cat_key: str) -> List[Dict[str, Any]]:
        cfg = DINING_SCAN_QUERIES.get(cat_key)
        if not cfg:
            return []
        cat = cfg["category"]
        channel = cfg["channel"]
        queries = cfg["queries"]
        hits: List[Dict[str, Any]] = []

        for q in queries[:2]:
            try:
                results = live_city_search(
                    city_name=city_name,
                    query=q,
                    channel=channel,
                    category_hint=cat,
                    max_results=max_per_type
                )
                for h in results:
                    title = (h.get("title") or "").strip()
                    if not title:
                        continue
                    h["title"] = title
                    h["category"] = cat
                    h["dining_type"] = cat_key
                    hits.append(h)
            except Exception as err:
                print(f"Notice: Dining hunter failed for {city_name} on {cat_key} ('{q}'): {err}")
        return hits

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_scan_category, t): t for t in types_to_scan}
        for future in as_completed(futures):
            try:
                for h in future.result():
                    norm = h["title"].lower()
                    if norm not in seen_titles:
                        seen_titles.add(norm)
                        discovered.append(h)
            except Exception as err:
                print(f"Notice: Dining hunter worker error: {err}")

    return discovered


def enrich_dining_venues(
    events: List[Dict[str, Any]],
    city_name: str,
    country: Optional[str] = None,
    stay: Optional[Any] = None,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    """Subagent 2: Venue Geocoder & Route Builder."""
    if not events:
        return []

    def _enrich_single(ev: Dict[str, Any]) -> Dict[str, Any]:
        venue_name = ev.get("title", "")
        lat, lon, address = resolve_venue_coordinates(venue_name, city_name, country)
        ev["lat"] = lat
        ev["lon"] = lon
        ev["address"] = address
        ev["neighborhood"] = ev.get("neighborhood") or f"{city_name} Dining District"

        # Rule 2 compliant directions from lodging
        dir_links = generate_directions_url(
            stay=stay,
            city_name=city_name,
            venue_lat=lat,
            venue_lon=lon,
            venue_title=venue_name,
            venue_address=address
        )
        ev["directions_url"] = dir_links["transit_url"]
        ev["walking_url"] = dir_links["walking_url"]
        return ev

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_enrich_single, events))


def curate_and_ingest_dining(
    db: Session,
    trip_id: str,
    city_segment_id: str,
    user_id: str,
    events: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Subagent 3: Curator & Database Ingester."""
    new_items: List[Dict[str, Any]] = []
    for ev in events:
        ev_title = (ev.get("title") or "").strip()
        if not ev_title:
            continue

        exists = db.query(ItineraryItem).filter(
            ItineraryItem.trip_id == trip_id,
            ItineraryItem.title == ev_title
        ).first()

        if not exists:
            cand_desc = ev.get("description")
            cand_hl = ev.get("highlight") or f"Recommended {ev.get('dining_type', 'dining')} spot in {ev.get('neighborhood', 'the city')}."
            cand_cost = ev.get("cost", "$$")
            cand_time = ev.get("time_info", "Check restaurant hours")
            cand_addr = ev.get("address", "")
            cand_url = ev.get("url")

            cand_hash = compute_item_hash(
                title=ev_title,
                description=cand_desc,
                highlight=cand_hl,
                address=cand_addr,
                cost=cand_cost,
                time_info=cand_time,
                url=cand_url
            )
            if is_item_deleted_and_unchanged(db, trip_id, ev_title, cand_hash):
                continue

            item = ItineraryItem(
                trip_id=trip_id,
                city_segment_id=city_segment_id,
                title=ev_title,
                category=ev.get("category", "dining"),
                neighborhood=ev.get("neighborhood", "Dining District"),
                address=cand_addr,
                lat=ev.get("lat"),
                lon=ev.get("lon"),
                cost=cand_cost,
                is_free=False,
                time_info=cand_time,
                highlight=cand_hl,
                description=cand_desc,
                url=cand_url,
                source_platform=ev.get("source_platform", "Dining Scout"),
                assigned_date="todo",
                added_by_user_id=user_id
            )
            db.add(item)
            new_items.append(ev)

    if new_items:
        db.commit()
        auto_backup_on_change(db)
    return new_items


def run_dining_agent_for_city_segment(
    db: Session,
    trip_id: str,
    city_id: str,
    user_id: str,
    categories: Optional[List[str]] = None,
    max_per_type: int = 3,
    enrich_locations: bool = True
) -> Dict[str, Any]:
    """Autonomous execution of the Culinary & Hidden Gems Scout Agent."""
    city_seg = db.query(CitySegment).filter(
        CitySegment.id == city_id,
        CitySegment.trip_id == trip_id
    ).first()

    if not city_seg:
        return {"error": "City segment not found in trip", "newly_discovered": 0, "items": []}

    city_name = city_seg.city_name
    country = city_seg.country
    active_stay = city_seg.stays[0] if (city_seg.stays and len(city_seg.stays) > 0) else None

    # 1. Hunt dining spots in parallel
    raw_spots = hunt_dining_spots(
        city_name=city_name,
        country=country,
        categories=categories,
        max_per_type=max_per_type
    )

    # 2. Enrich locations and transit
    enriched_spots = enrich_dining_venues(
        events=raw_spots,
        city_name=city_name,
        country=country,
        stay=active_stay
    ) if enrich_locations else raw_spots

    # 3. Curate & Ingest into database
    new_items = curate_and_ingest_dining(
        db=db,
        trip_id=trip_id,
        city_segment_id=city_seg.id,
        user_id=user_id,
        events=enriched_spots
    )

    return {
        "city_name": city_name,
        "country": country,
        "scanned_categories": categories or list(DINING_SCAN_QUERIES.keys()),
        "newly_discovered": len(new_items),
        "items": new_items
    }
