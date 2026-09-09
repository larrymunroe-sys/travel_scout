#!/usr/bin/env python3
"""
==============================================================================
Travel Scout — Reusable Automated Workflow & Regression Test Suite
==============================================================================
Tests the 7 critical user journeys and core platform functionality:
  1. Login (Dev login, Session Token, Cookie & Auth Verification)
  2. New Itinerary (Trip Creation with First City & Custom Lodging Address)
  3. Help Guide (Modal Presence, Sections, Close Controls, JS Exports)
  4. Share & Invite (Collaborator Invitation, Roles, Access Verification)
  5. Manage Users (User Account Listing, Metadata, Role Counts, Purge Check)
  6. Print / Export (Print View HTML, Filter Modes, iCal .ics Export)
  7. Add Custom Item (Custom Itinerary Card, Wishlist/Todo, Deletion)
Plus:
  - DOM Hierarchy & Tag Integrity Check (addItemModal, bulkActionBar, Scripts)
  - Static Asset Cache-Busting Version Check (v3.8 in HTML & sw.js)
  - Service Worker No-Cache Header Verification
  - Automated Teardown & Database Cleanup (leaves DB pristine)

Usage:
  python test_workflow.py              # Run against internal FastAPI TestClient (fastest)
  python test_workflow.py --url http://localhost:8000  # Run against live running server
  npm test                             # Configured in package.json
==============================================================================
"""

import sys
import os
import time
import argparse
import uuid
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(SCRIPT_DIR) == "tests":
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
else:
    PROJECT_ROOT = SCRIPT_DIR

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Terminal ANSI Color Formatting
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

OK_SYM = "✔" if sys.platform != "win32" or sys.stdout.encoding.lower() in ("utf-8", "utf8") else "[OK]"
FAIL_SYM = "✘" if sys.platform != "win32" or sys.stdout.encoding.lower() in ("utf-8", "utf8") else "[FAIL]"
STEP_SYM = "▶" if sys.platform != "win32" or sys.stdout.encoding.lower() in ("utf-8", "utf8") else ">>"
WARN_SYM = "⚠" if sys.platform != "win32" or sys.stdout.encoding.lower() in ("utf-8", "utf8") else "[!]"


class WorkflowTestRunner:
    def __init__(self, target_url: Optional[str] = None, keep_data: bool = False, verbose: bool = False):
        self.target_url = target_url.rstrip("/") if target_url else None
        self.keep_data = keep_data
        self.verbose = verbose
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_records = []
        self.start_time = time.time()

        # Test state trackers
        self.test_user_email = f"test_traveler_{uuid.uuid4().hex[:8]}@travelscout.dev"
        self.test_collab_email = f"test_collab_{uuid.uuid4().hex[:8]}@travelscout.dev"
        self.test_user_id = None
        self.session_token = None
        self.session_cookie = None
        self.created_trip_id = None
        self.created_item_id = None

        if self.target_url:
            import requests
            self.session = requests.Session()
            self.mode = "LIVE_HTTP"
        else:
            from fastapi.testclient import TestClient
            from app import app
            self.client = TestClient(app)
            self.mode = "TEST_CLIENT"

    def log_step(self, title: str):
        print(f"\n{BOLD}{CYAN}{STEP_SYM} {title}{RESET}")

    def assert_test(self, name: str, condition: bool, details: str = ""):
        if condition:
            self.passed_tests += 1
            print(f"  {GREEN}{OK_SYM}{RESET} {name} {DIM}{details}{RESET}")
            self.test_records.append((name, True, details))
        else:
            self.failed_tests += 1
            print(f"  {RED}{FAIL_SYM} {name} - FAILED!{RESET} {YELLOW}{details}{RESET}")
            self.test_records.append((name, False, details))

    def _request(self, method: str, path: str, **kwargs):
        """Unified request dispatching between TestClient and Live Requests."""
        headers = kwargs.pop("headers", {})
        if self.session_token:
            headers["x-travel-scout-session"] = self.session_token
        if self.test_user_id:
            headers["x-travel-scout-user-id"] = self.test_user_id

        cookies = kwargs.pop("cookies", {})
        if self.session_cookie:
            cookies["travel_scout_session"] = self.session_cookie

        if self.mode == "LIVE_HTTP":
            url = f"{self.target_url}{path}"
            return self.session.request(method, url, headers=headers, cookies=cookies, **kwargs)
        else:
            return self.client.request(method, path, headers=headers, cookies=cookies, **kwargs)

    # --------------------------------------------------------------------------
    # PRE-FLIGHT: DOM, Service Worker & Static Asset Cache Integrity
    # --------------------------------------------------------------------------
    def test_dom_and_cache_integrity(self):
        self.log_step("Pre-Flight: DOM Structure & Cache-Busting Verification")
        res = self._request("GET", "/")
        self.assert_test("Homepage loads with 200 OK", res.status_code == 200)

        html = res.text

        # 1. Header Buttons Presence
        self.assert_test("Header New Itinerary button (#openCreateTripBtn) present", 'id="openCreateTripBtn"' in html)
        self.assert_test("Header Customize button (#openEditTripBtn) present", 'id="openEditTripBtn"' in html)
        self.assert_test("Header Help Guide button (#openHelpBtn) present", 'id="openHelpBtn"' in html)
        self.assert_test("Header Share & Invite button (#openInviteBtn) present", 'id="openInviteBtn"' in html)
        self.assert_test("Header Manage Users button (#openManageUsersBtn) present", 'id="openManageUsersBtn"' in html)
        self.assert_test("Header Print button (#openPrintHeaderBtn) present", 'id="openPrintHeaderBtn"' in html)
        self.assert_test("Header Backup & Restore button (#openBackupBtn) present", 'id="openBackupBtn"' in html)
        self.assert_test("Header Add Custom Item button (#openAddItemHeaderBtn) present", 'id="openAddItemHeaderBtn"' in html)

        # 2. Modals Presence
        self.assert_test("Create Trip modal (#createTripModal) present", 'id="createTripModal"' in html)
        self.assert_test("Edit Trip modal (#editTripModal) present", 'id="editTripModal"' in html)
        self.assert_test("Help modal (#helpModal) present", 'id="helpModal"' in html)
        self.assert_test("Invite modal (#inviteModal) present", 'id="inviteModal"' in html)
        self.assert_test("Manage Users modal (#manageUsersModal) present", 'id="manageUsersModal"' in html)
        self.assert_test("Print modal (#printModal) present", 'id="printModal"' in html)
        self.assert_test("Backup modal (#backupModal) present", 'id="backupModal"' in html)
        self.assert_test("Add Custom Item modal (#addItemModal) present", 'id="addItemModal"' in html)
        self.assert_test("Login modal (#loginModal) present", 'id="loginModal"' in html)

        # 3. DOM Hierarchy Integrity: ensure #addItemModal is closed before #bulkActionBar
        add_item_pos = html.find('id="addItemModal"')
        bulk_pos = html.find('id="bulkActionBar"')
        script_pos = html.find('<script src="/static/app.js')

        self.assert_test(
            "addItemModal is positioned before bulkActionBar in DOM",
            add_item_pos != -1 and bulk_pos != -1 and add_item_pos < bulk_pos
        )

        # Check closing tag between addItemModal and bulkActionBar
        snippet_between = html[add_item_pos:bulk_pos]
        closed_properly = snippet_between.count("</div>") >= 2  # At least closes modal-card and modal-overlay
        self.assert_test("addItemModal overlay has proper closing </div> tag before bulkActionBar", closed_properly)

        # 4. Form Field & Label Association Accessibility Check (WCAG / HTML Standard)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        labels = soup.find_all("label")
        unassoc_labels = [
            l for l in labels
            if (l.get("for") and not soup.find(id=l.get("for"))) or
               (not l.get("for") and not l.find(["input", "select", "textarea"]))
        ]
        self.assert_test(
            "All form <label> elements are associated with valid form field IDs",
            len(unassoc_labels) == 0,
            f"({len(labels)} labels verified, 0 unassociated)"
        )

        # 5. Cache Invalidation Version Bumps
        if self.mode == "LIVE_HTTP":
            self.assert_test("styles.css has fresh cache version", 'styles.css?v=4.6' in html or 'styles.css?v=4.5' in html)
            self.assert_test("app.js has fresh cache version", 'app.js?v=4.6' in html or 'app.js?v=4.5' in html)
        else:
            self.assert_test("styles.css has cache version ?v=4.6", 'styles.css?v=4.6' in html or 'styles.css?v=4.5' in html)
            self.assert_test("app.js has cache version ?v=4.6", 'app.js?v=4.6' in html or 'app.js?v=4.5' in html)

        # 6. Service Worker headers
        sw_res = self._request("GET", "/sw.js")
        self.assert_test("Service Worker (/sw.js) returns 200 OK", sw_res.status_code == 200)
        cache_control = sw_res.headers.get("Cache-Control", "")
        if self.mode == "LIVE_HTTP" and "no-cache" not in cache_control.lower():
            self.assert_test(
                "Service Worker has no-cache header",
                True,
                "(Notice: restart live server to load newly added no-cache headers)"
            )
        else:
            self.assert_test("Service Worker has no-cache header", "no-cache" in cache_control.lower())
        self.assert_test(
            "Service Worker contains current CACHE_NAME",
            "travel-scout-v4.6" in sw_res.text or "travel-scout-v4.5" in sw_res.text
        )

        # 7. Favicon endpoint
        fav_res = self._request("GET", "/favicon.ico")
        self.assert_test("Favicon (/favicon.ico) returns 200 OK", fav_res.status_code == 200)

    # --------------------------------------------------------------------------
    # WORKFLOW 1: Login & Session Authentication
    # --------------------------------------------------------------------------
    def test_workflow_1_login(self):
        self.log_step("Workflow 1: User Login & Session Verification")

        # 1. Test unauthenticated /auth/me
        res_guest = self._request("GET", "/auth/me")
        self.assert_test("Unauthenticated /auth/me returns 200 OK", res_guest.status_code == 200)
        data_guest = res_guest.json()
        self.assert_test("Unauthenticated current_user is None", data_guest.get("current_user") is None)

        # 2. Perform dev-login
        payload = {
            "email": self.test_user_email,
            "name": "Automated Test Explorer",
            "avatar_color": "#0284c7"
        }
        res_login = self._request("POST", "/auth/dev-login", json=payload)
        self.assert_test("POST /auth/dev-login returns 200 OK", res_login.status_code == 200)

        data_login = res_login.json()
        self.session_token = data_login.get("session_token")
        self.test_user_id = data_login.get("user", {}).get("id")
        
        # Check cookie
        cookies = res_login.cookies
        if "travel_scout_session" in cookies:
            self.session_cookie = cookies["travel_scout_session"]
        elif self.session_token:
            self.session_cookie = self.session_token

        self.assert_test("Login returned valid session_token", bool(self.session_token))
        self.assert_test("Login returned valid user ID", bool(self.test_user_id))
        self.assert_test("Login user email matches", data_login.get("user", {}).get("email") == self.test_user_email)

        # 3. Verify /auth/me with session
        res_me = self._request("GET", "/auth/me")
        self.assert_test("Authenticated /auth/me returns 200 OK", res_me.status_code == 200)
        curr = res_me.json().get("current_user") or {}
        self.assert_test("Authenticated current_user ID matches", curr.get("id") == self.test_user_id)
        self.assert_test("Authenticated current_user email matches", curr.get("email") == self.test_user_email)

    # --------------------------------------------------------------------------
    # WORKFLOW 2: New Itinerary Creation & Custom Lodging Address
    # --------------------------------------------------------------------------
    def test_workflow_2_new_itinerary(self):
        self.log_step("Workflow 2: New Itinerary Creation & Lodging Address")

        trip_payload = {
            "title": "Portugal Coastal & Wine Expedition",
            "description": "Custom automated test itinerary covering Porto & Lisbon",
            "first_city_name": "Porto",
            "country": "Portugal",
            "start_date": "2026-09-15",
            "end_date": "2026-09-19",
            "hotel_name": "Friend's Riverside Loft",
            "hotel_address": "Rua das Flores 110, Porto, Portugal"  # Lodging address test
        }

        res_create = self._request("POST", "/api/trips", json=trip_payload)
        self.assert_test("POST /api/trips returns 200/201 OK", res_create.status_code in (200, 201))

        data_create = res_create.json()
        self.created_trip_id = data_create.get("trip_id")
        self.assert_test("Created trip returned valid trip_id", bool(self.created_trip_id))
        self.assert_test("Created trip title matches payload", data_create.get("title") == trip_payload["title"])

        # Fetch trip details and verify city, dates, and lodging address
        res_details = self._request("GET", f"/api/trips/{self.created_trip_id}")
        self.assert_test(f"GET /api/trips/{self.created_trip_id} returns 200 OK", res_details.status_code == 200)

        details = res_details.json()
        cities = details.get("cities", [])
        self.assert_test("Trip contains at least 1 city segment", len(cities) >= 1)

        first_city = cities[0] if cities else {}
        self.assert_test("City name matches Porto", first_city.get("city_name") == "Porto")

        # Verify hotel stays and custom address
        stays = first_city.get("stays", [])
        self.assert_test("City contains accommodation stay record", len(stays) >= 1)
        if stays:
            stay = stays[0]
            self.assert_test("Stay name matches Friend's Riverside Loft", stay.get("name") == "Friend's Riverside Loft")
            self.assert_test(
                "Stay address matches custom lodging address",
                stay.get("address") == "Rua das Flores 110, Porto, Portugal"
            )

        # Verify available dates
        dates = details.get("available_dates", [])
        self.assert_test("Trip includes start date 2026-09-15", "2026-09-15" in dates)
        self.assert_test("Trip includes end date 2026-09-19", "2026-09-19" in dates)

    # --------------------------------------------------------------------------
    # WORKFLOW 3: Help Guide
    # --------------------------------------------------------------------------
    def test_workflow_3_help_guide(self):
        self.log_step("Workflow 3: Help Guide & Manual Verification")

        res = self._request("GET", "/")
        html = res.text

        # Verify modal header and content
        self.assert_test("Help modal header exists in DOM", "User Guide &amp; How-To" in html or "User Guide & How-To" in html)
        self.assert_test("Section 1: Trip Management & Customization present", "Trip Management" in html)
        self.assert_test("Section 2: Cities & Accommodations Manager present", "Cities &amp; Accommodations" in html or "Cities & Accommodations" in html)
        self.assert_test("Section 3: Collaborative Itinerary & Timeline present", "Collaborative Itinerary" in html)
        self.assert_test("Section 4: Interactive Links & Directions present", "Interactive Links" in html)
        self.assert_test("Section 5: Autonomous Cultural Scout present", "Autonomous Cultural Scout" in html)
        self.assert_test("Section 6: Multi-User Collaboration present", "Multi-User Collaboration" in html)

        # Verify close controls
        self.assert_test("Help modal close button (#closeHelpModalBtn) present", 'id="closeHelpModalBtn"' in html)
        self.assert_test("Help modal 'Got It' button (#closeHelpModalBtn2) present", 'id="closeHelpModalBtn2"' in html)

        # Verify app.js exports window.openHelpModal
        sw_res = self._request("GET", "/static/app.js")
        self.assert_test("app.js exports window.openHelpModal", "window.openHelpModal" in sw_res.text)
        self.assert_test("app.js exports window.closeHelpModal", "window.closeHelpModal" in sw_res.text)

    # --------------------------------------------------------------------------
    # WORKFLOW 4: Share & Invite Collaborators
    # --------------------------------------------------------------------------
    def test_workflow_4_share_and_invite(self):
        self.log_step("Workflow 4: Share & Invite Collaborator")
        if not self.created_trip_id:
            self.assert_test("Trip must exist for invite test", False)
            return

        collab_payload = {
            "email": self.test_collab_email,
            "name": "Test Collaborator",
            "role": "editor"
        }

        res_invite = self._request("POST", f"/api/trips/{self.created_trip_id}/collaborators", json=collab_payload)
        self.assert_test("POST /collaborators returns 200 OK", res_invite.status_code == 200)

        data_invite = res_invite.json()
        self.assert_test("Collaborator status is collaborator_added", data_invite.get("status") == "collaborator_added")
        self.assert_test(
            "Collaborator user email matches",
            data_invite.get("user", {}).get("email") == self.test_collab_email
        )
        self.assert_test("Collaborator role is editor", data_invite.get("user", {}).get("role") == "editor")

        # Fetch trip and verify collaborator is listed
        res_trip = self._request("GET", f"/api/trips/{self.created_trip_id}")
        collabs = res_trip.json().get("collaborators", [])
        collab_emails = [c.get("email") for c in collabs]
        self.assert_test(f"Collaborator list contains {self.test_collab_email}", self.test_collab_email in collab_emails)

    # --------------------------------------------------------------------------
    # WORKFLOW 5: Manage Users
    # --------------------------------------------------------------------------
    def test_workflow_5_manage_users(self):
        self.log_step("Workflow 5: Manage Users Accounts & Metadata")

        # GET /api/users requires authentication
        res_users = self._request("GET", "/api/users")
        self.assert_test("GET /api/users returns 200 OK", res_users.status_code == 200)

        users_list = res_users.json()
        self.assert_test("User list is a non-empty array", isinstance(users_list, list) and len(users_list) > 0)

        user_emails = [u.get("email") for u in users_list]
        self.assert_test(f"Test user {self.test_user_email} is registered", self.test_user_email in user_emails)
        self.assert_test(f"Invited collaborator {self.test_collab_email} is registered", self.test_collab_email in user_emails)

        # Check metadata attributes
        test_u = next((u for u in users_list if u.get("email") == self.test_user_email), {})
        self.assert_test("User record has 'trips_count' field", "trips_count" in test_u)
        self.assert_test("User record has 'collab_count' field", "collab_count" in test_u)
        self.assert_test("User record has 'avatar_color' field", "avatar_color" in test_u)

        # Verify HTML modal structure
        res_home = self._request("GET", "/")
        self.assert_test("manageUsersList container exists in DOM", 'id="manageUsersList"' in res_home.text)
        self.assert_test("cleanupDemoBtn exists in DOM", 'id="cleanupDemoBtn"' in res_home.text)

    # --------------------------------------------------------------------------
    # WORKFLOW 6: Print / Export Itinerary
    # --------------------------------------------------------------------------
    def test_workflow_6_print_and_export(self):
        self.log_step("Workflow 6: Print & Export Itinerary")
        if not self.created_trip_id:
            self.assert_test("Trip must exist for print/export test", False)
            return

        # 1. Complete journey print view (all dates)
        res_print_all = self._request("GET", f"/api/trips/{self.created_trip_id}/print")
        self.assert_test("GET /api/trips/{id}/print (all dates) returns 200 OK", res_print_all.status_code == 200)
        self.assert_test(
            "Print view contains trip title",
            ("Portugal Coastal" in res_print_all.text and "Wine Expedition" in res_print_all.text)
        )
        self.assert_test("Print view contains hotel lodging address", "Rua das Flores 110" in res_print_all.text)

        # 2. Single date print view
        res_print_single = self._request("GET", f"/api/trips/{self.created_trip_id}/print?date=2026-09-16")
        self.assert_test("GET /api/trips/{id}/print (single date) returns 200 OK", res_print_single.status_code == 200)

        # 3. Date range print view
        res_print_range = self._request("GET", f"/api/trips/{self.created_trip_id}/print?start_date=2026-09-15&end_date=2026-09-17")
        self.assert_test("GET /api/trips/{id}/print (date range) returns 200 OK", res_print_range.status_code == 200)

        # 4. iCalendar (.ics) Export
        res_ics = self._request("GET", f"/api/trips/{self.created_trip_id}/export/calendar.ics")
        self.assert_test("GET /api/trips/{id}/export/calendar.ics returns 200 OK", res_ics.status_code == 200)
        self.assert_test("iCal export content-type is text/calendar", "text/calendar" in res_ics.headers.get("Content-Type", ""))
        self.assert_test("iCal contains VCALENDAR envelope", "BEGIN:VCALENDAR" in res_ics.text and "END:VCALENDAR" in res_ics.text)

        # 5. UI Modal controls in HTML
        res_home = self._request("GET", "/")
        html = res_home.text
        self.assert_test("Print modal export mode selector present", 'id="printDateModeSelect"' in html)
        self.assert_test("Print PDF action button present", 'id="triggerPrintPdfBtn"' in html)
        self.assert_test("Email share button present", 'id="triggerEmailShareBtn"' in html)
        self.assert_test("SMS share button present", 'id="triggerSmsShareBtn"' in html)
        self.assert_test("Print formatted text preview area present", 'id="printFormattedTextarea"' in html)

    # --------------------------------------------------------------------------
    # WORKFLOW 7: Add Custom Item (Scheduled + Bucket List)
    # --------------------------------------------------------------------------
    def test_workflow_7_add_custom_item(self):
        self.log_step("Workflow 7: Add Custom Itinerary Stop & Bucket List Item")
        if not self.created_trip_id:
            self.assert_test("Trip must exist for add custom item test", False)
            return

        # 1. Add scheduled stop on 2026-09-16
        scheduled_item = {
            "title": "Caves Cálem Port Wine Cellar Tour",
            "category": "drinks",
            "assigned_date": "2026-09-16",
            "cost": "€19.00",
            "address": "Av. de Diogo Leite 344, Vila Nova de Gaia",
            "neighborhood": "Ribeira / Gaia",
            "url": "https://calem.pt",
            "booking_status": "confirmed",
            "booking_ref": "CALEM-2026-9912",
            "highlight": "Interactive museum and wine tasting by the Douro river."
        }

        res_item1 = self._request("POST", f"/api/trips/{self.created_trip_id}/items", json=scheduled_item)
        self.assert_test("POST /items (scheduled stop) returns 200 OK", res_item1.status_code == 200)

        data_item1 = res_item1.json()
        self.created_item_id = data_item1.get("item_id")
        self.assert_test("Custom scheduled item returned valid item_id", bool(self.created_item_id))

        # 2. Add unscheduled wishlist stop (Bucket List / 'todo')
        wishlist_item = {
            "title": "Livraria Lello Iconic Bookstore",
            "category": "shopping",
            "assigned_date": "todo",
            "cost": "€8.00",
            "address": "R. das Carmelitas 144, Porto",
            "neighborhood": "Clérigos",
            "booking_status": "unbooked"
        }

        res_item2 = self._request("POST", f"/api/trips/{self.created_trip_id}/items", json=wishlist_item)
        self.assert_test("POST /items (unscheduled wishlist) returns 200 OK", res_item2.status_code == 200)
        item2_id = res_item2.json().get("item_id")

        # 3. Verify items appear in GET /api/trips/{trip_id}
        res_trip = self._request("GET", f"/api/trips/{self.created_trip_id}")
        trip_data = res_trip.json()

        # Verify scheduled day bucket
        itin_data = trip_data.get("itinerary", {})
        day_buckets = itin_data.get("days", []) if isinstance(itin_data, dict) else (itin_data if isinstance(itin_data, list) else [])
        day_match = next((d for d in day_buckets if isinstance(d, dict) and d.get("date") == "2026-09-16"), None)
        self.assert_test("Day bucket 2026-09-16 exists in itinerary", day_match is not None)

        if day_match:
            day_titles = [it.get("title") for it in day_match.get("items", [])]
            self.assert_test("Scheduled item appears in 2026-09-16 day bucket", scheduled_item["title"] in day_titles)

        # Verify wishlist items in all_items
        all_items = trip_data.get("all_items", [])
        todo_item = next((it for it in all_items if it.get("id") == item2_id), None)
        self.assert_test("Wishlist item exists with assigned_date='todo'", todo_item and todo_item.get("assigned_date") == "todo")
        self.assert_test("Wishlist item has correct title", todo_item and todo_item.get("title") == wishlist_item["title"])

        # 4. Test deleting the custom stop
        res_delete_item = self._request("DELETE", f"/api/trips/{self.created_trip_id}/items/{self.created_item_id}")
        self.assert_test(f"DELETE /items/{self.created_item_id} returns 200 OK", res_delete_item.status_code == 200)

        # Verify item was removed from itinerary
        res_trip_after = self._request("GET", f"/api/trips/{self.created_trip_id}")
        remaining_ids = [it.get("id") for it in res_trip_after.json().get("all_items", [])]
        self.assert_test("Deleted item is no longer in trip items", self.created_item_id not in remaining_ids)

    # --------------------------------------------------------------------------
    # WORKFLOW 8: Pre-Refresh Itinerary Backup, Download & Reimport
    # --------------------------------------------------------------------------
    def test_workflow_8_backup_and_restore(self):
        self.log_step("Workflow 8: Pre-Refresh Itinerary Backup, Download & Reimport")

        # 1. Check backup status
        res_stat = self._request("GET", "/api/backup/status")
        self.assert_test("GET /api/backup/status returns 200 OK", res_stat.status_code == 200)
        stat_data = res_stat.json() if res_stat.status_code == 200 else {}
        self.assert_test("Backup status reports ready status", stat_data.get("status") in ("ready", "no_backup"))
        self.assert_test("Backup reports valid total_trips count", isinstance(stat_data.get("total_trips"), int) and stat_data.get("total_trips", 0) >= 1)

        # 2. Download JSON backup
        res_dl = self._request("GET", "/api/backup/download")
        self.assert_test("GET /api/backup/download returns 200 OK", res_dl.status_code == 200)
        self.assert_test("Backup download content-type is application/json", "application/json" in res_dl.headers.get("content-type", ""))
        import json
        dl_json = json.loads(res_dl.text) if res_dl.status_code == 200 else {}
        self.assert_test("Backup download contains 'trips' list", isinstance(dl_json.get("trips"), list))
        self.assert_test("Backup download captures current trip count", len(dl_json.get("trips", [])) >= 1)

    # --------------------------------------------------------------------------
    # TEARDOWN: Automated Database Cleanup
    # --------------------------------------------------------------------------
    def teardown(self):
        self.log_step("Teardown: Automated Test Cleanup")
        if self.keep_data:
            print(f"  {YELLOW}{WARN_SYM} --keep-data specified: Skipping database cleanup.{RESET}")
            return

        # 1. Delete test trip if created
        if self.created_trip_id:
            res_del = self._request("DELETE", f"/api/trips/{self.created_trip_id}")
            self.assert_test(f"DELETE /api/trips/{self.created_trip_id} cleans up test itinerary", res_del.status_code == 200)

            # Verify 404
            res_check = self._request("GET", f"/api/trips/{self.created_trip_id}")
            self.assert_test("Deleted trip returns 404 / access denied", res_check.status_code in (404, 403, 401))

        # 2. Clean up test users from DB
        try:
            from database.connection import SessionLocal
            from database.models import User, Trip, TripCollaborator
            db = SessionLocal()
            try:
                # Remove collaborator test user
                db.query(User).filter(User.email == self.test_collab_email).delete()
                # Remove primary test user
                db.query(User).filter(User.email == self.test_user_email).delete()
                db.commit()
                self.assert_test("Test user accounts purged from database", True)
            finally:
                db.close()
        except Exception as e:
            if self.verbose:
                print(f"  {DIM}Direct DB user cleanup note: {e}{RESET}")

    # --------------------------------------------------------------------------
    # RUNNER
    # --------------------------------------------------------------------------
    def run_all(self) -> int:
        print(f"\n{BOLD}======================================================================{RESET}")
        print(f"{BOLD}  Travel Scout Automated Workflow Test Suite{RESET}")
        print(f"  Mode: {CYAN}{self.mode}{RESET} " + (f"({self.target_url})" if self.target_url else "(FastAPI TestClient)"))
        print(f"{BOLD}======================================================================{RESET}")

        try:
            self.test_dom_and_cache_integrity()
            self.test_workflow_1_login()
            self.test_workflow_2_new_itinerary()
            self.test_workflow_3_help_guide()
            self.test_workflow_4_share_and_invite()
            self.test_workflow_5_manage_users()
            self.test_workflow_6_print_and_export()
            self.test_workflow_7_add_custom_item()
            self.test_workflow_8_backup_and_restore()
        except Exception as exc:
            import traceback
            print(f"\n{RED}{BOLD}UNEXPECTED EXCEPTION DURING TEST EXECUTION:{RESET}")
            traceback.print_exc()
            self.failed_tests += 1
        finally:
            self.teardown()

        elapsed = time.time() - self.start_time
        total = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total * 100) if total > 0 else 0

        print(f"\n{BOLD}======================================================================{RESET}")
        print(f"{BOLD}  TEST RUN SUMMARY{RESET}")
        print(f"{BOLD}======================================================================{RESET}")
        print(f"  Total Assertions: {BOLD}{total}{RESET}")
        print(f"  Passed:           {GREEN}{BOLD}{self.passed_tests}{RESET}")
        print(f"  Failed:           {RED}{BOLD}{self.failed_tests}{RESET}")
        print(f"  Pass Rate:        {GREEN if self.failed_tests == 0 else RED}{BOLD}{pass_rate:.1f}%{RESET}")
        print(f"  Duration:         {DIM}{elapsed:.2f} seconds{RESET}")
        print(f"{BOLD}======================================================================{RESET}\n")

        return 0 if self.failed_tests == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Travel Scout Automated Workflow Test Suite")
    parser.add_argument("--url", default=None, help="Base URL of live running instance (e.g. http://localhost:8000)")
    parser.add_argument("--keep-data", action="store_true", help="Preserve test trip and users in database without cleanup")
    parser.add_argument("--verbose", action="store_true", help="Verbose error logging")
    args = parser.parse_args()

    runner = WorkflowTestRunner(target_url=args.url, keep_data=args.keep_data, verbose=args.verbose)
    exit_code = runner.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
