#!/usr/bin/env python3
"""CLI and Subagent Tool for Scouting Local Destination City Events.

Discovers local newspapers, weekly publications, and event directories for
destination cities on the itinerary, extracts events (movies, concerts, art
exhibits, restaurants, free events, record store gigs, street fairs, farmers
markets), and populates them directly into the Explore & Discover section of Travel Scout.
"""
import os
import sys
import argparse
import json

# Ensure utf-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# Ensure project root is in sys.path
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
from scout.local_agent import (
    discover_city_publications,
    scout_local_events_for_city,
    run_local_agent_for_city_segment,
    EVENT_SCAN_QUERIES
)

def main():
    parser = argparse.ArgumentParser(description="Local Destination City Cultural Scout")
    parser.add_argument("--city", type=str, help="Specific destination city name to scout")
    parser.add_argument("--country", type=str, default="", help="Country of destination city")
    parser.add_argument("--trip-id", type=str, help="Trip ID to attach discoveries to (optional)")
    parser.add_argument("--all-cities", action="store_true", help="Scout all destination cities in the trip")
    parser.add_argument(
        "--types",
        type=str,
        default="press,movies,music,records,art,festivals,markets,free,restaurants",
        help="Comma-separated event types to scout (movies, music, art, festivals, markets, records, free, press, restaurants)"
    )
    parser.add_argument("--max-per-type", type=int, default=3, help="Max results per event type")
    parser.add_argument("--dry-run", action="store_true", help="Search without saving to database")
    args = parser.parse_args()

    event_types = [t.strip().lower() for t in args.types.split(",") if t.strip()]

    db = SessionLocal()
    try:
        # Determine trip (prioritize explicit trip-id, then latest active trip)
        trip = None
        if args.trip_id:
            trip = db.query(Trip).filter(Trip.id == args.trip_id).first()
        else:
            # Pick most recently created trip with itinerary segments
            trip = db.query(Trip).order_by(Trip.created_at.desc()).first()
            if not trip or not trip.city_segments:
                for t in db.query(Trip).all():
                    if t.city_segments:
                        trip = t
                        break

        if not trip and not args.dry_run:
            print("Error: No trips found in database to attach discoveries to.")
            sys.exit(1)

        user = db.query(User).first()
        user_id = user.id if user else (trip.owner_id if trip else None)

        cities_to_scout = []
        if args.city:
            # Check if this city matches an existing segment in the trip itinerary
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
            # By default: automatically scout ALL destination cities directly from the itinerary!
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
        print(f"🤖 LOCAL CITY CULTURAL SCOUT AGENT")
        print(f"==================================================================")
        print(f"Destination Cities: {', '.join(c['name'] for c in cities_to_scout)}")
        print(f"Target Event Types: {', '.join(event_types)}")
        print(f"Dry Run: {args.dry_run}\n")

        total_discovered = 0

        for city_info in cities_to_scout:
            c_name = city_info["name"]
            c_country = city_info["country"]
            c_seg_id = city_info["segment_id"]

            print(f"--- Scouting Destination: {c_name}, {c_country} ---")

            # 1. Discover local publications
            pubs = discover_city_publications(c_name, c_country)
            print(f"📰 Recognized Local Press & Media Outlets ({len(pubs)}):")
            for p in pubs:
                print(f"   • {p['name']} ({p['type']}) - {p['url']}")

            # 2. Scout events or run segment agent
            if c_seg_id and trip and not args.dry_run:
                result = run_local_agent_for_city_segment(
                    db=db,
                    trip_id=trip.id,
                    city_id=c_seg_id,
                    user_id=user_id,
                    event_types=event_types,
                    max_per_type=args.max_per_type
                )
                new_count = result["newly_discovered"]
                total_discovered += new_count
                print(f"\n✨ Ingested {new_count} new discoveries into Explore & Discover wishlist:")
                for item in result["items"]:
                    free_tag = "[FREE]" if item.get("is_free") else f"[{item.get('cost', 'Cost varies')}]"
                    print(f"   [{item['category'].upper()}] {free_tag} {item['title']}")
                    print(f"      📍 {item['neighborhood']} | Platform: {item['source_platform']}")
                    if item.get("url"):
                        print(f"      🔗 {item['url']}")
            else:
                # Direct search
                items = scout_local_events_for_city(
                    city_name=c_name,
                    country=c_country,
                    event_types=event_types,
                    max_per_type=args.max_per_type
                )
                print(f"\n✨ Discovered {len(items)} events for {c_name}:")
                for item in items:
                    free_tag = "[FREE]" if item.get("is_free") else f"[{item.get('cost', 'Cost varies')}]"
                    print(f"   [{item['category'].upper()}] {free_tag} {item['title']}")
                    print(f"      📍 {item.get('neighborhood', c_name)} | Source: {item.get('source_platform', 'Web')}")
                    if item.get("url"):
                        print(f"      🔗 {item['url']}")
                total_discovered += len(items)

        print(f"\n==================================================================")
        print(f"✅ Local Scout Complete! Discovered {total_discovered} total cultural events.")
        print(f"==================================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()
