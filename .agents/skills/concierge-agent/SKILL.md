---
name: concierge-agent
description: Scans itinerary items and wishlist entries for ticketing and reservation requirements, classifies booking urgency (critical vs. walk-in), and produces an actionable reservation timeline.
---

# Autonomous Concierge & Reservation Assistant Skill

This skill acts as your personal trip concierge. It scans all planned sights, shows, and dinners, identifies which ones require advance booking (museum timed entries, concert tickets, popular dinner tables), categorizes them by urgency, and provides direct booking links.

## Execution
```bash
python .agents/skills/concierge-agent/scripts/concierge_plan.py
```
