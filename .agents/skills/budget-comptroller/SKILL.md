---
name: budget-comptroller
description: Audits group travel expenditures, calculates fair shares and minimal debt settlements between travelers, projects daily burn rates, and flags budget imbalance alerts.
---

# Group Budget & Expense Comptroller Skill

This skill acts as your group trip financial auditor. It computes category spending distributions, calculates per-traveler fair shares, solves the minimal peer-to-peer debt settlement graph, projects daily burn rates, and flags budget anomalies.

## Capabilities
1. **Expense Breakdown**: Groups costs by category (lodging, dining, transit, activities, shopping).
2. **Fair Share & Minimal Settlement**: Calculates exactly who owes whom to settle all balances with the fewest payments.
3. **Burn Rate Projection**: Estimates daily cost per traveler for the remainder of the itinerary.
4. **Health Alerts**: Flags category over-concentration or inactive spenders.

## Execution
```bash
python .agents/skills/budget-comptroller/scripts/audit_budget.py

# With a specific budget target:
python .agents/skills/budget-comptroller/scripts/audit_budget.py --budget 2500
```
