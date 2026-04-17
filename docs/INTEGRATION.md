# RiskWise Planner — Integration Notes

## Why this document exists

RiskWise is the **pre-trade decision-support** layer in the portfolio.

The primary product sequence remains:

```text
DataBridge Market API → RiskWise Planner → TradeIntel 360
```

That is the main portfolio story:
- **DataBridge Market API** supplies structured market data and upstream data-product credibility
- **RiskWise Planner** supports pre-trade downside review, simulation, and scenario planning
- **TradeIntel 360** supports post-trade performance review and analytics

A secondary **feedback loop** also exists for planning reuse:

```text
TradeIntel 360 flat outcome export
            ↓
      manual CSV/XLSX upload
            ↓
       RiskWise Planner
            ↓
 next planning-cycle calibration
```

This document defines the current compatibility boundary for that feedback loop.

---

## Current integration model

RiskWise currently supports a **file-based handoff path**.

That means the current public release uses:

- manual CSV upload
- manual XLSX upload
- manual XLS upload
- RiskWise-side column normalisation
- session-based planning activation after import

This is **not** a live API integration, broker sync, or one-click account connection.

---

## Supported now

### RiskWise-side import support

RiskWise currently accepts flat files that include trade-outcome data and a recognised P&L field.

Supported on the RiskWise side now:

- CSV files
- XLSX files
- XLS files
- recognised P&L-style columns such as:
  - `profit`
  - `pnl`
  - `net_profit`
  - `net_pnl`
  - `pl`
  - `p_l`
  - `gain_loss`
  - `profit_loss`

Helpful additional fields:

- date / datetime / timestamp
- session / market_session / trading_session
- symbol / instrument / asset / pair / ticker
- side / direction / trade_type / position
- status / trade_status

If a session field is not provided but a usable date/time field exists, RiskWise can derive a session label for planning filters.

---

## What this means for TradeIntel 360

RiskWise is ready to accept a **TradeIntel-style flat export** provided the exported file includes:

- a recognised P&L / outcome column
- numeric values that can be interpreted as observed outcomes
- optional date/time context for filtering and provenance

This document confirms **RiskWise-side compatibility readiness** for that flat-file handoff.

It does **not** claim that a specific TradeIntel 360 export schema has been verified in this repository unless that schema is separately documented in the TradeIntel project.

---

## Not yet supported

The following are **not** part of the current public release:

- direct API sync between TradeIntel 360 and RiskWise
- one-click “pull from TradeIntel 360” backend integration
- automatic export-schema validation against a documented TradeIntel contract
- background synchronisation between projects
- broker or platform account linking
- automatic cross-product user/session sharing

---

## Future possible

Possible future extensions, if product scope ever expands:

- dedicated TradeIntel export preset for RiskWise
- validated import template shared across both projects
- one-click prefilled import flow
- signed export manifest / provenance handoff
- direct authenticated cross-product import

These are future possibilities only, not current release features.

---

## Reviewer-facing summary

For portfolio review, the correct story is:

- **Primary flow:** DataBridge → RiskWise → TradeIntel
- **Secondary planning feedback loop:** TradeIntel flat outcome export → RiskWise upload → next-cycle planning review

That keeps the product story honest while still showing ecosystem thinking and reusable analytics workflow design.
