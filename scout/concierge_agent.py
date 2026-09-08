"""Autonomous Concierge & Reservation Assistant Agent for Travel Scout.

Scans all itinerary items and wishlist entries for ticketing and reservation requirements,
classifies booking urgency, and compiles an actionable reservation timeline.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from database.models import Trip, ItineraryItem


def evaluate_reservation_plan(
    db: Session,
    trip_id: str
) -> Dict[str, Any]:
    """Evaluates all items for booking urgency and compiles an actionable reservation plan."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}

    items = db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).all()

    actionable_reservations: List[Dict[str, Any]] = []
    walk_ins: List[Dict[str, Any]] = []

    for it in items:
        cost_str = (it.cost or "").lower()
        time_str = (it.time_info or "").lower()
        title_str = it.title.lower()
        cat_str = (it.category or "").lower()

        # Check booking signals
        is_ticketed = (
            it.is_free is False and
            any(k in cost_str or k in time_str for k in ["ticket", "rsvp", "$", "€", "£", "book", "reserve", "entry", "admission"])
        ) or any(k in title_str for k in ["concert", "tour", "exhibition", "festival", "show", "theatre"])

        # Determine urgency
        if any(k in title_str or k in cost_str for k in ["concert", "festival", "michelin", "resy", "opentable", "timed entry"]):
            urgency = "HIGH (Book 2-4 weeks in advance)"
            priority = 1
        elif is_ticketed or cat_str in ["movies", "music", "art"]:
            urgency = "MEDIUM (Book 3-7 days in advance)"
            priority = 2
        else:
            urgency = "LOW / FLEXIBLE (Walk-in friendly)"
            priority = 3

        item_payload = {
            "id": it.id,
            "title": it.title,
            "category": it.category,
            "neighborhood": it.neighborhood,
            "cost": it.cost or ("Free Admission" if it.is_free else "Check venue"),
            "is_free": it.is_free,
            "urgency": urgency,
            "priority": priority,
            "scheduled_date": it.assigned_date if it.assigned_date != "todo" else "Wishlist",
            "url": it.url,
            "booking_tip": "Online reservation recommended" if is_ticketed else "Walk-in access typically available"
        }

        if priority <= 2:
            actionable_reservations.append(item_payload)
        else:
            walk_ins.append(item_payload)

    # Sort actionable by priority, then by scheduled date
    actionable_reservations.sort(key=lambda x: (x["priority"], x["scheduled_date"]))

    return {
        "trip_id": trip_id,
        "trip_title": trip.title,
        "total_items_analyzed": len(items),
        "actionable_count": len(actionable_reservations),
        "walk_in_count": len(walk_ins),
        "actionable_reservations": actionable_reservations,
        "walk_in_friendly": walk_ins
    }
