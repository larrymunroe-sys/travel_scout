"""Entry point for Multi-City Collaborative Travel Scout Platform."""
import sys
import socket
import argparse
import uvicorn
from database.connection import init_db, SessionLocal
from scout.engine import ScoutEngine

def find_available_port(host: str = "127.0.0.1", start_port: int = 8001, max_port: int = 8030) -> int:
    """Find the first available TCP port to prevent collisions with other servers."""
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    return start_port

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_web(host: str = "127.0.0.1", port: int = 8000):
    chosen_port = find_available_port(host, port)
    print("=" * 65)
    print("Multi-City Collaborative Travel Scout Agent")
    print("Pre-Seeded Journey: Lisbon -> Porto -> Braganca")
    print(f"Dashboard running at: http://{host}:{chosen_port}")
    print("=" * 65)
    uvicorn.run("app:app", host=host, port=chosen_port, reload=False)

def run_scan():
    init_db()
    scout = ScoutEngine()
    with SessionLocal() as db:
        from database.models import Trip, User
        trip = db.query(Trip).first()
        user = db.query(User).first()
        if not trip or not user:
            print("No trips found in database to scan.")
            return

        print(f"⚡ Running autonomous multi-city scan for trip: '{trip.title}'...")
        res = scout.run_multi_city_daily_scan(db, trip.id, user.id)
        print(f"✓ Scan completed! Scanned {res['cities_scanned']} cities. Discovered {res['newly_discovered']} new items.")

def main():
    parser = argparse.ArgumentParser(description="Multi-City Collaborative Travel Scout")
    subparsers = parser.add_subparsers(dest="command")

    web_p = subparsers.add_parser("web", help="Start FastAPI web dashboard")
    web_p.add_argument("--host", default="127.0.0.1")
    web_p.add_argument("--port", type=int, default=8000)

    subparsers.add_parser("scan", help="Run multi-city autonomous scan")

    args = parser.parse_args()

    if args.command == "scan":
        run_scan()
    else:
        host = getattr(args, "host", "127.0.0.1")
        port = getattr(args, "port", 8001)
        run_web(host, port)

if __name__ == "__main__":
    main()
