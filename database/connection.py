"""Database engine, session management, and base declarative class."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "travel_scout.db"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{DB_PATH}"
elif DATABASE_URL.startswith("postgres://"):
    # Fix Render's legacy postgres:// scheme for SQLAlchemy 2.0
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """FastAPI dependency yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables defined on Base and perform safe column migrations."""
    from database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Lightweight SQLite column migrations (only applicable for SQLite)
    if DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                cursor = conn.connection.cursor()
                cursor.execute("PRAGMA table_info(itinerary_items)")
                cols = {row[1] for row in cursor.fetchall()}
                if "personal_note" not in cols:
                    cursor.execute("ALTER TABLE itinerary_items ADD COLUMN personal_note TEXT")
                if "note_by_user_id" not in cols:
                    cursor.execute("ALTER TABLE itinerary_items ADD COLUMN note_by_user_id VARCHAR(36)")
                if "note_updated_at" not in cols:
                    cursor.execute("ALTER TABLE itinerary_items ADD COLUMN note_updated_at DATETIME")
                conn.connection.commit()
        except Exception as e:
            print("Schema migration note:", e)
