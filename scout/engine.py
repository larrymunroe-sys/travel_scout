"""Scout Engine for Multi-City Collaborative Travel Platform."""
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from database.models import User, Trip, TripCollaborator, CitySegment, StayLocation, ItineraryItem
from scout.config import CITY_PRESETS
from scout.preseeded_data import PRESEEDED_ITEMS
from scout.web_search import live_city_search
from scout.transit import resolve_stay_for_date, calculate_transit_from_stay

class ScoutEngine:
    def __init__(self):
        pass

    def seed_initial_data_if_empty(self, db: Session):
        """Seed default demo trip and users if the database is newly initialized."""
        import os
        from database.connection import BASE_DIR
        sentinel_file = BASE_DIR / ".demo_seeded"
        if sentinel_file.exists():
            return

        if os.environ.get("DISABLE_DEMO_SEED", "false").lower() in ("true", "1", "yes"):
            try:
                sentinel_file.touch()
            except Exception:
                pass
            return

        if db.query(User).count() > 0:
            try:
                sentinel_file.touch()
            except Exception:
                pass
            return

        # 1. Create Default Users (Owner & Collaborator)
        user_larry = User(
            email="larrymunroe@gmail.com",
            name="Larry Munroe",
            avatar_color="#38bdf8"
        )
        user_sarah = User(
            email="sarah.chen@gmail.com",
            name="Sarah Chen",
            avatar_color="#e879f9"
        )
        db.add_all([user_larry, user_sarah])
        db.commit()
        db.refresh(user_larry)
        db.refresh(user_sarah)

        # 2. Create Default Multi-City Trip
        trip = Trip(
            title="Portugal Grand Cultural Expedition",
            description="Cultural journey through Lisbon, Porto, and historic Bragança. Curated fado, port wine lodges, medieval citadels, and culinary gems.",
            owner_id=user_larry.id
        )
        db.add(trip)
        db.commit()
        db.refresh(trip)

        # 3. Add Collaborators
        collab_larry = TripCollaborator(trip_id=trip.id, user_id=user_larry.id, role="owner")
        collab_sarah = TripCollaborator(trip_id=trip.id, user_id=user_sarah.id, role="editor")
        db.add_all([collab_larry, collab_sarah])

        # 4. Seed City Segments with Multiple Stays by Date
        cities_setup = [
            {
                "name": "Lisbon",
                "country": "Portugal",
                "start": "2027-05-10",
                "end": "2027-05-14",
                "order": 1,
                "lat": 38.7223,
                "lon": -9.1393,
                "stays": [
                    {
                        "name": "Heritage Avenida Liberdade Hotel",
                        "address": "Av. da Liberdade 28, 1250-145 Lisboa",
                        "start": "2027-05-10",
                        "end": "2027-05-12",
                        "lat": 38.7188,
                        "lon": -9.1438,
                        "notes": "First Stay: Central tree-lined avenue near Rossio and Baixa."
                    },
                    {
                        "name": "Bairro Alto Hotel (Chiado)",
                        "address": "Praça Luís de Camões 2, 1200-243 Lisboa",
                        "start": "2027-05-12",
                        "end": "2027-05-14",
                        "lat": 38.7107,
                        "lon": -9.1436,
                        "notes": "Second Stay: Moved to historic hilltop square for nightlife & Fado."
                    }
                ]
            },
            {
                "name": "Porto",
                "country": "Portugal",
                "start": "2027-05-14",
                "end": "2027-05-17",
                "order": 2,
                "lat": 41.1579,
                "lon": -8.6291,
                "stays": [
                    {
                        "name": "The Yeatman Hotel (Gaia)",
                        "address": "Rua do Choupelo, 4400-088 Vila Nova de Gaia",
                        "start": "2027-05-14",
                        "end": "2027-05-17",
                        "lat": 41.1340,
                        "lon": -8.6148,
                        "notes": "Panoramic views of Porto across the Douro, steps from Port lodges."
                    }
                ]
            },
            {
                "name": "Bragança",
                "country": "Portugal",
                "start": "2027-05-17",
                "end": "2027-05-20",
                "order": 3,
                "lat": 41.8061,
                "lon": -6.7567,
                "stays": [
                    {
                        "name": "Pousada de Bragança (São Bartolomeu)",
                        "address": "Rua Estrada do Turismo, 5300-271 Bragança",
                        "start": "2027-05-17",
                        "end": "2027-05-20",
                        "lat": 41.8020,
                        "lon": -6.7620,
                        "notes": "Historic pousada overlooking the medieval citadel fortress."
                    }
                ]
            }
        ]

        created_cities = {}
        for c_data in cities_setup:
            seg = CitySegment(
                trip_id=trip.id,
                city_name=c_data["name"],
                country=c_data["country"],
                start_date=c_data["start"],
                end_date=c_data["end"],
                order_index=c_data["order"],
                lat=c_data["lat"],
                lon=c_data["lon"]
            )
            db.add(seg)
            db.commit()
            db.refresh(seg)
            created_cities[c_data["name"]] = seg

            for s_data in c_data["stays"]:
                stay = StayLocation(
                    city_segment_id=seg.id,
                    name=s_data["name"],
                    address=s_data["address"],
                    start_date=s_data["start"],
                    end_date=s_data["end"],
                    lat=s_data["lat"],
                    lon=s_data["lon"],
                    notes=s_data["notes"]
                )
                db.add(stay)
            db.commit()

        # 5. Seed Pre-Curated Items with Collaborative Attribution
        users = [user_larry, user_sarah]
        u_idx = 0

        # Lisbon items
        lisbon_seg = created_cities["Lisbon"]
        for idx, item_data in enumerate(PRESEEDED_ITEMS.get("Lisbon", [])):
            assigned_date = f"2027-05-{10 + (idx % 4):02d}" if idx < 4 else "todo"
            item = ItineraryItem(
                trip_id=trip.id,
                city_segment_id=lisbon_seg.id,
                title=item_data["title"],
                category=item_data["category"],
                neighborhood=item_data.get("neighborhood"),
                address=item_data.get("address"),
                lat=item_data.get("lat"),
                lon=item_data.get("lon"),
                cost=item_data.get("cost", "Free"),
                is_free=item_data.get("is_free", False),
                time_info=item_data.get("time_info", "Flexible"),
                highlight=item_data.get("highlight"),
                description=item_data.get("description"),
                url=item_data.get("url"),
                source_platform=item_data.get("source_platform", "Curated"),
                assigned_date=assigned_date,
                added_by_user_id=users[u_idx % 2].id
            )
            db.add(item)
            u_idx += 1

        # Porto items
        porto_seg = created_cities["Porto"]
        for idx, item_data in enumerate(PRESEEDED_ITEMS.get("Porto", [])):
            assigned_date = f"2027-05-{14 + (idx % 3):02d}" if idx < 3 else "todo"
            item = ItineraryItem(
                trip_id=trip.id,
                city_segment_id=porto_seg.id,
                title=item_data["title"],
                category=item_data["category"],
                neighborhood=item_data.get("neighborhood"),
                address=item_data.get("address"),
                lat=item_data.get("lat"),
                lon=item_data.get("lon"),
                cost=item_data.get("cost", "Free"),
                is_free=item_data.get("is_free", False),
                time_info=item_data.get("time_info", "Flexible"),
                highlight=item_data.get("highlight"),
                description=item_data.get("description"),
                url=item_data.get("url"),
                source_platform=item_data.get("source_platform", "Curated"),
                assigned_date=assigned_date,
                added_by_user_id=users[u_idx % 2].id
            )
            db.add(item)
            u_idx += 1

        # Bragança items
        braganca_seg = created_cities["Bragança"]
        for idx, item_data in enumerate(PRESEEDED_ITEMS.get("Bragança", [])):
            assigned_date = f"2027-05-{17 + (idx % 3):02d}" if idx < 3 else "todo"
            item = ItineraryItem(
                trip_id=trip.id,
                city_segment_id=braganca_seg.id,
                title=item_data["title"],
                category=item_data["category"],
                neighborhood=item_data.get("neighborhood"),
                address=item_data.get("address"),
                lat=item_data.get("lat"),
                lon=item_data.get("lon"),
                cost=item_data.get("cost", "Free"),
                is_free=item_data.get("is_free", False),
                time_info=item_data.get("time_info", "Flexible"),
                highlight=item_data.get("highlight"),
                description=item_data.get("description"),
                url=item_data.get("url"),
                source_platform=item_data.get("source_platform", "Curated"),
                assigned_date=assigned_date,
                added_by_user_id=users[u_idx % 2].id
            )
            db.add(item)
            u_idx += 1

        db.commit()
        try:
            sentinel_file.touch()
        except Exception:
            pass

    def add_city(
        self,
        db: Session,
        trip_id: str,
        city_name: str,
        country: str,
        start_date: str,
        end_date: str,
        hotel_name: str,
        hotel_address: str
    ) -> CitySegment:
        """Add a new destination city with starting accommodation."""
        city_preset = CITY_PRESETS.get(city_name, {})
        city_lat = city_preset.get("lat", 38.7223)
        city_lon = city_preset.get("lon", -9.1393)

        stay_lat = city_preset.get("stay_lat", city_lat)
        stay_lon = city_preset.get("stay_lon", city_lon)

        # Determine next order index
        max_order = db.query(CitySegment).filter(CitySegment.trip_id == trip_id).count()

        segment = CitySegment(
            trip_id=trip_id,
            city_name=city_name,
            country=country,
            start_date=start_date,
            end_date=end_date,
            order_index=max_order + 1,
            lat=city_lat,
            lon=city_lon
        )
        db.add(segment)
        db.commit()
        db.refresh(segment)

        # Add initial hotel/stay
        stay = StayLocation(
            city_segment_id=segment.id,
            name=hotel_name or f"{city_name} Central Hotel",
            address=hotel_address or f"{city_name}, {country}",
            start_date=start_date,
            end_date=end_date,
            lat=stay_lat,
            lon=stay_lon,
            notes=f"Primary accommodation for {city_name}."
        )
        db.add(stay)
        db.commit()

        # Auto-seed curated items for this city preset if available
        preseeded = PRESEEDED_ITEMS.get(city_name, [])
        if preseeded:
            trip = db.query(Trip).filter(Trip.id == trip_id).first()
            owner_id = trip.owner_id if trip else None
            for item_data in preseeded:
                item = ItineraryItem(
                    trip_id=trip_id,
                    city_segment_id=segment.id,
                    title=item_data["title"],
                    category=item_data.get("category", "gems"),
                    neighborhood=item_data.get("neighborhood"),
                    address=item_data.get("address"),
                    lat=item_data.get("lat"),
                    lon=item_data.get("lon"),
                    cost=item_data.get("cost", "Free"),
                    is_free=item_data.get("is_free", False),
                    time_info=item_data.get("time_info", "Flexible"),
                    highlight=item_data.get("highlight"),
                    description=item_data.get("description"),
                    url=item_data.get("url"),
                    source_platform=item_data.get("source_platform", "Curated"),
                    assigned_date="todo",
                    added_by_user_id=owner_id
                )
                db.add(item)
            db.commit()

        return segment

    def delete_city(self, db: Session, trip_id: str, city_id: str) -> bool:
        """Delete a city segment and cascade clean its stays and items."""
        seg = db.query(CitySegment).filter(CitySegment.id == city_id, CitySegment.trip_id == trip_id).first()
        if not seg:
            return False

        db.delete(seg)
        db.commit()

        # Reindex remaining cities
        remaining = db.query(CitySegment).filter(CitySegment.trip_id == trip_id).order_by(CitySegment.start_date).all()
        for idx, c in enumerate(remaining, 1):
            c.order_index = idx
        db.commit()
        return True

    def add_stay(
        self,
        db: Session,
        city_id: str,
        name: str,
        address: str,
        start_date: str,
        end_date: str,
        notes: Optional[str] = None
    ) -> StayLocation:
        """Add an additional stay/hotel by date for moving hotels midway through a city stay."""
        seg = db.query(CitySegment).filter(CitySegment.id == city_id).first()
        city_lat = seg.lat if seg else 38.7223
        city_lon = seg.lon if seg else -9.1393

        stay = StayLocation(
            city_segment_id=city_id,
            name=name,
            address=address,
            start_date=start_date,
            end_date=end_date,
            lat=city_lat + 0.002,
            lon=city_lon + 0.002,
            notes=notes
        )
        db.add(stay)
        db.commit()
        db.refresh(stay)
        return stay

    def delete_stay(self, db: Session, stay_id: str) -> bool:
        stay = db.query(StayLocation).filter(StayLocation.id == stay_id).first()
        if not stay:
            return False
        db.delete(stay)
        db.commit()
        return True

    def run_multi_city_daily_scan(self, db: Session, trip_id: str, user_id: str) -> Dict[str, Any]:
        """Perform autonomous multi-channel scan across all cities in the trip."""
        cities = db.query(CitySegment).filter(CitySegment.trip_id == trip_id).all()
        all_new_items = []

        scan_templates = [
            ("live music concerts gig guide tickets and venues", "music", "music"),
            ("top wine tastings and cellars", "wine", "guides"),
            ("hidden gems and secret viewpoints Reddit", "gems", "reddit"),
            ("new restaurant openings and food finds", "dining", "blogs"),
            ("viral food and must visit spots", "dining", "tiktok"),
        ]

        for city in cities:
            for query, cat, channel in scan_templates:
                try:
                    found = live_city_search(city.city_name, query, channel=channel, category_hint=cat, max_results=2)
                    for f in found:
                        # Check if already in DB
                        exists = db.query(ItineraryItem).filter(
                            ItineraryItem.trip_id == trip_id,
                            ItineraryItem.title == f["title"]
                        ).first()
                        if not exists:
                            item = ItineraryItem(
                                trip_id=trip_id,
                                city_segment_id=city.id,
                                title=f["title"],
                                category=f["category"],
                                neighborhood=f["neighborhood"],
                                address=f["address"],
                                lat=f["lat"],
                                lon=f["lon"],
                                cost=f["cost"],
                                is_free=f["is_free"],
                                time_info=f["time_info"],
                                highlight=f["highlight"],
                                description=f["description"],
                                url=f["url"],
                                source_platform=f["source_platform"],
                                assigned_date="todo",
                                added_by_user_id=user_id
                            )
                            db.add(item)
                            all_new_items.append(f)
                except Exception as e:
                    print(f"Error scanning {city.city_name} for '{query}': {e}")

        db.commit()
        return {
            "cities_scanned": len(cities),
            "newly_discovered": len(all_new_items),
            "items": all_new_items
        }
