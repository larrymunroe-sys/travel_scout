"""CLI runner for the Lodging & Neighborhood Evaluator Agent."""
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
from database.models import Trip
from scout.stay_scout import evaluate_trip_lodging

def main():
    parser = argparse.ArgumentParser(description="Lodging & Neighborhood Evaluator Agent")
    parser.add_argument("--trip-id", type=str, help="Trip ID to evaluate (defaults to active trip)")
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

        print(f"\n==================================================================")
        print(f"🏨 LODGING & NEIGHBORHOOD EVALUATOR")
        print(f"==================================================================")
        print(f"Trip: {trip.title} ({trip.id})\n")

        result = evaluate_trip_lodging(db, trip.id)

        for ev in result["evaluations"]:
            if "status" in ev:
                print(f"📍 City: {ev['city_name']} - {ev['status']}")
                print(f"   ↳ {ev['message']}\n")
                continue

            print(f"🏨 Lodging: {ev['stay_name']} ({ev['city_name']})")
            print(f"   📅 Dates: {ev.get('dates')}")
            print(f"   📍 Address: {ev.get('address') or 'Address on file'}")
            print(f"   🏆 Walkability Score: {ev['walkability_score']} / 100")
            print(f"   🏷️ Verdict: {ev['verdict']}")
            print(f"   🚶 Distance: Avg {ev['avg_distance_km']} km | {ev['within_15min_walk_count']} spots within 15 min walk ({ev['within_15min_walk_pct']}%)")
            print(f"   💡 Assessment: {ev['summary']}\n")

        print(f"==================================================================")
        print(f"✅ Lodging Evaluation Complete!")
        print(f"==================================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()
