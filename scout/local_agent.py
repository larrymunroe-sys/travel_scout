"""Local Destination City Cultural Scout Agent.

Discovers local newspapers, alternative weeklies, community publications, and event websites
for destination cities on the itinerary, scans for upcoming cultural events (movies, concerts,
art exhibits, restaurants, free events, record store gigs, street fairs, farmers markets),
and ingests them directly into the Explore & Discover wishlist of Travel Scout.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from database.models import CitySegment, ItineraryItem
from scout.web_search import live_city_search
from scout.geocoding import resolve_city_coordinates

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


def scout_local_events_for_city(
    city_name: str,
    country: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    max_per_type: int = 3
) -> List[Dict[str, Any]]:
    """
    Scout local publications, event directories, and websites for a specific city.
    
    Returns structured event discoveries ready for Explore & Discover.
    """
    types_to_scan = event_types or list(EVENT_SCAN_QUERIES.keys())
    discovered: List[Dict[str, Any]] = []
    seen_titles = set()

    for event_type in types_to_scan:
        config = EVENT_SCAN_QUERIES.get(event_type)
        if not config:
            continue

        cat = config["category"]
        channel = config["channel"]
        queries = config["queries"]

        # Take the top query for this category
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
                    title_norm = title.lower()
                    if title_norm not in seen_titles:
                        seen_titles.add(title_norm)
                        # Ensure category matches our focused event type
                        h["title"] = title
                        h["category"] = cat
                        if event_type == "free":
                            h["is_free"] = True
                            h["cost"] = "Free Admission"
                        discovered.append(h)
            except Exception as err:
                print(f"Notice: Local scout failed for {city_name} on {event_type} ('{q}'): {err}")

    return discovered


def run_local_agent_for_city_segment(
    db: Session,
    trip_id: str,
    city_id: str,
    user_id: str,
    event_types: Optional[List[str]] = None,
    max_per_type: int = 3
) -> Dict[str, Any]:
    """
    Autonomous execution of the Local City Cultural Scout Agent.
    
    1. Identifies city name & country from city segment.
    2. Discovers local publications and alt-weeklies.
    3. Runs event searches across chosen event types (movies, concerts, art exhibits,
       restaurants, free events, record stores, outdoor festivals, farmers markets, street fairs).
    4. Automatically saves discovered items to ItineraryItem with assigned_date='todo'.
    5. Returns summary and items.
    """
    city_seg = db.query(CitySegment).filter(
        CitySegment.id == city_id,
        CitySegment.trip_id == trip_id
    ).first()

    if not city_seg:
        return {"error": "City segment not found in trip", "newly_discovered": 0, "items": []}

    city_name = city_seg.city_name
    country = city_seg.country

    # 1. Discover publications
    publications = discover_city_publications(city_name, country)

    # 2. Scout events
    events = scout_local_events_for_city(
        city_name=city_name,
        country=country,
        event_types=event_types,
        max_per_type=max_per_type
    )

    # 3. Ingest into database
    new_items: List[Dict[str, Any]] = []
    for ev in events:
        ev_title = (ev.get("title") or "").strip()
        if not ev_title:
            continue
        # Check if already in DB
        exists = db.query(ItineraryItem).filter(
            ItineraryItem.trip_id == trip_id,
            ItineraryItem.title == ev_title
        ).first()

        if not exists:
            item = ItineraryItem(
                trip_id=trip_id,
                city_segment_id=city_seg.id,
                title=ev_title,
                category=ev.get("category", "gems"),
                neighborhood=ev.get("neighborhood", f"{city_name} Cultural District"),
                address=ev.get("address", city_name),
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

    db.commit()

    return {
        "city_name": city_name,
        "country": country,
        "publications_found": len(publications),
        "publications": publications,
        "scanned_types": event_types or list(EVENT_SCAN_QUERIES.keys()),
        "newly_discovered": len(new_items),
        "items": new_items
    }
