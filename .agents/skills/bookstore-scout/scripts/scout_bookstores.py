"""CLI runner for the Independent & Vintage Bookstores Scout Agent."""
import os, sys, argparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
from database.models import Trip, User
from scout.specialist_scouts import run_specialist_scout, hunt_specialist_venues, enrich_specialist_venues

def main():
    parser = argparse.ArgumentParser(description="Independent & Vintage Bookstores Scout Agent")
    parser.add_argument("--city", type=str, help="Destination city name")
    parser.add_argument("--country", type=str, default="")
    parser.add_argument("--trip-id", type=str)
    parser.add_argument("--max-results", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        trip = db.query(Trip).filter(Trip.id == args.trip_id).first() if args.trip_id else db.query(Trip).order_by(Trip.created_at.desc()).first()
        user = db.query(User).first()
        user_id = user.id if user else (trip.owner_id if trip else None)

        cities = []
        if args.city:
            cities.append({"name": args.city, "country": args.country, "segment_id": None})
        elif trip and trip.city_segments:
            for s in sorted(trip.city_segments, key=lambda x: x.order_index):
                cities.append({"name": s.city_name, "country": s.country, "segment_id": s.id})

        print("\n==================================================================")
        print("📚 INDEPENDENT & VINTAGE BOOKSTORES SCOUT AGENT")
        print("==================================================================")
        print(f"Destination Cities: {', '.join(c['name'] for c in cities)}\n")

        for c in cities:
            print(f"--- Scouting Bookstores in {c['name']}, {c['country']} ---")
            if c["segment_id"] and trip and not args.dry_run:
                res = run_specialist_scout(db, trip.id, c["segment_id"], user_id, "bookstores", max_results=args.max_results)
                print(f"✨ Ingested {res['newly_discovered']} bookshops into Explore & Discover:")
                for item in res["items"]:
                    print(f"   📚 [{item.get('cost', 'Free')}] {item['title']}")
                    print(f"      📍 {item.get('address') or item.get('neighborhood')}")
                    if item.get("directions_url"):
                        print(f"      🧭 Transit Route: {item['directions_url']}")
                    if item.get("url"):
                        print(f"      🔗 {item['url']}")
            else:
                raw = hunt_specialist_venues(c["name"], c["country"], "bookstores", max_results=args.max_results)
                enriched = enrich_specialist_venues(raw, c["name"], c["country"])
                print(f"✨ Discovered {len(enriched)} bookshops:")
                for item in enriched:
                    print(f"   📚 {item['title']} - {item.get('address') or item.get('neighborhood')}")
                    if item.get("directions_url"):
                        print(f"      🧭 Transit Route: {item['directions_url']}")

        print("\n==================================================================")
        print("✅ Bookstore Scout Complete!")
        print("==================================================================\n")
    finally:
        db.close()

if __name__ == "__main__":
    main()
