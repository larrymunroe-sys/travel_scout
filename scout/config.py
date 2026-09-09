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
    "music": {"label": "Live Music & Concerts", "icon": "🎶", "color": "#a855f7"},
    "records": {"label": "Record Stores & In-Stores", "icon": "📻", "color": "#8b5cf6"},
    "bookstores": {"label": "Independent & Vintage Bookstores", "icon": "📚", "color": "#0ea5e9"},
    "vintage-fashion": {"label": "Vintage Clothing & Archival Fashion", "icon": "🧥", "color": "#f472b6"},
    "vintage-gear": {"label": "Vintage Guitars & Musical Gear", "icon": "🎸", "color": "#e879f9"},
    "home-design": {"label": "Vintage & Modern Home Design", "icon": "🛋️", "color": "#a78bfa"},
    "culinary-goods": {"label": "Gourmet Kitchenware & Food Specialties", "icon": "🔪", "color": "#fb923c"},
    "art": {"label": "Art Exhibits & Galleries", "icon": "🎨", "color": "#6366f1"},
    "movies": {"label": "Film & Open-Air Cinema", "icon": "🎬", "color": "#06b6d4"},
    "festivals": {"label": "Festivals & Street Fairs", "icon": "🎪", "color": "#f97316"},
    "markets": {"label": "Farmers Markets & Pop-ups", "icon": "🥖", "color": "#10b981"},
    "press": {"label": "Alt-Weeklies & Local Press", "icon": "📰", "color": "#38bdf8"},
    "historic": {"label": "Castles & Historic Sights", "icon": "🏰", "color": "#38bdf8"},
    "outdoors": {"label": "Miradouros & Trails", "icon": "🌊", "color": "#34d399"},
    "gems": {"label": "Local Neighborhood Gems", "icon": "💎", "color": "#e879f9"},
    "free": {"label": "Free Admission & Happenings", "icon": "🎟️", "color": "#4ade80"},
}

SEARCH_CHANNELS: Dict[str, Dict[str, str]] = {
    "all": {"label": "🌐 All Sources (Combined)", "badge": "All"},
    "press": {"label": "📰 Local Newspapers, Alt-Weeklies & Magazines", "badge": "Alt-Weekly"},
    "events": {"label": "📅 City Event Websites & Local Calendars", "badge": "Events"},
    "music": {"label": "🎵 Live Music & Tickets (Songkick, Eventbrite, DICE)", "badge": "Live Music"},
    "records": {"label": "📻 Record Stores & In-Store Live Performances", "badge": "Record Store"},
    "bookstores": {"label": "📚 Independent & Vintage Bookstores", "badge": "Bookstores"},
    "vintage-fashion": {"label": "🧥 Curated Vintage & Archival Fashion", "badge": "Vintage"},
    "vintage-gear": {"label": "🎸 Vintage Guitars & Boutique Amps", "badge": "Vintage Gear"},
    "home-design": {"label": "🛋️ Mid-Century & Modern Home Design", "badge": "Home Design"},
    "culinary-goods": {"label": "🔪 Gourmet Cookware & Specialty Foods", "badge": "Culinary"},
    "art": {"label": "🎨 Art Exhibits, Gallery Openings & Museum Shows", "badge": "Art"},
    "festivals": {"label": "🎪 Free Outdoor Festivals, Street Fairs & Carnivals", "badge": "Festivals"},
    "markets": {"label": "🥖 Farmers Markets & Weekend Flea Markets", "badge": "Markets"},
    "movies": {"label": "🎬 Film Festivals, Indie Cinema & Screenings", "badge": "Cinema"},
    "eater": {"label": "🍴 Eater.com Curated Heatmaps & Essential Guides", "badge": "Eater"},
    "yelp": {"label": "⭐ Yelp Top Reviews & Local Ratings", "badge": "Yelp"},
    "magazines": {"label": "📰 City Magazines & Local Lifestyle Press (TimeOut)", "badge": "City Mag"},
    "breweries": {"label": "🍺 Craft Breweries & Beer Tasting Rooms", "badge": "Breweries"},
    "cocktails": {"label": "🍸 Craft Cocktail Bars & Secret Speakeasies", "badge": "Speakeasies"},
    "michelin": {"label": "⭐ Michelin Guide & Fine Dining", "badge": "Michelin"},
    "venues": {"label": "🏛️ Music Venues & Concert Halls", "badge": "Venues"},
    "guides": {"label": "📖 Travel Guides (Lonely Planet, TimeOut, Fodor's)", "badge": "Guides"},
    "blogs": {"label": "✍️ Food & Culture Blogs", "badge": "Blogs"},
    "reddit": {"label": "💬 Reddit Community Advice & Hidden Gems", "badge": "Reddit"},
    "tiktok": {"label": "🎬 TikTok Viral Spots & Trends", "badge": "TikTok"},
    "social": {"label": "📱 Social Channels & Festival Calendars", "badge": "Social"},
}


