# RiskWise Planner — Project Status

## Current Release: v1.0 (Pre-Release)

### Completed

- [x] Phase 0 — Scope lock, positioning statement, SCOPE.md
- [x] Phase 1 — Repo cleanup (.idea, __pycache__, db.sqlite3, media/screenshots)
- [x] Phase 1 — .gitignore fixed (Unix line endings, media exclusion)
- [x] Phase 1 — settings.py wired to environment variables (SECRET_KEY, DEBUG, ALLOWED_HOSTS)
- [x] Phase 1 — Timezone set deliberately (Europe/London)
- [x] Phase 1 — requirements.txt created with actual dependency stack
- [x] Phase 1 — models.py cleaned (duplicate imports removed, Meta added, docstrings improved)
- [x] Phase 2 — Dashboard reframed with "Observed" prefixes on all KPI labels
- [x] Phase 2 — Dataset provenance banner added (record count, date range, planning-reference label)
- [x] Phase 2 — Homepage screenshot tooling removed from public-facing flow
- [x] Phase 2 — SCOPE.md documents portfolio separation (RiskWise vs TradeIntel)
- [x] Phase 3 — Login page redesigned (premium dark theme, branded, no raw Bootstrap)
- [x] Phase 3 — Topbar simplified (removed hardcoded chips, shows authenticated user)
- [x] Phase 3 — Simulation detail page redesigned (structured KPI cards, JSON download)
- [x] Phase 3 — Chart styling upgraded (dark matplotlib theme matching app colours)
- [x] Phase 3 — CSS: rw-form-input styles added for auth forms
- [x] Phase 4 — Methodology notes on Position Sizing, Trade Risk Controls, Strategy Exposure Review, SL/TP Planner
- [x] Phase 4 — Methodology notes on Monte Carlo Risk Simulation, Scenario Comparison
- [x] Phase 4 — Strategy Exposure Review formula explicitly labelled as heuristic
- [x] Phase 4 — Risk warnings with threshold levels (caution / elevated / high) on Trade Risk Controls
- [x] Phase 5 — Simulation history cards now display tags
- [x] Phase 5 — Delete flow button styling polished
- [x] Phase 6 — Baseline test suite: 20+ tests covering routes, auth, calculations, warnings, ownership
- [x] Phase 7 — README fully rewritten (business-facing, evidence-based, interview story, role fit)
- [x] Phase 7 — REVIEW_GUIDE.md created for reviewer walkthroughs
- [x] Phase 7 — STATUS.md tracks completion state

### Remaining for Full Public Release

- [ ] Phase 7 — Screenshot pack (4 curated images captured from running app)
- [ ] Phase 8 — GitHub release metadata (repo description, topics/tags)
- [ ] Phase 8 — LinkedIn packaging (post, bullets, CV summary)
- [ ] Optional — Plotly migration (if time allows for richer chart interactivity)
- [ ] Optional — Scenario comparison save/export to JSON
