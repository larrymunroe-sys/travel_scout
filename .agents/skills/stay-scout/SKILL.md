---
name: stay-scout
description: Evaluates booked hotels and prospective accommodations against the traveler's wishlist and scheduled itinerary, scoring walkability, transit commute times, and neighborhood character.
---

# Lodging & Neighborhood Evaluator Skill

This skill audits your accommodations. It computes geographic walking distances and travel times from your hotel or Airbnb to all the sights, restaurants, and cultural spots you have planned, assigns a Walkability Score (0-100), and provides actionable relocation or transit advice.

## Metrics Evaluated
1. **Average Distance**: Mean distance in kilometers to all planned activities.
2. **15-Minute Walk Radius**: Percentage of itinerary and wishlist spots within 1.2 km.
3. **Walkability Score**: 0-100 score weighing commute convenience.
4. **Strategic Verdict**: Whether the stay is a prime base or a high-commute spot.

## Execution
```bash
python .agents/skills/stay-scout/scripts/scout_stay.py
```
