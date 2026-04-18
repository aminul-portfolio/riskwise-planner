# RiskWise Planner — Review Guide

## Recommended Review Flow

Follow this sequence to see the full workflow clearly:

1. **Homepage** — review product framing, workflow language, and portfolio positioning
2. **Login** — sign in to access the authenticated product surfaces
3. **Upload Dataset** — upload a CSV or Excel dataset with outcome data
4. **Planning Baseline** — review downside posture, edge quality, sample depth, and planning interpretation
5. **Position Sizing** — inspect exposure-estimation logic and methodology notes
6. **Trade Risk Controls** — inspect account-risk logic and warning states
7. **Strategy Exposure Review** — inspect capped planning-heuristic logic and its interpretation boundary
8. **SL / TP Planner** — inspect risk, reward, and ratio framing
9. **Monte Carlo Lab** — run a simulation and review downside distribution metrics
10. **Stress-Test Review** — inspect decision-ready downside framing
11. **Scenario Comparison** — compare multiple planning assumptions side by side
12. **Saved Runs** — review archived stress-test results and archive filters
13. **Detail View** — inspect saved run detail, parameters, and evidence surfaces
14. **Delete Confirmation** — verify safe destructive-action flow

## What to Look For

- **Pre-trade positioning**: pages are framed as planning inputs, not post-trade performance summaries
- **Methodology notes**: calculators and simulation surfaces explain assumptions and interpretation limits
- **Risk warnings**: Trade Risk Controls surfaces threshold-based warning behaviour
- **Dataset provenance**: active dataset context is visible across planning surfaces
- **Workflow continuity**: the product flows from upload → baseline → calculators → simulation → scenario → archive
- **Ownership isolation**: saved simulation content is scoped to the authenticated user
- **Reviewer credibility**: CI, tests, coverage, and reviewer docs support trust

## Integration Story

RiskWise is the **pre-trade decision-support** layer in the broader portfolio sequence:

```text
DataBridge Market API → RiskWise Planner → TradeIntel 360