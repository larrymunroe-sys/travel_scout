# Travel Scout — Automated Test Suite & Regression Verification

This directory contains the automated testing workflows for Travel Scout.

## Running the Tests

### 1. Fast In-Memory Test (Default)
Runs all 7 critical user journeys directly against the FastAPI ASGI app using `TestClient`:
```bash
npm test
# OR
python tests/test_workflow.py
# OR
python test_workflow.py
```
*Execution time: ~2.5 seconds. Zero port conflicts, zero external server requirement, cleans up database automatically.*

### 2. Against a Running Server (Live HTTP)
To test an active development or staging server (e.g. `http://localhost:8000`):
```bash
python tests/test_workflow.py --url http://localhost:8000
```

### 3. Debugging (Preserve Test Data)
To inspect database records without running teardown cleanup:
```bash
python tests/test_workflow.py --keep-data --verbose
```

---

## What is Verified (93 Automated Assertions)

1. **Pre-Flight DOM & Cache Integrity**:
   - HTTP 200 OK on `/`
   - Presence of all 7 header action buttons (`#openCreateTripBtn`, `#openEditTripBtn`, `#openHelpBtn`, `#openInviteBtn`, `#openManageUsersBtn`, `#openPrintHeaderBtn`, `#openAddItemHeaderBtn`)
   - Presence of all 8 modal overlays
   - DOM tag hierarchy: ensures `#addItemModal` is closed properly before `#bulkActionBar`
   - Cache-busting version parameters (`?v=3.8` on `styles.css` and `app.js`)
   - Service Worker no-cache headers and active cache version

2. **Workflow 1: Login & Session Authentication**:
   - `GET /auth/me` unauthenticated guest state
   - `POST /auth/dev-login` instant login with HMAC-SHA256 session token
   - `GET /auth/me` authenticated identity and avatar color verification

3. **Workflow 2: New Itinerary & Custom Lodging Address**:
   - `POST /api/trips` creating custom itinerary with first destination city
   - Verifies custom lodging address (`hotel_address`) is saved on the hotel stay record
   - Date indexing (`available_dates`) and timeline initialization

4. **Workflow 3: Help & How-To Manual**:
   - `#helpModal` content verification across all 6 core guide sections
   - Close button event bindings and global window helper exports

5. **Workflow 4: Share & Invite Collaborators**:
   - `POST /api/trips/{trip_id}/collaborators` invitation by email with editor/viewer roles
   - Verifies contributor list updates and collaborator permissions

6. **Workflow 5: User Management**:
   - `GET /api/users` account listing, trip counts, collaborator counts, and metadata
   - Modal container `#manageUsersList` and `#cleanupDemoBtn` verification

7. **Workflow 6: Print & Export**:
   - Dedicated print view (`GET /api/trips/{trip_id}/print`) formatted for Letter/A4 and PDF
   - Single-day filter and custom date range filter
   - Calendar sync RFC 5545 iCalendar download (`GET /api/trips/{trip_id}/export/calendar.ics`)

8. **Workflow 7: Add Custom Itinerary Items**:
   - `POST /api/trips/{trip_id}/items` custom scheduled stop with cost, booking status, and reference code
   - Unscheduled Wishlist / Bucket List stop (`assigned_date="todo"`)
   - Deletion of custom stop (`DELETE /api/trips/{trip_id}/items/{item_id}`)

9. **Automated Teardown**:
   - Cascading deletion of test itinerary
   - Purging temporary test users from SQLite database
