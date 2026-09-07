# Travel Scout — Prompt Engineering & Task Formulation Handbook

This handbook provides practical prompt templates and the "Inputs, Outputs & Edge Cases" formula to get accurate, production-grade results from AI agents working on Travel Scout.

---

## The 3-Part Formula: Inputs, Outputs & Edge Cases

When prompting an agent, vague descriptions produce vague code. Structuring prompts with these three pillars ensures the agent implements exactly what you want on the first attempt:

```text
1. CONTEXT & GOAL: What problem are you solving, on which page/component?
2. INPUTS & SPECIFICATIONS: What data is entering? (Exact dates, coordinates, fields, URLs)
3. OUTPUTS & EDGE CASES: What should the UI/API return, and what failure modes must be handled?
```

---

## Real Before-and-After Prompt Recipes

### Recipe 1: Fixing Transit, Maps & Geocoding
- ❌ **Vague**: *"The walking times and maps look wrong, fix them."*
- ✅ **Anchored**:
  ```text
  Fix the transit and map links for the San Diego leg:
  - Context: The Lafayette Hotel is at 2223 El Cajon Blvd, San Diego, CA 92104.
  - Inputs: Use coordinates (32.7549, -117.1407) and MTS transit rules (Rapid Bus 215).
  - Outputs: 
    1. 'Maps & Directions' button must open Google Maps Directions (/maps/dir/) with 
       origin=hotel and destination=venue.
    2. Clicking the hotel pin on Leaflet map must open directions with the hotel as destination.
  - Edge Cases: If an item has no scheduled date, fall back to the first city hotel. If the venue has no coordinates, search by venue name + city.
  - Verification: Write and run a test script in scratch/ testing distance calculations and URL formats.
  ```

---

### Recipe 2: Adding a New UI Action or Modal
- ❌ **Vague**: *"Add bulk select to delete cards."*
- ✅ **Anchored**:
  ```text
  Add a bulk selection mode to delete multiple cards from the Itinerary:
  - Context: Collaborative Itinerary tab in static/app.js and templates/index.html.
  - Inputs: Multi-select checkbox on each card when 'Bulk Select' mode is toggled.
  - Outputs:
    1. A floating toolbar showing 'X items selected' with 'Select All', 'Delete Selected', and 'Cancel'.
    2. Confirmation prompt displaying how many items will be deleted.
    3. Calls DELETE /api/trips/{trip_id}/items in a loop or batch endpoint, then refreshes the cards.
  - Edge Cases:
    - If 0 items are selected, disable the delete button.
    - If deletion fails halfway, alert user and preserve remaining selected items.
    - Bump styles.css and app.js version in index.html and cache name in sw.js.
  - Verification: Test modal opening, selection toggle, and delete API call.
  ```

---

### Recipe 3: Adding a New Backend Endpoint or Database Column
- ❌ **Vague**: *"Let me edit the hotel information."*
- ✅ **Anchored**:
  ```text
  Add an endpoint and modal to edit existing hotel stays:
  - Context: stay_locations table in SQLite and Cities & Stays tab in UI.
  - Inputs: PUT /api/trips/{trip_id}/stays/{stay_id} accepting:
    { name: str, address: str, start_date: 'YYYY-MM-DD', end_date: 'YYYY-MM-DD', notes: str }
  - Outputs:
    1. Re-geocode coordinates automatically if address changes.
    2. Return updated stay JSON.
    3. Update UI city cards without full page reload.
  - Edge Cases:
    - Validate date order (start_date <= end_date).
    - Protect with trip ownership / editor permission check (BOLA).
    - Handle Nominatim rate limits or offline geocoding with city fallback cache.
  - Verification: Write a test in scratch/ that creates a stay, edits it, and checks DB values.
  ```

---

### Recipe 4: Running Cultural Scout on a New City
- ❌ **Vague**: *"Find events for Lisbon."*
- ✅ **Anchored**:
  ```text
  Run the local-city-scout skill for Lisbon, Portugal:
  - Dates: 2026-09-25 to 2026-09-30.
  - Target Sources: Mensagem de Lisboa, Agenda Cultural de Lisboa, Songkick, DICE.fm.
  - Categories: Indie cinema (movies), live concerts (music), vinyl record store gigs (records), and free events (free).
  - Output: Ingest 3-4 top events per category into the Explore & Discover tab with assigned_date='todo', accurate coordinates, neighborhood tags (e.g. Alfama, Bairro Alto), and official ticket/venue URLs.
  - Edge Cases: Exclude expired events or generic corporate aggregator spam. Ensure prices state 'Free' or exact EUR amount.
  ```

---

## ⚡ Quick Copy-Paste Prompt Modifiers

Append any of these snippets to your prompt for instant precision:

- **Verification Guard**:
  > *"Run `python -m py_compile` and write a standalone test script in `scratch/` to verify endpoint responses and DB state before concluding."*

- **Cache-Busting Guard**:
  > *"Remember to bump query params in `index.html` (`?v=X.Y`) and `CACHE_NAME` in `sw.js` for any CSS/JS changes."*

- **Security & Authorization Guard**:
  > *"Ensure this endpoint verifies trip ownership/collaborator permissions (BOLA check) and uses parameterized SQL queries."*

- **Strict Date & Geocoding Guard**:
  > *"Ensure dates are validated in strict `YYYY-MM-DD` format and coordinates are looked up in `GLOBAL_CITY_COORDINATES` or via Nominatim."*
