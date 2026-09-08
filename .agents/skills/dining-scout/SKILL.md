---
name: dining-scout
description: Discovers authentic neighborhood eateries, bakeries, third-wave coffee roasters, iconic local dishes, and craft cocktail bars for destination cities on the itinerary, saving discoveries directly into the Explore & Discover wishlist of Travel Scout.
---

# Culinary & Hidden Gems Scout Skill

This skill equips the agent to act as a **Foodie & Nightlife Scout**. For any destination city on the itinerary, the agent discovers essential neighborhood culinary institutions, Michelin Bib Gourmand picks, third-wave coffee roasters, artisan bakeries, and craft cocktail speakeasies.

## Categories Covered
- **Specialty Coffee (`coffee`)**: Third-wave espresso bars, artisan roasters, and morning pour-overs.
- **Artisan Bakeries (`bakeries`)**: Sourdough bakeries, regional pastry shops, and morning viennoiserie.
- **Casual & Street Eats (`casual`)**: Iconic sandwich joints, street stalls, taco counters, and local favorites.
- **Neighborhood Dining (`dinner`)**: Farm-to-table bistros, regional wine-and-dine spots, Eater 38 selections.
- **Cocktails & Aperitivo (`cocktails`)**: Natural wine bars, intimate craft cocktail lounges, and rooftop terraces.

## Execution

```bash
# Automatically scouts all itinerary destination cities:
python .agents/skills/dining-scout/scripts/scout_dining.py

# Or target specific city & categories:
python .agents/skills/dining-scout/scripts/scout_dining.py --city "San Diego" --categories "coffee,dinner,cocktails"
```
