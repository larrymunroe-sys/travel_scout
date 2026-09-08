"""Dynamic transit, mileage, bus routes, and date-aware stay matching for any destination city."""
import math
import urllib.parse
from typing import Optional, List, Dict, Any

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in kilometers."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def resolve_stay_for_date(stays: List[Any], target_date: Optional[str], allow_fallback: bool = True) -> Optional[Any]:
    """
    Select the active accommodation / hotel for a specific date from a list of stays.
    Enables switching hotels midway through a city stay!
    """
    if not stays:
        return None

    if not target_date or target_date == "todo":
        return stays[0] if allow_fallback else None

    # Look for exact date range match
    for s in stays:
        if s.start_date and s.end_date:
            if s.start_date <= target_date <= s.end_date:
                return s

    # Fallback to first stay only if allowed
    return stays[0] if allow_fallback else None


def resolve_stay_for_trip_date(
    city_segments: List[Any],
    target_date: Optional[str],
    preferred_city_id: Optional[str] = None
) -> tuple[Optional[Any], Optional[Any]]:
    """
    Resolve the active lodging / accommodation for a target date across all city segments.
    By default, the starting destination/origin is from the lodging for that date to the destination.
    Returns: (active_stay, active_city_segment)
    """
    if not city_segments:
        return None, None

    # 1. If assigned to a specific calendar date, find the stay whose date range covers it
    if target_date and target_date != "todo":
        # First priority: exact stay date match
        for seg in city_segments:
            for s in (seg.stays or []):
                if s.start_date and s.end_date and s.start_date <= target_date <= s.end_date:
                    return s, seg

        # Second priority: city segment date match
        for seg in city_segments:
            if seg.start_date and seg.end_date and seg.start_date <= target_date <= seg.end_date:
                if seg.stays:
                    return seg.stays[0], seg
                return None, seg

    # 2. If date is 'todo' or outside known ranges, use preferred city if specified
    if preferred_city_id:
        for seg in city_segments:
            if str(seg.id) == str(preferred_city_id):
                if seg.stays:
                    return resolve_stay_for_date(seg.stays, target_date, allow_fallback=True), seg
                return None, seg

    # 3. Default fallback: First city segment and its first stay
    first_seg = city_segments[0]
    first_stay = first_seg.stays[0] if (first_seg and first_seg.stays) else None
    return first_stay, first_seg


def _build_directions_urls(
    stay: Optional[Any],
    venue_lat: Optional[float],
    venue_lon: Optional[float],
    city_name: str,
    venue_title: str = "",
    venue_address: str = ""
) -> Dict[str, str]:
    """
    Build actionable Google Maps transit, walking, and driving directions URLs.
    The origin (starting point) is pre-populated by default from the lodging for that date.
    """
    base = "https://www.google.com/maps/dir/?api=1"

    # 1. Starting Origin: Default from lodging for that date
    if stay:
        if stay.lat is not None and stay.lon is not None and stay.lat != 0.0:
            orig = f"{stay.lat},{stay.lon}"
        elif stay.address:
            name_lower = (stay.name or "").lower()
            is_residential = any(w in name_lower for w in [
                "friend", "house", "home", "airbnb", "apartment", "apt", "staying with", "condo", "couch", "private"
            ])
            if is_residential or (stay.name and stay.name in stay.address):
                orig = urllib.parse.quote(stay.address.strip())
            else:
                orig = urllib.parse.quote(f"{stay.name}, {stay.address}".strip())
        else:
            orig = urllib.parse.quote(f"{stay.name or 'Hotel'}, {city_name}".strip())
    else:
        orig = urllib.parse.quote(city_name or "Hotel")

    # 2. Destination:
    if venue_lat is not None and venue_lon is not None and venue_lat != 0.0:
        dest = f"{venue_lat},{venue_lon}"
    else:
        dest_str = f"{venue_title or ''} {venue_address or ''}, {city_name}".strip()
        dest = urllib.parse.quote(dest_str or "Destination")

    return {
        "transit_url": f"{base}&origin={orig}&destination={dest}&travelmode=transit",
        "walking_url": f"{base}&origin={orig}&destination={dest}&travelmode=walking",
        "driving_url": f"{base}&origin={orig}&destination={dest}&travelmode=driving"
    }


generate_directions_url = _build_directions_urls
build_directions_urls = _build_directions_urls


def _resolve_transit_network(
    city_label: str,
    text_haystack: str,
    straight_km: float,
    stay_name: str
) -> Dict[str, Any]:
    """Resolve city-specific transit system, bus lines, metro stations, and fare tips."""
    c_lower = city_label.lower()
    h_lower = text_haystack.lower()

    # Default generic transit info
    est_transit_mins = max(6, min(55, round(straight_km * 2.2 + 5)))
    network_info = {
        "transit_mode": "Bus / Metro",
        "transit_line": f"{city_label + ' ' if city_label else ''}City Bus / Transit Network",
        "bus_routes": "Local city bus lines & urban transit",
        "transit_details": f"Board local city bus or metro towards destination ({est_transit_mins} mins total).",
        "fare_tip": "Contactless card tap or local transit pass.",
        "currency": "EUR" if any(eu in c_lower for eu in ["portugal", "spain", "france", "germany", "italy", "austria", "netherlands", "greece", "finland", "ireland", "lisbon", "porto", "bragança", "braganca", "coimbra", "barcelona", "madrid", "paris", "rome", "berlin", "amsterdam", "vienna"]) else "USD"
    }

    # 1. LISBON
    if "lisbon" in c_lower or "lisboa" in c_lower:
        network_info["currency"] = "EUR"
        network_info["fare_tip"] = "Navegante card €1.80/single trip (valid 60m with bus/metro/tram transfers), or €6.80 24h unlimited pass."
        
        if any(w in h_lower for w in ["belém", "belem", "jerónimos", "jeronimos", "torre de belém", "maat", "ccb", "ajuda", "pasteis de belém", "pastéis de belém"]):
            network_info["transit_mode"] = "Bus & Tram"
            network_info["transit_line"] = "Carris Bus 728 / Tram 15E"
            network_info["bus_routes"] = "Carris Bus 728 (rapid waterfront), Bus 714, Bus 727, Bus 729"
            network_info["transit_details"] = "Board Carris Bus 728 or historic Tram 15E from Praça da Figueira / Cais do Sodré direct along the Tagus to Belém (Mosteiro Jerónimos stop). Or take CP Cascais train from Cais do Sodré (7 mins)."
            est_transit_mins = max(16, min(25, round(straight_km * 2.0 + 8)))
        elif any(w in h_lower for w in ["alfama", "fado", "santa luzia", "portas do sol", "castelo", "são jorge", "sao jorge", "mouraria", "graça", "graca"]):
            network_info["transit_mode"] = "Historic Tram / Minibus"
            network_info["transit_line"] = "Iconic Tram 28E / Carris Bus 737"
            network_info["bus_routes"] = "Carris Bus 737 (Praça da Figueira ⇄ Castelo), Bus 712, Bus 734"
            network_info["transit_details"] = "Hop on Tram 28E through the winding cobblestone alleys of Alfama, or take minibus Bus 737 from Praça da Figueira directly to the Castle gate."
            est_transit_mins = max(10, min(18, round(straight_km * 2.2 + 6)))
        elif any(w in h_lower for w in ["lx factory", "alcântara", "alcantara", "docks", "ler devagar"]):
            network_info["transit_mode"] = "Tram / Carris Bus"
            network_info["transit_line"] = "Tram 15E / Carris Bus 720 & 728"
            network_info["bus_routes"] = "Carris Bus 720, 724, 728, 738, 760"
            network_info["transit_details"] = "Take Tram 15E or Bus 720/728 to Calvário / LX Factory stop right under 25 de Abril Bridge."
            est_transit_mins = max(12, min(20, round(straight_km * 2.0 + 6)))
        elif any(w in h_lower for w in ["oriente", "parque das nações", "oceanário", "oceanario"]):
            network_info["transit_mode"] = "Metro & Rapid Bus"
            network_info["transit_line"] = "Metro Red Line / Carris Bus 728"
            network_info["bus_routes"] = "Carris Bus 728, 744, 782"
            network_info["transit_details"] = "Take Metro Red Line (Linha Vermelha) direct to Oriente Station or scenic Bus 728 along the riverfront."
            est_transit_mins = max(18, min(28, round(straight_km * 1.8 + 8)))
        elif any(w in h_lower for w in ["gulbenkian", "saldanha", "campo pequeno", "avenidas novas"]):
            network_info["transit_mode"] = "Metro Blue / Yellow Line"
            network_info["transit_line"] = "Metro Linha Azul (São Sebastião) / Bus 726"
            network_info["bus_routes"] = "Carris Bus 713, 726, 746"
            network_info["transit_details"] = "Direct Metro Blue Line from Avenida/Restauradores to São Sebastião or Yellow Line to Saldanha."
            est_transit_mins = max(10, min(16, round(straight_km * 2.0 + 5)))
        elif any(w in h_lower for w in ["bairro alto", "chiado", "príncipe real", "principe real", "miradouro de santa catarina"]):
            network_info["transit_mode"] = "Funicular & Metro"
            network_info["transit_line"] = "Elevador da Glória / Metro Baixa-Chiado"
            network_info["bus_routes"] = "Carris Bus 758, 202, Elevador da Glória funicular"
            network_info["transit_details"] = "Take Elevador da Glória funicular from Praça dos Restauradores to São Pedro de Alcântara, or Metro Baixa-Chiado."
            est_transit_mins = max(6, min(12, round(straight_km * 2.0 + 4)))
        else:
            network_info["transit_mode"] = "Carris Bus & Metro"
            network_info["transit_line"] = "Carris City Bus & Lisbon Metro"
            network_info["bus_routes"] = "Carris Bus network (7xx routes) & Metro Blue/Green/Yellow lines"
            network_info["transit_details"] = f"Take Carris bus or Metro from near {stay_name} (~{est_transit_mins} mins total)."

    # 2. WASHINGTON, D.C.
    elif "washington" in c_lower or "d.c." in c_lower or "dc" in c_lower:
        network_info["currency"] = "USD"
        network_info["fare_tip"] = "SmarTrip card or tap Apple Wallet / Google Pay ($2.00-$2.25 off-peak Metro, $1.00 DC Circulator, $2.00 Metrobus with 2hr free bus transfer)."
        
        if any(w in h_lower for w in ["mall", "tidal basin", "cherry blossom", "lincoln", "washington monument", "smithsonian", "reflecting pool", "jefferson memorial", "vietnam", "korean", "wwii"]):
            network_info["transit_mode"] = "DC Circulator & Metrorail"
            network_info["transit_line"] = "DC Circulator (National Mall Loop) / Metro Blue Line"
            network_info["bus_routes"] = "DC Circulator ($1 National Mall Loop), Metrobus 32, 33, 36, 52"
            network_info["transit_details"] = "Hop on the DC Circulator National Mall loop ($1) or take Blue/Orange/Silver Metro lines to Smithsonian or Federal Triangle Station."
            est_transit_mins = max(10, min(18, round(straight_km * 2.2 + 6)))
        elif any(w in h_lower for w in ["capitol", "library of congress", "eastern market", "supreme court", "senate", "house"]):
            network_info["transit_mode"] = "Metrorail & Circulator"
            network_info["transit_line"] = "WMATA Blue/Orange/Silver Line to Capitol South / Eastern Market"
            network_info["bus_routes"] = "DC Circulator (Congress Heights - Union Station), Metrobus 90, 92, 32, 36"
            network_info["transit_details"] = "Direct Blue/Orange/Silver Metro from Farragut West / Metro Center direct to Capitol South (10 mins) or Eastern Market (12 mins)."
            est_transit_mins = max(11, min(18, round(straight_km * 2.0 + 6)))
        elif any(w in h_lower for w in ["georgetown", "blues alley", "m street", "wisconsin"]):
            network_info["transit_mode"] = "DC Circulator & Metrobus"
            network_info["transit_line"] = "DC Circulator (Georgetown Route) / Metrobus 31 & 33"
            network_info["bus_routes"] = "DC Circulator (Georgetown - Union Station route), Metrobus 31, 33, 38B, G2"
            network_info["transit_details"] = "Take DC Circulator along K Street / Pennsylvania Ave directly into the heart of Georgetown ($1)."
            est_transit_mins = max(9, min(16, round(straight_km * 2.2 + 5)))
        elif any(w in h_lower for w in ["u street", "ben's chili", "bens chili", "shaw", "14th street", "howard", "9:30 club"]):
            network_info["transit_mode"] = "Metrorail & Metrobus"
            network_info["transit_line"] = "WMATA Green/Yellow Line (U Street Station) / Metrobus S2"
            network_info["bus_routes"] = "Metrobus S2, S4 (16th Street line), Bus 52, 54 (14th St line), Bus 90, 92"
            network_info["transit_details"] = "Take Green/Yellow Metro Line to U Street/Cardozo Station or Metrobus S2/S4 north on 16th St to U Street."
            est_transit_mins = max(10, min(16, round(straight_km * 2.0 + 5)))
        elif any(w in h_lower for w in ["dupont", "adams morgan", "zoo", "connecticut"]):
            network_info["transit_mode"] = "Metro Red Line & Metrobus"
            network_info["transit_line"] = "WMATA Red Line / Metrobus 42 & 43"
            network_info["bus_routes"] = "Metrobus 42, 43 (Connecticut Ave line), DC Circulator (Woodley Park - Adams Morgan)"
            network_info["transit_details"] = "Take Metro Red Line to Dupont Circle or Woodley Park, or Metrobus 42/43 up Connecticut Ave."
            est_transit_mins = max(8, min(14, round(straight_km * 2.0 + 4)))
        else:
            network_info["transit_mode"] = "WMATA Metro & Bus"
            network_info["transit_line"] = "WMATA Metrorail (6 lines) & Metrobus"
            network_info["bus_routes"] = "DC Metrobus & DC Circulator routes"
            network_info["transit_details"] = f"Take WMATA Metrorail or Metrobus from near {stay_name} (~{est_transit_mins} mins total)."

    # 3. PORTO
    elif "porto" in c_lower or "gaia" in c_lower:
        network_info["currency"] = "EUR"
        network_info["fare_tip"] = "Andante card (Z2 zone ~€1.40). Validate at yellow station card readers before boarding."
        if any(w in h_lower for w in ["yeatman", "gaia", "ribeira", "douro", "wine lodge", "taylor", "sandeman", "calem", "graham", "d. luís", "dom luis"]):
            network_info["transit_mode"] = "Metro Line D & Scenic Bus"
            network_info["transit_line"] = "Metro Line D (Yellow) / STCP Bus 500"
            network_info["bus_routes"] = "STCP Bus 500 (scenic double-decker along Douro), Bus 900, 901, 906"
            network_info["transit_details"] = "Take Metro Line D across upper deck of Ponte Luís I to Jardim do Morro, or STCP double-decker Bus 500 along the riverbank."
            est_transit_mins = max(8, min(16, round(straight_km * 2.2 + 5)))
        elif any(w in h_lower for w in ["boavista", "casa da música", "casa da musica", "serralves"]):
            network_info["transit_mode"] = "Metro Trunk Lines & Bus"
            network_info["transit_line"] = "Metro Lines A, B, C, E, F (Casa da Música) / STCP Bus 201"
            network_info["bus_routes"] = "STCP Bus 200, 201, 203, 502"
            network_info["transit_details"] = "Direct Metro to Casa da Música Station, then STCP Bus 201/203 to Serralves gardens."
            est_transit_mins = max(11, min(18, round(straight_km * 2.0 + 5)))
        elif any(w in h_lower for w in ["foz", "passeio alegre", "matosinhos"]):
            network_info["transit_mode"] = "Scenic Bus & Historic Tram"
            network_info["transit_line"] = "STCP Bus 500 / Historic Tram 1"
            network_info["bus_routes"] = "STCP Bus 500 (along the Douro estuary), Bus 202, Bus 502"
            network_info["transit_details"] = "Ride historic Tram 1 from Infante or double-decker Bus 500 along the scenic riverbanks to Foz do Douro."
            est_transit_mins = max(15, min(24, round(straight_km * 2.0 + 6)))
        else:
            network_info["transit_mode"] = "STCP Bus & Metro do Porto"
            network_info["transit_line"] = "STCP Urban Bus Network & Metro do Porto"
            network_info["bus_routes"] = "STCP City Buses (routes 200-900 series)"
            network_info["transit_details"] = f"Take STCP bus or Metro do Porto from {stay_name} (~{est_transit_mins} mins total)."

    # 4. BRAGANÇA
    elif "bragança" in c_lower or "braganca" in c_lower:
        network_info["currency"] = "EUR"
        network_info["transit_mode"] = "STUB Urban Bus"
        network_info["transit_line"] = "STUB Linha 1 & Linha 2"
        network_info["bus_routes"] = "STUB Linha 1 (Citadel & Castle), Linha 2 (Polytechnic & Hospital), Linha 3 (Urban Belt)"
        network_info["transit_details"] = "Take STUB Linha 1 connecting the bus terminal, Praça da Sé, and the medieval Citadel."
        network_info["fare_tip"] = "STUB single onboard ticket ~€1.00 cash."
        est_transit_mins = max(6, min(14, round(straight_km * 2.8 + 4)))

    # 5. REYKJAVIK
    elif "reykjavik" in c_lower or "iceland" in c_lower:
        network_info["currency"] = "ISK"
        network_info["transit_mode"] = "Strætó City Bus"
        network_info["transit_line"] = "Strætó Bus Lines (1, 3, 6, 11, 12, 14)"
        network_info["bus_routes"] = "Strætó Bus 1, 3, 6, 11, 12, 14 from Hlemmur & Lækjartorg hubs"
        network_info["transit_details"] = "Take Strætó yellow city bus from central hubs (Hlemmur or Lækjartorg) across Reykjavik."
        network_info["fare_tip"] = "Klapp card or Klapp app (~570 ISK / $4.20 per ride, free transfers within 75 mins)."
        est_transit_mins = max(8, min(20, round(straight_km * 2.5 + 5)))

    # 6. NEW YORK
    elif "new york" in c_lower or "nyc" in c_lower:
        network_info["currency"] = "USD"
        network_info["transit_mode"] = "MTA Subway & Select Bus"
        network_info["transit_line"] = "MTA Subway & Select Bus Service (SBS)"
        network_info["bus_routes"] = "MTA Bus network (M1, M2, M3, M4, M15-SBS, M55, B62)"
        network_info["transit_details"] = "Take the MTA Subway or SBS crosstown/avenue buses."
        network_info["fare_tip"] = "OMNY contactless tap-to-pay ($2.90/ride with free 2h transfer; 7-day fare cap)."
        est_transit_mins = max(8, min(25, round(straight_km * 2.2 + 5)))

    # 7. SAN DIEGO
    elif "san diego" in c_lower:
        network_info["currency"] = "USD"
        network_info["transit_mode"] = "MTS Trolley & Rapid Bus"
        network_info["transit_line"] = "MTS Rapid Bus (Route 215) & MTS Trolley"
        network_info["bus_routes"] = "MTS Route 215 Rapid (El Cajon Blvd corridor), Route 1, Route 7 (Balboa Park/Downtown), Route 30 (La Jolla)"
        network_info["transit_details"] = "Take MTS Route 215 Rapid along El Cajon Blvd directly connecting North Park to Balboa Park and Downtown San Diego."
        network_info["fare_tip"] = "PRONTO contactless card or mobile app ($2.50 one-way, 2h free transfers, $6 daily fare cap)."
        est_transit_mins = max(8, min(28, round(straight_km * 2.3 + 5)))

    # 7. LONDON
    elif "london" in c_lower:
        network_info["currency"] = "GBP"
        network_info["transit_mode"] = "Underground & Red Buses"
        network_info["transit_line"] = "London Underground (Tube) & Iconic Red Buses"
        network_info["bus_routes"] = "London Bus network (Bus 9, 11, 15, 24, 73, 139)"
        network_info["transit_details"] = "Hop on an iconic red double-decker bus or take the Tube."
        network_info["fare_tip"] = "Contactless card / Oyster (£1.75 Hopper fare allows unlimited bus transfers in 1h)."
        est_transit_mins = max(10, min(26, round(straight_km * 2.2 + 6)))

    # 8. PARIS
    elif "paris" in c_lower:
        network_info["currency"] = "EUR"
        network_info["transit_mode"] = "Paris Métro & RATP Bus"
        network_info["transit_line"] = "Métro (Lines 1-14) / RATP Bus Network"
        network_info["bus_routes"] = "RATP Bus 24, 69, 72, 87 (along the Seine & major sights)"
        network_info["transit_details"] = "Take direct Métro or scenic RATP bus along the Seine."
        network_info["fare_tip"] = "Navigo Easy card or contactless (€2.15 per Ticket t+)."
        est_transit_mins = max(8, min(24, round(straight_km * 2.2 + 5)))

    # 9. BARCELONA
    elif "barcelona" in c_lower:
        network_info["currency"] = "EUR"
        network_info["transit_mode"] = "TMB Metro & Bus Network"
        network_info["transit_line"] = "TMB Metro (L1-L5) & Orthogonal Bus Network"
        network_info["bus_routes"] = "TMB Bus lines (D20, H12, V15, V17)"
        network_info["transit_details"] = "Take TMB Metro or high-frequency orthogonal bus (D, H, V routes)."
        network_info["fare_tip"] = "T-casual card or contactless (€2.55 single or €12.15 for 10-trip T-casual)."
        est_transit_mins = max(8, min(22, round(straight_km * 2.2 + 5)))

    network_info["transit_minutes"] = est_transit_mins
    return network_info


def calculate_transit_from_stay(
    stay: Optional[Any],
    venue_lat: Optional[float],
    venue_lon: Optional[float],
    city_name: str = "",
    venue_title: str = "",
    venue_address: str = "",
    venue_neighborhood: str = ""
) -> Dict[str, Any]:
    """
    Calculate accurate distance (km & miles), walking times, bus/transit routes,
    and direct directions URLs relative to the specific hotel active on that date.
    """
    city_label = city_name.strip() if city_name else ""
    text_haystack = f"{venue_title} {venue_address} {venue_neighborhood} {city_label}"
    directions_urls = _build_directions_urls(
        stay=stay,
        venue_lat=venue_lat,
        venue_lon=venue_lon,
        city_name=city_label,
        venue_title=venue_title,
        venue_address=venue_address
    )

    # Missing coordinates or stay
    if not stay or stay.lat is None or stay.lon is None or venue_lat is None or venue_lon is None or venue_lat == 0.0 or venue_lon == 0.0:
        stay_name = stay.name if stay else (city_label or "Hotel")
        net = _resolve_transit_network(city_label, text_haystack, 2.0, stay_name)
        return {
            "stay_name": stay_name,
            "stay_address": stay.address if stay else "",
            "miles": None,
            "km": None,
            "walk_time": "Location pending",
            "walk_minutes": None,
            "walk_label": "Directions available",
            "is_walkable": True,
            "transit_mode": net["transit_mode"],
            "transit_line": net["transit_line"],
            "bus_routes": net["bus_routes"],
            "transit_time": f"~{net['transit_minutes']} mins",
            "transit_minutes": net["transit_minutes"],
            "transit_details": net["transit_details"],
            "fare_tip": net["fare_tip"],
            "best_mode": f"🚌 {net['transit_line']} (~{net['transit_minutes']} mins)",
            "summary": f"Check live transit and walking directions from {stay_name}.",
            "rideshare_estimate": f"Uber/Taxi: ~{max(4, net['transit_minutes'] - 4)} mins",
            "transit_url": directions_urls["transit_url"],
            "walking_url": directions_urls["walking_url"],
            "driving_url": directions_urls["driving_url"],
            "is_cross_city": False
        }

    straight_km = haversine_km(stay.lat, stay.lon, venue_lat, venue_lon)
    stay_name = stay.name or "Hotel"

    # Detect cross-city or invalid distance (> 75 km / ~46 mi)
    if straight_km > 75.0:
        inter_miles = round(straight_km * 0.621371, 0)
        return {
            "stay_name": stay_name,
            "stay_address": stay.address,
            "miles": inter_miles,
            "km": round(straight_km, 0),
            "walk_time": "Inter-city (Train/Bus)",
            "walk_minutes": None,
            "walk_label": "Inter-city travel",
            "is_walkable": False,
            "transit_mode": "Inter-city Rail / Express Bus",
            "transit_line": f"Regional Train / Express Bus ({city_label})",
            "bus_routes": "Inter-city coach (FlixBus, Rede Expressos, Greyhound) or Regional Rail",
            "transit_time": "Check departure times",
            "transit_minutes": round(straight_km * 0.8),
            "transit_details": f"Destination is {int(inter_miles)} miles from {stay_name}. Inter-city train or express coach recommended.",
            "fare_tip": "Book inter-city rail or bus tickets in advance for best fares.",
            "best_mode": f"🚆 Regional Rail / Inter-city Coach ({int(inter_miles)} mi)",
            "summary": f"Inter-city trip ({int(inter_miles)} mi) from {stay_name}. Board regional train or coach.",
            "rideshare_estimate": "Inter-city transit recommended",
            "transit_url": directions_urls["transit_url"],
            "walking_url": directions_urls["walking_url"],
            "driving_url": directions_urls["driving_url"],
            "is_cross_city": True
        }

    # Realistic urban pedestrian walking factor (streets are ~1.20x straight line)
    walking_km = straight_km * 1.20
    miles = round(walking_km * 0.621371, 1)
    if miles < 0.1 and straight_km < 0.12:
        miles = 0.1
    km_rounded = round(walking_km, 1)

    # Pedestrian walking speed: 4.8 km/h = 12.5 mins/km = ~20.1 mins/mile
    walk_mins = max(1, round(walking_km * 12.5))

    if walk_mins <= 3:
        walk_time_str = "2-3 min walk"
        walk_label = "Steps away"
        is_walkable = True
    elif walk_mins <= 15:
        walk_time_str = f"{walk_mins} min walk"
        walk_label = "Quick walk"
        is_walkable = True
    elif walk_mins <= 25:
        walk_time_str = f"{walk_mins} min walk"
        walk_label = "Scenic walk"
        is_walkable = True
    elif walk_mins <= 40:
        walk_time_str = f"{walk_mins} min walk"
        walk_label = "Moderate walk"
        is_walkable = True
    else:
        hours = walk_mins // 60
        rem_mins = walk_mins % 60
        walk_time_str = f"{hours}h {rem_mins}m walk" if hours > 0 else f"{walk_mins} mins"
        walk_label = "Long walk • Transit advised"
        is_walkable = False

    # Resolve comprehensive transit information
    net = _resolve_transit_network(city_label, text_haystack, straight_km, stay_name)
    transit_mins = net["transit_minutes"]
    transit_time_str = f"{transit_mins} mins"

    # Rideshare estimate
    ride_mins = max(4, min(30, round(straight_km * 1.5 + 3)))
    if net["currency"] == "USD":
        low_cost = max(8, round(straight_km * 2.0 + 5))
        high_cost = max(11, round(straight_km * 2.6 + 9))
        rideshare_str = f"Uber/Lyft: ~{ride_mins} mins (${low_cost}-{high_cost})"
    elif net["currency"] == "GBP":
        low_cost = max(7, round(straight_km * 1.8 + 5))
        high_cost = max(10, round(straight_km * 2.4 + 8))
        rideshare_str = f"Uber/Taxi: ~{ride_mins} mins (£{low_cost}-{high_cost})"
    elif net["currency"] == "ISK":
        low_cost = max(1800, round(straight_km * 450 + 1200))
        high_cost = max(2400, round(straight_km * 550 + 1600))
        rideshare_str = f"Taxi: ~{ride_mins} mins ({low_cost}-{high_cost} ISK)"
    else:
        low_cost = max(5, round(straight_km * 1.4 + 4))
        high_cost = max(8, round(straight_km * 2.0 + 7))
        rideshare_str = f"Uber/Bolt: ~{ride_mins} mins (€{low_cost}-{high_cost})"

    # Mode hierarchy based on distance
    if walk_mins <= 12:
        best_mode = f"🚶 Direct Walk ({walk_mins} mins)"
        summary = f"Steps away from {stay_name} ({walk_time_str} • {miles} mi). Public transit ({net['transit_line']}) also available."
    elif walk_mins <= 25:
        best_mode = f"🚶 Scenic Walk ({walk_mins} mins) or 🚌 {net['transit_mode']} ({transit_mins} mins)"
        summary = f"Pleasant {walk_mins} min walk ({miles} mi) from {stay_name}, or take {net['transit_line']} (~{transit_mins} mins)."
    else:
        # Distance > 1.2-1.5 miles: Public transit is the primary recommended mode!
        best_mode = f"🚌 {net['transit_line']} ({transit_mins} mins)"
        summary = f"Take {net['transit_line']} from near {stay_name} (~{transit_mins} mins • {miles} mi). Walking takes {walk_time_str}."

    return {
        "stay_name": stay_name,
        "stay_address": stay.address,
        "stay_lat": stay.lat,
        "stay_lon": stay.lon,
        "venue_lat": venue_lat,
        "venue_lon": venue_lon,
        "miles": miles,
        "km": km_rounded,
        "walk_time": walk_time_str,
        "walk_minutes": walk_mins,
        "walk_label": walk_label,
        "is_walkable": is_walkable,
        "transit_mode": net["transit_mode"],
        "transit_line": net["transit_line"],
        "bus_routes": net["bus_routes"],
        "transit_time": transit_time_str,
        "transit_minutes": transit_mins,
        "transit_details": net["transit_details"],
        "fare_tip": net["fare_tip"],
        "best_mode": best_mode,
        "summary": summary,
        "rideshare_estimate": rideshare_str,
        "transit_url": directions_urls["transit_url"],
        "walking_url": directions_urls["walking_url"],
        "driving_url": directions_urls["driving_url"],
        "is_cross_city": False
    }

