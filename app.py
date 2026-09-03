"""FastAPI Application for Multi-City Collaborative Travel Scout."""
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, Request, Response, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import init_db, get_db, SessionLocal
from database.models import User, Trip, TripCollaborator, CitySegment, StayLocation, ItineraryItem
from scout.config import BASE_DIR, CITY_PRESETS, CATEGORIES, SEARCH_CHANNELS
from scout.engine import ScoutEngine
from scout.web_search import live_city_search
from scout.transit import resolve_stay_for_date, calculate_transit_from_stay

app = FastAPI(
    title="Multi-City Collaborative Travel Scout",
    description="Plan multi-city journeys with multiple stays per city, dynamic transit, and real-time collaboration.",
    version="1.0.0",
)

scout_engine = ScoutEngine()

# Mount Static & Templates
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
templates_dir = BASE_DIR / "templates"
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Ensure database tables and seeds exist on import
init_db()
with SessionLocal() as _db:
    scout_engine.seed_initial_data_if_empty(_db)

# ==================== AUTHENTICATION HELPER ====================

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Retrieve user from session cookie or fallback to first user."""
    user_id = request.cookies.get("travel_scout_user_id")
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    
    # Default to Larry Munroe if no cookie
    default_user = db.query(User).filter(User.email == "larrymunroe@gmail.com").first()
    if default_user:
        return default_user
    
    first = db.query(User).first()
    if first:
        return first
    
    raise HTTPException(status_code=401, detail="No users found. Please log in.")

# ==================== SCHEMAS ====================

class DevLoginPayload(BaseModel):
    email: str
    name: str
    avatar_color: Optional[str] = "#38bdf8"

class AddCityPayload(BaseModel):
    city_name: str
    country: str = "Portugal"
    start_date: str
    end_date: str
    hotel_name: str
    hotel_address: str

class UpdateCityPayload(BaseModel):
    city_name: Optional[str] = None
    country: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    order_index: Optional[int] = None

class AddStayPayload(BaseModel):
    name: str
    address: str
    start_date: str
    end_date: str
    notes: Optional[str] = None

class AddItemPayload(BaseModel):
    city_segment_id: Optional[str] = None
    title: str
    category: str = "gems"
    neighborhood: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    cost: Optional[str] = "Free"
    is_free: Optional[bool] = False
    time_info: Optional[str] = "Flexible"
    highlight: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    source_platform: Optional[str] = "Curated"
    assigned_date: Optional[str] = "todo"

class UpdateItemPayload(BaseModel):
    assigned_date: Optional[str] = None
    city_segment_id: Optional[str] = None
    title: Optional[str] = None

class InviteCollaboratorPayload(BaseModel):
    email: str
    name: Optional[str] = None
    role: str = "editor"

class SearchPayload(BaseModel):
    city_name: str
    query: str
    channel: str = "all"
    category: Optional[str] = None

# ==================== FRONTEND ROOT ====================

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    trip = db.query(Trip).first()
    all_users = db.query(User).all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "current_user": user,
            "trip": trip,
            "all_users": all_users,
            "categories": CATEGORIES,
            "search_channels": SEARCH_CHANNELS,
            "city_presets": CITY_PRESETS,
        }
    )

# ==================== AUTH ROUTES ====================

@app.post("/auth/dev-login")
async def dev_login(payload: DevLoginPayload, response: Response, db: Session = Depends(get_db)):
    """One-click instant login/switching for multi-user collaboration testing."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        user = User(
            email=payload.email,
            name=payload.name,
            avatar_color=payload.avatar_color or "#38bdf8"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    response.set_cookie(key="travel_scout_user_id", value=user.id, max_age=86400 * 30, httponly=False)
    return {
        "status": "success",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "avatar_color": user.avatar_color
        }
    }

@app.get("/auth/me")
async def get_me(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    all_users = db.query(User).all()
    return {
        "current_user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "avatar_color": user.avatar_color
        },
        "available_users": [
            {"id": u.id, "name": u.name, "email": u.email, "avatar_color": u.avatar_color}
            for u in all_users
        ]
    }

@app.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="travel_scout_user_id")
    return {"status": "logged_out"}

# ==================== TRIP & CITY API ROUTES ====================

@app.get("/api/trips")
async def list_trips(db: Session = Depends(get_db)):
    trips = db.query(Trip).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "owner_id": t.owner_id,
            "cities_count": len(t.city_segments),
            "collaborators_count": len(t.collaborators)
        }
        for t in trips
    ]

@app.get("/api/trips/{trip_id}")
async def get_trip_details(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # 1. Format Collaborators
    collabs = []
    for c in trip.collaborators:
        u = c.user
        collabs.append({
            "user_id": u.id,
            "name": u.name,
            "email": u.email,
            "avatar_color": u.avatar_color,
            "role": c.role
        })

    # 2. Format Cities & Stays
    cities = []
    all_dates = set()
    for seg in sorted(trip.city_segments, key=lambda x: x.order_index):
        stays = [
            {
                "id": s.id,
                "name": s.name,
                "address": s.address,
                "start_date": s.start_date,
                "end_date": s.end_date,
                "lat": s.lat,
                "lon": s.lon,
                "notes": s.notes
            }
            for s in seg.stays
        ]
        cities.append({
            "id": seg.id,
            "city_name": seg.city_name,
            "country": seg.country,
            "start_date": seg.start_date,
            "end_date": seg.end_date,
            "order_index": seg.order_index,
            "lat": seg.lat,
            "lon": seg.lon,
            "stays": stays
        })

        # Collect dates
        try:
            curr = datetime.strptime(seg.start_date, "%Y-%m-%d")
            end = datetime.strptime(seg.end_date, "%Y-%m-%d")
            while curr <= end:
                all_dates.add(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
        except Exception:
            pass

    sorted_dates = sorted(list(all_dates))

    # 3. Format Itinerary (Days & To-Do)
    todo_items = []
    days_map = {d: [] for d in sorted_dates}

    for item in trip.items:
        u = item.added_by
        seg = item.city_segment
        author_data = {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "avatar_color": u.avatar_color
        }

        # Resolve active hotel for this item's assigned date
        active_stay = None
        if seg and seg.stays:
            active_stay = resolve_stay_for_date(seg.stays, item.assigned_date)

        transit_info = calculate_transit_from_stay(
            active_stay,
            item.lat,
            item.lon,
            city_name=seg.city_name if seg else "City"
        )

        item_dict = {
            "id": item.id,
            "trip_id": item.trip_id,
            "city_id": seg.id if seg else None,
            "city_name": seg.city_name if seg else "Universal",
            "title": item.title,
            "category": item.category,
            "neighborhood": item.neighborhood,
            "address": item.address,
            "lat": item.lat,
            "lon": item.lon,
            "cost": item.cost,
            "is_free": item.is_free,
            "time_info": item.time_info,
            "highlight": item.highlight,
            "description": item.description,
            "url": item.url,
            "source_platform": item.source_platform,
            "assigned_date": item.assigned_date,
            "added_by": author_data,
            "transit": transit_info
        }

        if not item.assigned_date or item.assigned_date == "todo":
            todo_items.append(item_dict)
        elif item.assigned_date in days_map:
            days_map[item.assigned_date].append(item_dict)
        else:
            # Date outside segments, append anyway
            if item.assigned_date not in days_map:
                days_map[item.assigned_date] = []
            days_map[item.assigned_date].append(item_dict)

    days_list = [
        {"date": d, "items": days_map[d]}
        for d in sorted(days_map.keys())
    ]

    return {
        "trip": {
            "id": trip.id,
            "title": trip.title,
            "description": trip.description,
            "owner_id": trip.owner_id
        },
        "collaborators": collabs,
        "cities": cities,
        "available_dates": sorted_dates,
        "itinerary": {
            "todo": todo_items,
            "days": days_list
        }
    }

# ==================== CITY CRUD ====================

@app.post("/api/trips/{trip_id}/cities")
async def add_city(trip_id: str, payload: AddCityPayload, db: Session = Depends(get_db)):
    """Add a new destination city with starting accommodation."""
    seg = scout_engine.add_city(
        db=db,
        trip_id=trip_id,
        city_name=payload.city_name,
        country=payload.country,
        start_date=payload.start_date,
        end_date=payload.end_date,
        hotel_name=payload.hotel_name,
        hotel_address=payload.hotel_address
    )
    return {"status": "created", "city_id": seg.id, "city_name": seg.city_name}

@app.put("/api/trips/{trip_id}/cities/{city_id}")
async def update_city(trip_id: str, city_id: str, payload: UpdateCityPayload, db: Session = Depends(get_db)):
    seg = db.query(CitySegment).filter(CitySegment.id == city_id, CitySegment.trip_id == trip_id).first()
    if not seg:
        raise HTTPException(status_code=404, detail="City not found")

    if payload.city_name:
        seg.city_name = payload.city_name
    if payload.country:
        seg.country = payload.country
    if payload.start_date:
        seg.start_date = payload.start_date
    if payload.end_date:
        seg.end_date = payload.end_date
    if payload.order_index is not None:
        seg.order_index = payload.order_index

    db.commit()
    return {"status": "updated", "city_id": seg.id}

@app.delete("/api/trips/{trip_id}/cities/{city_id}")
async def delete_city(trip_id: str, city_id: str, db: Session = Depends(get_db)):
    """Delete a destination city and cascade clean its stays and assigned items."""
    success = scout_engine.delete_city(db, trip_id, city_id)
    if not success:
        raise HTTPException(status_code=404, detail="City not found")
    return {"status": "deleted", "city_id": city_id}

# ==================== STAY / HOTEL CRUD ====================

@app.post("/api/trips/{trip_id}/cities/{city_id}/stays")
async def add_stay(trip_id: str, city_id: str, payload: AddStayPayload, db: Session = Depends(get_db)):
    """Add an additional stay/hotel by date for moving accommodations midway."""
    stay = scout_engine.add_stay(
        db=db,
        city_id=city_id,
        name=payload.name,
        address=payload.address,
        start_date=payload.start_date,
        end_date=payload.end_date,
        notes=payload.notes
    )
    return {"status": "created", "stay_id": stay.id, "stay_name": stay.name}

@app.delete("/api/trips/{trip_id}/stays/{stay_id}")
async def delete_stay(trip_id: str, stay_id: str, db: Session = Depends(get_db)):
    success = scout_engine.delete_stay(db, stay_id)
    if not success:
        raise HTTPException(status_code=404, detail="Stay not found")
    return {"status": "deleted", "stay_id": stay_id}

# ==================== ITINERARY ITEM CRUD ====================

@app.post("/api/trips/{trip_id}/items")
async def add_itinerary_item(
    trip_id: str,
    payload: AddItemPayload,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    item = ItineraryItem(
        trip_id=trip_id,
        city_segment_id=payload.city_segment_id,
        title=payload.title,
        category=payload.category,
        neighborhood=payload.neighborhood,
        address=payload.address,
        lat=payload.lat,
        lon=payload.lon,
        cost=payload.cost,
        is_free=payload.is_free,
        time_info=payload.time_info,
        highlight=payload.highlight,
        description=payload.description,
        url=payload.url,
        source_platform=payload.source_platform,
        assigned_date=payload.assigned_date or "todo",
        added_by_user_id=user.id
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"status": "created", "item_id": item.id}

@app.put("/api/trips/{trip_id}/items/{item_id}")
async def update_itinerary_item(
    trip_id: str,
    item_id: str,
    payload: UpdateItemPayload,
    db: Session = Depends(get_db)
):
    item = db.query(ItineraryItem).filter(ItineraryItem.id == item_id, ItineraryItem.trip_id == trip_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if payload.assigned_date is not None:
        item.assigned_date = payload.assigned_date
    if payload.city_segment_id is not None:
        item.city_segment_id = payload.city_segment_id
    if payload.title is not None:
        item.title = payload.title

    db.commit()
    return {"status": "updated", "item_id": item.id, "assigned_date": item.assigned_date}

@app.delete("/api/trips/{trip_id}/items/{item_id}")
async def delete_itinerary_item(trip_id: str, item_id: str, db: Session = Depends(get_db)):
    item = db.query(ItineraryItem).filter(ItineraryItem.id == item_id, ItineraryItem.trip_id == trip_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return {"status": "deleted", "item_id": item_id}

# ==================== COLLABORATION & SHARING ====================

@app.post("/api/trips/{trip_id}/collaborators")
async def invite_collaborator(
    trip_id: str,
    payload: InviteCollaboratorPayload,
    db: Session = Depends(get_db)
):
    """Invite collaborator by Gmail / email address."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        colors = ["#38bdf8", "#e879f9", "#fbbf24", "#34d399", "#f43f5e", "#c084fc"]
        import random
        user = User(
            email=payload.email,
            name=payload.name or payload.email.split("@")[0].capitalize(),
            avatar_color=random.choice(colors)
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    existing = db.query(TripCollaborator).filter(
        TripCollaborator.trip_id == trip_id,
        TripCollaborator.user_id == user.id
    ).first()

    if not existing:
        collab = TripCollaborator(
            trip_id=trip_id,
            user_id=user.id,
            role=payload.role
        )
        db.add(collab)
        db.commit()

    return {
        "status": "collaborator_added",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "avatar_color": user.avatar_color,
            "role": payload.role
        }
    }

# ==================== CITY-SCOPED LIVE SEARCH & DAILY SCAN ====================

@app.post("/api/search")
async def search_city(payload: SearchPayload):
    """Run live web scout scoped to the target city."""
    results = live_city_search(
        city_name=payload.city_name,
        query=payload.query,
        channel=payload.channel,
        category_hint=payload.category,
        max_results=8
    )
    return {
        "city_name": payload.city_name,
        "query": payload.query,
        "channel": payload.channel,
        "count": len(results),
        "results": results
    }

@app.post("/api/trips/{trip_id}/scan/daily")
async def trigger_daily_scan(
    trip_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    scan_result = scout_engine.run_multi_city_daily_scan(db, trip_id, user.id)
    return scan_result

# ==================== MAP COORDINATES ENDPOINT ====================

@app.get("/api/trips/{trip_id}/map")
async def get_map_data(trip_id: str, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    city_points = []
    stay_points = []
    for city in trip.city_segments:
        city_points.append({
            "id": city.id,
            "city_name": city.city_name,
            "country": city.country,
            "lat": city.lat,
            "lon": city.lon,
            "start_date": city.start_date,
            "end_date": city.end_date
        })
        for s in city.stays:
            stay_points.append({
                "id": s.id,
                "city_id": city.id,
                "city_name": city.city_name,
                "name": s.name,
                "address": s.address,
                "lat": s.lat,
                "lon": s.lon,
                "start_date": s.start_date,
                "end_date": s.end_date,
                "notes": s.notes
            })

    item_points = []
    for it in trip.items:
        if it.lat and it.lon:
            u = it.added_by
            item_points.append({
                "id": it.id,
                "title": it.title,
                "category": it.category,
                "city_id": it.city_segment_id,
                "city_name": it.city_segment.city_name if it.city_segment else "Trip",
                "lat": it.lat,
                "lon": it.lon,
                "cost": it.cost,
                "assigned_date": it.assigned_date,
                "highlight": it.highlight,
                "added_by": {
                    "name": u.name,
                    "avatar_color": u.avatar_color
                }
            })

    return {
        "cities": city_points,
        "stays": stay_points,
        "items": item_points
    }
