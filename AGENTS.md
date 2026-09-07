# Travel Scout — Agent Development & Behavioral Guidelines

This document provides foundational architecture instructions, coding standards, and operational guidelines for AI agents working in the **Travel Scout** codebase. Read this document before making modifications or implementing new features.

---

## 1. Project & Architectural Overview

Travel Scout is a multi-city collaborative travel platform built with:
- **Backend**: Python 3.11+ / FastAPI (`app.py`), Pydantic models for request validation, Uvicorn ASGI server (`main.py web`).
- **Core Engine**: `scout/`
  - `scout/engine.py`: Core trip management, day bucket scheduling, expense splitting, collaborators, notes.
  - `scout/transit.py`: Walking time calculations, transit agency routing rules (MTS, Carris, Metro, etc.), and Google Maps directions URL generation.
  - `scout/geocoding.py`: OpenStreetMap Nominatim geocoding with local city fallback cache (`GLOBAL_CITY_COORDINATES`).
  - `scout/weather.py`: Open-Meteo weather forecasts and rain advisories (zero API key required).
  - `scout/web_search.py` & `scout/local_agent.py`: Multi-channel web search and cultural event ingestion.
- **Database**: SQLite (`travel_scout.db`) using raw SQL queries with parameterized inputs via `database/connection.py` and schema definitions in `database/models.py`.
- **Frontend**: Vanilla JavaScript SPA (`static/app.js`), responsive CSS (`static/styles.css`), Jinja2 HTML (`templates/index.html`), Leaflet.js interactive maps, and Service Worker (`static/sw.js`) for PWA and offline access.
- **Agent Extensions**: Custom skills and scripts located in `.agents/skills/` (e.g. `local-city-scout`).

---

## 2. Non-Negotiable Project Rules

### Rule 1: Static Asset Versioning & Cache Invalidation
Whenever you modify `static/app.js` or `static/styles.css`:
1. **Bump the query version parameter** in `templates/index.html`:
   ```html
   <link rel="stylesheet" href="/static/styles.css?v=X.Y">
   <script src="/static/app.js?v=X.Y"></script>
   ```
2. **Bump the cache name** in `static/sw.js`:
   ```javascript
   const CACHE_NAME = 'travel-scout-vX.Y';
   ```
*Why:* The PWA Service Worker aggressively caches static assets. If versions are not bumped, users will run stale JavaScript and CSS.

### Rule 2: Maps & Navigation URLs
- **Never** generate navigation links using Google Maps search (`/maps/search/?api=1&query=...`).
- **Always** use Google Maps Directions API format:
  ```
  https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode={travelmode}
  ```
- **Hotel / Stay Matching**: When resolving the origin for an itinerary item, match the item's `date` against hotel stay ranges (`stay.start_date <= item.date <= stay.end_date`). Use the matched hotel's coordinates or address as `origin`.
- Clicking a hotel itself should launch directions with the hotel as the destination.

### Rule 3: Geocoding & Coordinate Accuracy
- Never silently fall back to default/placeholder coordinates (e.g. Lisbon) when the destination is in another city or country.
- When adding or updating destination cities or hotel stays, resolve actual coordinates via Nominatim or add the city to `GLOBAL_CITY_COORDINATES` in `scout/geocoding.py`.
- Ensure date strings are strict ISO `YYYY-MM-DD` format (watch out for typos such as `0226` instead of `2026`, which break string comparison).

### Rule 4: Security, Authentication & Data Isolation
- Authentication uses HMAC-SHA256 signed session tokens (`travel_scout_session` cookie).
- Frontend requests must specify `credentials: 'include'` when fetching protected endpoints.
- Backend routes must verify trip ownership or collaborator permissions before allowing mutations (BOLA / IDOR protection).
- Validate all user-supplied URLs with `Pydantic` and sanitize DOM injection via `sanitizeUrl` to prevent XSS.

### Rule 5: Database Schema & Migration Hygiene
- Database tables are initialized in `database/models.py`.
- When adding columns to existing tables, ensure `ALTER TABLE` fallback handling or migration checks exist so existing `travel_scout.db` files do not crash on startup.
- Always use parameterized queries (`?`) to prevent SQL injection.

### Rule 6: Input, Output & Edge Case Specification
- Never implement features or bugfixes based solely on ambiguous or ungrounded assumptions.
- **Inputs**: Explicitly confirm data formats (strict ISO dates `YYYY-MM-DD`, geocoding coordinates, payload schemas).
- **Outputs**: Define the expected user-facing response or API payload (status code, schema, DOM updates).
- **Edge Cases**: Always handle empty lists (empty itinerary/wishlist), null/missing coordinates, expired session cookies, out-of-range dates, and special characters.
- Refer to `.agents/PROMPTS.md` for task recipes and prompt templates.

---

## 3. Mandatory Verification Workflow

Before concluding any code change or reporting back to the user:
1. **Syntax Check**: Run `python -m py_compile <modified_file>.py` on all edited Python files.
2. **Automated Verification Script**: Write and execute a focused standalone test script in `scratch/` (or run an existing test) to verify:
   - Endpoint responses (status codes, JSON payload structure).
   - Database operations (insert, update, delete).
   - Business logic edge cases (date boundaries, missing fields).
3. **Frontend Sanity**: If modifying HTML/JS/CSS, check for unclosed tags, modal backdrop behaviors, and verify that button click event listeners are properly registered.
4. **Git Hygiene**: Check `git status` and `git diff` to ensure no unintended files or temporary debug files are left untracked.

---

## 4. Skills & Autonomous Agents (`.agents/`)

- Domain-specific skills are located under `.agents/skills/<skill-name>/SKILL.md`.
- Primary skill: **`local-city-scout`**
  - Discovers local press, alternative weeklies, concerts, indie cinema, record store performances, and festivals for destination cities.
  - Ingests events into the `Explore & Discover` tab (`assigned_date="todo"`).
  - CLI script: `.agents/skills/local-city-scout/scripts/scout_events.py`
  - API endpoint: `POST /api/trips/{trip_id}/scout/local-agent`
- When expanding scout capabilities, maintain consistent category taxonomy (`movies`, `music`, `records`, `art`, `festivals`, `markets`, `free`, `dining`, `press`).
