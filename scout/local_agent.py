"""Local Destination City Cultural Scout Agent.

Discovers local newspapers, alternative weeklies, community publications, and event websites
for destination cities on the itinerary, scans for upcoming cultural events (movies, concerts,
art exhibits, restaurants, free events, record store gigs, street fairs, farmers markets),
and ingests them directly into the Explore & Discover wishlist of Travel Scout.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session

from database.models import CitySegment, ItineraryItem
from scout.web_search import live_city_search
from scout.geocoding import resolve_city_coordinates, resolve_venue_coordinates
from scout.transit import generate_directions_url

# Well-known local media & cultural publications for major destinations
KNOWN_LOCAL_PUBLICATIONS: Dict[str, List[Dict[str, str]]] = {
    "lisbon": [
        {"name": "Mensagem de Lisboa", "type": "Community Journalism", "url": "https://amensagem.pt"},
        {"name": "Time Out Lisboa", "type": "Culture & Events Guide", "url": "https://www.timeout.pt/lisboa"},
        {"name": "Agenda Cultural de Lisboa", "type": "Official City Cultural Calendar", "url": "https://agendaculturallisboa.pt"},
        {"name": "The Portugal News", "type": "Weekly English Newspaper", "url": "https://www.theportugalnews.com"},
        {"name": "Gerador", "type": "Indie Arts & Culture Magazine", "url": "https://gerador.eu"},
        {"name": "Público - Guia do Lazer", "type": "Arts, Cinema & Concerts", "url": "https://guiadolazer.publico.pt"},
    ],
    "porto": [
        {"name": "Time Out Porto", "type": "Culture & Events Guide", "url": "https://www.timeout.pt/porto"},
        {"name": "Porto Secreto", "type": "Local Culture & Food Guide", "url": "https://portosecreto.co"},
        {"name": "Jornal de Notícias", "type": "Daily Regional Newspaper", "url": "https://www.jn.pt"},
        {"name": "Ágora Porto Cultural", "type": "City Events & Festivals", "url": "https://agoraporto.pt"},
    ],
    "new york": [
        {"name": "The Village Voice", "type": "Alternative Weekly", "url": "https://villagevoice.com"},
        {"name": "Gothamist", "type": "Local News & Events", "url": "https://gothamist.com"},
        {"name": "BrooklynVegan", "type": "Indie Music, Concerts & Screenings", "url": "https://brooklynvegan.com"},
        {"name": "Time Out New York", "type": "Events, Theater & Food", "url": "https://timeout.com/newyork"},
    ],
    "london": [
        {"name": "Time Out London", "type": "Culture & Nightlife Weekly", "url": "https://timeout.com/london"},
        {"name": "Londonist", "type": "Local Culture & Free Events", "url": "https://londonist.com"},
        {"name": "The Standard", "type": "City Newspaper & What's On", "url": "https://standard.co.uk"},
    ],
    "paris": [
        {"name": "Sortir à Paris", "type": "Exhibitions & Events Guide", "url": "https://sortiraparis.com"},
        {"name": "Le Bonbon", "type": "Neighborhood Culture & Pop-ups", "url": "https://lebonbon.fr"},
        {"name": "Paris Secret", "type": "Cultural Discoveries", "url": "https://parissecret.com"},
    ],
    "tokyo": [
        {"name": "Time Out Tokyo", "type": "City Culture Guide", "url": "https://timeout.com/tokyo"},
        {"name": "Tokyo Cheapo", "type": "Free Events, Markets & Indie Guide", "url": "https://tokyocheapo.com"},
        {"name": "Metropolis Japan", "type": "English Weekly Magazine", "url": "https://metropolisjapan.com"},
    ],
    "san diego": [
        {"name": "San Diego Reader", "type": "Alternative Weekly & Events Calendar", "url": "https://www.sandiegoreader.com"},
        {"name": "Voice of San Diego", "type": "Local Culture & Community Journalism", "url": "https://voiceofsandiego.org"},
        {"name": "KPBS Arts & Culture Calendar", "type": "San Diego Public Media Events", "url": "https://www.kpbs.org/arts-culture"},
        {"name": "There San Diego", "type": "What's Happening in San Diego", "url": "https://theresandiego.com"},
        {"name": "San Diego Magazine", "type": "Dining, Culture & Neighborhood Guides", "url": "https://sandiegomagazine.com"},
        {"name": "Pacific San Diego", "type": "Nightlife, Music & Arts", "url": "https://pacificsandiego.com"},
    ],
}

# Event scan search templates categorized by focus
EVENT_SCAN_QUERIES: Dict[str, Dict[str, Any]] = {
    "press": {
        "label": "Local Alt-Weeklies & Newspapers",
        "category": "press",
        "channel": "press",
        "queries": [
            "alternative weekly newspaper events calendar this week",
            "weekly arts culture entertainment paper what's on",
            "local city newspaper weekend events guide"
        ]
    },
    "movies": {
        "label": "Film Festivals & Cinema",
        "category": "movies",
        "channel": "movies",
        "queries": [
            "open air cinema outdoor movie screenings film festival",
            "independent cinema repertory film screening schedule",
            "cinematheque and foreign film screenings"
        ]
    },
    "music": {
        "label": "Live Music & Concerts",
        "category": "music",
        "channel": "music",
        "queries": [
            "live music concerts gigs this month tickets",
            "jazz clubs and intimate acoustic music venues",
            "indie band performances club shows tour dates"
        ]
    },
    "records": {
        "label": "Record Stores & In-Store Performances",
        "category": "records",
        "channel": "records",
        "queries": [
            "record store in-store live performance gig",
            "independent vinyl record shops live music sessions",
            "record store vinyl pop-up and DJ sets"
        ]
    },
    "art": {
        "label": "Art Exhibits & Gallery Openings",
        "category": "art",
        "channel": "art",
        "queries": [
            "art gallery openings vernissage and contemporary exhibits",
            "museum exhibitions and sculpture shows calendar",
            "independent art space open studios and exhibitions"
        ]
    },
    "festivals": {
        "label": "Street Fairs & Outdoor Festivals",
        "category": "festivals",
        "channel": "festivals",
        "queries": [
            "outdoor festival street fair block party carnival",
            "neighborhood street festival celebration open air",
            "cultural celebration street fair free outdoor stage"
        ]
    },
    "markets": {
        "label": "Farmers Markets & Pop-ups",
        "category": "markets",
        "channel": "markets",
        "queries": [
            "farmers market artisan food and weekend flea market",
            "neighborhood weekend fresh market organic produce",
            "makers market crafts flea market pop up"
        ]
    },
    "free": {
        "label": "Free Admission & Community Events",
        "category": "free",
        "channel": "events",
        "queries": [
            "free events this weekend admission free no cover",
            "free outdoor concerts exhibitions and community events",
            "free admission cultural happenings open to the public"
        ]
    },
    "restaurants": {
        "label": "New Restaurants & Dining Pop-ups",
        "category": "dining",
        "channel": "eater",
        "queries": [
            "essential new restaurants and culinary pop ups",
            "eater heatmap best new dining and food halls",
            "local food market stalls and neighborhood gems"
        ]
    }
}


def discover_city_publications(city_name: str, country: Optional[str] = None) -> List[Dict[str, str]]:
    """Discover local newspapers, alternative weeklies, and publications for a city."""
    key = city_name.strip().lower()
    results: List[Dict[str, str]] = []

    # Check known presets first
    if key in KNOWN_LOCAL_PUBLICATIONS:
        results.extend(KNOWN_LOCAL_PUBLICATIONS[key])

    # Dynamic search for any city in the world
    try:
        query = f"{city_name} alternative weekly newspaper OR arts culture magazine OR local events guide"
        found = live_city_search(city_name, query, channel="press", category_hint="press", max_results=4)
        for f in found:
            # Add if title and url are valid and not duplicate
            url = f.get("url", "").strip()
            title = f.get("title", "").strip()
            if url and title and not any(r["url"] == url for r in results):
                results.append({
                    "name": title,
                    "type": "Local Press / Alt-Weekly",
                    "url": url,
                    "highlight": f.get("highlight", "")
                })
    except Exception as e:
        print(f"Notice: Publication discovery search for {city_name} failed: {e}")

    return results


# ==============================================================================
# QUOTA-AWARE MULTI-SUBAGENT PIPELINE (subagent-orchestrator pattern)
# ==============================================================================

def hunt_cultural_events(
    city_name: str,
    country: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    max_per_type: int = 3,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    """
    Subagent 1: Cultural Event Hunter (Model: Gemini Flash)
    
    Parallelizes category scans across local event channels and queries.
    Deduplicates candidates and normalizes titles.
    """
    types_to_scan = event_types or list(EVENT_SCAN_QUERIES.keys())
    discovered: List[Dict[str, Any]] = []
    seen_titles = set()

    def _scan_category(cat_key: str) -> List[Dict[str, Any]]:
        cfg = EVENT_SCAN_QUERIES.get(cat_key)
        if not cfg:
            return []
        cat = cfg["category"]
        channel = cfg["channel"]
        queries = cfg["queries"]
        cat_hits: List[Dict[str, Any]] = []
        for q in queries[:2]:
            try:
                hits = live_city_search(
                    city_name=city_name,
                    query=q,
                    channel=channel,
                    category_hint=cat,
                    max_results=max_per_type
                )
                for h in hits:
                    title = (h.get("title") or "").strip()
                    if not title:
                        continue
                    h["title"] = title
                    h["category"] = cat
                    if cat_key == "free":
                        h["is_free"] = True
                        h["cost"] = "Free Admission"
                    cat_hits.append(h)
            except Exception as err:
                print(f"Notice: Hunter failed for {city_name} on {cat_key} ('{q}'): {err}")
        return cat_hits

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_scan_category, t): t for t in types_to_scan}
        for future in as_completed(futures):
            try:
                res = future.result()
                for h in res:
                    norm = h["title"].lower()
                    if norm not in seen_titles:
                        seen_titles.add(norm)
                        discovered.append(h)
            except Exception as e:
                print(f"Notice: Hunter category error: {e}")

    return discovered


def enrich_venue_locations(
    events: List[Dict[str, Any]],
    city_name: str,
    country: Optional[str] = None,
    stay: Optional[Any] = None,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    """
    Subagent 2: Venue Geocoder & Transit Enricher (Model: Gemini Flash-Lite / Flash)
    
    Concurrently geocodes venues and landmarks, extracts street addresses, and
    generates compliant Google Maps directions links with lodging as the starting origin (Rule 2).
    """
    if not events:
        return []

    def _enrich_single(ev: Dict[str, Any]) -> Dict[str, Any]:
        venue_name = ev.get("title", "")
        # Resolve coordinates & address
        lat, lon, address = resolve_venue_coordinates(venue_name, city_name, country)
        ev["lat"] = lat
        ev["lon"] = lon
        ev["address"] = address
        ev["neighborhood"] = ev.get("neighborhood") or f"{city_name} Cultural District"

        # Generate Rule-2 compliant Google Maps directions
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
        enriched = list(executor.map(_enrich_single, events))

    return enriched


def curate_and_ingest_events(
    db: Session,
    trip_id: str,
    city_segment_id: str,
    user_id: str,
    events: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Subagent 3: Itinerary Curator & Ingester (Model: Gemini Flash)
    
    Validates, deduplicates against database items, and commits new discoveries
    into ItineraryItem with assigned_date='todo'.
    """
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
            item = ItineraryItem(
                trip_id=trip_id,
                city_segment_id=city_segment_id,
                title=ev_title,
                category=ev.get("category", "gems"),
                neighborhood=ev.get("neighborhood", "Cultural District"),
                address=ev.get("address", ""),
                lat=ev.get("lat"),
                lon=ev.get("lon"),
                cost=ev.get("cost", "Free Admission" if ev.get("is_free") else "Check venue"),
                is_free=ev.get("is_free", False),
                time_info=ev.get("time_info", "Check local listings"),
                highlight=ev.get("highlight"),
                description=ev.get("description"),
                url=ev.get("url"),
                source_platform=ev.get("source_platform", "Local Press Scout"),
                assigned_date="todo",
                added_by_user_id=user_id
            )
            db.add(item)
            new_items.append(ev)

    if new_items:
        db.commit()

    return new_items


def scout_local_events_for_city(
    city_name: str,
    country: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    max_per_type: int = 3,
    enrich_locations: bool = True
) -> List[Dict[str, Any]]:
    """
    Scout local publications, event directories, and websites for a specific city.
    Orchestrates the Cultural Hunter and Venue Geocoder subagents.
    """
    # 1. Hunter Agent
    raw_events = hunt_cultural_events(
        city_name=city_name,
        country=country,
        event_types=event_types,
        max_per_type=max_per_type
    )

    # 2. Enricher Agent
    if enrich_locations:
        return enrich_venue_locations(
            events=raw_events,
            city_name=city_name,
            country=country
        )
    return raw_events


def run_local_agent_for_city_segment(
    db: Session,
    trip_id: str,
    city_id: str,
    user_id: str,
    event_types: Optional[List[str]] = None,
    max_per_type: int = 3,
    enrich_locations: bool = True
) -> Dict[str, Any]:
    """
    Autonomous execution of the Local City Cultural Scout Agent via
    the 3-Subagent Orchestrator pipeline.
    
    1. Identifies city name & country from city segment.
    2. Discovers local publications and alt-weeklies.
    3. Subagent 1 (Hunter): Runs parallel event searches across chosen categories.
    4. Subagent 2 (Enricher): Geocodes venues & builds Rule-2 compliant transit routes.
    5. Subagent 3 (Curator): Deduplicates and ingests into ItineraryItem with assigned_date='todo'.
    """
    city_seg = db.query(CitySegment).filter(
        CitySegment.id == city_id,
        CitySegment.trip_id == trip_id
    ).first()

    if not city_seg:
        return {"error": "City segment not found in trip", "newly_discovered": 0, "items": []}

    city_name = city_seg.city_name
    country = city_seg.country
    active_stay = city_seg.stays[0] if (city_seg.stays and len(city_seg.stays) > 0) else None

    # Step 1: Discover publications
    publications = discover_city_publications(city_name, country)

    # Subagent 1: Hunt cultural events in parallel
    raw_events = hunt_cultural_events(
        city_name=city_name,
        country=country,
        event_types=event_types,
        max_per_type=max_per_type
    )

    # Subagent 2: Enrich venue locations & transit directions
    enriched_events = enrich_venue_locations(
        events=raw_events,
        city_name=city_name,
        country=country,
        stay=active_stay
    ) if enrich_locations else raw_events

    # Subagent 3: Curate & Ingest into database
    new_items = curate_and_ingest_events(
        db=db,
        trip_id=trip_id,
        city_segment_id=city_seg.id,
        user_id=user_id,
        events=enriched_events
    )

    return {
        "city_name": city_name,
        "country": country,
        "publications_found": len(publications),
        "publications": publications,
        "scanned_types": event_types or list(EVENT_SCAN_QUERIES.keys()),
        "newly_discovered": len(new_items),
        "items": new_items
    }
