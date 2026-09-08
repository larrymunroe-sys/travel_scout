---
name: transit-optimizer
description: Solves the day itinerary routing problem by ordering scheduled activities geographically to minimize walking distance and transit transfers starting from the active hotel stay, calculates mileage savings, and recommends local transit passes.
---

# Transit Route & Itinerary Optimizer Skill

This skill solves the daily routing puzzle. It takes all activities assigned to a specific day, matches the active lodging for that date as the origin, and applies a Traveling Salesperson heuristic to minimize walking distance and backtracking. It also outputs recommendations for local transit agency cards and passes (e.g. MTS Pronto in San Diego, Navegante in Lisbon, Oyster in London, Navigo in Paris).

## Execution
```bash
# Preview route optimization for all scheduled days:
python .agents/skills/transit-optimizer/scripts/optimize_route.py

# Apply the optimized order to the database schedule:
python .agents/skills/transit-optimizer/scripts/optimize_route.py --date "2026-09-10" --apply
```
