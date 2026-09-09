"""Specialist Discovery Scouts Engine for Travel Scout.

Powers 6 specialized shopping, cultural, and nightlife agents:
1. Vintage Musical Instruments (guitars, bass, amps, synths)
2. Vintage Clothing Stores (thrift, archival fashion, retro apparel)
3. Vintage & Modern Home Design (mid-century modern, ceramics, architectural decor)
4. Cooking & Food-Related Stores (kitchenware, Japanese knives, gourmet pantries)
5. Record Stores (used & new vinyl, crate digging, rare pressings)
6. Craft Cocktail Bars & Speakeasies (hidden entrances, artisanal mixology)
"""
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session

from database.models import CitySegment, ItineraryItem
from scout.web_search import live_city_search
from scout.geocoding import resolve_venue_coordinates
from scout.transit import generate_directions_url
from scout.backup import compute_item_hash, is_item_deleted_and_unchanged, auto_backup_on_change

SPECIALIST_AGENTS_CONFIG: Dict[str, Dict[str, Any]] = {
    "vintage-gear": {
        "name": "Vintage Music Instruments Scout",
        "category": "vintage-gear",
        "icon": "🎸",
        "queries": [
            "vintage guitars and tube amps guitar shop",
            "used bass vintage synthesizer boutique pedal guitar store",
            "independent musical instrument shop rare guitars"
        ],
        "default_cost": "$$ - $$$",
        "tag": "Vintage Gear",
        "description_template": "Specialized vintage and boutique music shop featuring vintage guitars, tube amps, and gear."
    },
    "vintage-fashion": {
        "name": "Vintage Clothing Stores Scout",
        "category": "vintage-fashion",
        "icon": "🧥",
        "queries": [
            "best vintage clothing stores curated thrift boutique",
            "vintage denim archival designer retro apparel shop",
            "independent vintage fashion store secondhand gems"
        ],
        "default_cost": "$$ - $$$",
        "tag": "Vintage Clothing",
        "description_template": "Curated vintage clothing boutique specializing in archival apparel, denim, and retro garments."
    },
    "home-design": {
        "name": "Vintage & Modern Home Design Scout",
        "category": "home-design",
        "icon": "🛋️",
        "queries": [
            "mid century modern furniture vintage home decor design shop",
            "artisan ceramics architectural antiques modern interior design store",
            "independent home goods and design showroom vintage furniture"
        ],
        "default_cost": "$$ - $$$$",
        "tag": "Home Design",
        "description_template": "Boutique design showroom featuring mid-century modern furniture, artisan ceramics, and unique home decor."
    },
    "culinary-goods": {
        "name": "Cooking & Food-Related Stores Scout",
        "category": "culinary-goods",
        "icon": "🔪",
        "queries": [
            "culinary store gourmet kitchenware japanese knives cook shop",
            "artisan spice merchant specialty food market gourmet pantry",
            "cookware store culinary books olive oil provisions"
        ],
        "default_cost": "$$ - $$$",
        "tag": "Culinary Goods",
        "description_template": "Specialty culinary purveyor offering artisan kitchenware, chef knives, and gourmet pantry provisions."
    },
    "vinyl-records": {
        "name": "Record Stores (Used & New) Scout",
        "category": "records",
        "icon": "📻",
        "queries": [
            "best record stores vinyl shop crate digging used records",
            "independent vinyl record store rare LPs audiophile records",
            "used vinyl shop record store day 45s jazz soul indie rock"
        ],
        "default_cost": "Free / Browse Vinyl",
        "tag": "Record Store",
        "description_template": "Essential independent record store with deep crates of used and new vinyl."
    },
    "speakeasy-cocktails": {
        "name": "Craft Cocktail Bars & Speakeasies Scout",
        "category": "cocktails",
        "icon": "🍸",
        "queries": [
            "hidden speakeasy bar secret entrance craft cocktails",
            "best craft cocktail bars mixology speakeasy unmarked door",
            "intimate speakeasy cocktail lounge historic cocktail bar"
        ],
        "default_cost": "$$$ Craft Cocktails",
        "tag": "Speakeasy Bar",
        "description_template": "Intimate craft cocktail destination featuring artisanal mixology and speakeasy ambiance."
    },
    "bookstores": {
        "name": "Independent & Vintage Bookstores Scout",
        "category": "bookstores",
        "icon": "📚",
        "queries": [
            "best independent bookstores vintage used books rare editions",
            "secondhand bookstore antiquarian books used novels indie bookshop",
            "literary bookshop independent bookstore community cafe books"
        ],
        "default_cost": "Free / Browse Books",
        "tag": "Bookstore",
        "description_template": "Beloved independent bookstore featuring curated collections of new, vintage, and used books."
    }
}


def hunt_specialist_venues(
    city_name: str,
    country: Optional[str] = None,
    agent_type: str = "vintage-gear",
    max_results: int = 3,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    """Subagent 1: Specialist Hunter (Concurrent Search Queries)."""
    cfg = SPECIALIST_AGENTS_CONFIG.get(agent_type)
    if not cfg:
        return []

    queries = cfg["queries"]
    cat = cfg["category"]
    discovered: List[Dict[str, Any]] = []
    seen_titles = set()

    def _execute_query(q: str) -> List[Dict[str, Any]]:
        hits = []
        try:
            results = live_city_search(
                city_name=city_name,
                query=q,
                channel=cat,
                category_hint=cat,
                max_results=max_results
            )
            for h in results:
                title = (h.get("title") or "").strip()
                if not title:
                    continue
                h["title"] = title
                h["category"] = cat
                h["agent_type"] = agent_type
                hits.append(h)
        except Exception as err:
            print(f"Notice: Specialist hunt failed for '{q}': {err}")
        return hits

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_execute_query, q) for q in queries]
        for f in as_completed(futures):
            for h in f.result():
                norm = h["title"].lower()
                if norm not in seen_titles:
                    seen_titles.add(norm)
                    discovered.append(h)

    return discovered


def enrich_specialist_venues(
    venues: List[Dict[str, Any]],
    city_name: str,
    country: Optional[str] = None,
    stay: Optional[Any] = None,
    max_workers: int = 4
) -> List[Dict[str, Any]]:
    """Subagent 2: Location & Transit Enricher."""
    if not venues:
        return []

    def _enrich_single(v: Dict[str, Any]) -> Dict[str, Any]:
        venue_name = v.get("title", "")
        lat, lon, address = resolve_venue_coordinates(venue_name, city_name, country)
        v["lat"] = lat
        v["lon"] = lon
        v["address"] = address
        v["neighborhood"] = v.get("neighborhood") or f"{city_name} Cultural Quarter"

        dir_links = generate_directions_url(
            stay=stay,
            city_name=city_name,
            venue_lat=lat,
            venue_lon=lon,
            venue_title=venue_name,
            venue_address=address
        )
        v["directions_url"] = dir_links["transit_url"]
        v["walking_url"] = dir_links["walking_url"]
        return v

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_enrich_single, venues))


def curate_and_ingest_specialist(
    db: Session,
    trip_id: str,
    city_segment_id: str,
    user_id: str,
    agent_type: str,
    venues: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Subagent 3: Curator & Database Ingester."""
    cfg = SPECIALIST_AGENTS_CONFIG.get(agent_type, {})
    new_items: List[Dict[str, Any]] = []

    for v in venues:
        v_title = (v.get("title") or "").strip()
        if not v_title:
            continue

        exists = db.query(ItineraryItem).filter(
            ItineraryItem.trip_id == trip_id,
            ItineraryItem.title == v_title
        ).first()

        if not exists:
            v_desc = v.get("description") or f"Curated by {cfg.get('name', 'Specialist Agent')}."
            v_hl = v.get("highlight") or cfg.get("description_template", "Curated local venue.")
            v_cost = v.get("cost") or cfg.get("default_cost", "$$")
            v_time = v.get("time_info", "Check shop hours")
            v_addr = v.get("address", "")
            v_url = v.get("url")

            cand_hash = compute_item_hash(
                title=v_title,
                description=v_desc,
                highlight=v_hl,
                address=v_addr,
                cost=v_cost,
                time_info=v_time,
                url=v_url
            )
            if is_item_deleted_and_unchanged(db, trip_id, v_title, cand_hash):
                continue

            item = ItineraryItem(
                trip_id=trip_id,
                city_segment_id=city_segment_id,
                title=v_title,
                category=cfg.get("category", "gems"),
                neighborhood=v.get("neighborhood", "Cultural District"),
                address=v_addr,
                lat=v.get("lat"),
                lon=v.get("lon"),
                cost=v_cost,
                is_free=cfg.get("category") == "records" or "free" in v_cost.lower(),
                time_info=v_time,
                highlight=v_hl,
                description=v_desc,
                url=v_url,
                source_platform=cfg.get("tag", "Specialist Scout"),
                assigned_date="todo",
                added_by_user_id=user_id
            )
            db.add(item)
            new_items.append(v)

    if new_items:
        db.commit()
        auto_backup_on_change(db)
    return new_items


def run_specialist_scout(
    db: Session,
    trip_id: str,
    city_id: str,
    user_id: str,
    agent_type: str,
    max_results: int = 3,
    enrich_locations: bool = True
) -> Dict[str, Any]:
    """Autonomous execution of any of the 6 Specialist Discovery Agents."""
    city_seg = db.query(CitySegment).filter(
        CitySegment.id == city_id,
        CitySegment.trip_id == trip_id
    ).first()

    if not city_seg:
        return {"error": "City segment not found", "newly_discovered": 0, "items": []}

    cfg = SPECIALIST_AGENTS_CONFIG.get(agent_type)
    if not cfg:
        return {"error": f"Unknown agent type '{agent_type}'", "newly_discovered": 0, "items": []}

    city_name = city_seg.city_name
    country = city_seg.country
    active_stay = city_seg.stays[0] if (city_seg.stays and len(city_seg.stays) > 0) else None

    # 1. Hunt
    raw_venues = hunt_specialist_venues(
        city_name=city_name,
        country=country,
        agent_type=agent_type,
        max_results=max_results
    )

    # 2. Enrich
    enriched_venues = enrich_specialist_venues(
        venues=raw_venues,
        city_name=city_name,
        country=country,
        stay=active_stay
    ) if enrich_locations else raw_venues

    # 3. Curate & Ingest
    new_items = curate_and_ingest_specialist(
        db=db,
        trip_id=trip_id,
        city_segment_id=city_seg.id,
        user_id=user_id,
        agent_type=agent_type,
        venues=enriched_venues
    )

    return {
        "agent_type": agent_type,
        "agent_name": cfg["name"],
        "icon": cfg["icon"],
        "city_name": city_name,
        "country": country,
        "newly_discovered": len(new_items),
        "items": new_items
    }
