<div align="center">

<img src="docs/screenshots/02.1_planning_baseline.png" alt="RiskWise Planner — Planning Baseline" width="80%" style="border-radius:12px;"/>

<br/>
<br/>

# RiskWise Planner

### Pre-Trade Risk Planning & Scenario Modelling

*Observed outcomes → planning metrics → simulation → scenario comparison → capital-preservation decisions*

<br/>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.x-092E20?style=flat-square&logo=django&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-data--processing-150458?style=flat-square&logo=pandas&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-charts-11557c?style=flat-square)
[![CI](https://github.com/aminul-portfolio/riskwise-planner/actions/workflows/django-ci.yml/badge.svg)](https://github.com/aminul-portfolio/riskwise-planner/actions/workflows/django-ci.yml)
![Tests](https://img.shields.io/badge/tests-64_passing-2ea44f?style=flat-square)
![Coverage](https://img.shields.io/badge/coverage-71%25-2ea44f?style=flat-square)

</div>

---

## Overview

Most risk-related portfolio projects stop at isolated calculators or post-trade dashboards. **RiskWise Planner** goes further — it is structured as a pre-trade risk planning product that uses observed trade outcomes as reference inputs for downside-aware planning, simulation-backed review, and capital-preservation decisions.

> This is not a post-trade journal, a trading dashboard, or a calculator bundle.
> It is a planning-first risk product with methodology notes, threshold warnings, and simulation workflows.

**Best role fit**

`Analytics Engineer (FinTech)` &nbsp; `Data Engineer — Finance / Risk` &nbsp; `Python / Django data-product roles` &nbsp; `Product-focused Full-Stack Developer`

**Best industry fit**

`FinTech` &nbsp; `Risk Analytics` &nbsp; `Quantitative Planning` &nbsp; `Capital Markets Tooling` &nbsp; `Trading Technology`

---

## What This Project Demonstrates

| Capability | Evidence |
|---|---|
| **Domain-specific product thinking** | Every page is framed around pre-trade planning, not generic CRUD or post-trade review |
| **Full-stack Django engineering** | Views, models, forms, templates, session handling, authentication, ownership isolation |
| **Simulation & analytics pipeline** | Monte Carlo simulation, equity curve generation, multi-scenario comparison |
| **Risk-product credibility** | Methodology notes, heuristic labels, threshold-based warnings, dataset provenance |
| **Premium UI execution** | Dark design system, KPI cards, responsive sidebar, consistent visual hierarchy |
| **Software discipline** | 64 passing tests, 71% measured coverage, ownership isolation, CI workflow, reviewer documentation |

---

## Screenshots

<br>

<!-- Row 1: Homepage hero + workflow -->
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="border:1px solid #1e2d45;border-radius:10px;overflow:hidden;background:#0e1420">
  <tr>
    <td width="50%" valign="top"
        style="padding:20px 12px 20px 20px;border-right:1px solid #1e2d45">
      <img src="docs/screenshots/00.1_homepage_hero.png"
           alt="Homepage hero"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
    <td width="50%" valign="top"
        style="padding:20px 20px 20px 12px">
      <img src="docs/screenshots/00.2_homepage_workflow.png"
           alt="Homepage workflow and product value"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
  </tr>
  <tr>
    <td valign="top"
        style="padding:10px 12px 16px 20px;border-right:1px solid #1e2d45;border-top:1px solid #1e2d45">
      <sub><strong>Homepage hero</strong><br>
      Product framing, reviewer path, positioning, and primary calls to action</sub>
    </td>
    <td valign="top"
        style="padding:10px 20px 16px 12px;border-top:1px solid #1e2d45">
      <sub><strong>Workflow and product value</strong><br>
      Core workflow, active session context, and what the project demonstrates</sub>
    </td>
  </tr>
</table>

<br>

<!-- Row 2: Upload + Planning Baseline -->
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="border:1px solid #1e2d45;border-radius:10px;overflow:hidden;background:#0e1420">
  <tr>
    <td width="50%" valign="top"
        style="padding:20px 12px 20px 20px;border-right:1px solid #1e2d45">
      <img src="docs/screenshots/01.1_upload_surface.png"
           alt="Upload dataset surface"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
    <td width="50%" valign="top"
        style="padding:20px 20px 20px 12px">
      <img src="docs/screenshots/02.1_planning_baseline.png"
           alt="Planning Baseline"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
  </tr>
  <tr>
    <td valign="top"
        style="padding:10px 12px 16px 20px;border-right:1px solid #1e2d45;border-top:1px solid #1e2d45">
      <sub><strong>Upload surface</strong><br>
      Manual CSV/XLSX intake, dataset expectations, and documented TradeIntel-style flat-file handoff</sub>
    </td>
    <td valign="top"
        style="padding:10px 20px 16px 12px;border-top:1px solid #1e2d45">
      <sub><strong>Planning Baseline</strong><br>
      Downside posture, sample quality, observed risk profile, and decision-ready next steps</sub>
    </td>
  </tr>
</table>

<br>

<!-- Row 3: Monte Carlo + Stress-Test -->
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="border:1px solid #1e2d45;border-radius:10px;overflow:hidden;background:#0e1420">
  <tr>
    <td width="50%" valign="top"
        style="padding:20px 12px 20px 20px;border-right:1px solid #1e2d45">
      <img src="docs/screenshots/04.1_monte_carlo_results.png"
           alt="Monte Carlo results"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
    <td width="50%" valign="top"
        style="padding:20px 20px 20px 12px">
      <img src="docs/screenshots/05.1_stress_test_summary.png"
           alt="Stress-Test Review"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
  </tr>
  <tr>
    <td valign="top"
        style="padding:10px 12px 16px 20px;border-right:1px solid #1e2d45;border-top:1px solid #1e2d45">
      <sub><strong>Monte Carlo Lab</strong><br>
      Filtered-sample run context, simulation result cards, and sampled-record review</sub>
    </td>
    <td valign="top"
        style="padding:10px 20px 16px 12px;border-top:1px solid #1e2d45">
      <sub><strong>Stress-Test Review</strong><br>
      Decision-ready downside summary with tail-risk framing and simulation KPIs</sub>
    </td>
  </tr>
</table>

<br>

<!-- Row 4: Scenario comparison top + results -->
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="border:1px solid #1e2d45;border-radius:10px;overflow:hidden;background:#0e1420">
  <tr>
    <td width="50%" valign="top"
        style="padding:20px 12px 20px 20px;border-right:1px solid #1e2d45">
      <img src="docs/screenshots/06.1_scenario_comparison_top.png"
           alt="Scenario Comparison top section"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
    <td width="50%" valign="top"
        style="padding:20px 20px 20px 12px">
      <img src="docs/screenshots/06.2_scenario_results.png"
           alt="Scenario comparison results"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
  </tr>
  <tr>
    <td valign="top"
        style="padding:10px 12px 16px 20px;border-right:1px solid #1e2d45;border-top:1px solid #1e2d45">
      <sub><strong>Scenario comparison setup</strong><br>
      Dataset context, scenario configuration, and comparison framing before results are generated</sub>
    </td>
    <td valign="top"
        style="padding:10px 20px 16px 12px;border-top:1px solid #1e2d45">
      <sub><strong>Scenario comparison results</strong><br>
      Side-by-side downside, percentile, and distribution evidence across competing planning setups</sub>
    </td>
  </tr>
</table>

<br>

<!-- Row 5: Modal review surfaces -->
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="border:1px solid #1e2d45;border-radius:10px;overflow:hidden;background:#0e1420">
  <tr>
    <td width="50%" valign="top"
        style="padding:20px 12px 20px 20px;border-right:1px solid #1e2d45">
      <img src="docs/screenshots/07.1_scenario_modal_distribution.png"
           alt="Scenario modal distribution review"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
    <td width="50%" valign="top"
        style="padding:20px 20px 20px 12px">
      <img src="docs/screenshots/07.2_scenario_modal_histogram.png"
           alt="Scenario modal histogram review"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
  </tr>
  <tr>
    <td valign="top"
        style="padding:10px 12px 16px 20px;border-right:1px solid #1e2d45;border-top:1px solid #1e2d45">
      <sub><strong>Distribution view modal</strong><br>
      Percentile-path review with downside dispersion, best/worst paths, and quick decision stats</sub>
    </td>
    <td valign="top"
        style="padding:10px 20px 16px 12px;border-top:1px solid #1e2d45">
      <sub><strong>Final profit distribution modal</strong><br>
      Histogram review showing clustering, left-tail depth, and conservative planning context</sub>
    </td>
  </tr>
</table>

<br>

<!-- Row 6: Archive + detail -->
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="border:1px solid #1e2d45;border-radius:10px;overflow:hidden;background:#0e1420">
  <tr>
    <td width="50%" valign="top"
        style="padding:20px 12px 20px 20px;border-right:1px solid #1e2d45">
      <img src="docs/screenshots/08.1_saved_runs.png"
           alt="Saved Runs archive"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
    <td width="50%" valign="top"
        style="padding:20px 20px 20px 12px">
      <img src="docs/screenshots/09.1_run_detail_view.png"
           alt="Run detail view"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
  </tr>
  <tr>
    <td valign="top"
        style="padding:10px 12px 16px 20px;border-right:1px solid #1e2d45;border-top:1px solid #1e2d45">
      <sub><strong>Saved Runs</strong><br>
      Archive filters, run summaries, and chart previews for structured review and retrieval</sub>
    </td>
    <td valign="top"
        style="padding:10px 20px 16px 12px;border-top:1px solid #1e2d45">
      <sub><strong>Run detail view</strong><br>
      Archived run summary, chart review, provenance, and reviewer-facing run controls</sub>
    </td>
  </tr>
</table>

<br>

<!-- Row 7: Audit breakdown -->
<table width="100%" cellpadding="0" cellspacing="0" border="0"
       style="border:1px solid #1e2d45;border-radius:10px;overflow:hidden;background:#0e1420">
  <tr>
    <td valign="top" style="padding:20px">
      <img src="docs/screenshots/09.2_run_detail_audit_breakdown.png"
           alt="Run detail audit breakdown"
           width="100%"
           style="border-radius:6px;border:1px solid #1e2d45;display:block">
    </td>
  </tr>
  <tr>
    <td valign="top" style="padding:10px 20px 16px 20px;border-top:1px solid #1e2d45">
      <sub><strong>Audit breakdown</strong><br>
      Stored parameter and result detail for deeper technical inspection without making the primary run view feel too raw</sub>
    </td>
  </tr>
</table>

<br>