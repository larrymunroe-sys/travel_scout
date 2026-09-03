"""SQLAlchemy Database Models for Multi-City Collaborative Travel Scout."""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database.connection import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(512), nullable=True)
    avatar_color = Column(String(32), default="#38bdf8")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    collaborations = relationship("TripCollaborator", back_populates="user", cascade="all, delete-orphan")
    items_added = relationship("ItineraryItem", back_populates="added_by")

class Trip(Base):
    __tablename__ = "trips"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    collaborators = relationship("TripCollaborator", back_populates="trip", cascade="all, delete-orphan")
    city_segments = relationship("CitySegment", back_populates="trip", cascade="all, delete-orphan", order_by="CitySegment.order_index")
    items = relationship("ItineraryItem", back_populates="trip", cascade="all, delete-orphan")

class TripCollaborator(Base):
    __tablename__ = "trip_collaborators"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    trip_id = Column(String(36), ForeignKey("trips.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role = Column(String(32), default="editor")  # "owner", "editor", "viewer"
    created_at = Column(DateTime, default=datetime.utcnow)

    trip = relationship("Trip", back_populates="collaborators")
    user = relationship("User", back_populates="collaborations")

class CitySegment(Base):
    __tablename__ = "city_segments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    trip_id = Column(String(36), ForeignKey("trips.id"), nullable=False)
    city_name = Column(String(128), nullable=False)
    country = Column(String(128), default="Portugal")
    start_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    end_date = Column(String(10), nullable=False)    # YYYY-MM-DD
    order_index = Column(Integer, default=0)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)

    trip = relationship("Trip", back_populates="city_segments")
    stays = relationship("StayLocation", back_populates="city_segment", cascade="all, delete-orphan")
    items = relationship("ItineraryItem", back_populates="city_segment")

class StayLocation(Base):
    """Accommodations / hotels per city, supporting multiple stays by date."""
    __tablename__ = "stay_locations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    city_segment_id = Column(String(36), ForeignKey("city_segments.id"), nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(String(512), nullable=False)
    start_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    end_date = Column(String(10), nullable=False)    # YYYY-MM-DD
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    city_segment = relationship("CitySegment", back_populates="stays")

class ItineraryItem(Base):
    """Itinerary venue, activity, or To-Do item with user attribution."""
    __tablename__ = "itinerary_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    trip_id = Column(String(36), ForeignKey("trips.id"), nullable=False)
    city_segment_id = Column(String(36), ForeignKey("city_segments.id"), nullable=True)
    title = Column(String(255), nullable=False)
    category = Column(String(64), default="gems")
    neighborhood = Column(String(128), nullable=True)
    address = Column(String(512), nullable=True)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    cost = Column(String(64), default="Free")
    is_free = Column(Boolean, default=False)
    time_info = Column(String(128), default="Flexible")
    highlight = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String(512), nullable=True)
    source_platform = Column(String(64), default="Curated")
    assigned_date = Column(String(10), nullable=True)  # "todo" or "YYYY-MM-DD"
    added_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    trip = relationship("Trip", back_populates="items")
    city_segment = relationship("CitySegment", back_populates="items")
    added_by = relationship("User", back_populates="items_added")
