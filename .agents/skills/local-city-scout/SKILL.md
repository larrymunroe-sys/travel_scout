---
name: local-city-scout
description: Discovers local newspapers, alternative weeklies, community publications, and event directories for destination cities on the itinerary. Uses web browsing and search to find events (movies, concerts, art exhibits, restaurants, free events, record store performances, outdoor festivals, farmers markets, street fairs) and registers them directly into the Explore & Discover section of Travel Scout.
---

# Local City Cultural Scout Skill

This skill equips the agent to act as a **Hyper-Local Destination City Cultural Scout**. For any destination city on the itinerary, the agent discovers local newspapers, alternative weeklies, indie culture magazines, and event platforms, searches for upcoming events across diverse cultural categories, and automatically ingests them into the **Explore & Discover** wishlist section of Travel Scout.

--------------------------------------------------------------------------------

## Event Scope & Categories Covered

The scout extracts and categorizes happenings including, but not limited to:

1. **Movies & Cinema (`movies`)**: Film festivals, open-air and rooftop cinema, independent repertory theaters, and special screenings.
2. **Live Music & Concerts (`music`)**: Concerts, gig guides, club tours, jazz clubs, and ticketing via Songkick, DICE, Eventbrite, and Ticketmaster.
3. **Record Store Performances (`records`)**: Independent vinyl shops hosting in-store acoustic sets, DJ sessions, and album launch performances.
4. **Art Exhibits & Galleries (`art`)**: Contemporary art gallery openings, museum retrospectives, vernissages, and open studios.
5. **Restaurants & Pop-ups (`dining` / `michelin`)**: Essential new openings, chef pop-ups, Eater heatmaps, and culinary markets.
6. **Free Events & Open Gatherings (`free`)**: Admission-free community happenings, outdoor shows, and public cultural events.
7. **Outdoor Festivals & Street Fairs (`festivals`)**: Neighborhood block parties, street carnivals, summer festas, and outdoor stages.
8. **Farmers Markets & Artisan Pop-ups (`markets`)**: Weekend farmers markets, artisan flea markets, and organic street markets.
9. **Local Press & Alt-Weeklies (`press`)**: Curated "What's On This Week" highlights from local alternative weeklies and city newspapers.

--------------------------------------------------------------------------------

## Multi-Step Execution Procedure

### Step 1: Identify Destination Cities on the Itinerary
**Mandatory Requirement**: The cultural scout agent **MUST ALWAYS** resolve destination cities directly from the active trip's itinerary (`city_segments` table in `travel_scout.db` or the active trip in Travel Scout). Never use hardcoded placeholders or arbitrary cities.
- Determine destination cities on the itinerary using the helper script:
  ```bash
  # Automatically pulls and scouts all destination cities directly from the active itinerary:
  python .agents/skills/local-city-scout/scripts/scout_events.py
  ```
- Or specify a specific destination city from the itinerary:
  ```bash
  python .agents/skills/local-city-scout/scripts/scout_events.py --city "San Diego"
  ```

### Step 2: Uncover Local Newspapers & Media Outlets
For each destination city, identify authentic local publications rather than generic corporate portals:
- **Alternative Weeklies & Indie Press**: e.g., *Mensagem de Lisboa*, *The Portugal News*, *The Village Voice*, *Chicago Reader*, *Austin Chronicle*, *Londonist*, *Le Bonbon*.
- **Official City Cultural Agendas**: e.g., *Agenda Cultural de Lisboa*, *Sortir à Paris*, *Time Out Local*.
- **Specialty Event Sites**: Local ticketing hubs (Eventbrite, DICE, Songkick, Resident Advisor).

### Step 3: Browse Publications & Search Event Feeds
Execute web searches or open publication URLs using browser / web tools to extract upcoming events matching the user's travel window.

Target queries for each category:
- **Movies**: `"{city} open air cinema outdoor movie screenings film festival"`
- **Live Music**: `"{city} live music concerts gigs tickets site:songkick.com OR site:dice.fm"`
- **Record Stores**: `"{city} record store in-store live performance vinyl shop"`
- **Art Exhibits**: `"{city} art gallery openings vernissage contemporary exhibits"`
- **Festivals**: `"{city} outdoor festival street fair block party celebration"`
- **Farmers Markets**: `"{city} farmers market weekend flea market produce market"`
- **Free Events**: `"{city} free events this weekend admission free no cover"`
- **Local Press**: `"{city} alternative weekly newspaper events what's on"`

### Step 4: Extract Structured Event Data
For every discovered event, extract:
- **Title**: Clean name of the event or performance
- **Category**: `movies`, `music`, `records`, `art`, `festivals`, `markets`, `free`, `dining`, `press`
- **Neighborhood**: District or neighborhood (e.g. *Bairro Alto*, *Alfama*, *SoHo*, *Shoreditch*)
- **Coordinates (lat, lon)**: Resolved geographic location for map pins
- **Cost**: Specific ticket price or `"Free Admission"`
- **Is Free**: Flag `true` if admission is free
- **Time/Schedule**: Opening times, dates, or showtimes
- **Highlight**: 1-2 sentence compelling summary of why it's worth attending
- **Source Platform & URL**: Link to the publication, ticket page, or venue website

### Step 5: Ingest into Explore & Discover Wishlist
Save newly discovered events directly into Travel Scout's database with `assigned_date="todo"` so they immediately appear in the **Explore & Discover** tab.

**Via CLI Runner Script**:
```bash
python .agents/skills/local-city-scout/scripts/scout_events.py \
  --city "Lisbon" \
  --country "Portugal" \
  --types "movies,music,records,art,festivals,markets,free"
```

**Via HTTP API Endpoint**:
```http
POST /api/trips/{trip_id}/scout/local-agent
Content-Type: application/json

{
  "city_id": "all",
  "event_types": ["movies", "music", "records", "art", "festivals", "markets", "free", "press"],
  "max_per_type": 3
}
```

### Step 6: Verify in the Web Interface
1. Navigate to the **🧭 Explore & Discover** tab in Travel Scout.
2. Verify that the new items appear in the cards grid with:
   - Interactive category pills (`🎬 Film`, `🎨 Art`, `🎪 Festivals`, `🥖 Markets`, `📻 Record Stores`, `🎶 Music`, `🎟️ Free`).
   - Clickable `🌐 Live Scout` or `📰 Alt-Weekly` source badges.
   - 1-click **"➕ Add to Day"** scheduling button to place the event directly onto the day-by-day itinerary.
   - Interactive map pin linking to Leaflet / OpenStreetMap.
