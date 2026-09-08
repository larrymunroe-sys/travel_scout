---
name: bookstore-scout
description: Discovers independent bookstores (vintage, used, antiquarian, rare first editions, and new indie bookshops) for itinerary destination cities.
---

# Independent & Vintage Bookstores Scout Skill

Discovers independent bookstores, antiquarian and used book vaults, rare first editions, community literary cafes, and indie presses in your destination city.

## Capabilities
- Uncovers historic and neighborhood indie bookstores.
- Discovers secondhand bookshops, used paperback dens, and antiquarian booksellers.
- Resolves coordinates and provides Google Maps directions starting from the traveler's active lodging stay.
- Ingests bookshops directly into the Explore & Discover wishlist for the active trip.

## Execution
```bash
# Run for all destination cities on the most recent trip:
python .agents/skills/bookstore-scout/scripts/scout_bookstores.py

# Or target a specific city:
python .agents/skills/bookstore-scout/scripts/scout_bookstores.py --city "San Diego"

# Dry-run without saving to database:
python .agents/skills/bookstore-scout/scripts/scout_bookstores.py --city "Lisbon" --dry-run
```
