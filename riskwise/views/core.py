from __future__ import annotations

import numpy as np
import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import ScreenshotForm
from ..models import Screenshot
from ..services import (
    build_dashboard_interpretation,
    get_active_planning_df,
    prepare_trade_import_dataframe,
    save_dataset_meta_to_session,
    save_uploaded_df_to_session,
    with_dataset_context,
)
from .shared import (
    _build_dashboard_decision_context,
    _build_empty_dashboard_context,
    _normalize_dataset_meta,
)


def home(request):
    features = [
        {
            "title": "Load Planning Dataset",
            "description": "Import CSV or Excel data to build a downside-aware planning baseline for simulation and scenario review.",
            "icon": "bi bi-upload",
            "color": "primary",
            "url": "/upload/",
            "button_text": "Load Dataset",
        },
        {
            "title": "Planning Baseline",
            "description": "Review observed downside depth, edge quality, and stability signals before taking new risk.",
            "icon": "bi bi-shield-check",
            "color": "success",
            "url": "/dashboard/",
            "button_text": "Review Planning Baseline",
        },
        {
            "title": "Position Sizing",
            "description": "Estimate trade size in line with account balance, pip distance, and capital preservation rules.",
            "icon": "bi bi-bullseye",
            "color": "primary",
            "url": "/calculators/lot-size/",
            "button_text": "Open Position Sizing",
        },
        {
            "title": "Trade Risk Controls",
            "description": "Evaluate per-trade downside using account balance, lot size, pip value, and stop-loss distance.",
            "icon": "bi bi-percent",
            "color": "warning",
            "url": "/calculators/risk-per-trade/",
            "button_text": "Open Trade Risk Controls",
        },
        {
            "title": "Strategy Exposure Review",
            "description": "Review strategy-level risk assumptions using win rate, risk-reward, and volatility-aware sizing logic.",
            "icon": "bi bi-bar-chart",
            "color": "info",
            "url": "/calculators/strategy-risk/",
            "button_text": "Open Strategy Review",
        },
        {
            "title": "Monte Carlo Risk Simulation",
            "description": "Stress-test planning assumptions through simulated outcome distributions and downside-aware review.",
            "icon": "bi bi-shuffle",
            "color": "info",
            "url": "/simulations/monte-carlo/",
            "button_text": "Run Monte Carlo",
        },
        {
            "title": "Scenario Comparison",
            "description": "Compare multiple planning assumptions side by side before committing capital.",
            "icon": "bi bi-diagram-3",
            "color": "primary",
            "url": "/simulations/scenario/",
            "button_text": "Compare Scenarios",
        },
        {
            "title": "Saved Planning Runs",
            "description": "Review saved stress tests and simulations for follow-up analysis and decision support.",
            "icon": "bi bi-clock-history",
            "color": "secondary",
            "url": "/simulations/history/",
            "button_text": "Open Saved Runs",
        },
    ]

    return render(
        request,
        "riskwise/home.html",
        with_dataset_context(request, {"features": features}),
    )



@login_required
def upload_screenshot(request):
    if not request.user.is_staff:
        messages.error(request, "Only staff users can manage homepage screenshots.")
        return redirect("home")

    if request.method == "POST":
        form = ScreenshotForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Screenshot uploaded successfully.")
        else:
            messages.error(request, "Screenshot upload failed.")

    return redirect("home")



@login_required
def delete_screenshot(request, pk):
    if not request.user.is_staff:
        messages.error(request, "Only staff users can manage homepage screenshots.")
        return redirect("home")

    screenshot = get_object_or_404(Screenshot, pk=pk)

    if request.method == "POST":
        screenshot.image.delete(save=False)
        screenshot.delete()
        messages.success(request, "Screenshot deleted successfully.")

    return redirect("home")



@login_required
def upload_file(request):
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]

        try:
            df = prepare_trade_import_dataframe(uploaded_file)
        except ValueError as exc:
            return render(
                request,
                "riskwise/upload.html",
                with_dataset_context(request, {"error": str(exc)}),
            )
        except Exception as exc:
            return render(
                request,
                "riskwise/upload.html",
                with_dataset_context(request, {"error": f"Error reading file: {exc}"}),
            )

        loaded_count = len(df)

        if loaded_count:
            save_uploaded_df_to_session(request, df)
            save_dataset_meta_to_session(request, uploaded_file.name, df)
            messages.success(
                request,
                f"Planning dataset loaded. {loaded_count} records are now available for baseline review and simulation.",
            )
            return redirect("dashboard")

        messages.warning(request, "No planning records were loaded from the uploaded file.")
        return redirect("upload")

    return render(
        request,
        "riskwise/upload.html",
        with_dataset_context(request, {}),
    )


@login_required
def dashboard(request):
    df, dataset_meta = get_active_planning_df(request)

    if df is None or df.empty:
        return render(
            request,
            "riskwise/dashboard.html",
            with_dataset_context(
                request,
                _build_empty_dashboard_context(
                    "No planning dataset has been loaded yet.",
                    dataset_meta=dataset_meta,
                ),
            ),
        )

    if "profit" not in df.columns:
        return render(
            request,
            "riskwise/dashboard.html",
            with_dataset_context(
                request,
                _build_empty_dashboard_context(
                    "No profit data is available in the current planning dataset.",
                    dataset_meta=dataset_meta,
                ),
                df=df,
            ),
        )

    df = df.copy()
    df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0)
    dataset_meta = _normalize_dataset_meta(dataset_meta, df=df)

    cumulative_profit = df["profit"].cumsum()
    running_peak = cumulative_profit.cummax()
    drawdown_series = cumulative_profit - running_peak

    wins = df.loc[df["profit"] > 0, "profit"]
    losses = df.loc[df["profit"] < 0, "profit"]

    total_profit = float(df["profit"].sum())
    win_rate = float((df["profit"] > 0).mean() * 100)
    max_drawdown = float(drawdown_series.min()) if not drawdown_series.empty else 0.0
    avg_risk = abs(float(losses.mean())) if not losses.empty else 0.0
    volatility = float(df["profit"].std()) if len(df) > 1 else 0.0
    downside_percentile = float(np.percentile(df["profit"], 5)) if len(df) > 0 else 0.0
    avg_win = float(wins.mean()) if not wins.empty else 0.0
    avg_loss = abs(float(losses.mean())) if not losses.empty else 0.0

    gross_profit = float(wins.sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses.sum())) if not losses.empty else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

    drawdown_depth = abs(max_drawdown)

    interpretation = build_dashboard_interpretation(
        df=df,
        max_drawdown=drawdown_depth,
        volatility=volatility,
        profit_factor=profit_factor,
    )

    primary_downside_concern = interpretation["primary_downside_concern"]
    planning_implication = interpretation["planning_implication"]
    suggested_next_step = interpretation["suggested_next_step"]

    insight_items = [
        {
            "variant": "danger",
            "label": "Primary downside concern",
            "text": primary_downside_concern,
        },
        {
            "variant": "warning",
            "label": "Planning implication",
            "text": planning_implication,
        },
        {
            "variant": "primary",
            "label": "Suggested next step",
            "text": suggested_next_step,
        },
    ]

    context = {
        "total_profit": total_profit,
        "win_rate": win_rate,
        "max_drawdown": drawdown_depth,
        "max_drawdown_raw": max_drawdown,
        "avg_risk": avg_risk,
        "volatility": volatility,
        "percentile_95": downside_percentile,
        "downside_percentile": downside_percentile,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "trade_count": len(df),
        "date_range_start": dataset_meta.get("date_start"),
        "date_range_end": dataset_meta.get("date_end"),
        "dataset_meta": dataset_meta,
        "planning_reference_notice": (
            "These metrics are derived from the currently loaded reference dataset. "
            "Use them to calibrate future risk planning, not as a post-trade report card."
        ),
        "what_this_suggests": (
            "Review downside depth, edge quality, and outcome dispersion together before committing new capital."
        ),
        "primary_downside_concern": primary_downside_concern,
        "planning_implication": planning_implication,
        "suggested_next_step": suggested_next_step,
        "insight_items": insight_items,
    }

    context.update(
        _build_dashboard_decision_context(
            total_profit=total_profit,
            win_rate=win_rate,
            max_drawdown=drawdown_depth,
            avg_risk=avg_risk,
            volatility=volatility,
            downside_percentile=downside_percentile,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trade_count=len(df),
            primary_downside_concern=primary_downside_concern,
            planning_implication=planning_implication,
            suggested_next_step=suggested_next_step,
        )
    )

    return render(
        request,
        "riskwise/dashboard.html",
        with_dataset_context(request, context, df=df),
    )

