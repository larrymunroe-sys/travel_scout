"""CLI runner for the Transit Route & Itinerary Optimizer Agent."""
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
from database.models import Trip, ItineraryItem
from scout.transit_optimizer import optimize_trip_day_schedule

def main():
    parser = argparse.ArgumentParser(description="Transit Route & Day Itinerary Optimizer Agent")
    parser.add_argument("--trip-id", type=str, help="Trip ID (defaults to active trip)")
    parser.add_argument("--date", type=str, help="Specific ISO date (YYYY-MM-DD) to optimize")
    parser.add_argument("--apply", action="store_true", help="Apply the optimized order to database order_index")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.trip_id:
            trip = db.query(Trip).filter(Trip.id == args.trip_id).first()
        else:
            trip = db.query(Trip).order_by(Trip.created_at.desc()).first()

        if not trip:
            print("Error: No trips found.")
            sys.exit(1)

        dates_to_eval = []
        if args.date:
            dates_to_eval.append(args.date)
        else:
            # Find all dates with scheduled items
            items = db.query(ItineraryItem).filter(
                ItineraryItem.trip_id == trip.id,
                ItineraryItem.assigned_date != "todo"
            ).all()
            dates_to_eval = sorted(list(set(it.assigned_date for it in items)))

        if not dates_to_eval:
            print(f"No scheduled dates found on trip '{trip.title}'. Items are in wishlist (todo).")
            print("Assign items to dates in Travel Scout to run route optimization!")
            sys.exit(0)

        print(f"\n==================================================================")
        print(f"🧭 TRANSIT ROUTE & ITINERARY DAY OPTIMIZER")
        print(f"==================================================================")
        print(f"Trip: {trip.title} ({trip.id})")
        print(f"Apply changes to DB: {args.apply}\n")

        for d in dates_to_eval:
            result = optimize_trip_day_schedule(db, trip.id, d, apply_order_index=args.apply)
            if "error" in result or not result.get("ordered_items"):
                continue

            print(f"📅 Date: {result['date']} ({result['city_name']})")
            print(f"   🏠 Starting Lodging / Origin: {result['origin_name']}")
            print(f"   🗺️ Distance: {result['original_km']} km -> {result['optimized_km']} km (Saved {result['saved_km']} km of walking/transit)")
            print(f"   🎟️ Recommended Transit Pass: {result['transit_pass_recommendation']['card_name']} ({result['transit_pass_recommendation']['fare_info']})")
            print(f"   💡 Transit Tip: {result['transit_pass_recommendation']['tip']}")
            print(f"   📍 Optimal Sequence ({len(result['ordered_items'])} stops):")
            for it in result["ordered_items"]:
                print(f"      [{it['order']}] {it['title']} ({it['category']}) - {it['address']}")
            print()

        print(f"==================================================================")
        print(f"✅ Route Optimization Complete!")
        print(f"==================================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()
