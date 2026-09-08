"""Group Budget & Expense Comptroller Agent for Travel Scout.

Audits group travel expenditures, calculates fair shares and minimal debt settlements,
projects daily burn rates, and flags budget imbalance alerts.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import Trip, TripExpense, TripCollaborator, User


def audit_trip_budget(
    db: Session,
    trip_id: str,
    target_budget: Optional[float] = None
) -> Dict[str, Any]:
    """Performs a comprehensive financial and debt-settlement audit of a trip."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}

    expenses = db.query(TripExpense).filter(TripExpense.trip_id == trip_id).all()
    collabs = db.query(TripCollaborator).filter(TripCollaborator.trip_id == trip_id).all()

    # Member mapping
    members: Dict[str, str] = {}
    if trip.owner_id:
        owner_user = db.query(User).filter(User.id == trip.owner_id).first()
        members[trip.owner_id] = owner_user.name if owner_user else "Trip Owner"
    for c in collabs:
        if c.user:
            members[c.user_id] = c.user.name

    member_count = max(1, len(members))
    total_spent = sum(e.amount for e in expenses)
    curr = expenses[0].currency if expenses else "USD"

    # Category breakdown
    category_totals: Dict[str, float] = {}
    user_paid: Dict[str, float] = {uid: 0.0 for uid in members}

    for e in expenses:
        cat = e.category or "general"
        category_totals[cat] = round(category_totals.get(cat, 0.0) + e.amount, 2)
        uid = e.paid_by_user_id or trip.owner_id
        user_paid[uid] = round(user_paid.get(uid, 0.0) + e.amount, 2)

    # Fair share
    fair_share = round(total_spent / member_count, 2)

    # Settlement calculations
    debtors = []
    creditors = []
    settlement_balances = []

    for uid, name in members.items():
        paid = user_paid.get(uid, 0.0)
        net = round(paid - fair_share, 2)
        settlement_balances.append({
            "user_id": uid,
            "name": name,
            "total_paid": paid,
            "fair_share": fair_share,
            "net_balance": net
        })
        if net < -0.01:
            debtors.append({"name": name, "amount": -net})
        elif net > 0.01:
            creditors.append({"name": name, "amount": net})

    # Minimal settlement transfers
    settlement_plan = []
    d_i = 0
    c_i = 0
    while d_i < len(debtors) and c_i < len(creditors):
        d = debtors[d_i]
        c = creditors[c_i]
        amt = min(d["amount"], c["amount"])
        if amt > 0.01:
            settlement_plan.append({
                "from_member": d["name"],
                "to_member": c["name"],
                "amount": round(amt, 2),
                "currency": curr
            })
        d["amount"] -= amt
        c["amount"] -= amt
        if d["amount"] <= 0.01:
            d_i += 1
        if c["amount"] <= 0.01:
            c_i += 1

    # Trip days calculation
    total_days = 0
    for seg in trip.city_segments:
        if seg.start_date and seg.end_date:
            try:
                d1 = datetime.strptime(seg.start_date, "%Y-%m-%d")
                d2 = datetime.strptime(seg.end_date, "%Y-%m-%d")
                total_days += max(1, (d2 - d1).days + 1)
            except Exception:
                pass
    if total_days == 0:
        total_days = max(1, len(trip.city_segments) * 3)

    daily_burn_rate = round(total_spent / max(1, total_days), 2)
    daily_burn_per_person = round(daily_burn_rate / member_count, 2)

    # Alerts & insights
    alerts: List[Dict[str, str]] = []
    if total_spent > 0:
        for cat, amt in category_totals.items():
            pct = round((amt / total_spent) * 100, 1)
            if pct >= 50.0 and cat != "lodging":
                alerts.append({
                    "severity": "warning",
                    "message": f"High concentration: {cat.title()} accounts for {pct}% ({curr} {amt}) of entire trip spend."
                })

    zero_spenders = [name for uid, name in members.items() if user_paid.get(uid, 0.0) == 0.0]
    if zero_spenders and len(members) > 1:
        alerts.append({
            "severity": "info",
            "message": f"{', '.join(zero_spenders)} have not logged any expenses yet."
        })

    if target_budget and target_budget > 0:
        remaining_budget = round(target_budget - total_spent, 2)
        budget_pct = round((total_spent / target_budget) * 100, 1)
        if budget_pct >= 90.0:
            alerts.append({
                "severity": "critical",
                "message": f"Budget alert: {budget_pct}% of target budget spent ({curr} {remaining_budget} remaining)."
            })
    else:
        remaining_budget = None
        budget_pct = None

    return {
        "trip_id": trip_id,
        "trip_title": trip.title,
        "currency": curr,
        "total_spent": round(total_spent, 2),
        "target_budget": target_budget,
        "remaining_budget": remaining_budget,
        "budget_used_pct": budget_pct,
        "member_count": member_count,
        "fair_share_per_person": fair_share,
        "total_days": total_days,
        "daily_burn_rate": daily_burn_rate,
        "daily_burn_per_person": daily_burn_per_person,
        "category_totals": category_totals,
        "settlement_balances": settlement_balances,
        "settlement_plan": settlement_plan,
        "alerts": alerts
    }
