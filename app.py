"""FastAPI Application for Multi-City Collaborative Travel Scout."""
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, Request, Response, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import or_
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

def get_optional_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Retrieve user from session cookie or header. Returns None if explicitly logged out or no valid user found."""
    user_id = request.cookies.get("travel_scout_user_id")
    if not user_id:
        user_id = request.headers.get("x-travel-scout-user-id")

    if user_id == "logged_out":
        return None

    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user

    # Default to Larry Munroe if no cookie on first visit
    default_user = db.query(User).filter(User.email == "larrymunroe@gmail.com").first()
    if default_user:
        return default_user

    return db.query(User).first()

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Retrieve user from session cookie or raise 401 if logged out."""
    user = get_optional_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not logged in. Please sign in with your Gmail account."
        )
    return user

def get_user_accessible_trips(user: User, db: Session) -> List[Trip]:
    """Retrieve only trips owned by or explicitly shared with the current user."""
    collab_trip_ids = [
        c.trip_id for c in db.query(TripCollaborator.trip_id).filter(TripCollaborator.user_id == user.id).all()
    ]
    trips = db.query(Trip).filter(
        or_(
            Trip.owner_id == user.id,
            Trip.id.in_(collab_trip_ids)
        )
    ).all()
    return trips

def check_trip_access(trip_id: str, user: User, db: Session, require_edit: bool = False) -> Trip:
    """Verify that the user is authorized to view or edit this private itinerary."""
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.owner_id == user.id:
        return trip

    collab = db.query(TripCollaborator).filter(
        TripCollaborator.trip_id == trip.id,
        TripCollaborator.user_id == user.id
    ).first()

    if not collab:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This itinerary is private to its creator and invited collaborators."
        )

    if require_edit and collab.role == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read-only access. You have viewer permissions on this itinerary."
        )

    return trip

# ==================== SCHEMAS ====================

class DevLoginPayload(BaseModel):
    email: str
    name: str
    avatar_color: Optional[str] = "#38bdf8"

class CreateTripPayload(BaseModel):
    title: str
    description: Optional[str] = None
    first_city_name: Optional[str] = None
    country: Optional[str] = "Portugal"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    hotel_name: Optional[str] = None
    hotel_address: Optional[str] = None

class UpdateTripPayload(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

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

class UpdateNotePayload(BaseModel):
    personal_note: str

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
    user = get_optional_current_user(request, db)
    accessible_trips = get_user_accessible_trips(user, db) if user else []
    trip = accessible_trips[0] if accessible_trips else None
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
async def dev_login(payload: DevLoginPayload, request: Request, response: Response, db: Session = Depends(get_db)):
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

    is_https = request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https"
    response.set_cookie(
        key="travel_scout_user_id",
        value=user.id,
        max_age=86400 * 30,
        httponly=False,
        path="/",
        samesite="lax",
        secure=is_https
    )
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
    user = get_optional_current_user(request, db)
    all_users = db.query(User).all()
    return {
        "current_user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "avatar_color": user.avatar_color
        } if user else None,
        "available_users": [
            {"id": u.id, "name": u.name, "email": u.email, "avatar_color": u.avatar_color}
            for u in all_users
        ]
    }

@app.post("/auth/logout")
async def logout(request: Request, response: Response):
    is_https = request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https"
    response.set_cookie(
        key="travel_scout_user_id",
        value="logged_out",
        max_age=86400 * 30,
        httponly=False,
        path="/",
        samesite="lax",
        secure=is_https
    )
    return {"status": "logged_out"}

# ==================== TRIP & CITY API ROUTES ====================

@app.get("/api/trips")
async def list_trips(request: Request, db: Session = Depends(get_db)):
    """List only itineraries owned by or shared with the logged-in user."""
    user = get_optional_current_user(request, db)
    if not user:
        return []
    trips = get_user_accessible_trips(user, db)
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "owner_id": t.owner_id,
            "is_owner": (t.owner_id == user.id),
            "cities_count": len(t.city_segments),
            "collaborators_count": len(t.collaborators)
        }
        for t in trips
    ]

@app.post("/api/trips")
async def create_trip(payload: CreateTripPayload, request: Request, db: Session = Depends(get_db)):
    """Create a new custom journey with editable title, description, and first city."""
    user = get_current_user(request, db)
    trip = Trip(
        title=payload.title,
        description=payload.description or f"Custom itinerary designed by {user.name}",
        owner_id=user.id
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)

    collab = TripCollaborator(trip_id=trip.id, user_id=user.id, role="owner")
    db.add(collab)
    db.commit()

    if payload.first_city_name and payload.start_date and payload.end_date:
        scout_engine.add_city(
            db=db,
            trip_id=trip.id,
            city_name=payload.first_city_name,
            country=payload.country or "Country",
            start_date=payload.start_date,
            end_date=payload.end_date,
            hotel_name=payload.hotel_name or f"{payload.first_city_name} Hotel",
            hotel_address=payload.hotel_address or f"{payload.first_city_name}"
        )

    return {"status": "created", "trip_id": trip.id, "title": trip.title}

@app.put("/api/trips/{trip_id}")
async def update_trip(trip_id: str, payload: UpdateTripPayload, request: Request, db: Session = Depends(get_db)):
    """Update trip title and description (requires owner or editor permissions)."""
    user = get_current_user(request, db)
    trip = check_trip_access(trip_id, user, db, require_edit=True)

    if payload.title:
        trip.title = payload.title
    if payload.description is not None:
        trip.description = payload.description

    db.commit()
    return {"status": "updated", "trip_id": trip.id, "title": trip.title}

@app.get("/api/trips/{trip_id}")
async def get_trip_details(trip_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    trip = check_trip_access(trip_id, user, db, require_edit=False)

    # 1. Format Collaborators
    collabs = []
    for c in trip.collaborators:
        u = c.user
        collabs.append({
            "id": u.id,
            "user_id": u.id,
            "name": u.name,
            "email": u.email,
            "avatar_color": u.avatar_color,
            "role": c.role,
            "is_owner": (u.id == trip.owner_id)
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

        note_author = None
        if item.note_by:
            note_author = {
                "id": item.note_by.id,
                "name": item.note_by.name,
                "email": item.note_by.email,
                "avatar_color": item.note_by.avatar_color
            }

        note_date_str = item.note_updated_at.strftime("%b %d, %Y, %I:%M %p") if item.note_updated_at else None

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
            "transit": transit_info,
            "personal_note": item.personal_note,
            "note_author": note_author,
            "note_date": note_date_str
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

# ==================== PRINT & EXPORT VIEW ====================

@app.get("/api/trips/{trip_id}/print", response_class=HTMLResponse)
async def print_itinerary_view(
    trip_id: str,
    request: Request,
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_todo: bool = True,
    autoprint: bool = False,
    db: Session = Depends(get_db)
):
    """Render a dedicated, high-contrast, printer-friendly view formatted for Letter/A4 printing and PDF saving."""
    user = get_current_user(request, db)
    trip = check_trip_access(trip_id, user, db, require_edit=False)

    collabs = [c.user for c in trip.collaborators]

    # Stays and Cities
    all_stays = []
    for seg in sorted(trip.city_segments, key=lambda x: x.order_index):
        for s in seg.stays:
            all_stays.append(s)

    # Format dates
    all_dates = set()
    for seg in trip.city_segments:
        try:
            curr = datetime.strptime(seg.start_date, "%Y-%m-%d")
            end = datetime.strptime(seg.end_date, "%Y-%m-%d")
            while curr <= end:
                all_dates.add(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
        except Exception:
            pass
    sorted_dates = sorted(list(all_dates))

    # Apply date filter
    filter_label = "All Dates (Full Itinerary)"
    target_dates = sorted_dates
    if date and date != "all":
        target_dates = [d for d in sorted_dates if d == date]
        filter_label = f"Single Date: {date}"
    elif start_date and end_date:
        target_dates = [d for d in sorted_dates if start_date <= d <= end_date]
        filter_label = f"Date Range: {start_date} to {end_date}"

    # Build items and transit
    days_map = {d: [] for d in target_dates}
    todo_items = []

    for item in trip.items:
        u = item.added_by
        seg = item.city_segment
        author_data = {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "avatar_color": u.avatar_color
        }

        active_stay = None
        if seg and seg.stays:
            active_stay = resolve_stay_for_date(seg.stays, item.assigned_date)

        transit_info = calculate_transit_from_stay(
            active_stay,
            item.lat,
            item.lon,
            city_name=seg.city_name if seg else "City"
        )

        note_author = None
        if item.note_by:
            note_author = {
                "id": item.note_by.id,
                "name": item.note_by.name,
                "email": item.note_by.email,
                "avatar_color": item.note_by.avatar_color
            }

        note_date_str = item.note_updated_at.strftime("%b %d, %Y, %I:%M %p") if item.note_updated_at else None

        item_dict = {
            "id": item.id,
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
            "transit": transit_info,
            "personal_note": item.personal_note,
            "note_author": note_author,
            "note_date": note_date_str
        }

        if item.assigned_date in days_map:
            days_map[item.assigned_date].append(item_dict)
        elif not item.assigned_date or item.assigned_date == "todo":
            todo_items.append(item_dict)

    # Attach active stays to days
    days_list = []
    for d in target_dates:
        day_stay = None
        for seg in trip.city_segments:
            s = resolve_stay_for_date(seg.stays, d)
            if s:
                day_stay = s
                break
        days_list.append({
            "date": d,
            "active_stay": day_stay,
            "stops": days_map.get(d, []),
            "items": days_map.get(d, [])
        })

    date_range_str = f"{sorted_dates[0]} to {sorted_dates[-1]}" if sorted_dates else "Flexible"

    return templates.TemplateResponse(
        request=request,
        name="print.html",
        context={
            "trip": trip,
            "collaborators": collabs,
            "cities": trip.city_segments,
            "stays": all_stays,
            "days": days_list,
            "todo_items": todo_items if include_todo else [],
            "include_todo": include_todo,
            "filter_label": filter_label,
            "date_range_str": date_range_str,
            "now_str": datetime.now().strftime("%B %d, %Y"),
            "current_user": user,
            "autoprint": autoprint
        }
    )

# ==================== CITY CRUD ====================

@app.post("/api/trips/{trip_id}/cities")
async def add_city(trip_id: str, payload: AddCityPayload, request: Request, db: Session = Depends(get_db)):
    """Add a new destination city with starting accommodation."""
    user = get_current_user(request, db)
    check_trip_access(trip_id, user, db, require_edit=True)
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
async def update_city(trip_id: str, city_id: str, payload: UpdateCityPayload, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    check_trip_access(trip_id, user, db, require_edit=True)
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
async def delete_city(trip_id: str, city_id: str, request: Request, db: Session = Depends(get_db)):
    """Delete a destination city and cascade clean its stays and assigned items."""
    user = get_current_user(request, db)
    check_trip_access(trip_id, user, db, require_edit=True)
    success = scout_engine.delete_city(db, trip_id, city_id)
    if not success:
        raise HTTPException(status_code=404, detail="City not found")
    return {"status": "deleted", "city_id": city_id}

# ==================== STAY / HOTEL CRUD ====================

@app.post("/api/trips/{trip_id}/cities/{city_id}/stays")
async def add_stay(trip_id: str, city_id: str, payload: AddStayPayload, request: Request, db: Session = Depends(get_db)):
    """Add an additional stay/hotel by date for moving accommodations midway."""
    user = get_current_user(request, db)
    check_trip_access(trip_id, user, db, require_edit=True)
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
async def delete_stay(trip_id: str, stay_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    check_trip_access(trip_id, user, db, require_edit=True)
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
    check_trip_access(trip_id, user, db, require_edit=True)
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
    request: Request,
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    check_trip_access(trip_id, user, db, require_edit=True)
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

@app.put("/api/trips/{trip_id}/items/{item_id}/note")
async def update_item_note(
    trip_id: str,
    item_id: str,
    payload: UpdateNotePayload,
    request: Request,
    db: Session = Depends(get_db)
):
    """Update or remove a personal note on an item, recording author attribution and timestamp."""
    user = get_current_user(request, db)
    check_trip_access(trip_id, user, db, require_edit=True)
    item = db.query(ItineraryItem).filter(ItineraryItem.id == item_id, ItineraryItem.trip_id == trip_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    note_txt = (payload.personal_note or "").strip()
    if note_txt:
        item.personal_note = note_txt
        item.note_by_user_id = user.id
        item.note_updated_at = datetime.utcnow()
    else:
        item.personal_note = None
        item.note_by_user_id = None
        item.note_updated_at = None

    db.commit()
    db.refresh(item)

    note_author = None
    if item.note_by:
        note_author = {
            "id": item.note_by.id,
            "name": item.note_by.name,
            "email": item.note_by.email,
            "avatar_color": item.note_by.avatar_color
        }

    return {
        "status": "updated",
        "item_id": item.id,
        "personal_note": item.personal_note,
        "note_author": note_author,
        "note_date": item.note_updated_at.strftime("%b %d, %Y, %I:%M %p") if item.note_updated_at else None
    }

@app.delete("/api/trips/{trip_id}/items/{item_id}")
async def delete_itinerary_item(trip_id: str, item_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    check_trip_access(trip_id, user, db, require_edit=True)
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
    request: Request,
    db: Session = Depends(get_db)
):
    """Invite collaborator by Gmail / email address."""
    current_user = get_current_user(request, db)
    check_trip_access(trip_id, current_user, db, require_edit=True)

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

@app.delete("/api/trips/{trip_id}/collaborators/{collaborator_user_id}")
async def remove_collaborator(
    trip_id: str,
    collaborator_user_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Remove an invited contributor from the trip."""
    current_user = get_current_user(request, db)
    trip = check_trip_access(trip_id, current_user, db, require_edit=True)

    if trip.owner_id == collaborator_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the trip creator/owner from the trip."
        )

    collab = db.query(TripCollaborator).filter(
        TripCollaborator.trip_id == trip_id,
        TripCollaborator.user_id == collaborator_user_id
    ).first()

    if not collab:
        raise HTTPException(status_code=404, detail="Collaborator not found on this itinerary.")

    db.delete(collab)
    db.commit()
    return {"status": "collaborator_removed", "user_id": collaborator_user_id}

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
    check_trip_access(trip_id, user, db, require_edit=True)
    scan_result = scout_engine.run_multi_city_daily_scan(db, trip_id, user.id)
    return scan_result

# ==================== MAP COORDINATES ENDPOINT ====================

@app.get("/api/trips/{trip_id}/map")
async def get_map_data(trip_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    trip = check_trip_access(trip_id, user, db, require_edit=False)

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
