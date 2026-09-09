"""Multi-channel live web scout tailored dynamically to any destination city."""
import re
from typing import List, Dict, Any, Optional
from ddgs import DDGS
from scout.config import CITY_PRESETS
from scout.geocoding import resolve_city_coordinates

CHANNEL_SITE_MODIFIERS = {
    "all": "",
    "press": "\"weekly newspaper\" OR \"alternative weekly\" OR \"city paper\" OR \"arts and culture\" OR \"events calendar\" OR site:timeout.com",
    "events": "site:eventbrite.com OR site:timeout.com OR \"events calendar\" OR \"what's on\" OR \"things to do this weekend\"",
    "music": "site:eventbrite.com OR site:songkick.com OR site:dice.fm OR site:ticketmaster.com",
    "records": "\"record store\" OR \"vinyl shop\" OR \"used records\" OR \"crate digging\" OR \"record shop\"",
    "bookstores": "",
    "vintage-fashion": "",
    "vintage-gear": "",
    "home-design": "",
    "culinary-goods": "",
    "art": "\"art exhibit\" OR \"gallery opening\" OR \"museum exhibition\" OR vernissage OR \"contemporary art\"",
    "festivals": "\"street fair\" OR \"outdoor festival\" OR \"block party\" OR \"festa\" OR carnival OR \"street festival\"",
    "markets": "\"farmers market\" OR \"flea market\" OR \"artisan market\" OR \"mercado\" OR \"street market\"",
    "movies": "\"film festival\" OR \"open air cinema\" OR \"independent cinema\" OR screening OR \"indie film\"",
    "reddit": "site:reddit.com",
    "tiktok": "site:tiktok.com",
    "eater": "site:eater.com",
    "yelp": "site:yelp.com",
    "magazines": "site:timeout.com OR \"city magazine\" OR \"monthly magazine\" OR \"best of\" OR \"local guide\" OR magazine",
    "breweries": "brewery OR \"tasting room\" OR \"craft beer\" OR taproom OR microbrewery OR alehouse",
    "cocktails": "speakeasy OR \"craft cocktail\" OR \"cocktail bar\" OR \"hidden bar\" OR mixology",
    "michelin": "site:guide.michelin.com OR \"michelin star\" OR \"michelin guide\" OR \"bib gourmand\"",
    "guides": "site:lonelyplanet.com OR site:timeout.com OR site:fodors.com",
    "blogs": "site:eater.com OR blog OR food",
    "social": "site:facebook.com OR site:x.com OR site:instagram.com",
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
                    try:
                        raw_results = list(ddgs.text(f"{full_query} {site_mod}", max_results=max_results))
                    except Exception:
                        raw_results = []

                if not raw_results:
                    try:
                        raw_results = list(ddgs.text(full_query, max_results=max_results))
                    except Exception as clean_err:
                        print(f"Clean query search error for '{full_query}': {clean_err}")
                        raw_results = []
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
        return []

    # Resolve city centroid dynamically for coordinate fallback
    res_lat, res_lon, _ = resolve_city_coordinates(city_name)
    city_info = CITY_PRESETS.get(city_name, {})
    default_lat = city_info.get("lat") or (res_lat if res_lat != 0.0 else 0.0)
    default_lon = city_info.get("lon") or (res_lon if res_lon != 0.0 else 0.0)

    results = []
    for i, r in enumerate(raw_results):
        title = r.get("title", "")
        body = r.get("body", "")
        url = r.get("href", "")

        # Clean title
        clean_title = re.sub(
            r"\s*[-|–]\s*(Eventbrite|Songkick|DICE|Ticketmaster|Reddit|TikTok|Tripadvisor|Timeout|Lonely Planet|YouTube|SeatGeek|Bandsintown|Yelp|Eater|Michelin Guide).*",
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
        lower_text = f"{clean_title} {body}".lower()

        if "eventbrite" in lower_url:
            platform = "Eventbrite"
        elif "songkick.com" in lower_url:
            platform = "Songkick"
        elif "dice.fm" in lower_url or "dice.com" in lower_url:
            platform = "DICE"
        elif "ticketmaster" in lower_url:
            platform = "Ticketmaster"
        elif any(w in lower_text or w in lower_url for w in ["record store", "vinyl shop", "record shop", "in-store"]):
            platform = "Record Store"
        elif any(w in lower_text or w in lower_url for w in ["bookstore", "book shop", "antiquarian books", "used books", "rare editions", "livraria", "indie bookshop"]):
            platform = "Bookstore"
        elif any(w in lower_text or w in lower_url for w in ["vintage clothing", "vintage boutique", "curated thrift", "archival fashion", "retro apparel", "vintage fashion"]):
            platform = "Vintage Clothing"
        elif any(w in lower_text or w in lower_url for w in ["vintage guitar", "tube amp", "vintage amp", "guitar shop", "synthesizer", "used guitar", "pedal boutique"]):
            platform = "Vintage Gear"
        elif any(w in lower_text or w in lower_url for w in ["mid century modern", "vintage furniture", "home design", "artisan ceramics", "modernist design"]):
            platform = "Home Design"
        elif any(w in lower_text or w in lower_url for w in ["kitchenware", "japanese knives", "culinary store", "cookware", "gourmet pantry", "spice merchant"]):
            platform = "Culinary Goods"
        elif any(w in lower_text or w in lower_url for w in ["art gallery", "gallery opening", "contemporary art", "art exhibit", "museum exhibit", "vernissage"]):
            platform = "Art Gallery"
        elif any(w in lower_text or w in lower_url for w in ["film festival", "cinema", "open air cinema", "indie theatre", "screening"]):
            platform = "Cinema & Film"
        elif any(w in lower_text or w in lower_url for w in ["street fair", "street festival", "outdoor festival", "festa", "carnival"]):
            platform = "Street Fair & Festival"
        elif any(w in lower_text or w in lower_url for w in ["farmers market", "flea market", "artisan market", "mercado"]):
            platform = "Farmers & Artisan Market"
        elif "yelp.com" in lower_url or "yelp" in lower_title:
            platform = "Yelp"
        elif "eater.com" in lower_url or "eater" in lower_title:
            platform = "Eater"
        elif "guide.michelin.com" in lower_url or "michelin guide" in lower_text or "michelin star" in lower_text:
            platform = "Michelin Guide"
        elif "reddit.com" in lower_url:
            platform = "Reddit"
        elif "tiktok.com" in lower_url:
            platform = "TikTok"
        elif any(w in lower_url or w in lower_text for w in ["alternative weekly", "weekly paper", "alt weekly", "gazette", "chronicle", "city paper", "the portugal news", "mensagem de lisboa", "village voice", "chicago reader", "austin chronicle", "sf bay guardian", "londonist", "stranger"]):
            platform = "Alt-Weekly / Local Press"
        elif "timeout.com" in lower_url or any(m in lower_url or m in lower_title for m in ["magazine", "citymag", "eatery guide"]):
            platform = "City Magazine"
        elif "lonelyplanet.com" in lower_url:
            platform = "Lonely Planet"
        elif "fodors.com" in lower_url:
            platform = "Fodor's"
        elif any(k in lower_url or k in lower_title for k in ["brewery", "brewing", "taproom", "tasting room", "craft beer", "microbrewery", "alehouse"]):
            platform = "Craft Brewery"
        elif any(k in lower_url or k in lower_title for k in ["speakeasy", "cocktail bar", "craft cocktail", "hidden bar", "mixology"]):
            platform = "Speakeasy Lounge"
        elif any(k in lower_url or k in lower_title for k in ["venue", "concert hall", "jazz club", "coliseu", "casa da música", "musicbox", "theatro", "theatre", "auditorium"]):
            platform = "Music Venue"

        # Detect category: Honor caller's explicit category_hint if provided and specific
        valid_hint = category_hint if (category_hint and category_hint not in ("all", "gems")) else None
        if valid_hint:
            cat = valid_hint
        elif platform == "Record Store" or any(w in lower_text for w in ["record store", "vinyl shop", "in-store performance", "album signing", "turntable", "record shop", "crate digging", "used vinyl"]):
            cat = "records"
        elif platform == "Bookstore" or any(w in lower_text for w in ["bookstore", "book shop", "antiquarian books", "used books", "rare editions", "livraria", "book seller", "indie bookshop"]):
            cat = "bookstores"
        elif platform == "Vintage Clothing" or any(w in lower_text for w in ["vintage clothing", "vintage fashion", "curated thrift", "archival fashion", "retro apparel", "vintage boutique"]):
            cat = "vintage-fashion"
        elif platform == "Vintage Gear" or any(w in lower_text for w in ["vintage guitar", "tube amp", "vintage amp", "synthesizer", "guitar shop", "used guitar", "pedal boutique", "musical instruments"]):
            cat = "vintage-gear"
        elif platform == "Home Design" or any(w in lower_text for w in ["mid century modern", "vintage furniture", "home design", "artisan ceramics", "modernist design", "architectural antiques"]):
            cat = "home-design"
        elif platform == "Culinary Goods" or any(w in lower_text for w in ["kitchenware", "japanese knives", "culinary store", "artisan spices", "gourmet pantry", "cookware shop"]):
            cat = "culinary-goods"
        elif platform == "Art Gallery" or any(w in lower_text for w in ["art exhibit", "gallery opening", "vernissage", "museum exhibition", "contemporary art", "sculpture", "biennale", "curator"]):
            cat = "art"
        elif platform == "Cinema & Film" or any(w in lower_text for w in ["film festival", "open air cinema", "outdoor movie", "screening", "indie cinema", "cinephile", "documentary screening"]):
            cat = "movies"
        elif platform == "Street Fair & Festival" or any(w in lower_text for w in ["street fair", "block party", "outdoor festival", "street festival", "festa popular", "carnival"]):
            cat = "festivals"
        elif platform == "Farmers & Artisan Market" or any(w in lower_text for w in ["farmers market", "flea market", "artisan market", "produce market", "organic market", "weekend market"]):
            cat = "markets"
        elif platform == "Alt-Weekly / Local Press" or any(w in lower_text for w in ["alternative weekly", "weekly paper", "arts & culture guide", "city paper", "local gazette"]):
            cat = "press"
        elif platform == "Michelin Guide" or any(w in lower_text for w in ["michelin", "bib gourmand", "tasting menu", "fine dining", "chef's table", "degustation"]):
            cat = "michelin"
        elif platform == "Craft Brewery" or any(w in lower_text for w in ["brewery", "craft beer", "tasting room", "taproom", "microbrewery", "alehouse", "brewhouse", "ipa", "stout", "lager"]):
            cat = "beer"
        elif platform == "Speakeasy Lounge" or any(w in lower_text for w in ["speakeasy", "craft cocktail", "cocktail bar", "mixology", "hidden bar", "secret bar", "libations"]):
            cat = "cocktails"
        elif platform in ("Eventbrite", "Songkick", "DICE", "Ticketmaster", "Music Venue") or re.search(r"\b(concert|live music|fado|gig|orchestra|recital|jazz club)\b", lower_text):
            cat = "music"
        elif re.search(r"\b(wine|winery|vineyard|cellar|quintas?|port wine|porto wine|vinho|adega)\b", lower_text):
            cat = "wine"
        elif any(w in lower_text for w in ["restaurant", "food", "cafe", "bistro", "pastéis", "seafood", "tasca", "trattoria", "brasserie", "eatery"]):
            cat = "dining"
        elif any(w in lower_text for w in ["castle", "cathedral", "monastery", "historic", "palace", "citadel"]):
            cat = "historic"
        elif any(w in lower_text for w in ["miradouro", "viewpoint", "trail", "park", "beach", "walk", "river", "hike"]):
            cat = "outdoors"
        else:
            cat = category_hint or "gems"

        # Check for free admission
        is_free = False
        if any(w in lower_text or w in lower_title for w in ["free admission", "free event", "free entry", "no cover", "free and open", "admission is free", "entrada livre", "grátis", "gratuit"]):
            is_free = True

        # Cost and time estimates tailored for categories & platforms
        cost_val = "Free Admission" if is_free else "Check venue"
        time_val = "Flexible"
        if is_free:
            time_val = "Free & Open to public"
        elif platform == "Record Store" or cat == "records":
            cost_val = "Free / Browse Vinyl"
            time_val = "Afternoon / Evening In-Store"
        elif platform == "Bookstore" or cat == "bookstores":
            cost_val = "Free / Browse Books"
            time_val = "Daytime & Literary Hours"
        elif platform == "Vintage Clothing" or cat == "vintage-fashion":
            cost_val = "$$ - $$$"
            time_val = "Boutique Hours"
        elif platform == "Vintage Gear" or cat == "vintage-gear":
            cost_val = "$$ - $$$$"
            time_val = "Afternoon Auditions"
        elif platform == "Home Design" or cat == "home-design":
            cost_val = "$$ - $$$$"
            time_val = "Showroom Hours"
        elif platform == "Culinary Goods" or cat == "culinary-goods":
            cost_val = "$$ - $$$"
            time_val = "Market & Pantry Hours"
        elif platform == "Art Gallery" or cat == "art":
            cost_val = "Free Gallery / Ticketed Museum"
            time_val = "Gallery Hours & Vernissages"
        elif platform == "Cinema & Film" or cat == "movies":
            cost_val = "$8 - $15 Tickets"
            time_val = "Evening Showtimes"
        elif platform == "Street Fair & Festival" or cat == "festivals":
            cost_val = "Free Admission"
            is_free = True
            time_val = "Weekend / All-Day Festival"
        elif platform == "Farmers & Artisan Market" or cat == "markets":
            cost_val = "Free Entry"
            is_free = True
            time_val = "Morning / Afternoon Market"
        elif platform == "Michelin Guide" or cat == "michelin":
            cost_val = "$$$$ Fine Dining"
            time_val = "Dinner / Reservations required"
        elif platform == "Craft Brewery" or cat == "beer":
            cost_val = "$$ Pints & Flights"
            time_val = "Afternoon / Evening Taproom"
        elif platform == "Speakeasy Lounge" or cat == "cocktails":
            cost_val = "$$$ Craft Cocktails"
            time_val = "Late Evening / Nightcap"
        elif platform in ("Eventbrite", "Songkick", "DICE", "Ticketmaster"):
            cost_val = "RSVP / Tickets online"
            time_val = "Check tour & concert dates"
        elif platform == "Music Venue":
            cost_val = "Check box office"
            time_val = "Evening performances"
        elif platform in ("Yelp", "Eater", "City Magazine", "Alt-Weekly / Local Press"):
            cost_val = "$$ - $$$"
            time_val = "Weekly & Seasonal Guides"

        # Slight coordinate jitter around city center so pins don't overlap exactly
        jitter_lat = default_lat + ((i % 5) - 2) * 0.006
        jitter_lon = default_lon + ((i % 4) - 1.5) * 0.007

        results.append({
            "title": clean_title,
            "city_name": city_name,
            "category": cat,
            "neighborhood": f"{city_name} Cultural District",
            "address": f"{city_name}",
            "lat": round(jitter_lat, 4),
            "lon": round(jitter_lon, 4),
            "cost": cost_val,
            "is_free": is_free,
            "time_info": time_val,
            "highlight": body[:120] + "..." if len(body) > 120 else body,
            "description": body,
            "url": url,
            "source_platform": platform,
            "assigned_date": "todo",
        })


    return results

