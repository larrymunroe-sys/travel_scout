"""Configuration, schemas, and city registries for Multi-City Travel Scout."""
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent

CITY_PRESETS: Dict[str, Dict[str, Any]] = {
    "Lisbon": {
        "country": "Portugal",
        "lat": 38.7223,
        "lon": -9.1393,
        "default_stay_name": "Heritage Avenida Liberdade Hotel",
        "default_stay_address": "Av. da Liberdade 28, 1250-145 Lisboa, Portugal",
        "stay_lat": 38.7188,
        "stay_lon": -9.1438,
        "subreddits": ["lisboa", "portugal"],
        "transit_system": "Lisbon Metro & Iconic Yellow Trams (Tram 28)"
    },
    "Porto": {
        "country": "Portugal",
        "lat": 41.1579,
        "lon": -8.6291,
        "default_stay_name": "The Yeatman Hotel (Gaia)",
        "default_stay_address": "Rua do Choupelo, 4400-088 Vila Nova de Gaia, Portugal",
        "stay_lat": 41.1340,
        "stay_lon": -8.6148,
        "subreddits": ["porto", "portugal"],
        "transit_system": "Metro do Porto & Funicular dos Guindais"
    },
    "Bragança": {
        "country": "Portugal",
        "lat": 41.8061,
        "lon": -6.7567,
        "default_stay_name": "Pousada de Bragança (São Bartolomeu)",
        "default_stay_address": "Rua Estrada do Turismo, 5300-271 Bragança, Portugal",
        "stay_lat": 41.8020,
        "stay_lon": -6.7620,
        "subreddits": ["portugal", "solotravel"],
        "transit_system": "STUB Urban Bus & Historic Citadel Walking Trails"
    },
    "Washington, D.C.": {
        "country": "United States",
        "lat": 38.9048,
        "lon": -77.0436,
        "default_stay_name": "Farragut Cultural Base",
        "default_stay_address": "1112 19th St NW, Washington, DC 20036",
        "stay_lat": 38.9048,
        "stay_lon": -77.0436,
        "subreddits": ["washingtondc"],
        "transit_system": "WMATA Metrorail & Circulator"
    }
}

CATEGORIES: Dict[str, Dict[str, str]] = {
    "dining": {"label": "Iconic Dining & Taverns", "icon": "🍽️", "color": "#fbbf24"},
    "beer": {"label": "Breweries & Beer Tasting Rooms", "icon": "🍺", "color": "#f59e0b"},
    "cocktails": {"label": "Craft Cocktails & Speakeasies", "icon": "🍸", "color": "#ec4899"},
    "michelin": {"label": "Michelin Star & Fine Dining", "icon": "⭐", "color": "#eab308"},
    "wine": {"label": "Wine Cellars & Lodges", "icon": "🍷", "color": "#f43f5e"},
    "historic": {"label": "Castles & Historic Sights", "icon": "🏰", "color": "#38bdf8"},
    "music": {"label": "Live Music & Gigs", "icon": "🎶", "color": "#a855f7"},
    "outdoors": {"label": "Miradouros & Trails", "icon": "🌊", "color": "#34d399"},
    "gems": {"label": "Local Neighborhood Gems", "icon": "💎", "color": "#e879f9"},
    "free": {"label": "Free Admission", "icon": "🎟️", "color": "#4ade80"},
}

SEARCH_CHANNELS: Dict[str, Dict[str, str]] = {
    "all": {"label": "🌐 All Sources (Combined)", "badge": "All"},
    "eater": {"label": "🍴 Eater.com Curated Heatmaps & Essential Guides", "badge": "Eater"},
    "yelp": {"label": "⭐ Yelp Top Reviews & Local Ratings", "badge": "Yelp"},
    "magazines": {"label": "📰 City Magazines & Local Lifestyle Press (TimeOut, Local Mags)", "badge": "City Mag"},
    "breweries": {"label": "🍺 Craft Breweries & Beer Tasting Rooms", "badge": "Breweries"},
    "cocktails": {"label": "🍸 Craft Cocktail Bars & Secret Speakeasies", "badge": "Speakeasies"},
    "michelin": {"label": "⭐ Michelin Guide & Fine Dining", "badge": "Michelin"},
    "music": {"label": "🎵 Live Music & Tickets (Eventbrite, DICE, Songkick, Ticketmaster)", "badge": "Live Music"},
    "venues": {"label": "🏛️ Music Venues & Concert Halls", "badge": "Venues"},
    "guides": {"label": "📖 Travel Guides (Lonely Planet, TimeOut, Fodor's)", "badge": "Guides"},
    "blogs": {"label": "✍️ Food & Culture Blogs", "badge": "Blogs"},
    "reddit": {"label": "💬 Reddit Community Advice & Hidden Gems", "badge": "Reddit"},
    "tiktok": {"label": "🎬 TikTok Viral Spots & Trends", "badge": "TikTok"},
    "social": {"label": "📱 Social Channels & Festival Calendars", "badge": "Social"},
}

