# RiskWise Planner — Reviewer Guide

## Recommended Review Flow

Follow this sequence to see the full product workflow:

1. **Homepage** — Read the product overview and core workflow cards
2. **Login** — Sign in with the demo account
3. **Upload Dataset** — Import a CSV or Excel file with trade data
4. **Capital Preservation Dashboard** — Review observed risk metrics and provenance
5. **Position Sizing** — Estimate position dollar value
6. **Trade Risk Controls** — Calculate risk per trade with warnings
7. **Strategy Exposure Review** — Review heuristic sizing signal
8. **SL / TP Planner** — Calculate risk, reward, and R:R ratio
9. **Run Simulation** — Execute a simulation with custom parameters
10. **Monte Carlo Risk Simulation** — Stress-test with randomised distributions
11. **Scenario Comparison** — Compare multiple planning assumptions side by side
12. **Simulation History** — Review saved runs
13. **Simulation Detail** — Inspect parameters, results, and charts
14. **Delete Confirmation** — Verify safe destructive-action flow

## What to Look For

- **Pre-trade positioning**: Every page frames outputs as planning inputs, not post-trade performance
- **Methodology notes**: Calculator pages explain what they estimate and state assumptions
- **Risk warnings**: Trade Risk Controls surfaces threshold-based alerts (caution / elevated / high)
- **Dataset provenance**: Dashboard shows record count, date range, and planning-reference label
- **Ownership isolation**: Simulations are scoped to the authenticated user
- **Baseline tests**: Run `python manage.py test` to see route, auth, and ownership coverage

## Demo Dataset Format

Upload a CSV or Excel file with at minimum these columns:

| Column | Type | Example |
|--------|------|---------|
| date | Date | 2024-01-15 |
| symbol | String | EURUSD |
| volume | Float | 1.0 |
| entry_price | Float | 1.0850 |
| exit_price | Float | 1.0900 |
| profit | Float | 50.00 |
| account_type | String | Funded |

## Quick Start

```bash
git clone https://github.com/aminul-portfolio/riskwise-planner.git
cd riskwise-planner
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
