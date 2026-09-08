"""CLI runner for the Culinary & Hidden Gems Scout Agent."""
import os
import sys
import argparse

current_dir = os.path.dirname(os.path.abspath(__file__))
while current_dir and not os.path.exists(os.path.join(current_dir, "app.py")):
    parent = os.path.dirname(current_dir)
    if parent == current_dir:
        break
    current_dir = parent
PROJECT_ROOT = current_dir
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.connection import SessionLocal
from database.models import Trip, CitySegment, User
from scout.dining_agent import (
    hunt_dining_spots,
    enrich_dining_venues,
    curate_and_ingest_dining,
    run_dining_agent_for_city_segment,
    DINING_SCAN_QUERIES
)

def main():
    parser = argparse.ArgumentParser(description="Culinary & Hidden Gems Scout Agent")
    parser.add_argument("--city", type=str, help="Destination city name to scout")
    parser.add_argument("--country", type=str, default="", help="Country of destination city")
    parser.add_argument("--trip-id", type=str, help="Trip ID to attach discoveries to (optional)")
    parser.add_argument(
        "--categories",
        type=str,
        default="coffee,bakeries,casual,dinner,cocktails",
        help="Comma-separated dining categories (coffee, bakeries, casual, dinner, cocktails)"
    )
    parser.add_argument("--max-per-type", type=int, default=3, help="Max results per category")
    parser.add_argument("--workers", type=int, default=4, help="Worker threads for parallel search")
    parser.add_argument("--skip-enrichment", action="store_true", help="Skip venue geocoding and transit URL enrichment")
    parser.add_argument("--dry-run", action="store_true", help="Search without saving to database")
    args = parser.parse_args()

    categories = [c.strip().lower() for c in args.categories.split(",") if c.strip()]

    db = SessionLocal()
    try:
        trip = None
        if args.trip_id:
            trip = db.query(Trip).filter(Trip.id == args.trip_id).first()
        else:
            trip = db.query(Trip).order_by(Trip.created_at.desc()).first()

        user = db.query(User).first()
        user_id = user.id if user else (trip.owner_id if trip else None)

        cities_to_scout = []
        if args.city:
            matched_seg = None
            if trip:
                for seg in trip.city_segments:
                    if seg.city_name.lower() == args.city.strip().lower():
                        matched_seg = seg
                        break
            cities_to_scout.append({
                "name": args.city,
                "country": args.country or (matched_seg.country if matched_seg else ""),
                "segment_id": matched_seg.id if matched_seg else None
            })
        elif trip and trip.city_segments:
            for seg in sorted(trip.city_segments, key=lambda x: x.order_index):
                cities_to_scout.append({
                    "name": seg.city_name,
                    "country": seg.country,
                    "segment_id": seg.id
                })
        else:
            print("No destination cities found on trip itinerary. Use --city <name>.")
            sys.exit(1)

        print(f"\n==================================================================")
        print(f"🍽️ CULINARY & HIDDEN GEMS SCOUT AGENT")
        print(f"==================================================================")
        print(f"Destination Cities: {', '.join(c['name'] for c in cities_to_scout)}")
        print(f"Categories: {', '.join(categories)}")
        print(f"Workers: {args.workers} | Location Enrichment: {not args.skip_enrichment}")
        print(f"Dry Run: {args.dry_run}\n")

        total_discovered = 0

        for city_info in cities_to_scout:
            c_name = city_info["name"]
            c_country = city_info["country"]
            c_seg_id = city_info["segment_id"]

            print(f"--- Scouting Culinary Gems: {c_name}, {c_country} ---")
            print(f"⚡ Spawning Parallel Food & Drink Scouts for {c_name}...")

            if c_seg_id and trip and not args.dry_run:
                result = run_dining_agent_for_city_segment(
                    db=db,
                    trip_id=trip.id,
                    city_id=c_seg_id,
                    user_id=user_id,
                    categories=categories,
                    max_per_type=args.max_per_type,
                    enrich_locations=not args.skip_enrichment
                )
                new_count = result["newly_discovered"]
                total_discovered += new_count
                print(f"\n✨ Ingested {new_count} new culinary gems into Explore & Discover:")
                for item in result["items"]:
                    print(f"   [{item['category'].upper()}] [{item.get('cost', '$$')}] {item['title']}")
                    print(f"      📍 {item.get('address') or item.get('neighborhood')}")
                    if item.get("directions_url"):
                        print(f"      🧭 Transit Route: {item['directions_url']}")
                    if item.get("url"):
                        print(f"      🔗 {item['url']}")
            else:
                raw_spots = hunt_dining_spots(
                    city_name=c_name,
                    country=c_country,
                    categories=categories,
                    max_per_type=args.max_per_type,
                    max_workers=args.workers
                )
                spots = enrich_dining_venues(
                    events=raw_spots,
                    city_name=c_name,
                    country=c_country
                ) if not args.skip_enrichment else raw_spots

                print(f"\n✨ Discovered {len(spots)} dining spots for {c_name}:")
                for item in spots:
                    print(f"   [{item['category'].upper()}] {item['title']}")
                    print(f"      📍 {item.get('address') or item.get('neighborhood', c_name)}")
                    if item.get("directions_url"):
                        print(f"      🧭 Transit Route: {item['directions_url']}")
                    if item.get("url"):
                        print(f"      🔗 {item['url']}")
                total_discovered += len(spots)

        print(f"\n==================================================================")
        print(f"✅ Dining Scout Complete! Discovered {total_discovered} culinary spots.")
        print(f"==================================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()
