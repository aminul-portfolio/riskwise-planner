# RiskWise Planner — Project Status

## Current Release
**v1.0 — Final packaging in progress**

## Completed

- [x] Product positioning locked as **pre-trade risk planning and scenario modelling**
- [x] Portfolio framing locked as **pre-trade decision-support**
- [x] Core workflow exists across:
  - [x] overview
  - [x] upload
  - [x] planning baseline
  - [x] calculators
  - [x] Monte Carlo
  - [x] stress-test review
  - [x] scenario comparison
  - [x] saved runs
  - [x] detail view
- [x] Calculator suite exists:
  - [x] Position Sizing
  - [x] Trade Risk Controls
  - [x] Strategy Exposure Review
  - [x] SL / TP Planner
- [x] Scenario comparison flagship surface is implemented
- [x] Saved runs archive and detail workflow are implemented
- [x] Monte Carlo sampled-record review now uses pagination for better usability
- [x] Views are modularised into a `views/` package
- [x] Shared service-layer logic exists in `services.py`
- [x] Dark SaaS-style UI system exists
- [x] Left-aligned wide app-shell layout is in place
- [x] Reviewer-facing documentation exists:
  - [x] `README.md`
  - [x] `docs/REVIEW_GUIDE.md`
  - [x] `docs/SCOPE.md`
  - [x] `docs/INTEGRATION.md`
- [x] Screenshot pack exists in `docs/screenshots/`
- [x] CI is passing in GitHub Actions
- [x] `seed_demo` works
- [x] WhiteNoise / Gunicorn / Procfile / custom 404 / 500 are already done
- [x] Current verified quality markers:
  - [x] 64 tests passing
  - [x] 71% coverage
- [x] Sprint 9 TradeIntel integration story completed:
  - [x] `docs/INTEGRATION.md` added
  - [x] homepage messaging updated
  - [x] upload messaging updated
  - [x] README integration story aligned

## In progress

- [ ] Sprint 10 — Public packaging and launch

## Remaining before release sign-off

- [ ] Sync final reviewer docs to the current shipped state
- [ ] Add `CHANGELOG.md`
- [ ] Refresh screenshots where current UI has changed materially
- [ ] Run final verification:
  - [ ] `python manage.py check --deploy` clean pass after production security settings are hardened
  - [x] `python manage.py test`
  - [x] `python manage.py seed_demo`
  - [ ] full click-through from home to archive
  - [ ] mobile review at 375px
  - [ ] README render check on GitHub
- [ ] Set GitHub description and topics
- [ ] Draft LinkedIn launch post
- [ ] Write CV bullets

## Release notes

RiskWise Planner is being packaged as a portfolio-grade Django fintech product focused on **pre-trade decision-support**.

It should be reviewed as:
- a downside-aware planning product
- a scenario and simulation workflow
- a capital-preservation decision-support surface

It should **not** be reviewed as:
- a CRUD app
- a generic dashboard
- a trade journal
- a simple calculator bundle