"""Multi-channel live web scout tailored dynamically to any destination city."""
import re
from typing import List, Dict, Any, Optional
from ddgs import DDGS
from scout.config import CITY_PRESETS

CHANNEL_SITE_MODIFIERS = {
    "reddit": "site:reddit.com",
    "tiktok": "site:tiktok.com",
    "guides": "site:lonelyplanet.com OR site:timeout.com OR site:fodors.com",
    "blogs": "site:eater.com OR blog OR food",
    "social": "site:facebook.com OR site:x.com OR site:instagram.com",
    "music": "site:eventbrite.com OR site:songkick.com OR site:dice.fm OR site:ticketmaster.com",
    "venues": "\"live music venue\" OR \"concert hall\" OR \"jazz club\" OR \"music club\"",
    "tickets": "site:eventbrite.com OR site:ticketmaster.com OR site:dice.fm OR site:songkick.com",
}

def live_city_search(
    city_name: str,
    query: str,
    channel: str = "all",
    category_hint: Optional[str] = None,
    max_results: int = 8
) -> List[Dict[str, Any]]:
    """Query live internet feeds scoped to a specific city and channel."""
    is_music_search = (
        channel in ("music", "venues", "tickets")
        or category_hint == "music"
        or any(w in query.lower() for w in ["music", "concert", "gig", "show", "band", "fado", "venue", "ticket", "eventbrite", "songkick", "dice", "ticketmaster"])
    )

    raw_results = []
    seen_urls = set()

    try:
        with DDGS() as ddgs:
            if channel == "music" or (channel == "all" and is_music_search):
                # Targeted dual-scan for live music tickets, tour dates, and music venues
                q1 = f"{city_name} {query} site:eventbrite.com OR site:songkick.com OR site:dice.fm"
                q2 = f"{city_name} {query} site:ticketmaster.com OR \"live music venue\" OR \"concert hall\""
                for subquery in [q1, q2]:
                    try:
                        for r in list(ddgs.text(subquery, max_results=max(3, max_results // 2))):
                            if r.get("href") not in seen_urls:
                                seen_urls.add(r.get("href"))
                                raw_results.append(r)
                    except Exception as sub_err:
                        print(f"Music subquery error for '{subquery}': {sub_err}")
            else:
                site_mod = CHANNEL_SITE_MODIFIERS.get(channel, "")
                full_query = f"{city_name} {query}".strip()
                if site_mod:
                    full_query = f"{full_query} {site_mod}"

                raw_results = list(ddgs.text(full_query, max_results=max_results))
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
        return []

    # Get city centroid for default coordinate fallback
    city_info = CITY_PRESETS.get(city_name, {})
    default_lat = city_info.get("lat", 38.7223)
    default_lon = city_info.get("lon", -9.1393)

    results = []
    for i, r in enumerate(raw_results):
        title = r.get("title", "")
        body = r.get("body", "")
        url = r.get("href", "")

        # Clean title
        clean_title = re.sub(
            r"\s*[-|–]\s*(Eventbrite|Songkick|DICE|Ticketmaster|Reddit|TikTok|Tripadvisor|Timeout|Lonely Planet|YouTube|SeatGeek|Bandsintown).*",
            "",
            title,
            flags=re.I
        ).strip()
        if not clean_title:
            clean_title = title

        # Detect source platform
        platform = "Web"
        lower_url = url.lower()
        lower_title = clean_title.lower()
        if "eventbrite" in lower_url:
            platform = "Eventbrite"
        elif "songkick.com" in lower_url:
            platform = "Songkick"
        elif "dice.fm" in lower_url or "dice.com" in lower_url:
            platform = "DICE"
        elif "ticketmaster" in lower_url:
            platform = "Ticketmaster"
        elif "reddit.com" in lower_url:
            platform = "Reddit"
        elif "tiktok.com" in lower_url:
            platform = "TikTok"
        elif "timeout.com" in lower_url:
            platform = "TimeOut"
        elif "lonelyplanet.com" in lower_url:
            platform = "Lonely Planet"
        elif "fodors.com" in lower_url:
            platform = "Fodor's"
        elif "eater.com" in lower_url:
            platform = "Eater"
        elif any(k in lower_url or k in lower_title for k in ["venue", "concert hall", "jazz club", "coliseu", "casa da música", "musicbox", "theatro", "theatre", "auditorium"]):
            platform = "Music Venue"

        # Detect category
        cat = category_hint or "gems"
        lower_text = f"{clean_title} {body}".lower()
        if platform in ("Eventbrite", "Songkick", "DICE", "Ticketmaster", "Music Venue"):
            cat = "music"
        elif any(w in lower_text for w in ["fado", "music", "concert", "band", "live", "gig", "show", "tour", "venue", "festival", "orchestra", "dj"]):
            cat = "music"
        elif any(w in lower_text for w in ["wine", "port", "cellar", "quinta", "tasting", "douro"]):
            cat = "wine"
        elif any(w in lower_text for w in ["restaurant", "food", "tasting", "cafe", "bistro", "pastéis", "seafood", "tasca"]):
            cat = "dining"
        elif any(w in lower_text for w in ["castle", "museum", "cathedral", "monastery", "historic", "palace", "citadel"]):
            cat = "historic"
        elif any(w in lower_text for w in ["miradouro", "viewpoint", "trail", "park", "beach", "walk", "river", "hike"]):
            cat = "outdoors"

        # Cost and time estimates tailored for live music / ticketing
        cost_val = "Check venue"
        time_val = "Check live schedule"
        if platform in ("Eventbrite", "Songkick", "DICE", "Ticketmaster"):
            cost_val = "RSVP / Tickets online"
            time_val = "Check tour & concert dates"
        elif platform == "Music Venue":
            cost_val = "Check box office"
            time_val = "Evening performances"

        # Slight coordinate jitter around city center so pins don't overlap exactly
        jitter_lat = default_lat + ((i % 5) - 2) * 0.006
        jitter_lon = default_lon + ((i % 4) - 1.5) * 0.007

        results.append({
            "title": clean_title,
            "category": cat,
            "neighborhood": f"{city_name} Cultural District",
            "address": f"{city_name}",
            "lat": round(jitter_lat, 4),
            "lon": round(jitter_lon, 4),
            "cost": cost_val,
            "is_free": False,
            "time_info": time_val,
            "highlight": body[:120] + "..." if len(body) > 120 else body,
            "description": body,
            "url": url,
            "source_platform": platform,
            "assigned_date": "todo",
        })

    return results

