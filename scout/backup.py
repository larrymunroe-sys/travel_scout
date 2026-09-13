"""Automated Itinerary Backup, Restore, and Deletion Memory Engine.

Ensures:
1. Automated backup of all trips, cities, stays, items, personal notes, expenses, and collaborators.
2. Automated restore/sync upon code refresh or server startup.
3. Deletion Memory: If a card was previously deleted, it is NOT reimported unless
   its information (description, time, cost, address, url) has changed!
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

# Ensure project root is in sys.path when executed directly
_ROOT_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from database.connection import BASE_DIR
from database.models import (
    Trip, User, TripCollaborator, CitySegment, StayLocation,
    ItineraryItem, TripExpense, DeletedItem
)

BACKUP_DIR = BASE_DIR / "backups"
HISTORY_DIR = BACKUP_DIR / "history"
LOCAL_BACKUP_DIR = BACKUP_DIR / "local"
DEFAULT_BACKUP_FILE = BACKUP_DIR / "itineraries_backup.json"

def compute_item_hash(
    title: str,
    description: Optional[str] = None,
    highlight: Optional[str] = None,
    address: Optional[str] = None,
    cost: Optional[str] = None,
    time_info: Optional[str] = None,
    url: Optional[str] = None
) -> str:
    """Compute a SHA-256 fingerprint of the card's meaningful information."""
    tokens = [
        (title or "").strip().lower(),
        (description or "").strip().lower(),
        (highlight or "").strip().lower(),
        (address or "").strip().lower(),
        (cost or "").strip().lower(),
        (time_info or "").strip().lower(),
        (url or "").strip().lower()
    ]
    raw = "|".join(tokens)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_deleted_item(db: Session, trip_id: str, item: ItineraryItem) -> None:
    """Record a single deleted item into DeletedItem registry with its content hash."""
    record_deleted_items(db, trip_id, [item])


def record_deleted_items(db: Session, trip_id: str, items: List[ItineraryItem]) -> None:
    """Record multiple deleted items into DeletedItem registry with their content hashes."""
    if not items:
        return

    for it in items:
        clean_title = (it.title or "").strip()
        if not clean_title:
            continue

        c_hash = compute_item_hash(
            title=clean_title,
            description=it.description,
            highlight=it.highlight,
            address=it.address,
            cost=it.cost,
            time_info=it.time_info,
            url=it.url
        )

        city_name = it.city_segment.city_name if it.city_segment else None

        existing = db.query(DeletedItem).filter(
            DeletedItem.trip_id == trip_id,
            func.lower(DeletedItem.title) == clean_title.lower()
        ).first()

        if existing:
            existing.content_hash = c_hash
            existing.city_name = city_name or existing.city_name
            existing.deleted_at = datetime.utcnow()
        else:
            del_rec = DeletedItem(
                trip_id=trip_id,
                title=clean_title,
                content_hash=c_hash,
                city_name=city_name,
                deleted_at=datetime.utcnow()
            )
            db.add(del_rec)

    try:
        db.commit()
    except Exception as err:
        db.rollback()
        print("Notice: Error recording deleted items:", err)


def is_item_deleted_and_unchanged(
    db: Session,
    trip_id: str,
    title: str,
    candidate_hash: str
) -> bool:
    """
    Check whether an item with this title was previously deleted by the user for this trip.
    Returns True if deleted AND the candidate's content hash is identical to when it was deleted
    (meaning the information hasn't changed -> DO NOT REIMPORT!).
    Returns False if never deleted, or if the candidate information HAS changed.
    """
    if not title:
        return False

    del_rec = db.query(DeletedItem).filter(
        DeletedItem.trip_id == trip_id,
        func.lower(DeletedItem.title) == title.strip().lower()
    ).first()

    if not del_rec:
        return False

    # If the hash is identical, the information has NOT changed -> suppress reimport!
    if del_rec.content_hash == candidate_hash:
        return True

    # If the hash is different, the information has changed -> allow import and clear tombstone!
    try:
        db.delete(del_rec)
        db.commit()
    except Exception:
        db.rollback()
    return False


def unmark_deleted_item(db: Session, trip_id: str, title: str) -> None:
    """If a user manually re-adds an item, remove it from the DeletedItem registry."""
    if not title:
        return
    db.query(DeletedItem).filter(
        DeletedItem.trip_id == trip_id,
        func.lower(DeletedItem.title) == title.strip().lower()
    ).delete(synchronize_session=False)
    try:
        db.commit()
    except Exception:
        db.rollback()


def backup_itineraries(
    db: Session,
    backup_file: Optional[Path] = None,
    backup_folder: Optional[Path] = None,
    save_history: bool = True,
    save_local_snapshot: bool = True
) -> Dict[str, Any]:
    """
    Serialize all users, trips, cities, stays, itinerary items, expenses, and deletion memory
    into a structured JSON backup.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if backup_folder:
        Path(backup_folder).mkdir(parents=True, exist_ok=True)

    target_path = backup_file or DEFAULT_BACKUP_FILE

    trips = db.query(Trip).all()
    users = db.query(User).all()

    users_data = [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "avatar_color": u.avatar_color,
            "avatar_url": u.avatar_url,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]

    backup_data = {
        "version": "1.1",
        "created_at": datetime.utcnow().isoformat(),
        "total_trips": len(trips),
        "total_users": len(users),
        "users": users_data,
        "trips": []
    }

    for t in trips:
        # Collaborators
        collabs = [
            {
                "user_id": c.user_id,
                "role": c.role,
                "email": c.user.email if c.user else "",
                "name": c.user.name if c.user else ""
            }
            for c in t.collaborators
        ]

        # Cities & Stays
        city_segments = []
        city_id_map = {}
        for c in sorted(t.city_segments, key=lambda x: x.order_index):
            city_id_map[c.id] = c.city_name
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
                for s in c.stays
            ]
            city_segments.append({
                "id": c.id,
                "city_name": c.city_name,
                "country": c.country,
                "start_date": c.start_date,
                "end_date": c.end_date,
                "order_index": c.order_index,
                "lat": c.lat,
                "lon": c.lon,
                "stays": stays
            })

        # Items
        items = []
        for it in t.items:
            c_hash = compute_item_hash(
                title=it.title,
                description=it.description,
                highlight=it.highlight,
                address=it.address,
                cost=it.cost,
                time_info=it.time_info,
                url=it.url
            )
            items.append({
                "id": it.id,
                "city_segment_id": it.city_segment_id,
                "city_name": city_id_map.get(it.city_segment_id),
                "title": it.title,
                "category": it.category,
                "neighborhood": it.neighborhood,
                "address": it.address,
                "lat": it.lat,
                "lon": it.lon,
                "cost": it.cost,
                "is_free": it.is_free,
                "time_info": it.time_info,
                "highlight": it.highlight,
                "description": it.description,
                "url": it.url,
                "source_platform": it.source_platform,
                "assigned_date": it.assigned_date,
                "order_index": it.order_index or 0,
                "added_by_user_id": it.added_by_user_id,
                "personal_note": it.personal_note,
                "note_by_user_id": it.note_by_user_id,
                "note_updated_at": it.note_updated_at.isoformat() if it.note_updated_at else None,
                "booking_status": it.booking_status or "unbooked",
                "booking_ref": it.booking_ref,
                "content_hash": c_hash
            })

        # Deleted Items Registry
        del_records = [
            {
                "title": d.title,
                "content_hash": d.content_hash,
                "city_name": d.city_name,
                "deleted_at": d.deleted_at.isoformat() if d.deleted_at else None
            }
            for d in t.deleted_items
        ]

        # Expenses
        expenses = [
            {
                "id": exp.id,
                "paid_by_user_id": exp.paid_by_user_id,
                "title": exp.title,
                "amount": exp.amount,
                "currency": exp.currency,
                "category": exp.category,
                "split_type": exp.split_type,
                "expense_date": exp.expense_date,
                "notes": exp.notes
            }
            for exp in t.expenses
        ]

        backup_data["trips"].append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "owner_id": t.owner_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "collaborators": collabs,
            "city_segments": city_segments,
            "items": items,
            "deleted_items": del_records,
            "expenses": expenses
        })

    # Atomic write to JSON
    temp_target = target_path.with_suffix(".tmp")
    with open(temp_target, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    temp_target.replace(target_path)

    # Save local snapshot in local backup folder
    local_snapshot_path = None
    if save_local_snapshot:
        try:
            target_folder = Path(backup_folder) if backup_folder else LOCAL_BACKUP_DIR
            target_folder.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            local_target = target_folder / f"travel_scout_backup_{ts}.json"
            import shutil
            shutil.copy2(target_path, local_target)
            local_snapshot_path = str(local_target)

            # Keep rolling last 25 local snapshots
            local_files = sorted(target_folder.glob("travel_scout_backup_*.json"), key=os.path.getmtime)
            if len(local_files) > 25:
                for old_f in local_files[:-25]:
                    try:
                        old_f.unlink()
                    except Exception:
                        pass
        except Exception as e:
            print("Notice: Error writing local backup snapshot:", e)

    # Save timestamped history
    if save_history:
        try:
            HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            hist_file = HISTORY_DIR / f"itineraries_{ts}.json"
            import shutil
            shutil.copy2(target_path, hist_file)

            # Keep rolling last 10 historical backups
            hist_files = sorted(HISTORY_DIR.glob("itineraries_*.json"), key=os.path.getmtime)
            if len(hist_files) > 10:
                for old_f in hist_files[:-10]:
                    try:
                        old_f.unlink()
                    except Exception:
                        pass
        except Exception as e:
            print("Notice: Error writing backup history:", e)

    return {
        "status": "success",
        "backup_file": str(target_path),
        "local_snapshot": local_snapshot_path,
        "total_trips": len(trips),
        "total_users": len(users),
        "timestamp": backup_data["created_at"]
    }


def restore_itineraries(
    db: Session,
    backup_file: Optional[Path] = None,
    backup_folder: Optional[Path] = None,
    sync_mode: bool = True,
    backup_data: Optional[Dict[str, Any]] = None,
    target_user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Restore and sync itineraries from JSON backup file, folder, or raw backup dictionary.
    
    If sync_mode is True:
    - Restores missing users, trips and cities.
    - If a card was deleted in the current trip or in backup's deleted_items,
      it is NOT re-imported unless its information (hash) has changed!
    """
    if backup_data is not None:
        data = backup_data
    else:
        source_path = backup_file
        if not source_path and backup_folder:
            folder = Path(backup_folder)
            if folder.exists():
                files = sorted(list(folder.glob("*.json")), key=os.path.getmtime, reverse=True)
                if files:
                    source_path = files[0]

        if not source_path:
            source_path = DEFAULT_BACKUP_FILE

        if not source_path.exists():
            return {"status": "skipped", "message": f"No backup file found at {source_path}"}

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as err:
            return {"status": "error", "message": f"Failed to read backup file: {err}"}

    trips_data = data.get("trips", [])
    restored_trips = 0
    restored_items = 0
    restored_users = 0
    skipped_deleted_items = 0

    # 0. Sync Users First (preserves user identities and foreign key integrity)
    for u_data in data.get("users", []):
        u_id = u_data.get("id")
        u_email = u_data.get("email")
        if not u_id or not u_email:
            continue
        existing_u = db.query(User).filter((User.id == u_id) | (User.email == u_email)).first()
        if not existing_u:
            new_u = User(
                id=u_id,
                email=u_email,
                name=u_data.get("name", "Traveler"),
                avatar_color=u_data.get("avatar_color", "#38bdf8"),
                avatar_url=u_data.get("avatar_url")
            )
            db.add(new_u)
            restored_users += 1
        else:
            if not existing_u.name and u_data.get("name"):
                existing_u.name = u_data["name"]
            if not existing_u.avatar_color and u_data.get("avatar_color"):
                existing_u.avatar_color = u_data["avatar_color"]
    try:
        db.commit()
    except Exception:
        db.rollback()

    # Ensure at least one valid user exists for foreign key references
    fallback_user = db.query(User).first()

    for t_data in trips_data:
        trip_id = t_data["id"]
        trip = db.query(Trip).filter(Trip.id == trip_id).first()

        # Resolve valid owner
        raw_owner_id = t_data.get("owner_id")
        owner_exists = db.query(User).filter(User.id == raw_owner_id).first() if raw_owner_id else None
        resolved_owner_id = owner_exists.id if owner_exists else (target_user_id or (fallback_user.id if fallback_user else raw_owner_id))

        # 1. Create trip if it doesn't exist
        if not trip:
            trip = Trip(
                id=trip_id,
                title=t_data["title"],
                description=t_data.get("description"),
                owner_id=resolved_owner_id
            )
            db.add(trip)
            db.commit()
            db.refresh(trip)
            restored_trips += 1

        # If importing on behalf of target_user_id, ensure they are collaborator/owner
        if target_user_id and target_user_id != trip.owner_id:
            has_collab = db.query(TripCollaborator).filter(
                TripCollaborator.trip_id == trip.id,
                TripCollaborator.user_id == target_user_id
            ).first()
            if not has_collab:
                db.add(TripCollaborator(trip_id=trip.id, user_id=target_user_id, role="editor"))
                db.commit()

        # 2. Sync Collaborators
        existing_collabs = {c.user_id for c in trip.collaborators}
        for c_data in t_data.get("collaborators", []):
            u_id = c_data["user_id"]
            if u_id not in existing_collabs:
                collab = TripCollaborator(
                    trip_id=trip.id,
                    user_id=u_id,
                    role=c_data.get("role", "editor")
                )
                db.add(collab)
        db.commit()

        # 3. Sync Deleted Items Registry into Database
        del_records = db.query(DeletedItem).filter(DeletedItem.trip_id == trip.id).all()
        existing_del_map = {
            d.title.lower(): d.content_hash for d in del_records
        }
        for del_info in t_data.get("deleted_items", []):
            d_title = del_info["title"].strip()
            d_hash = del_info["content_hash"]
            if d_title.lower() not in existing_del_map:
                del_rec = DeletedItem(
                    trip_id=trip.id,
                    title=d_title,
                    content_hash=d_hash,
                    city_name=del_info.get("city_name")
                )
                db.add(del_rec)
                existing_del_map[d_title.lower()] = d_hash
        db.commit()

        # 4. Sync City Segments & Stays
        city_name_to_seg = {seg.city_name.lower(): seg for seg in trip.city_segments}
        for c_info in t_data.get("city_segments", []):
            c_name = c_info["city_name"]
            seg = city_name_to_seg.get(c_name.lower())
            if not seg:
                seg = CitySegment(
                    id=c_info["id"],
                    trip_id=trip.id,
                    city_name=c_name,
                    country=c_info.get("country", ""),
                    start_date=c_info["start_date"],
                    end_date=c_info["end_date"],
                    order_index=c_info.get("order_index", 0),
                    lat=c_info.get("lat"),
                    lon=c_info.get("lon")
                )
                db.add(seg)
                db.commit()
                db.refresh(seg)
                city_name_to_seg[c_name.lower()] = seg

            # Stays
            existing_stay_names = {s.name.lower() for s in seg.stays}
            for s_info in c_info.get("stays", []):
                s_name = s_info["name"]
                if s_name.lower() not in existing_stay_names:
                    stay = StayLocation(
                        id=s_info["id"],
                        city_segment_id=seg.id,
                        name=s_name,
                        address=s_info["address"],
                        start_date=s_info["start_date"],
                        end_date=s_info["end_date"],
                        lat=s_info.get("lat"),
                        lon=s_info.get("lon"),
                        notes=s_info.get("notes")
                    )
                    db.add(stay)
                    existing_stay_names.add(s_name.lower())
            db.commit()

        # 5. Sync Itinerary Items (Enforcing Deletion Memory & Change Detection)
        existing_items = db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip.id).all()
        existing_items_map = {it.title.lower(): it for it in existing_items}

        for item_info in t_data.get("items", []):
            item_title = item_info["title"].strip()
            item_hash = item_info.get("content_hash") or compute_item_hash(
                title=item_title,
                description=item_info.get("description"),
                highlight=item_info.get("highlight"),
                address=item_info.get("address"),
                cost=item_info.get("cost"),
                time_info=item_info.get("time_info"),
                url=item_info.get("url")
            )

            # Case A: Item already exists in trip -> keep or update
            if item_title.lower() in existing_items_map:
                continue

            # Case B: Item is NOT currently in trip.
            # Check if it was previously deleted by the user!
            if item_title.lower() in existing_del_map:
                del_hash = existing_del_map[item_title.lower()]
                if del_hash == item_hash:
                    # User deleted this entry and information hasn't changed -> DO NOT REIMPORT!
                    skipped_deleted_items += 1
                    continue
                else:
                    # Information HAS changed since deletion! Allow reimport as updated card.
                    db.query(DeletedItem).filter(
                        DeletedItem.trip_id == trip.id,
                        func.lower(DeletedItem.title) == item_title.lower()
                    ).delete(synchronize_session=False)
                    existing_del_map.pop(item_title.lower(), None)

            # Resolve city segment
            target_seg = None
            if item_info.get("city_segment_id"):
                target_seg = db.query(CitySegment).filter(CitySegment.id == item_info["city_segment_id"]).first()
            if not target_seg and item_info.get("city_name"):
                target_seg = city_name_to_seg.get(item_info["city_name"].lower())
            if not target_seg and trip.city_segments:
                target_seg = trip.city_segments[0]

            new_it = ItineraryItem(
                id=item_info["id"],
                trip_id=trip.id,
                city_segment_id=target_seg.id if target_seg else None,
                title=item_title,
                category=item_info.get("category", "gems"),
                neighborhood=item_info.get("neighborhood"),
                address=item_info.get("address"),
                lat=item_info.get("lat"),
                lon=item_info.get("lon"),
                cost=item_info.get("cost", "Free"),
                is_free=item_info.get("is_free", False),
                time_info=item_info.get("time_info", "Flexible"),
                highlight=item_info.get("highlight"),
                description=item_info.get("description"),
                url=item_info.get("url"),
                source_platform=item_info.get("source_platform", "Backup Restore"),
                assigned_date=item_info.get("assigned_date", "todo"),
                order_index=item_info.get("order_index", 0),
                added_by_user_id=item_info.get("added_by_user_id") or trip.owner_id,
                personal_note=item_info.get("personal_note"),
                note_by_user_id=item_info.get("note_by_user_id"),
                booking_status=item_info.get("booking_status", "unbooked"),
                booking_ref=item_info.get("booking_ref")
            )
            db.add(new_it)
            existing_items_map[item_title.lower()] = new_it
            restored_items += 1

        db.commit()

        # 6. Sync Expenses
        existing_expenses = db.query(TripExpense).filter(TripExpense.trip_id == trip.id).all()
        existing_exp_titles = {exp.title.lower() for exp in existing_expenses}
        for exp_info in t_data.get("expenses", []):
            if exp_info["title"].lower() not in existing_exp_titles:
                expense = TripExpense(
                    id=exp_info["id"],
                    trip_id=trip.id,
                    paid_by_user_id=exp_info["paid_by_user_id"],
                    title=exp_info["title"],
                    amount=exp_info["amount"],
                    currency=exp_info.get("currency", "EUR"),
                    category=exp_info.get("category", "dining"),
                    split_type=exp_info.get("split_type", "equal"),
                    expense_date=exp_info.get("expense_date"),
                    notes=exp_info.get("notes")
                )
                db.add(expense)
                existing_exp_titles.add(exp_info["title"].lower())
        db.commit()

    return {
        "status": "success",
        "restored_trips": restored_trips,
        "restored_items": restored_items,
        "restored_users": restored_users,
        "skipped_deleted_items": skipped_deleted_items
    }


def auto_backup_on_change(db: Session) -> None:
    """Convenience helper to safely trigger non-blocking backup update."""
    try:
        # Safety guard: do not overwrite a populated backup file if current DB has 0 trips
        trips_count = db.query(Trip).count()
        if trips_count == 0 and DEFAULT_BACKUP_FILE.exists() and DEFAULT_BACKUP_FILE.stat().st_size > 50:
            return
        backup_itineraries(db, save_history=False, save_local_snapshot=True)
    except Exception as err:
        print("Notice: Auto-backup skipped:", err)


if __name__ == "__main__":
    import argparse
    from database.connection import SessionLocal

    parser = argparse.ArgumentParser(description="Travel Scout Itinerary Backup & Restore")
    parser.add_argument("--action", choices=["backup", "restore", "status"], default="backup", help="Action to execute")
    parser.add_argument("--file", type=str, help="Custom JSON backup file path")
    parser.add_argument("--folder", type=str, default=str(LOCAL_BACKUP_DIR), help="Custom backup folder path")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        custom_p = Path(args.file) if args.file else None
        custom_folder = Path(args.folder) if args.folder else None
        if args.action == "backup":
            res = backup_itineraries(db, backup_file=custom_p, backup_folder=custom_folder, save_local_snapshot=True)
            print("Backup complete:", res)
        elif args.action == "restore":
            res = restore_itineraries(db, backup_file=custom_p, backup_folder=custom_folder)
            print("Restore complete:", res)
        elif args.action == "status":
            trips_c = db.query(Trip).count()
            users_c = db.query(User).count()
            print(f"Status: {trips_c} trips, {users_c} users in database.")
            if DEFAULT_BACKUP_FILE.exists():
                print(f"Default backup file: {DEFAULT_BACKUP_FILE} ({DEFAULT_BACKUP_FILE.stat().st_size} bytes)")
            if LOCAL_BACKUP_DIR.exists():
                local_f = list(LOCAL_BACKUP_DIR.glob("*.json"))
                print(f"Local backup folder: {LOCAL_BACKUP_DIR} ({len(local_f)} snapshots)")
    finally:
        db.close()
