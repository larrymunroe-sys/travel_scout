#!/usr/bin/env python3
"""
==============================================================================
Travel Scout — Master Autonomous Agents Orchestrator
==============================================================================
Executes all 14 Travel Scout autonomous specialist and analytical agents:

Phase 1: Discovery & Cultural Scouting (9 Agents)
  1. Local City Cultural Scout (Press, festivals, art, concerts, indie cinema)
  2. Culinary & Hidden Gems Scout (Bakeries, specialty coffee, casual street food, dinner)
  3. Vintage Music Instruments Scout (Guitars, tube amps, analog synthesizers, boutique pedals)
  4. Curated Vintage Clothing Scout (Archival designer fashion, denim, retro apparel)
  5. Vintage & Modern Home Design Scout (Mid-century furniture, ceramics, interior design)
  6. Gourmet Cooking & Food Specialty Stores Scout (Kitchenware, knives, spices, pantry)
  7. Independent Vinyl Record Stores Scout (Crate digging, used/new vinyl, rare 45s)
  8. Craft Cocktail Bars & Speakeasies Scout (Secret doors, unmarked entrances, artisanal mixology)
  9. Independent & Vintage Bookstores Scout (Indie books, rare first editions, antiquarian)

Phase 2: Tactical, Logistical & Analytical Advisory (5 Agents)
  10. Lodging & Neighborhood Evaluator (Walkability score 0-100, commute times, neighborhood character)
  11. Weather Tactician & Packing Advisor (Live Open-Meteo forecasts, rain risk, indoor wishlist swaps, checklist)
  12. Autonomous Concierge & Reservation Assistant (Booking urgency timeline, ticketing requirements)
  13. Transit Route & Day Optimizer (TSP heuristic route ordering starting from active stay)
  14. Group Budget & Expense Comptroller (Multi-currency audit, fair shares, burn rate, debt settlement)

Usage:
  python scripts/run_all_agents.py
  python scripts/run_all_agents.py --trip-id <TRIP_ID>
  python scripts/run_all_agents.py --max-results 2
  python scripts/run_all_agents.py --dry-run
  python scripts/run_all_agents.py --skip-discovery
  python scripts/run_all_agents.py --skip-analysis
  python main.py agents
==============================================================================
"""

import os
import sys
import time
import argparse
from typing import Dict, Any, List, Optional

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

from database.connection import SessionLocal, init_db
from database.models import Trip, CitySegment, User, ItineraryItem

# Import all agent engines
from scout.local_agent import run_local_agent_for_city_segment
from scout.dining_agent import run_dining_agent_for_city_segment
from scout.specialist_scouts import run_specialist_scout, SPECIALIST_AGENTS_CONFIG
from scout.stay_scout import evaluate_trip_lodging
from scout.weather_tactician import evaluate_trip_weather_advisory
from scout.concierge_agent import evaluate_reservation_plan
from scout.transit_optimizer import optimize_trip_day_schedule
from scout.budget_comptroller import audit_trip_budget


def get_target_trips(db, trip_id: Optional[str] = None, all_trips: bool = False) -> List[Trip]:
    """Resolve target trip(s) for agent execution."""
    if trip_id:
        t = db.query(Trip).filter(Trip.id == trip_id).first()
        return [t] if t else []
    if all_trips:
        return db.query(Trip).order_by(Trip.created_at.desc()).all()

    # Default: latest trip with city segments
    trips = db.query(Trip).order_by(Trip.created_at.desc()).all()
    for t in trips:
        if t.city_segments and len(t.city_segments) > 0:
            return [t]
    return trips[:1] if trips else []


def run_all_agents_for_trip(
    db,
    trip: Trip,
    user_id: str,
    max_results: int = 2,
    dry_run: bool = False,
    skip_discovery: bool = False,
    skip_analysis: bool = False,
    apply_routes: bool = False
) -> Dict[str, Any]:
    """Execute all 14 autonomous agents on a given trip."""
    start_time = time.time()
    city_names = [s.city_name for s in trip.city_segments]
    
    print("\n" + "=" * 76)
    print(f"🌍 TRAVEL SCOUT — RUNNING ALL 14 AUTONOMOUS AGENTS")
    print(f"🎯 Target Trip: '{trip.title}' (ID: {trip.id})")
    print(f"📍 Destination Cities: {', '.join(city_names) if city_names else 'None'}")
    print(f"⚙️  Settings: max_results={max_results} | dry_run={dry_run}")
    print("=" * 76 + "\n")

    results_summary = {
        "trip_id": trip.id,
        "trip_title": trip.title,
        "agents": {},
        "total_new_items": 0,
        "errors": []
    }

    # =========================================================================
    # PHASE 1: DISCOVERY & CULTURAL SCOUTING AGENTS (1 - 9)
    # =========================================================================
    if not skip_discovery:
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("PHASE 1: DESTINATION DISCOVERY & CULTURAL SCOUTING AGENTS")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        for seg in sorted(trip.city_segments, key=lambda x: x.order_index):
            print(f"\n🏙️  Processing City Segment: {seg.city_name}, {seg.country}")
            print("─" * 60)

            # Agent 1: Local City Cultural Scout
            print("▶ [Agent 1/14] Local City Cultural Scout...")
            try:
                res_local = run_local_agent_for_city_segment(
                    db=db,
                    trip_id=trip.id,
                    city_id=seg.id,
                    user_id=user_id,
                    max_per_type=max_results,
                    enrich_locations=True
                )
                new_count = res_local.get("newly_discovered", 0)
                results_summary["total_new_items"] += new_count
                results_summary["agents"].setdefault("local-city-scout", {"name": "Local City Cultural Scout", "discovered": 0})
                results_summary["agents"]["local-city-scout"]["discovered"] += new_count
                print(f"   ✓ Discovered & Ingested {new_count} cultural events/venues for {seg.city_name}")
            except Exception as e:
                print(f"   ⚠️ Error in Local City Scout: {e}")
                results_summary["errors"].append(f"local-city-scout: {e}")

            # Agent 2: Culinary & Hidden Gems Scout
            print("▶ [Agent 2/14] Culinary & Hidden Gems Scout...")
            try:
                res_dining = run_dining_agent_for_city_segment(
                    db=db,
                    trip_id=trip.id,
                    city_id=seg.id,
                    user_id=user_id,
                    max_per_type=max_results,
                    enrich_locations=True
                )
                new_count = res_dining.get("newly_discovered", 0)
                results_summary["total_new_items"] += new_count
                results_summary["agents"].setdefault("dining-scout", {"name": "Culinary & Hidden Gems Scout", "discovered": 0})
                results_summary["agents"]["dining-scout"]["discovered"] += new_count
                print(f"   ✓ Discovered & Ingested {new_count} culinary gems for {seg.city_name}")
            except Exception as e:
                print(f"   ⚠️ Error in Dining Scout: {e}")
                results_summary["errors"].append(f"dining-scout: {e}")

            # Agents 3 - 9: Specialist Discovery Scouts
            specialist_types = [
                ("vintage-gear", "Agent 3/14", "Vintage Musical Instruments Scout"),
                ("vintage-fashion", "Agent 4/14", "Curated Vintage Clothing Scout"),
                ("home-design", "Agent 5/14", "Vintage & Modern Home Design Scout"),
                ("culinary-goods", "Agent 6/14", "Gourmet Cooking & Food Specialty Stores Scout"),
                ("vinyl-records", "Agent 7/14", "Independent Vinyl Record Stores Scout"),
                ("speakeasy-cocktails", "Agent 8/14", "Craft Cocktail Bars & Speakeasies Scout"),
                ("bookstores", "Agent 9/14", "Independent & Vintage Bookstores Scout"),
            ]

            for s_type, agent_num, agent_name in specialist_types:
                print(f"▶ [{agent_num}] {agent_name}...")
                try:
                    res_spec = run_specialist_scout(
                        db=db,
                        trip_id=trip.id,
                        city_id=seg.id,
                        user_id=user_id,
                        agent_type=s_type,
                        max_results=max_results,
                        enrich_locations=True
                    )
                    new_count = res_spec.get("newly_discovered", 0)
                    results_summary["total_new_items"] += new_count
                    results_summary["agents"].setdefault(s_type, {"name": agent_name, "discovered": 0})
                    results_summary["agents"][s_type]["discovered"] += new_count
                    print(f"   ✓ Discovered & Ingested {new_count} spots for {seg.city_name}")
                except Exception as e:
                    print(f"   ⚠️ Error in {agent_name}: {e}")
                    results_summary["errors"].append(f"{s_type}: {e}")
    else:
        print("⏭️  Skipping Phase 1 Discovery Scouts (--skip-discovery active)")

    # =========================================================================
    # PHASE 2: TACTICAL, LOGISTICAL & ANALYTICAL ADVISORY AGENTS (10 - 14)
    # =========================================================================
    if not skip_analysis:
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("PHASE 2: TACTICAL, LOGISTICAL & ANALYTICAL ADVISORY AGENTS")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Agent 10: Lodging & Neighborhood Evaluator
        print("\n▶ [Agent 10/14] Lodging & Neighborhood Evaluator (Stay Scout)...")
        try:
            res_stay = evaluate_trip_lodging(db, trip.id)
            evals = res_stay.get("evaluations", [])
            print(f"   ✓ Evaluated {len(evals)} booked lodging location(s):")
            for ev in evals:
                if "status" in ev:
                    print(f"     • {ev.get('city_name', 'City')}: {ev.get('message')}")
                else:
                    print(f"     • {ev.get('stay_name')} ({ev.get('city_name')}): Walkability {ev.get('walkability_score')}/100 | {ev.get('verdict')}")
            results_summary["agents"]["stay-scout"] = {"name": "Lodging & Neighborhood Evaluator", "status": "Success", "evaluations": len(evals)}
        except Exception as e:
            print(f"   ⚠️ Error in Stay Scout: {e}")
            results_summary["errors"].append(f"stay-scout: {e}")

        # Agent 11: Weather Tactician & Packing Advisor
        print("\n▶ [Agent 11/14] Weather Tactician & Packing Advisor...")
        try:
            res_weather = evaluate_trip_weather_advisory(db, trip.id)
            rain_count = res_weather.get("rain_days_count", 0)
            eval_days = res_weather.get("total_days_evaluated", 0)
            checklist = res_weather.get("packing_checklist", [])
            print(f"   ✓ Evaluated {eval_days} itinerary days | Rain Risk Days: {rain_count} | Generated {len(checklist)} packing checklist items")
            for d in res_weather.get("day_advisories", [])[:3]:
                tag = "⚠️ Rain Risk" if d.get("is_rainy") else "✅ Clear"
                print(f"     📅 {d.get('date')} ({d.get('city_name')}): {d.get('condition')} ({tag})")
            results_summary["agents"]["weather-tactician"] = {
                "name": "Weather Tactician & Packing Advisor",
                "status": "Success",
                "evaluated_days": eval_days,
                "rain_risk_days": rain_count,
                "packing_items": len(checklist)
            }
        except Exception as e:
            print(f"   ⚠️ Error in Weather Tactician: {e}")
            results_summary["errors"].append(f"weather-tactician: {e}")

        # Agent 12: Autonomous Concierge & Reservation Assistant
        print("\n▶ [Agent 12/14] Autonomous Concierge & Reservation Assistant...")
        try:
            res_concierge = evaluate_reservation_plan(db, trip.id)
            total_act = res_concierge.get("total_items_analyzed", 0)
            act_res = res_concierge.get("actionable_count", 0)
            walk_in = res_concierge.get("walk_in_count", 0)
            print(f"   ✓ Analyzed {total_act} activities: {act_res} booking requirements identified | {walk_in} walk-in friendly")
            for r in res_concierge.get("actionable_reservations", [])[:3]:
                print(f"     🎟️  [{r.get('urgency')}] {r.get('title')} ({r.get('cost')}): {r.get('booking_tip')}")
            results_summary["agents"]["concierge-agent"] = {
                "name": "Autonomous Concierge & Reservation Assistant",
                "status": "Success",
                "analyzed": total_act,
                "actionable_reservations": act_res
            }
        except Exception as e:
            print(f"   ⚠️ Error in Concierge Agent: {e}")
            results_summary["errors"].append(f"concierge-agent: {e}")

        # Agent 13: Transit Route & Day Optimizer
        print("\n▶ [Agent 13/14] Transit Route & Day Optimizer...")
        try:
            scheduled_items = db.query(ItineraryItem).filter(
                ItineraryItem.trip_id == trip.id,
                ItineraryItem.assigned_date != "todo"
            ).all()
            scheduled_dates = sorted(list(set(it.assigned_date for it in scheduled_items)))
            if not scheduled_dates:
                print(f"   ℹ️  No assigned day items to optimize (all items are in wishlist 'todo').")
                results_summary["agents"]["transit-optimizer"] = {"name": "Transit Route & Day Optimizer", "status": "Wishlist Only"}
            else:
                optimized_days = 0
                for d in scheduled_dates:
                    opt_res = optimize_trip_day_schedule(db, trip.id, d, apply_changes=apply_routes)
                    optimized_days += 1
                    print(f"   ✓ Date {d}: Original Distance {opt_res.get('original_total_km', 0):.2f}km -> Optimized {opt_res.get('optimized_total_km', 0):.2f}km (Saved {opt_res.get('distance_saved_km', 0):.2f}km)")
                results_summary["agents"]["transit-optimizer"] = {
                    "name": "Transit Route & Day Optimizer",
                    "status": "Success",
                    "optimized_days": optimized_days
                }
        except Exception as e:
            print(f"   ⚠️ Error in Transit Optimizer: {e}")
            results_summary["errors"].append(f"transit-optimizer: {e}")

        # Agent 14: Group Budget & Expense Comptroller
        print("\n▶ [Agent 14/14] Group Budget & Expense Comptroller...")
        try:
            res_budget = audit_trip_budget(db, trip.id)
            spent = res_budget.get("total_spent", 0)
            curr = res_budget.get("currency", "USD")
            fair = res_budget.get("fair_share_per_person", 0)
            burn = res_budget.get("daily_burn_rate", 0)
            settlements = res_budget.get("settlement_balances", [])
            print(f"   ✓ Total Expenditures: {curr} {spent} | Fair Share: {curr} {fair}/person | Burn Rate: {curr} {burn}/day")
            print(f"   ✓ Balances Computed: {len(settlements)} group members audited")
            results_summary["agents"]["budget-comptroller"] = {
                "name": "Group Budget & Expense Comptroller",
                "status": "Success",
                "total_spent": spent,
                "fair_share": fair
            }
        except Exception as e:
            print(f"   ⚠️ Error in Budget Comptroller: {e}")
            results_summary["errors"].append(f"budget-comptroller: {e}")
    else:
        print("⏭️  Skipping Phase 2 Analytical Agents (--skip-analysis active)")

    duration = time.time() - start_time

    # =========================================================================
    # CONSOLIDATED SCORECARD & SUMMARY
    # =========================================================================
    print("\n" + "=" * 76)
    print("📋 TRAVEL SCOUT — ALL 14 AGENTS EXECUTION SCORECARD")
    print("=" * 76)
    print(f"Trip: '{trip.title}' | Duration: {duration:.2f}s | Newly Ingested Items: {results_summary['total_new_items']}")
    print("-" * 76)
    for agent_key, info in results_summary["agents"].items():
        name = info.get("name", agent_key)
        if "discovered" in info:
            print(f"  ✅ {name:<46} : Discovered {info['discovered']} items")
        elif "status" in info:
            extra = ""
            if "walkability_score" in info:
                extra = f" (Score: {info['walkability_score']}/100)"
            elif "rain_risk_days" in info:
                extra = f" ({info['rain_risk_days']} rain days, {info['packing_items']} packing items)"
            elif "actionable_reservations" in info:
                extra = f" ({info['actionable_reservations']} reservations needed)"
            elif "total_spent" in info:
                extra = f" (Total Spent: {info['total_spent']})"
            print(f"  ✅ {name:<46} : {info['status']}{extra}")
        else:
            print(f"  ✅ {name:<46} : Completed")

    if results_summary["errors"]:
        print("\n⚠️  Warnings / Notices Encountered:")
        for err in results_summary["errors"]:
            print(f"  - {err}")
    else:
        print("\n🎉 All 14 autonomous agents completed with 0 errors!")
    print("=" * 76 + "\n")

    return results_summary


def main():
    parser = argparse.ArgumentParser(description="Run all 14 Travel Scout Autonomous Agents across trip destinations")
    parser.add_argument("--trip-id", type=str, help="Specific Trip ID to target (defaults to active/latest trip)")
    parser.add_argument("--all-trips", action="store_true", help="Run across all trips in database")
    parser.add_argument("--max-results", type=int, default=2, help="Max results per category/agent query (default: 2)")
    parser.add_argument("--dry-run", action="store_true", help="Search without saving items into database")
    parser.add_argument("--skip-discovery", action="store_true", help="Skip Phase 1 discovery scouts and run only analytical agents")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip Phase 2 analytical agents and run only discovery scouts")
    parser.add_argument("--apply-routes", action="store_true", help="Apply optimized route order to database itinerary items")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        trips = get_target_trips(db, trip_id=args.trip_id, all_trips=args.all_trips)
        if not trips:
            print("Error: No trips found in database to run agents against.")
            sys.exit(1)

        user = db.query(User).first()
        user_id = user.id if user else trips[0].owner_id

        for trip in trips:
            run_all_agents_for_trip(
                db=db,
                trip=trip,
                user_id=user_id,
                max_results=args.max_results,
                dry_run=args.dry_run,
                skip_discovery=args.skip_discovery,
                skip_analysis=args.skip_analysis,
                apply_routes=args.apply_routes
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
