# Changelog

All notable changes to **RiskWise Planner** will be documented in this file.

## [v1.0] - 2026-04-18

### Added
- Added `docs/INTEGRATION.md` to document the RiskWise ↔ TradeIntel flat-file compatibility story
- Added homepage messaging for documented TradeIntel 360 compatibility
- Added upload-page messaging for manual CSV/XLSX/XLS handoff from TradeIntel-style exports
- Added Monte Carlo sampled-record pagination for better review usability
- Added stronger reviewer-facing packaging across README and supporting docs

### Changed
- Updated README to reflect the current portfolio story, decision-support framing, and review flow
- Updated upload flow messaging to keep the integration story honest and manual-first
- Updated app-shell layout to a left-aligned wide SaaS-style product shell
- Refined sidebar scrollbar placement and app-shell spacing
- Improved Monte Carlo review experience by replacing an overlong table with paginated review controls
- Upgraded scenario chart modals into structured SaaS-style review surfaces with summary stats and viewport-fit tuning
- Updated `docs/STATUS.md` and `docs/REVIEW_GUIDE.md` to match the shipped product state

### Verified
- GitHub Actions CI passing
- 64 tests passing
- 71% coverage
- `seed_demo` working

### Known Deployment Notes
- `python manage.py check --deploy` still reports production security warnings until production settings are hardened
- Current warnings relate to `DEBUG`, `SECRET_KEY`, HSTS, HTTPS redirect, and secure cookies

### Packaging Notes
- Current product should be reviewed as a **pre-trade decision-support** product
- Manual flat-file compatibility with TradeIntel-style exports is documented
- Live sync or direct API integration is not part of the current public release