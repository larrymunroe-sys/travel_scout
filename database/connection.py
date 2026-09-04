"""Database engine, session management, and base declarative class."""
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "travel_scout.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
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

    # Lightweight SQLite column migrations
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
