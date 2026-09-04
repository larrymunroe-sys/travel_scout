# Travel Scout: Complete User Guide & How-To Manual

Welcome to **Travel Scout**, a standalone, multi-city collaborative travel platform built to design, customize, and coordinate complex multi-destination itineraries with friends and co-travelers.

This comprehensive guide covers every feature of the platform, from your first login to multi-hotel date-matched routing, live music and concert discovery across top ticketing platforms, and interactive mapping.

---

## 📑 Table of Contents

1. [Quick Start & Access](#1-quick-start--access)
2. [User Identity, Google OAuth & Account Management](#2-user-identity-google-oauth--account-management)
3. [Trip Management (Create, Customize, Switch, Delete)](#3-trip-management-create-customize-switch-delete)
4. [Cities & Accommodations Manager](#4-cities--accommodations-manager)
5. [Collaborative Itinerary Planning](#5-collaborative-itinerary-planning)
6. [Interactive Links & Navigation](#6-interactive-links--navigation)
7. [Explore & Discover Cultural Hub](#7-explore--discover-cultural-hub)
8. [Live Web Scout & Live Music Search](#8-live-web-scout--live-music-search)
9. [Interactive Multi-City Route Map](#9-interactive-multi-city-route-map)
10. [Sharing & Multi-User Collaboration](#10-sharing--multi-user-collaboration)
11. [Printing, PDF Export & Email/SMS Sharing](#11-printing-pdf-export--emailsms-sharing)
12. [Frequently Asked Questions (FAQ)](#12-frequently-asked-questions-faq)
13. [Security Architecture & Hardening](#13-security-architecture--hardening)

---

## 1. Quick Start & Access

### Accessing the Dashboard Locally
- Open your web browser and navigate to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**
- The platform loads in an obsidian dark-matter interface optimized for desktop, tablet, and mobile screens.

### Starting and Stopping the Server
```bash
# Navigate to the project directory
cd C:\Users\larry\Documents\A1\travel-scout

# Launch the local web server on port 8000
python main.py web

# Or run an autonomous multi-city background scan via CLI
python main.py scan
```

### Accessing the Production Deployment on Render
- Production URL: **[https://travel-scout.onrender.com](https://travel-scout.onrender.com)**
- Auto-deploys from the GitHub `main` branch. To trigger manual rebuilds or cache purges, visit [dashboard.render.com](https://dashboard.render.com) and select **"Manual Deploy" -> "Clear build cache & deploy"**.

---

## 2. User Identity, Google OAuth & Account Management

Every action on Travel Scout—adding venues, creating trips, or scheduling dates—is tied to an active traveler profile for transparent team co-planning.

### Logged-In User Display
- The header prominently displays the active traveler profile in the top-right toolbar:
  - **User Avatar Badge:** Shows the traveler's initial and unique color badge.
  - **User Name & Role:** (e.g. `Larry Munroe` &bull; `ACTIVE`).
  - **Gmail Account Address:** The active Google/Gmail address is shown directly below the name (e.g., `✉️ larrymunroe@gmail.com`).

### 🔑 Google OAuth 2.0 Sign-In
- Click **`🔑 Sign In`** in the header or in the welcome banner.
- **One-Click Google Authentication:** When configured with `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, clicking **"Sign in with Google"** redirects to Google's secure OAuth consent screen and returns you authenticated with your real profile image and verified email.
- **Quick Team Select (Demo / Offline):** One-click buttons to quickly switch between team profiles (`Larry Munroe`, `Sarah Chen`, `David Ross`).
- **Custom Account Creation:** Enter any traveler name and email address to create a brand-new profile instantly.

### 🚪 Log Off
- Located directly in the user profile menu.
- Clicking **"Log Off"** immediately clears session cookies and local storage, returning the app to secure guest mode.

### 🗑️ Managing & Deleting Users
- Click the user profile dropdown and select **"Manage Users / Delete Profiles"**.
- View all registered accounts on the server (requires authentication).
- **Self-Deletion Security Policy:** Travelers can permanently delete their own account and all associated itineraries. To prevent account destruction by third parties, deleting someone else's account is strictly rejected with `HTTP 403 Forbidden`.
- **Demo Accounts Cleanup:** Pre-seeded demo profiles (Larry Munroe and Sarah Chen) can be purged via the **"Purge Demo Accounts"** action by authorized accounts to deliver a clean workspace for production teams.

### 🔒 User Privacy, Cryptographic Sessions & Data Isolation
- **Private Workspaces:** Trips you create are owned by you. They remain invisible to other users unless you explicitly invite them.
- **Strict Access Control:** Unauthorized attempts to access an unshared trip ID return `HTTP 403 Forbidden`.
- **HMAC-SHA256 Signed Sessions:** Authentication uses cryptographically signed session tokens (`travel_scout_session`) verified on every request. Tampered or forged tokens are automatically rejected.
- **Hardened Cookies:** Session cookies are set with `HttpOnly`, `SameSite: Lax`, and `Secure` on HTTPS, preventing credential theft via client-side JavaScript or cross-site request hijacking.
- **OAuth 2.0 CSRF Protection:** Google OAuth login flows generate and enforce cryptographically random `state` tokens to prevent OAuth login CSRF attacks.

---

## 3. Trip Management (Create, Customize, Switch, Delete)

Manage multiple independent itineraries simultaneously.

### ✏️ Customizing Trip Name & Purpose
1. Click the **`✏️ Customize`** button in the header next to the trip title.
2. In the modal:
   - **Trip Title:** Edit the itinerary title (e.g., *Portugal Grand Cultural Expedition*).
   - **Description / Purpose:** Add notes about the trip theme or goals.
3. Click **"Save Changes"** to update immediately across the app.

### ➕ Starting a Fresh Custom Trip
1. Click the **`➕ New Trip`** button in the header.
2. Fill out the **Start a New Custom Journey** wizard:
   - **Trip Name:** e.g., *Japan Cherry Blossom & Culinary Tour*
   - **First Destination City:** e.g., *Tokyo*
   - **Start Date & End Date:** Date range for the first leg.
   - **Starting Hotel Name:** Primary accommodation.
3. Click **"Create Journey"**. The platform creates your itinerary, sets you as **Owner**, populates calendar day buckets, and switches directly to the new trip.

### 🔄 Switching Trips
- Use the **Trip Switcher dropdown** in the header to switch instantly between all itineraries you own or collaborate on.

### 🗑️ Deleting a Trip (Permanent Removal)
You can permanently delete any trip you own using either of two methods:
1. **Header Button:** Click the red **`🗑️ Delete Trip`** button in the top navigation bar.
2. **Customize Modal:** Click **`✏️ Customize`** and click the red **`🗑️ Delete Trip`** button at the bottom of the dialog.
3. **Confirmation:** Confirm the prompt. The system permanently deletes:
   - The trip record itself
   - All associated city segments
   - All hotel and accommodation records
   - All scheduled itinerary stops and unassigned bucket-list items
   - All collaborator sharing records
4. **No Ghost Trips:** If you delete your last remaining trip, the platform will **not** auto-resurrect starter trips. Instead, it cleanly renders an empty state with a **"➕ Start a New Trip"** button.

---

## 4. Cities & Accommodations Manager

Click the **`🏙️ Cities & Stays`** tab in the main navigation bar.

### Adding a Destination City
1. Click **`➕ Add Destination City`**.
2. Enter the city name, country, arrival/departure dates, hotel name, and address.
3. The platform geocodes the coordinates via OpenStreetMap Nominatim and creates day buckets for your timeline.

### 🏨 Multiple Hotels per City (Date-Matched Stays)
If you move accommodations during your stay in a city:
1. Click **`🏨 Add Hotel by Date`** on the city card.
2. Specify the hotel name, street address, and exact check-in/check-out dates.
3. **Dynamic Distance Calculations:** Stops scheduled on that date will automatically measure walking distances and transit directions from that specific hotel!

---

## 5. Collaborative Itinerary Planning

Click the **`📅 Collaborative Itinerary`** tab.

### Unified Timeline vs. City-Specific View
- Use the **`🌐 Filter by City`** dropdown at the top to toggle between the complete journey timeline or a single city's stops.

### 📋 Unscheduled To-Do Wishlist
- Items discovered during web scouting or added manually begin in the **To-Do Bucket List** at the top until scheduled.
- Use the date dropdown on any card to move it directly to a specific calendar day.

### 📝 Personal Notes on Cards
- Click **`+ Add Personal Note`** at the bottom of any card.
- Record custom notes, table reservation numbers, or personal recommendations.
- Notes display the contributor's name, email, and exact timestamp, and appear in printouts and exports.

---

## 6. Interactive Links & Navigation

Every venue card across the application features interactive navigation:
- **Clickable Title Link (`↗`):** Opens the venue's official website or source article.
- **`🌐 [Source / Platform] ↗`:** Direct link to the source platform (Eventbrite, Songkick, DICE, Ticketmaster, Reddit, TimeOut, etc.).
- **`📍 Maps & Directions ↗`:** Launches Google Maps with accurate GPS coordinates for instant driving, walking, or transit directions.

---

## 7. Explore & Discover Cultural Hub

Click the **`🧭 Explore & Discover`** tab to browse curated recommendations, filter by theme, or search across activities.

### Category Filter Tabs
Instantly filter cards by clicking the category pills at the top:
- 🍽️ **Iconic Dining & Taverns (`dining`):** Traditional tascas, regional culinary staples, seafood houses, food markets, and cafes.
- 🍷 **Wine Cellars & Lodges (`wine`):** Port wine cellars, quintas, wine tasting rooms, and vineyard estates.
- 🏰 **Castles & Historic Sights (`historic`):** Castles, citadels, cathedrals, monasteries, palaces, and UNESCO monuments.
- 🎶 **Live Music & Concerts (`music`):** Traditional Fado houses, live acoustic gigs, concert halls, jazz clubs, and music venues.
- 🌊 **Miradouros & Trails (`outdoors`):** Scenic hilltop viewpoints (*miradouros*), riverfront walks, hiking trails, and parks.
- 💎 **Local Neighborhood Gems (`gems`):** Hidden alleyways, artisan workshops, indie cafes, and local neighborhood favorites.
- 🎟️ **Free Admission (`free`):** Zero-cost attractions, public gardens, scenic walks, and free museum admission hours.

### Interactive Card Badges
Every card in Explore & Discover features interactive clickable filter tags:
- **Category Badge:** Click to filter down to that category.
- **City Badge:** Click to show only recommendations in that destination.
- **Neighborhood Badge:** Click to focus on that specific district (e.g. *Alfama*, *Baixa*, *Ribeira*).

---

## 8. Live Web Scout & Live Music Search

Click the **`🔍 Scout & Discover`** tab or click **Scout City 🚀** to scan live web sources for real-time recommendations and concert dates.

### Live Web Channels & Discovery Sources
Travel Scout features multi-channel web scouting across culinary, nightlife, and cultural platforms:
- **`🍺 Craft Breweries & Beer Tasting Rooms`**: Local microbreweries, taprooms, alehouses, and tasting rooms.
- **`🍸 Craft Cocktail Bars & Secret Speakeasies`**: Hidden lounges, mixology bars, and secret entrance speakeasies.
- **`⭐ Michelin Guide & Fine Dining`**: Michelin-starred venues, Bib Gourmand awards, and chef's tasting menus.
- **`🍴 Eater.com Heatmaps & Guides`**: Essential 38 heatmaps, critic maps, and newly opened hotspots.
- **`⭐ Yelp Top Reviews & Ratings`**: Highly reviewed neighborhood dining, bars, and dessert spots.
- **`📰 City Magazines & Local Press`**: Top editorial roundups from *TimeOut*, city lifestyle monthlies, and local food critics.
- **`🎵 Live Music & Tickets`**: Actively scans:
  - 🎟️ **Eventbrite** (`eventbrite.com`)
  - 🎸 **Songkick** (`songkick.com`)
  - 🎲 **DICE** (`dice.fm` / `dice.com`)
  - 🎫 **Ticketmaster** (`ticketmaster.com`)
- **`🏛️ Music Venues & Concert Halls`**: Scans iconic music clubs, concert halls, jazz bars, and performance stages.
- **`📖 Travel Guides`**: Editorial insights from *Lonely Planet*, *TimeOut*, and *Fodor's*.
- **`💬 Reddit Communities`**: Insider threads, hidden gems, and traveler advice.
- **`🎬 TikTok`**: Viral spots, hidden viewpoints, and video recommendations.

### ⚡ Autonomous Multi-City Daily Scanner
- Click **`⚡ Run Daily Autonomous Scan (All Trip Cities)`**.
- The engine runs a background sweep across all itinerary cities, checking breweries, speakeasies, Michelin stars, live music tickets, tour dates, and Reddit hidden gems, automatically adding new finds to your To-Do wishlist.

---

## 9. Interactive Multi-City Route Map

Click the **`🗺️ Interactive Map`** tab for a visual overview of your journey.
- **City Jump Dropdown:** Select any city to fly directly to its center, or choose **"🌍 Whole Journey Overview"** to view all stops nationwide.
- **🏨 Blue Hotel Pins:** Mark your accommodation bases with active dates and directions.
- **📍 Red Venue Pins:** Mark cultural venues, restaurants, viewpoints, and concerts.
- **Interactive Sidebar:** Click any venue in the left drawer to center the map on it and open its details popup.

---

## 10. Sharing & Multi-User Collaboration

### Inviting Co-Travelers
1. Click **`👥 Share & Invite`** in the header.
2. Enter your companion's **Name** and **Email**.
3. Choose their role:
   - **Editor:** Can add, edit, schedule, and delete stops, cities, and hotels.
   - **Viewer:** Read-only access to view the unified schedule and map.
4. Click **"Send Invitation"**.

### Managing Collaborators
- View all active collaborators under **Active Contributors**.
- **Owner-Controlled Access:** Only the original **Trip Owner** (`👑 Trip Owner`) can invite collaborators or revoke access. Collaborators can also remove themselves from a shared journey.
- The original **Trip Owner** is protected with a gold crown tag and cannot be removed.

---

## 11. Printing, PDF Export & Email/SMS Sharing

Click **`🖨️ Print / Export`** in the header or on the Itinerary toolbar.

### Output Scope
- **🌐 All Dates (Complete Journey):** Full multi-city itinerary.
- **📅 Single Date:** Focus on one day's stops and hotel base.
- **📆 Custom Date Range:** Output a multi-day weekend leg or city stopover.
- **Bucket List Toggle:** Include or exclude unscheduled wishlist items.

### Formats & Actions
1. **🖨️ Print / Save as PDF:** Generates a high-contrast, ink-friendly view optimized for printing or saving as PDF with personal notes and transit directions.
2. **📄 Open Print View:** Opens the printable layout in a new tab for review.
3. **✉️ Send by Email (`mailto:`):** Pre-formats an email with complete stops, hotel check-ins, addresses, and maps links. Includes a **"📋 Copy Email Text"** button.
4. **💬 Send by Text / SMS (`sms:`):** Compact smartphone-friendly summary for WhatsApp, iMessage, or SMS. Includes a **"📋 Copy SMS Text"** button.

---

## 12. Frequently Asked Questions (FAQ)

#### Q: How do I delete an itinerary I no longer need?
**A:** Click the red **`🗑️ Delete Trip`** button in the header toolbar, or click **`✏️ Customize`** and click **`🗑️ Delete Trip`** at the bottom of the modal. Deleting your last trip leaves your workspace clean without auto-creating unwanted starter itineraries.

#### Q: How do I find live music and concert tickets in my destination?
**A:** Go to the **Scout & Discover** tab, select your city, choose the **"🎵 Live Music & Tickets"** channel, and click **Scout City 🚀**. The engine queries Eventbrite, Songkick, DICE, Ticketmaster, and local concert venues for upcoming tour dates and ticket links.

#### Q: Where is my data saved?
**A:** All data is stored in the local SQLite database (`travel_scout.db`) when running locally, or in the cloud database on Render.

#### Q: Can companions collaborate without logging in with Google?
**A:** Yes! Companions can use the **Switch Account** dropdown or type their name and email into the sign-in modal to immediately collaborate.

---

## 13. Security Architecture & Hardening

Travel Scout incorporates defense-in-depth security controls based on OWASP Top 10 recommendations:

### 🛡️ Core Security Controls
1. **Cryptographic Session Authentication (CWE-287 / CWE-306):**
   - Session identifiers are signed with HMAC-SHA256 (`sign_session_token`, `verify_session_token`).
   - Sessions are bound to `travel_scout_session` cookies configured with `HttpOnly: true`, `SameSite: lax`, and `Secure` (over HTTPS).
   - Unauthenticated header-based identity spoofing is eliminated in production.
2. **Strict Authorization & Object-Level Isolation (BOLA / IDOR - CWE-639):**
   - Multi-hotel accommodations (`/api/trips/{trip_id}/cities/{city_id}/stays`) and stay deletions (`/api/trips/{trip_id}/stays/{stay_id}`) strictly verify parent trip and city segment ownership before executing modifications.
   - User account deletion is restricted to self-deletion.
3. **Cross-Site Scripting (XSS) Defense (CWE-79):**
   - Backend validation in Pydantic models (`AddItemPayload`, `UpdateItemPayload`) enforces strict URL scheme checking, rejecting dangerous schemes like `javascript:`, `data:`, or `vbscript:`.
   - Client-side sanitization (`sanitizeUrl`) neutralizes unvetted URLs before injecting into DOM anchor links.
   - Dynamic search result cards use safe event indexing (`addSearchResultToWishlist(index)`) rather than inline JSON evaluation.
4. **OAuth 2.0 CSRF Protection (CWE-352):**
   - Implements unique, time-bound `state` tokens stored in ephemeral HttpOnly cookies during Google Sign-In, verified upon callback to prevent login CSRF.
5. **OWASP HTTP Security Headers (CWE-1021 / CWE-693):**
   - `X-Frame-Options: SAMEORIGIN` (prevents clickjacking and UI redressing)
   - `X-Content-Type-Options: nosniff` (prevents MIME type confusion)
   - `Referrer-Policy: strict-origin-when-cross-origin` (prevents sensitive path / token leakage)
   - `Permissions-Policy: geolocation=(), microphone=(), camera=()` (disables unused hardware APIs)
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (enforces HTTPS on production)

### ⚙️ Environment Configuration Variables

| Variable | Required | Description | Default |
|---|---|---|---|
| `SESSION_SECRET` | Recommended | Secret key for signing HMAC session tokens. Auto-generated to `.session_secret` if omitted. | Auto-generated |
| `ENVIRONMENT` | Optional | Runtime environment mode (`development`, `production`). In production, dev-login is disabled. | `development` |
| `ENABLE_DEV_LOGIN` | Optional | Set to `true` to force-enable developer instant login in production environments. | `false` |
| `ALLOWED_HOSTS` | Optional | Comma-separated list of permitted host headers to prevent reverse proxy cache poisoning. | `*` |
| `BASE_URL` | Optional | Explicit public reverse proxy URL (e.g. `https://travel-scout.onrender.com`). | Auto-detected |
| `GOOGLE_CLIENT_ID` | Optional | Google OAuth 2.0 client ID from Google Cloud Console. | None |
| `GOOGLE_CLIENT_SECRET` | Optional | Google OAuth 2.0 client secret. | None |
| `DATABASE_URL` | Optional | SQLAlchemy database connection URI (PostgreSQL or SQLite). | `sqlite:///travel_scout.db` |
| `DISABLE_DEMO_SEED` | Optional | Set to `true` to disable seeding default demo trip data on clean database initialization. | `false` |

