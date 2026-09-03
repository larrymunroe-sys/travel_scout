# Travel Scout: Complete User Guide & How-To Manual

Welcome to **Travel Scout**, a standalone, multi-city collaborative travel platform built to design, customize, and coordinate complex multi-destination itineraries with friends and co-travelers.

This comprehensive guide covers every feature of the platform, from your first login to multi-hotel date-matched routing, autonomous event discovery, and interactive mapping.

---

## 📑 Table of Contents

1. [Quick Start & Access](#1-quick-start--access)
2. [User Identity & Account Management](#2-user-identity--account-management)
3. [Trip Management (Create, Edit, Switch)](#3-trip-management-create-edit-switch)
4. [Cities & Accommodations Manager](#4-cities--accommodations-manager)
5. [Collaborative Itinerary Planning](#5-collaborative-itinerary-planning)
6. [Interactive Links & Navigation](#6-interactive-links--navigation)
7. [Live Autonomous Cultural Scout & Discovery](#7-live-autonomous-cultural-scout--discovery)
8. [Interactive Multi-City Route Map](#8-interactive-multi-city-route-map)
9. [Sharing & Multi-User Collaboration](#9-sharing--multi-user-collaboration)
10. [Frequently Asked Questions (FAQ)](#10-frequently-asked-questions-faq)

---

## 1. Quick Start & Access

### Accessing the Dashboard
- Open your browser and navigate to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**
- The platform loads instantly in an obsidian dark-matter interface optimized for desktop and tablet screens.

### Starting and Stopping the Server
The application runs locally on your machine with zero cloud dependencies:
```bash
# Navigate to the project directory
cd C:\Users\larry\Documents\A1\travel-scout

# Launch the web dashboard on port 8000
python main.py web

# Or run an autonomous multi-city background scan via CLI
python main.py scan
```

---

## 2. User Identity & Account Management

Every action on Travel Scout—adding venues, creating trips, or scheduling dates—is tied to an active user profile for transparent team co-planning.

### Default Owner Profile
- Upon launching, you are logged in as **Larry Munroe (Owner)** with a sky-blue avatar badge in the top right.

### One-Click User Switcher
To simulate collaborative planning with companions or switch to another traveler's view:
1. Locate the **user profile menu** in the top right corner of the header.
2. Click the **"Switch User..."** dropdown.
3. Select an existing companion:
   - **Sarah Chen** (Co-Editor, magenta badge)
   - **David Ross** (Collaborator, amber badge)
4. The page instantly reloads under that user's identity. Any cards you add will now feature that user's avatar attribution.

### Adding New Traveler Accounts
1. In the **"Switch User..."** dropdown, click **`+ Add New Collaborator Account`**.
2. Enter the new traveler's name (e.g., *Alex Rivera*) and email (e.g., *alex@gmail.com*).
3. The platform creates the account, assigns a unique avatar color, and logs in as that user.

---

## 3. Trip Management (Create, Edit, Switch)

Travel Scout allows you to manage multiple independent trips simultaneously.

### ✏️ Customizing the Current Trip Name & Purpose
1. In the header next to the title, click the **`✏️ Customize`** button.
2. In the modal dialog:
   - **Trip Title:** Update the name (e.g., *Portugal Grand Cultural Expedition* or *Spring Break European Tour*).
   - **Description / Purpose:** Add notes about the trip theme (e.g., *Curated fado, port wine lodges, and medieval citadels*).
3. Click **"Save Changes"**. The header and subtitle update immediately in the database.

### ➕ Starting a Fresh Custom Trip from Scratch
To plan an entirely new vacation (e.g., Japan, Italy, California):
1. In the header, click the **`➕ New Trip`** button.
2. Fill out the **Start a New Custom Journey** wizard:
   - **Trip Name:** e.g., *Japan Cherry Blossom & Culinary Tour*
   - **First Destination City:** e.g., *Tokyo*
   - **Start Date & End Date:** e.g., `2026-04-01` to `2026-04-06`
   - **Starting Hotel Name:** e.g., *Hotel Gracery Shinjuku*
3. Click **"Create Journey"**.
4. The platform will:
   - Initialize the trip with you as the **Owner**.
   - Create the first city segment and stay location.
   - Automatically generate day timeline buckets for every single calendar day of the trip.
   - Switch your active dashboard directly to the new journey.

### 🔄 Multi-Trip Switcher Dropdown
- Located directly in the top header, the **Trip Switcher dropdown** lists all saved trips along with their city count.
- Click any trip in the dropdown to switch your view instantly between different itineraries.

---

## 4. Cities & Accommodations Manager

Click the **`🏙️ Cities & Stays`** tab in the main navigation bar to manage where you are going and where you are staying.

### Adding a Destination City
1. Click the **`➕ Add Destination City`** button.
2. Enter:
   - **City Name:** e.g., *Sintra*, *Kyoto*, *Coimbra*
   - **Country:** e.g., *Portugal*, *Japan*
   - **Arrival Date & Departure Date:** The date range you will be in that city.
   - **Hotel / Accommodation Name:** Primary hotel or Airbnb name.
   - **Hotel Address:** Street address or neighborhood for geocoding.
3. Click **"Save City & Accommodation"**.
4. The city card is created with its order index, and its dates are automatically added to the master timeline.

### Deleting a City
- Click the **`🗑️ Delete City`** button on any city card.
- Confirm the dialog. The city, its associated hotels, and its timeline segments are safely removed, and remaining cities automatically re-index their order.

### 🏨 Multiple Hotels per City (Segmented by Date)
> [!IMPORTANT]
> If you move accommodations midway through your stay in a city (e.g., staying near the historic center for 2 nights, then moving to a beach resort for 2 nights), Travel Scout supports date-matched stays!

1. On the city card, click **`🏨 Add Hotel by Date`**.
2. Enter:
   - **Hotel / Stay Name:** e.g., *Bairro Alto Hotel* or *Ritz Four Seasons*
   - **Address:** Street address
   - **Check-in Date & Check-out Date:** The specific subset of dates you will be at this hotel.
   - **Notes (Optional):** e.g., *Boutique hotel with rooftop terrace overlooking the river.*
3. Click **"Add Accommodation"**.

**How Date-Matching Works:**
- When an itinerary stop is scheduled for **May 11**, the system checks which hotel is active on May 11 and calculates walking distance from **Hotel #1**.
- If another stop is scheduled for **May 13**, the system detects you have moved to **Hotel #2** and automatically recalculates distances and transit tips from **Hotel #2**!

---

## 5. Collaborative Itinerary Planning

Click the **`📅 Collaborative Itinerary`** tab to view and build your day-by-day plan.

### Unified Timeline vs. City-Specific View
- Use the **`🌐 Filter by City`** dropdown at the top of the itinerary:
  - **🌐 All Cities (Unified Timeline):** View your entire journey chronologically from Day 1 to the final day.
  - **Specific City (e.g. Lisbon, Porto):** Filters the view to only show stops and to-dos for that selected city.

### 📋 Bucket List / Unscheduled To-Do Grid
- At the top of the tab is the **Unscheduled To-Do Wishlist**.
- Items found during web scouting or added manually start here until you decide which day to visit them.
- A badge shows how many items are waiting to be scheduled.

### Scheduling Stops to Specific Days
- Every itinerary card features an inline date selector dropdown:
  - Select any calendar date (e.g. `📅 2027-05-11`) to move the card directly to that day's scheduled block.
  - Select `📋 Bucket List` to move a scheduled stop back to the unscheduled wishlist.
- All distance, walk time, and transit calculations update dynamically based on the hotel active on that date!

### Deleting Itinerary Stops
- Click the red **`&times;` (trash)** icon in the lower right corner of any card to remove it from your itinerary.

### Author Attribution Badges
- In the footer of each card, look for the **Author Tag** (e.g., 👤 `LM Larry` or 👤 `SC Sarah`).
- Hovering over the badge shows the full name and email of the traveler who contributed that venue.

---

## 6. Interactive Links & Navigation

Every item card across the application is equipped with direct, interactive external links:

| Link Element | Action & Destination |
|---|---|
| **Clickable Title Link (`↗`)** | Clicking the card's title opens the official website or primary source article in a new browser tab. |
| **`🌐 [Source / Website] ↗`** | Blue pill button that takes you to the venue's official homepage, booking page, or source review (e.g., *Lonely Planet*, *TimeOut*, *Reddit*). |
| **`📍 Maps & Directions ↗`** | Amber pill button that launches Google Maps directly with the venue's GPS coordinates or address for instant driving, walking, or public transit directions. |

---

## 7. Live Autonomous Cultural Scout & Discovery

Click the **`🔍 Scout & Discover`** tab to find hidden gems, upcoming festivals, concerts, and dining recommendations.

### Targeted Search Parameters
1. **Target Destination City:** Select which city in your journey you want to search for.
2. **Search Channel:**
   - **🌐 All Channels Combined:** Comprehensive multi-source scan.
   - **📖 Curated Travel Guides:** High-reputation editorial reviews (Lonely Planet, Michelin, Conde Nast Traveler).
   - **✍️ Local Blogs & Food Critics:** Insider neighborhood posts and food critics.
   - **💬 Reddit Communities:** Real traveler advice and hidden gem threads (`r/lisboa`, `r/porto`, etc.).
   - **📱 TikTok & Viral Video Finds:** Trending food spots and viral viewpoints.
3. **Category Filter:** Filter by Dining, Wine & Port Cellars, Hidden Gems, Live Music & Fado, Historic Citadels, or Outdoors.
4. **Search Query:** Type any custom keyword (e.g. *fado dinner with guitar*, *best pastel de nata*, *craft beer bar*, *contemporary art gallery*).
5. Click **`🔍 Run City Scout`**.

### Quick Suggestion Chips
- Click any of the pre-configured suggestion chips at the top of the search form (e.g., `🍷 Porto Wine Lodges`, `🎶 Lisbon Fado Nights`, `🏰 Bragança Medieval Citadel`, `🍽️ Sintra Pastries`) to run an instant search without typing.

### Adding Scout Results to Your Itinerary
- Each returned card displays the title, platform badge, summary highlight, direct links, and a **`➕ Add to To-Do List`** button.
- Clicking **"Add to To-Do List"** saves the item into your database under the active user's name and places it into the **To-Do Bucket List**.

### ⚡ Autonomous Multi-City Daily Scanner
- Click the glowing gradient button **`⚡ Run Daily Autonomous Scan (All Trip Cities)`**.
- The platform executes a background sweep across every city in your itinerary simultaneously, analyzing cultural calendars, Reddit discussions, and local blogs.
- Any newly discovered events that do not already exist in your itinerary are automatically imported into your To-Do wishlist!

---

## 8. Interactive Multi-City Route Map

Click the **`🗺️ Interactive Map`** tab for a visual overview of your journey.

### Map Controls
- **City Jump Dropdown (`mapCityJump`):**
  - Select **`🌍 Whole Journey Overview`** to zoom out and see all destination cities and pins across the entire country.
  - Select **`Lisbon`**, **`Porto`**, or **`Bragança`** to fly smoothly to that specific city.

### Marker Types
- **🏨 Blue Hotel Pins:** Mark your accommodation locations.
  - Clicking a hotel pin reveals its name, address, active dates, and a **`📍 Google Maps Directions ↗`** link.
- **📍 Red Venue Pins:** Mark cultural venues, restaurants, viewpoints, and events.
  - Clicking a venue pin displays its title, neighborhood, cost badge, author attribution, a **`🌐 Website ↗`** link, and a **`📍 Directions ↗`** button.

### Interactive Sidebar Drawer
- The left sidebar lists all stops plotted on the map.
- Clicking any item in the sidebar immediately centers and zooms the map to that venue's coordinates and opens its popup.

---

## 9. Sharing & Multi-User Collaboration

### Inviting Co-Travelers
1. Click the **`👥 Share & Invite`** button in the header.
2. In the modal:
   - Enter your co-traveler's **Email** (e.g. `sarah.chen@gmail.com`).
   - Enter their **Name** (e.g. `Sarah Chen`).
   - Choose their **Permission Role**:
     - **Editor:** Can add, edit, schedule, and delete stops, cities, and hotels.
     - **Viewer:** Read-only access to view the itinerary and map.
3. Click **"Send Invitation"**.
4. The new collaborator is registered and their avatar circle appears in the header's collaborator stack.

---

## 10. Frequently Asked Questions (FAQ)

#### Q: How do transit calculations work if I change hotels?
**A:** Travel Scout compares the date assigned to an itinerary item against the check-in and check-out dates of all hotels in that city. If you move from Hotel A to Hotel B on May 12, an event scheduled on May 13 will automatically calculate distance and walking time from Hotel B.

#### Q: Can I use this for trips outside Portugal?
**A:** Absolutely! Click **`➕ New Trip`** or **`➕ Add Destination City`** and enter any city worldwide (e.g. *Tokyo, Japan*, *Florence, Italy*, *Washington D.C.*). OpenStreetMap Nominatim coordinates will geocode the destination automatically.

#### Q: Where is my data saved?
**A:** All trips, cities, hotels, itinerary items, and user accounts are persisted in a local SQLite database (`travel_scout.db`) located inside `C:\Users\larry\Documents\A1\travel-scout`.

#### Q: Can two people edit at the same time?
**A:** Yes. Multiple users can log in via their respective browsers or devices pointing to your local IP / domain, and changes are synced directly to the SQLite backend.

#### Q: What if a venue doesn't have an official website?
**A:** When an item does not have a dedicated homepage URL, the title link and the **`🔍 Web Info ↗`** pill automatically generate a Google search query for the venue name and city, and the **`📍 Maps & Directions ↗`** pill provides direct Google Maps geocoding.
