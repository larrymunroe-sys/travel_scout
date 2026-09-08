"""CLI runner for the Concierge & Reservation Assistant Agent."""
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
from scout.concierge_agent import evaluate_reservation_plan

def main():
    parser = argparse.ArgumentParser(description="Concierge & Reservation Assistant Agent")
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
        print(f"🤖 CONCIERGE & RESERVATION ASSISTANT")
        print(f"==================================================================")
        print(f"Trip: {trip.title} ({trip.id})\n")

        plan = evaluate_reservation_plan(db, trip.id)

        print(f"Analyzed: {plan['total_items_analyzed']} activities")
        print(f"Actionable Reservations: {plan['actionable_count']} | Walk-in Friendly: {plan['walk_in_count']}\n")

        print("--- 🎫 Actionable Reservations & Ticket Requirements ---")
        for res in plan["actionable_reservations"]:
            print(f"[{res['urgency']}]")
            print(f"   • {res['title']} ({res['category']})")
            print(f"     📍 {res['neighborhood']} | 📅 Date: {res['scheduled_date']} | 💰 {res['cost']}")
            print(f"     💡 Tip: {res['booking_tip']}")
            if res.get("url"):
                print(f"     🔗 Link: {res['url']}")
            print()

        print("--- 🚶 Walk-In Friendly / Flexible Items ---")
        for w in plan["walk_in_friendly"][:5]:
            print(f"   • {w['title']} ({w['category']}) - {w['cost']} ({w['neighborhood']})")
        if len(plan["walk_in_friendly"]) > 5:
            print(f"   ... and {len(plan['walk_in_friendly']) - 5} more walk-in friendly spots.")

        print(f"\n==================================================================")
        print(f"✅ Concierge Plan Complete!")
        print(f"==================================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()
