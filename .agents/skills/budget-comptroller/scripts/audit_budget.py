"""CLI runner for the Group Budget & Expense Comptroller Agent."""
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
from scout.budget_comptroller import audit_trip_budget

def main():
    parser = argparse.ArgumentParser(description="Group Budget & Expense Comptroller Agent")
    parser.add_argument("--trip-id", type=str, help="Trip ID to audit (defaults to active trip)")
    parser.add_argument("--budget", type=float, help="Target total budget cap (optional)")
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
        print(f"💰 GROUP BUDGET & EXPENSE COMPTROLLER")
        print(f"==================================================================")
        print(f"Trip: {trip.title} ({trip.id})")

        result = audit_trip_budget(db, trip.id, target_budget=args.budget)
        curr = result["currency"]

        print(f"\n📊 Financial Summary:")
        print(f"   • Total Spent: {curr} {result['total_spent']}")
        if result["target_budget"]:
            print(f"   • Target Budget: {curr} {result['target_budget']} ({result['budget_used_pct']}% used, {curr} {result['remaining_budget']} remaining)")
        print(f"   • Members: {result['member_count']} | Fair Share per Person: {curr} {result['fair_share_per_person']}")
        print(f"   • Estimated Trip Duration: {result['total_days']} days")
        print(f"   • Daily Burn Rate: {curr} {result['daily_burn_rate']}/day ({curr} {result['daily_burn_per_person']}/person/day)")

        print(f"\n🏷️ Category Breakdown:")
        for cat, amt in result["category_totals"].items():
            pct = round((amt / max(0.01, result["total_spent"])) * 100, 1)
            print(f"   • {cat.title()}: {curr} {amt} ({pct}%)")

        print(f"\n⚖️ Balances & Settlements:")
        for b in result["settlement_balances"]:
            status = f"+{curr} {b['net_balance']} (owed back)" if b['net_balance'] > 0 else f"-{curr} {-b['net_balance']} (owes)" if b['net_balance'] < 0 else "Even"
            print(f"   • {b['name']}: Paid {curr} {b['total_paid']} -> {status}")

        if result["settlement_plan"]:
            print(f"\n🤝 Minimal Settlement Plan:")
            for s in result["settlement_plan"]:
                print(f"   ↳ {s['from_member']} pays {s['to_member']} {s['currency']} {s['amount']}")
        else:
            print(f"\n🤝 All balances are currently settled!")

        if result["alerts"]:
            print(f"\n⚠️ Budget Health Alerts ({len(result['alerts'])}):")
            for a in result["alerts"]:
                print(f"   [{a['severity'].upper()}] {a['message']}")

        print(f"\n==================================================================")
        print(f"✅ Budget Comptroller Audit Complete!")
        print(f"==================================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    main()
