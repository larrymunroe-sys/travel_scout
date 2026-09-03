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
}

def live_city_search(
    city_name: str,
    query: str,
    channel: str = "all",
    category_hint: Optional[str] = None,
    max_results: int = 8
) -> List[Dict[str, Any]]:
    """Query live internet feeds scoped to a specific city and channel."""
    site_mod = CHANNEL_SITE_MODIFIERS.get(channel, "")
    full_query = f"{city_name} {query}".strip()
    if site_mod:
        full_query = f"{full_query} {site_mod}"

    results = []
    try:
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(full_query, max_results=max_results))
    except Exception as e:
        print(f"DuckDuckGo search error for '{full_query}': {e}")
        return []

    # Get city centroid for default coordinate fallback
    city_info = CITY_PRESETS.get(city_name, {})
    default_lat = city_info.get("lat", 38.7223)
    default_lon = city_info.get("lon", -9.1393)

    for i, r in enumerate(raw_results):
        title = r.get("title", "")
        body = r.get("body", "")
        url = r.get("href", "")

        # Clean title
        clean_title = re.sub(r"\s*[-|–]\s*(Reddit|TikTok|Tripadvisor|Timeout|Lonely Planet|YouTube).*", "", title, flags=re.I).strip()
        if not clean_title:
            clean_title = title

        # Detect source platform
        platform = "Web"
        if "reddit.com" in url:
            platform = "Reddit"
        elif "tiktok.com" in url:
            platform = "TikTok"
        elif "timeout.com" in url:
            platform = "TimeOut"
        elif "lonelyplanet.com" in url:
            platform = "Lonely Planet"
        elif "fodors.com" in url:
            platform = "Fodor's"
        elif "eater.com" in url:
            platform = "Eater"

        # Detect category
        cat = category_hint or "gems"
        lower_text = f"{clean_title} {body}".lower()
        if any(w in lower_text for w in ["fado", "music", "concert", "band", "live"]):
            cat = "music"
        elif any(w in lower_text for w in ["wine", "port", "cellar", "quinta", "tasting", "douro"]):
            cat = "wine"
        elif any(w in lower_text for w in ["restaurant", "food", "tasting", "cafe", "bistro", "pastéis", "seafood"]):
            cat = "dining"
        elif any(w in lower_text for w in ["castle", "museum", "cathedral", "monastery", "historic", "palace"]):
            cat = "historic"
        elif any(w in lower_text for w in ["miradouro", "viewpoint", "trail", "park", "beach", "walk", "river"]):
            cat = "outdoors"

        # Slight coordinate jitter around city center so pins don't overlap exactly
        jitter_lat = default_lat + ((i % 5) - 2) * 0.006
        jitter_lon = default_lon + ((i % 4) - 1.5) * 0.007

        results.append({
            "title": clean_title,
            "category": cat,
            "neighborhood": f"{city_name} Center",
            "address": f"{city_name}, Portugal",
            "lat": round(jitter_lat, 4),
            "lon": round(jitter_lon, 4),
            "cost": "Check venue",
            "is_free": False,
            "time_info": "Check live schedule",
            "highlight": body[:120] + "..." if len(body) > 120 else body,
            "description": body,
            "url": url,
            "source_platform": platform,
            "assigned_date": "todo",
        })

    return results
