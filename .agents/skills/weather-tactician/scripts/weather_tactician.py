"""CLI runner for the Weather Tactician & Dynamic Re-Scheduler Agent."""
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
from scout.weather_tactician import evaluate_trip_weather_advisory

def main():
    parser = argparse.ArgumentParser(description="Weather Tactician & Dynamic Re-Scheduler Agent")
    parser.add_argument("--trip-id", type=str, help="Trip ID to evaluate (defaults to active trip)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.trip_id:
            trip = db.query(Trip).filter(Trip.id == args.trip_id).first()
        else:
            trip = db.query(Trip).order_by(Trip.created_at.desc()).first()

        if not trip:
            print("Error: No trips found in database.")
            sys.exit(1)

        print(f"\n==================================================================")
        print(f"🌦️ WEATHER TACTICIAN & PACKING ADVISOR")
        print(f"==================================================================")
        print(f"Trip: {trip.title} ({trip.id})")

        advisory = evaluate_trip_weather_advisory(db, trip.id)

        print(f"Evaluated Days: {advisory['total_days_evaluated']} | Rain Risk Days: {advisory['rain_days_count']}")
        print(f"Forecast Temp Range: {advisory['temp_range']['min_c']}°C to {advisory['temp_range']['max_c']}°C\n")

        print("--- Daily Tactical Weather Breakdown ---")
        for day in advisory["day_advisories"][:7]:
            rain_tag = "⚠️ RAIN ADVISORY" if day["is_rainy"] else "✅ Good Weather"
            print(f"📅 {day['date']} ({day['city_name']}): {day['icon']} {day['condition']} | {day['temp_min']}°C - {day['temp_max']}°C ({day['rain_prob']}% rain) -> {rain_tag}")
            if day["outdoor_at_risk"]:
                print(f"   🚨 Outdoor Activities at Risk ({len(day['outdoor_at_risk'])}):")
                for out in day["outdoor_at_risk"]:
                    print(f"      • {out['title']} ({out['category']})")
            if day["suggested_indoor_swaps"]:
                print(f"   💡 Suggested Indoor Replacements from Wishlist:")
                for sw in day["suggested_indoor_swaps"]:
                    print(f"      ↳ [SWAP] {sw['title']} ({sw['category']})")

        print("\n--- 🎒 Custom Dynamic Packing Checklist ---")
        for p in advisory["packing_checklist"]:
            print(f"   [ ] [{p['category'].upper()}] {p['item']}")
            print(f"       ↳ {p['reason']}")

        print(f"\n==================================================================")
        print(f"✅ Weather Tactical Evaluation Complete!")
        print(f"==================================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()
