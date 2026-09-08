---
name: weather-tactician
description: Analyzes live Open-Meteo weather forecasts for trip dates, issues rain and weather advisories, proactively suggests swapping outdoor activities with indoor cultural gems, and generates tailored packing lists.
---

# Smart Weather Re-Scheduler & Packing Agent Skill

This skill equips the agent to monitor live high-resolution weather forecasts for destination cities across the trip schedule. When inclement weather (rain, cold snaps, or extreme heat) is detected, the agent identifies compromised outdoor activities and suggests optimal indoor cultural swaps from the wishlist, and produces an itemized packing checklist.

## Capabilities
1. **Forecast Audit**: Checks daily temperature ranges and precipitation probabilities using zero-key Open-Meteo APIs.
2. **Rain Swaps**: Detects outdoor activities (markets, festivals, parks, walking tours) scheduled on rainy dates and pairs them with indoor alternatives (museums, art galleries, record stores, cafes).
3. **Dynamic Packing List**: Compiles a tailored packing list based on actual trip weather conditions.

## Execution
```bash
python .agents/skills/weather-tactician/scripts/weather_tactician.py
```
