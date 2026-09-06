"""Calendar Sync & Export (.ics and Google Calendar) for Travel Scout.

Generates standard RFC 5545 iCalendar files (.ics) compatible with Apple Calendar,
Google Calendar, and Microsoft Outlook, as well as direct one-click Google Calendar web links.
"""
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional

def escape_ics_text(text: Optional[str]) -> str:
    """Escape special characters for iCalendar format."""
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
        .replace("\r", "")
    )

def generate_trip_ics(trip: Any) -> str:
    """
    Generate an RFC 5545 .ics calendar string for a trip.
    
    Includes all scheduled activities, dinner reservations, concert tickets,
    and hotel check-in stays with dates, addresses, and booking references.
    """
    now_str = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Travel Scout//Collaborative Travel Platform//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(trip.title)}",
        f"X-WR-CALDESC:{escape_ics_text(trip.description or 'Travel Scout Itinerary')}",
    ]

    # 1. Add Hotel Stays
    for city in trip.city_segments:
        for stay in city.stays:
            if not stay.start_date:
                continue
            s_dt = stay.start_date.replace("-", "")
            e_dt = (stay.end_date or stay.start_date).replace("-", "")

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:stay-{stay.id}@travelscout.app",
                f"DTSTAMP:{now_str}",
                f"DTSTART;VALUE=DATE:{s_dt}",
                f"DTEND;VALUE=DATE:{e_dt}",
                f"SUMMARY:🏨 Stay: {escape_ics_text(stay.name)} ({city.city_name})",
                f"DESCRIPTION:{escape_ics_text(stay.notes or f'Accommodation in {city.city_name}')}",
                f"LOCATION:{escape_ics_text(stay.address)}",
            ])
            if stay.lat and stay.lon:
                lines.append(f"GEO:{stay.lat};{stay.lon}")
            lines.extend([
                "STATUS:CONFIRMED",
                "END:VEVENT"
            ])

    # 2. Add Scheduled Itinerary Items
    for item in trip.items:
        if not item.assigned_date or item.assigned_date == "todo":
            continue

        dt_clean = item.assigned_date.replace("-", "")
        summary_prefix = "📍"
        if item.category == "music":
            summary_prefix = "🎶"
        elif item.category in ("dining", "michelin"):
            summary_prefix = "🍽️"
        elif item.category == "movies":
            summary_prefix = "🎬"
        elif item.category == "art":
            summary_prefix = "🎨"
        elif item.category == "records":
            summary_prefix = "📻"
        elif item.category == "festivals":
            summary_prefix = "🎪"
        elif item.category == "markets":
            summary_prefix = "🥖"

        booking_note = ""
        if item.booking_status and item.booking_status != "unbooked":
            booking_note = f"\nBooking Status: {item.booking_status.upper()}"
            if item.booking_ref:
                booking_note += f" (Confirmation: {item.booking_ref})"

        personal_note = f"\nNote: {item.personal_note}" if item.personal_note else ""
        cost_info = f"\nCost: {item.cost}" if item.cost else ""
        url_info = f"\nLink: {item.url}" if item.url else ""
        schedule_info = f"\nTime: {item.time_info}" if item.time_info else ""

        full_desc = (
            f"{(item.highlight or item.description or '')}"
            f"{schedule_info}{cost_info}{booking_note}{personal_note}{url_info}"
        ).strip()

        loc = item.address or item.neighborhood or (item.city_segment.city_name if item.city_segment else "")

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:item-{item.id}@travelscout.app",
            f"DTSTAMP:{now_str}",
            f"DTSTART;VALUE=DATE:{dt_clean}",
            f"DTEND;VALUE=DATE:{dt_clean}",
            f"SUMMARY:{summary_prefix} {escape_ics_text(item.title)}",
            f"DESCRIPTION:{escape_ics_text(full_desc)}",
            f"LOCATION:{escape_ics_text(loc)}",
        ])
        if item.lat and item.lon:
            lines.append(f"GEO:{item.lat};{item.lon}")
        if item.url:
            lines.append(f"URL:{item.url}")
        lines.extend([
            "STATUS:CONFIRMED",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def generate_google_calendar_url(
    title: str,
    date_str: str,
    location: str = "",
    details: str = ""
) -> str:
    """Generate a one-click Google Calendar web event creation link."""
    dt_clean = date_str.replace("-", "")
    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": f"{dt_clean}/{dt_clean}",
        "details": details,
        "location": location,
    }
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"
