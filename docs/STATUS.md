# RiskWise Planner — Project Status

## Current Release
**v1.0 — In final polish**

## Completed

- [x] Product positioning locked as **pre-trade risk planning and scenario modelling**
- [x] Core workflow exists across overview, planning surfaces, simulation, comparison, archive, and detail
- [x] Calculator suite exists:
  - [x] Lot Size
  - [x] Trade Risk Controls
  - [x] Strategy Exposure Review
  - [x] SL / TP Planner
- [x] Views are modularised into a `views/` package
- [x] Shared service-layer logic exists in `services.py`
- [x] Dark SaaS-style UI system exists
- [x] Reviewer documentation exists:
  - [x] `README.md`
  - [x] `docs/REVIEW_GUIDE.md`
  - [x] `docs/SCOPE.md`
- [x] Screenshot pack exists in `docs/screenshots/`
- [x] Test suite exists in `riskwise/tests.py` with **38 tests in suite**
- [x] Sprint 1 public-release cleanup completed:
  - [x] legacy view file removed
  - [x] `db.sqlite3` excluded from public distribution
  - [x] `__pycache__/` removed
  - [x] `media/screenshots/` removed from public distribution
  - [x] `LICENSE` added
  - [x] README portfolio context aligned to final portfolio structure
  - [x] MarketVista reference removed from this repo
  - [x] README and status wording updated for trust and accuracy

## Remaining before public release

- [ ] Sprint 2 — Workflow clarity
- [ ] Sprint 3 — Scenario comparison flagship upgrade
- [ ] Sprint 4 — Archive/detail/calculator QA
- [ ] Sprint 5 — SaaS frontend polish
- [ ] Sprint 6 — Domain trust and methodology hardening
- [ ] Sprint 7 — Technical hardening
- [ ] Sprint 8 — Test credibility expansion
- [ ] Sprint 9 — TradeIntel integration story
- [ ] Sprint 10 — Public packaging and launch

## Release notes

This project is being packaged as a portfolio-grade Django fintech product focused on **pre-trade decision-support**, not as a CRUD app, generic dashboard, or trade journal.