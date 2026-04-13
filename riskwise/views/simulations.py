from __future__ import annotations

import logging

import numpy as np
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..models import SimulationHistory
from ..services import (
    build_equity_curve_chart,
    build_equity_curve_summary,
    build_final_profit_histogram,
    build_percentile_band_chart,
    build_result_list,
    build_run_summary,
    build_simulation_warning,
    clear_uploaded_dataset_from_session,
    clip_range,
    filter_df_by_date_range,
    filter_df_by_session,
    get_dataset_meta,
    load_dataset_meta_from_session,
    load_uploaded_df_from_session,
    prepare_simulation_dataframe,
    run_simulation,
    safe_int,
    save_dataset_meta_to_session,
    save_uploaded_df_to_session,
    with_dataset_context,
)
from .shared import (
    _build_simulation_presentation_context,
    _default_simulation_form_data,
    _normalize_dataset_meta,
    _normalize_scenario_dataset_meta,
)

logger = logging.getLogger("riskwise")


def _calculate_max_consecutive_losses(equity_curves):
    if equity_curves is None:
        return None

    try:
        curves = np.asarray(equity_curves, dtype=float)
    except Exception:
        return None

    if curves.size == 0:
        return None

    if curves.ndim == 1:
        curves = curves.reshape(1, -1)

    if curves.shape[1] == 0:
        return None

    step_results = np.diff(curves, axis=1, prepend=0.0)

    max_streak = 0
    for path in step_results:
        streak = 0
        for step in path:
            if step < 0:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0

    return int(max_streak)


@login_required
def monte_carlo_simulation(request):
    results = None
    instruction = None
    trade_count = None
    summary = None
    result_list = []
    form_data = {}
    date_start = None
    date_end = None
    simulation_warning = None
    dataset_meta = load_dataset_meta_from_session(request)

    if request.method == "POST":
        if "reset" in request.POST:
            clear_uploaded_dataset_from_session(request)
            logger.info("monte_carlo_reset | user=%s", request.user.username)
            return render(
                request,
                "riskwise/monte_carlo.html",
                with_dataset_context(
                    request,
                    {
                        "instruction": "Planning dataset reset successfully.",
                        "form_data": {},
                    },
                ),
            )

        if request.FILES.get("file"):
            uploaded_file = request.FILES["file"]

            try:
                df = prepare_simulation_dataframe(uploaded_file)
            except ValueError as exc:
                return render(
                    request,
                    "riskwise/monte_carlo.html",
                    with_dataset_context(request, {"instruction": str(exc)}),
                )
            except Exception as exc:
                return render(
                    request,
                    "riskwise/monte_carlo.html",
                    with_dataset_context(request, {"instruction": f"Error reading file: {exc}"}),
                )

            save_uploaded_df_to_session(request, df)
            save_dataset_meta_to_session(request, uploaded_file.name, df)
            dataset_meta = _normalize_dataset_meta(load_dataset_meta_from_session(request), df=df)
            trade_count, date_start, date_end = get_dataset_meta(df)

            logger.info(
                "monte_carlo_dataset_loaded | user=%s | filename=%s | rows=%s",
                request.user.username,
                uploaded_file.name,
                trade_count,
            )

            return render(
                request,
                "riskwise/monte_carlo.html",
                with_dataset_context(
                    request,
                    {
                        "instruction": "Planning dataset loaded. Review the baseline and run a simulation when ready.",
                        "trade_count": trade_count,
                        "date_start": date_start,
                        "date_end": date_end,
                        "form_data": {},
                        "dataset_meta": dataset_meta,
                    },
                    df=df,
                ),
            )

        df = load_uploaded_df_from_session(request)
        if df is None or df.empty:
            logger.warning("monte_carlo_missing_dataset | user=%s", request.user.username)
            return render(
                request,
                "riskwise/monte_carlo.html",
                with_dataset_context(
                    request,
                    {"instruction": "Please load a planning dataset first."},
                ),
            )

        dataset_meta = _normalize_dataset_meta(load_dataset_meta_from_session(request), df=df)
        trade_count, date_start, date_end = get_dataset_meta(df)

        try:
            n_sim = safe_int(request.POST.get("num_simulations"))
            n_trades = safe_int(request.POST.get("num_trades"))
            if n_sim <= 0 or n_trades <= 0:
                raise ValueError
        except ValueError:
            return render(
                request,
                "riskwise/monte_carlo.html",
                with_dataset_context(
                    request,
                    {
                        "instruction": "Please enter valid numbers for simulations and trades.",
                        "trade_count": trade_count,
                        "date_start": date_start,
                        "date_end": date_end,
                        "dataset_meta": dataset_meta,
                    },
                    df=df,
                ),
            )

        try:
            start = safe_int(request.POST.get("range_start"), default=0)
            end = safe_int(request.POST.get("range_end"), default=len(df))
        except ValueError:
            start = 0
            end = len(df)

        start, end = clip_range(start, end, len(df))

        if start >= end:
            return render(
                request,
                "riskwise/monte_carlo.html",
                with_dataset_context(
                    request,
                    {
                        "instruction": "Range End must be greater than Range Start.",
                        "trade_count": trade_count,
                        "date_start": date_start,
                        "date_end": date_end,
                        "dataset_meta": dataset_meta,
                    },
                    df=df,
                ),
            )

        market_session = request.POST.get("session", "All")
        uk_start = request.POST.get("uk_start")
        uk_end = request.POST.get("uk_end")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        form_data = {
            "num_simulations": n_sim,
            "num_trades": n_trades,
            "range_start": start,
            "range_end": end,
            "session": market_session,
            "uk_start": uk_start,
            "uk_end": uk_end,
            "start_date": start_date,
            "end_date": end_date,
        }

        df_range = df.iloc[start:end].copy()
        df_range = filter_df_by_session(df_range, market_session, uk_start=uk_start, uk_end=uk_end)
        df_range = filter_df_by_date_range(df_range, start_date=start_date, end_date=end_date)

        profits_filtered = df_range["profit"].dropna().to_numpy(dtype=float)

        summary = build_run_summary(
            df_range=df_range,
            filtered_profit_count=len(profits_filtered),
            range_start=start,
            range_end=end,
            session_name=market_session,
        )

        filtered_trade_count, filtered_date_start, filtered_date_end = get_dataset_meta(df_range)
        summary["trade_count"] = filtered_trade_count
        summary["date_start"] = filtered_date_start
        summary["date_end"] = filtered_date_end

        if len(profits_filtered) == 0:
            logger.warning(
                "monte_carlo_no_filtered_results | user=%s | range_start=%s | range_end=%s | session=%s",
                request.user.username,
                start,
                end,
                market_session,
            )
            instruction = "No records matched your current filters."
        else:
            simulation_warning = build_simulation_warning(len(profits_filtered), n_sim, n_trades)
            results = run_simulation(
                profits=profits_filtered,
                num_simulations=n_sim,
                num_trades=n_trades,
                include_curves=False,
            )
            results["trades_used"] = profits_filtered.tolist()
            result_list = build_result_list(results)

            logger.info(
                "monte_carlo_completed | user=%s | filtered_rows=%s | num_simulations=%s | num_trades=%s",
                request.user.username,
                len(profits_filtered),
                n_sim,
                n_trades,
            )

    else:
        df = load_uploaded_df_from_session(request)
        if df is not None and not df.empty:
            trade_count, date_start, date_end = get_dataset_meta(df)
            dataset_meta = _normalize_dataset_meta(load_dataset_meta_from_session(request), df=df)

    return render(
        request,
        "riskwise/monte_carlo.html",
        with_dataset_context(
            request,
            {
                "instruction": instruction,
                "results": results,
                "result_list": result_list,
                "trade_count": trade_count,
                "summary": summary,
                "form_data": form_data,
                "date_start": date_start,
                "date_end": date_end,
                "simulation_warning": simulation_warning,
                "dataset_meta": dataset_meta,
                "suggested_next_step": "Compare scenarios side by side if the simulated distribution shows elevated downside pressure.",
            },
            df=load_uploaded_df_from_session(request),
        ),
    )


@login_required
def simulation_run_view(request):
    instruction = None
    message = None
    trade_count = None
    result_list = []
    equity_curve_base64 = None
    date_start = None
    date_end = None
    form_data = {}
    summary = None
    simulation_warning = None
    dataset_meta = load_dataset_meta_from_session(request)
    has_active_dataset = False
    has_simulation_result = False

    if request.method == "POST":
        if "reset" in request.POST:
            clear_uploaded_dataset_from_session(request)
            logger.info("stress_test_reset | user=%s", request.user.username)
            return render(
                request,
                "riskwise/simulation_run.html",
                with_dataset_context(
                    request,
                    {
                        "instruction": "Planning dataset reset successfully.",
                        "message": "Load a planning dataset first.",
                        "form_data": {},
                        "has_active_dataset": False,
                        "has_simulation_result": False,
                    },
                ),
            )

        if request.FILES.get("file"):
            uploaded_file = request.FILES["file"]

            try:
                df = prepare_simulation_dataframe(uploaded_file)
            except ValueError as exc:
                return render(
                    request,
                    "riskwise/simulation_run.html",
                    with_dataset_context(
                        request,
                        {
                            "instruction": str(exc),
                            "message": str(exc),
                            "has_active_dataset": False,
                            "has_simulation_result": False,
                        },
                    ),
                )
            except Exception as exc:
                return render(
                    request,
                    "riskwise/simulation_run.html",
                    with_dataset_context(
                        request,
                        {
                            "instruction": f"Error reading file: {exc}",
                            "message": f"Error reading file: {exc}",
                            "has_active_dataset": False,
                            "has_simulation_result": False,
                        },
                    ),
                )

            save_uploaded_df_to_session(request, df)
            save_dataset_meta_to_session(request, uploaded_file.name, df)
            dataset_meta = _normalize_dataset_meta(load_dataset_meta_from_session(request), df=df)
            trade_count, date_start, date_end = get_dataset_meta(df)

            logger.info(
                "stress_test_dataset_loaded | user=%s | filename=%s | rows=%s",
                request.user.username,
                uploaded_file.name,
                trade_count,
            )

            return render(
                request,
                "riskwise/simulation_run.html",
                with_dataset_context(
                    request,
                    {
                        "instruction": "Planning dataset loaded. Configure the settings below and run a stress test.",
                        "message": None,
                        "trade_count": trade_count,
                        "date_start": date_start,
                        "date_end": date_end,
                        "form_data": _default_simulation_form_data(trade_count),
                        "dataset_meta": dataset_meta,
                        "settings_sample_size": f"{trade_count:,}" if trade_count else "—",
                        "has_active_dataset": True,
                        "has_simulation_result": False,
                    },
                    df=df,
                ),
            )

        df = load_uploaded_df_from_session(request)
        if df is None or df.empty:
            logger.warning("stress_test_missing_dataset | user=%s", request.user.username)
            return render(
                request,
                "riskwise/simulation_run.html",
                with_dataset_context(
                    request,
                    {
                        "instruction": "Please load a planning dataset first.",
                        "message": "Please load a planning dataset first.",
                        "has_active_dataset": False,
                        "has_simulation_result": False,
                    },
                ),
            )

        has_active_dataset = True
        dataset_meta = _normalize_dataset_meta(load_dataset_meta_from_session(request), df=df)
        trade_count, date_start, date_end = get_dataset_meta(df)

        try:
            n_sim = safe_int(request.POST.get("num_simulations"))
            n_trades = safe_int(request.POST.get("num_trades"))
            if n_sim <= 0 or n_trades <= 0:
                raise ValueError
        except ValueError:
            return render(
                request,
                "riskwise/simulation_run.html",
                with_dataset_context(
                    request,
                    {
                        "instruction": "Please enter valid numbers for simulations and trades.",
                        "message": None,
                        "trade_count": trade_count,
                        "date_start": date_start,
                        "date_end": date_end,
                        "dataset_meta": dataset_meta,
                        "form_data": request.POST,
                        "has_active_dataset": True,
                        "has_simulation_result": False,
                    },
                    df=df,
                ),
            )

        try:
            start = safe_int(request.POST.get("range_start"), default=0)
            end = safe_int(request.POST.get("range_end"), default=len(df))
        except ValueError:
            start = 0
            end = len(df)

        start, end = clip_range(start, end, len(df))

        if start >= end:
            return render(
                request,
                "riskwise/simulation_run.html",
                with_dataset_context(
                    request,
                    {
                        "instruction": "Range End must be greater than Range Start.",
                        "message": None,
                        "trade_count": trade_count,
                        "date_start": date_start,
                        "date_end": date_end,
                        "dataset_meta": dataset_meta,
                        "form_data": request.POST,
                        "has_active_dataset": True,
                        "has_simulation_result": False,
                    },
                    df=df,
                ),
            )

        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")

        form_data = {
            "num_simulations": n_sim,
            "num_trades": n_trades,
            "range_start": start,
            "range_end": end,
            "start_date": start_date,
            "end_date": end_date,
        }

        df_range = df.iloc[start:end].copy()
        df_range = filter_df_by_date_range(df_range, start_date=start_date, end_date=end_date)

        profits = df_range["profit"].dropna().to_numpy(dtype=float)

        if len(profits) == 0:
            logger.warning(
                "stress_test_no_filtered_results | user=%s | range_start=%s | range_end=%s",
                request.user.username,
                start,
                end,
            )
            return render(
                request,
                "riskwise/simulation_run.html",
                with_dataset_context(
                    request,
                    {
                        "instruction": "No records matched your current filters.",
                        "message": None,
                        "trade_count": trade_count,
                        "form_data": form_data,
                        "date_start": date_start,
                        "date_end": date_end,
                        "dataset_meta": dataset_meta,
                        "has_active_dataset": True,
                        "has_simulation_result": False,
                    },
                    df=df,
                ),
            )

        simulation_warning = build_simulation_warning(len(profits), n_sim, n_trades)

        simulation_data = run_simulation(
            profits=profits,
            num_simulations=n_sim,
            num_trades=n_trades,
            include_curves=True,
        )

        curve_summary = build_equity_curve_summary(simulation_data["equity_curves"])

        band_chart_base64 = build_percentile_band_chart(
            curve_summary,
            title="Stress-Test Distribution",
        )

        histogram_chart_base64 = build_final_profit_histogram(
            curve_summary,
            title="Final Profit Distribution",
        )

        p10_final = curve_summary["p10_final"]
        p25_final = curve_summary["p25_final"]
        p50_final = curve_summary["p50_final"]
        p75_final = curve_summary["p75_final"]
        p90_final = curve_summary["p90_final"]
        positive_count = curve_summary["positive_count"]
        path_count = curve_summary["path_count"]
        positive_rate = curve_summary["positive_rate"]
        max_consecutive_losses = _calculate_max_consecutive_losses(simulation_data["equity_curves"])

        results_data = {
            "min": simulation_data["min"],
            "max": simulation_data["max"],
            "mean": simulation_data["mean"],
            "median": simulation_data["median"],
            "p05": simulation_data["p05"],
            "p95": simulation_data["p95"],
            "prob_positive": simulation_data["prob_positive"],
            "max_consecutive_losses": max_consecutive_losses,
        }

        result_list = build_result_list(
            {
                "min": results_data["min"],
                "max": results_data["max"],
                "mean": results_data["mean"],
                "median": results_data["median"],
                "p05": results_data["p05"],
                "p95": results_data["p95"],
                "prob_positive": results_data["prob_positive"],
            }
        )

        equity_curve_base64 = build_equity_curve_chart(
            simulation_data["equity_curves"],
            title="Stress-Test Distribution View",
        )

        summary = build_run_summary(
            df_range=df_range,
            filtered_profit_count=len(profits),
            range_start=start,
            range_end=end,
        )

        filtered_trade_count, filtered_date_start, filtered_date_end = get_dataset_meta(df_range)
        summary["trade_count"] = filtered_trade_count
        summary["date_start"] = filtered_date_start
        summary["date_end"] = filtered_date_end
        summary["source_file"] = dataset_meta.get("source_file") or dataset_meta.get("filename")

        avg_profit_per_trade = float(np.mean(profits)) if len(profits) > 0 else 0.0

        history_parameters = {
            **form_data,
            "dataset_meta": dataset_meta,
            "run_type": "stress_test",
        }

        SimulationHistory.objects.create(
            user=request.user,
            label="Stress-Test Run",
            parameters=history_parameters,
            results={
                **results_data,
                "p10_final": p10_final,
                "p25_final": p25_final,
                "p50_final": p50_final,
                "p75_final": p75_final,
                "p90_final": p90_final,
                "positive_count": positive_count,
                "path_count": path_count,
                "positive_rate": positive_rate,
            },
            chart_base64=band_chart_base64,
        )

        logger.info(
            "stress_test_history_saved | user=%s | label=%s | filtered_rows=%s | simulations=%s | trades=%s",
            request.user.username,
            "Stress-Test Run",
            len(profits),
            n_sim,
            n_trades,
        )

        context = {
            "trade_count": trade_count,
            "result_list": result_list,
            "equity_curve": equity_curve_base64,
            "chart_base64": equity_curve_base64,
            "plot_image": equity_curve_base64,
            "all_paths_chart_base64": equity_curve_base64,
            "band_chart_base64": band_chart_base64,
            "histogram_chart_base64": histogram_chart_base64,
            "form_data": form_data,
            "summary": summary,
            "date_start": date_start,
            "date_end": date_end,
            "simulation_warning": simulation_warning,
            "dataset_meta": dataset_meta,
            "avg_profit_per_trade": avg_profit_per_trade,
            "avg_profit_per_trade_display": f"{avg_profit_per_trade:,.2f}",
            "suggested_next_step": "Compare this run against alternative scenarios before increasing size.",
            "message": None,
            "has_active_dataset": True,
            "has_simulation_result": True,
            "median_final_profit": f"{p50_final:,.2f}",
            "p10_final_profit": f"{p10_final:,.2f}",
            "p90_final_profit": f"{p90_final:,.2f}",
            "positive_outcomes_pct": f"{positive_rate:.1f}",
            "positive_outcomes_label": f"{positive_count} out of {path_count} paths",
            "settings_runs": f"{n_sim:,}",
            "settings_trades": f"{n_trades:,}",
            "settings_sample_size": f"{len(profits):,}",
        }

        context.update(
            _build_simulation_presentation_context(
                results_data=results_data,
                num_simulations=n_sim,
                num_trades=n_trades,
                sample_size=len(profits),
                avg_profit_per_trade=avg_profit_per_trade,
                summary=summary,
            )
        )

        return render(
            request,
            "riskwise/simulation_run.html",
            with_dataset_context(request, context, df=df),
        )

    else:
        df = load_uploaded_df_from_session(request)
        if df is not None and not df.empty:
            has_active_dataset = True
            trade_count, date_start, date_end = get_dataset_meta(df)
            dataset_meta = _normalize_dataset_meta(load_dataset_meta_from_session(request), df=df)

            return render(
                request,
                "riskwise/simulation_run.html",
                with_dataset_context(
                    request,
                    {
                        "trade_count": trade_count,
                        "date_start": date_start,
                        "date_end": date_end,
                        "form_data": _default_simulation_form_data(trade_count),
                        "instruction": "Reference dataset loaded. Configure the settings below and run a stress test.",
                        "message": None,
                        "dataset_meta": dataset_meta,
                        "settings_sample_size": f"{trade_count:,}" if trade_count else "—",
                        "has_active_dataset": True,
                        "has_simulation_result": False,
                    },
                    df=df,
                ),
            )

    return render(
        request,
        "riskwise/simulation_run.html",
        with_dataset_context(
            request,
            {
                "trade_count": trade_count,
                "date_start": date_start,
                "date_end": date_end,
                "form_data": _default_simulation_form_data(trade_count),
                "instruction": "Load a planning dataset first, then run a stress test.",
                "message": "Load a planning dataset first, then run a stress test.",
                "dataset_meta": dataset_meta,
                "has_active_dataset": False,
                "has_simulation_result": False,
            },
            df=load_uploaded_df_from_session(request),
        ),
    )


@login_required
def simulation_scenario_view(request):
    template_name = "riskwise/simulation_scenario.html"
    persistence_note = (
        "Scenario comparison results are not yet persisted to history in the current public release."
    )

    def empty_form_data():
        return {"1": {}, "2": {}, "3": {}}

    def render_scenario_page(context, df=None):
        base_context = {
            "instruction": None,
            "trade_count": None,
            "date_start": None,
            "date_end": None,
            "form_data": empty_form_data(),
            "scenarios": [],
            "dataset_meta": {},
            "scenario_persistence_note": persistence_note,
            "best_scenario": None,
        }
        base_context.update(context)
        return render(
            request,
            template_name,
            with_dataset_context(request, base_context, df=df),
        )

    def build_scenario_label(
        scenario_id: str,
        n_trades: int,
        start: int,
        end: int,
        total_count: int,
        start_date: str,
        end_date: str,
    ) -> str:
        if start_date or end_date:
            return f"Scenario {scenario_id} — Filtered Period"
        if start > 0 or end < total_count:
            return f"Scenario {scenario_id} — Range Filtered"
        if total_count and n_trades >= max(10, int(total_count * 0.60)):
            return f"Scenario {scenario_id} — Long Horizon"
        if total_count and n_trades <= max(5, int(total_count * 0.20)):
            return f"Scenario {scenario_id} — Short Horizon"
        if scenario_id == "1":
            return "Scenario 1 — Base Case"
        return f"Scenario {scenario_id} — Comparison Case"

    def build_setup_note(
        n_sim: int,
        n_trades: int,
        start: int,
        end: int,
        start_date: str,
        end_date: str,
    ) -> str:
        parts = [f"{n_sim:,} runs", f"{n_trades} trades/path"]

        if start_date or end_date:
            if start_date and end_date:
                parts.append(f"{start_date} to {end_date}")
            elif start_date:
                parts.append(f"from {start_date}")
            else:
                parts.append(f"until {end_date}")
        elif start > 0 or end > 0:
            parts.append(f"range {start} to {end}")

        return " · ".join(parts)

    def normalize(value: float, values: list[float]) -> float:
        if not values:
            return 1.0
        low = min(values)
        high = max(values)
        if high == low:
            return 1.0
        return (value - low) / (high - low)

    def build_delta_note(current: dict, best: dict) -> str:
        if current is best:
            return "Leads the current comparison on combined downside resilience, reliability, and median outcome."

        prob_gap = current["prob_positive"] - best["prob_positive"]
        median_gap = current["median"] - best["median"]
        p05_gap = current["p05"] - best["p05"]

        prob_text = (
            f"{abs(prob_gap):.2f} percentage points {'lower' if prob_gap < 0 else 'higher'}"
        )
        median_text = (
            f"${abs(median_gap):,.2f} {'below' if median_gap < 0 else 'above'}"
        )
        p05_text = (
            f"${abs(p05_gap):,.2f} {'weaker' if p05_gap < 0 else 'stronger'}"
        )

        return (
            f"Median is {median_text} than the leading setup, positive probability is "
            f"{prob_text}, and 5th-percentile downside is {p05_text}."
        )

    def build_best_summary(best: dict, runner_up: dict | None) -> str:
        if runner_up is None:
            return "Only configured scenario in the current comparison set."

        prob_gap = best["prob_positive"] - runner_up["prob_positive"]
        p05_gap = best["p05"] - runner_up["p05"]
        median_gap = best["median"] - runner_up["median"]

        return (
            f"Leads the next-best setup by {prob_gap:.2f} percentage points on positive probability, "
            f"${p05_gap:,.2f} on 5th-percentile downside, and ${median_gap:,.2f} on median outcome."
        )

    if request.method == "POST":
        if "reset" in request.POST:
            clear_uploaded_dataset_from_session(request)
            logger.info("scenario_compare_reset | user=%s", request.user.username)
            return render_scenario_page(
                {
                    "instruction": "Planning dataset reset successfully.",
                }
            )

        if request.FILES.get("file"):
            uploaded_file = request.FILES["file"]

            try:
                df = prepare_simulation_dataframe(uploaded_file)
            except ValueError as exc:
                return render_scenario_page(
                    {
                        "instruction": str(exc),
                    }
                )
            except Exception as exc:
                return render_scenario_page(
                    {
                        "instruction": f"Error reading file: {exc}",
                    }
                )

            save_uploaded_df_to_session(request, df)
            save_dataset_meta_to_session(request, uploaded_file.name, df)

            trade_count, date_start, date_end = get_dataset_meta(df)
            dataset_meta = _normalize_scenario_dataset_meta(
                _normalize_dataset_meta(load_dataset_meta_from_session(request), df=df),
                trade_count=trade_count,
                date_start=date_start,
                date_end=date_end,
            )

            logger.info(
                "scenario_compare_dataset_loaded | user=%s | filename=%s | rows=%s",
                request.user.username,
                uploaded_file.name,
                trade_count,
            )

            return render_scenario_page(
                {
                    "instruction": "Planning dataset loaded. You can now compare scenarios side by side.",
                    "trade_count": trade_count,
                    "date_start": date_start,
                    "date_end": date_end,
                    "dataset_meta": dataset_meta,
                },
                df=df,
            )

        df = load_uploaded_df_from_session(request)
        if df is None or df.empty:
            logger.warning("scenario_compare_missing_dataset | user=%s", request.user.username)
            return render_scenario_page(
                {
                    "instruction": "Please load a planning dataset first.",
                }
            )

        trade_count, date_start, date_end = get_dataset_meta(df)
        dataset_meta = _normalize_scenario_dataset_meta(
            _normalize_dataset_meta(load_dataset_meta_from_session(request), df=df),
            trade_count=trade_count,
            date_start=date_start,
            date_end=date_end,
        )

        scenarios = []
        form_data = empty_form_data()

        for i in ("1", "2", "3"):
            label = f"Scenario {i}"

            n_sim_raw = request.POST.get(f"num_simulations_{i}", "")
            n_trades_raw = request.POST.get(f"num_trades_{i}", "")
            start_raw = request.POST.get(f"range_start_{i}", "")
            end_raw = request.POST.get(f"range_end_{i}", "")
            start_date_raw = request.POST.get(f"start_date_{i}", "")
            end_date_raw = request.POST.get(f"end_date_{i}", "")

            form_data[i] = {
                "num_simulations": n_sim_raw,
                "num_trades": n_trades_raw,
                "range_start": start_raw,
                "range_end": end_raw,
                "start_date": start_date_raw,
                "end_date": end_date_raw,
            }

            try:
                if not n_sim_raw or not n_trades_raw:
                    scenarios.append(
                        {
                            "label": label,
                            "error": "Skipped: no parameters provided.",
                        }
                    )
                    continue

                n_sim = safe_int(n_sim_raw)
                n_trades = safe_int(n_trades_raw)
                start = safe_int(start_raw, default=0)
                end = safe_int(end_raw, default=len(df))

                if n_sim <= 0 or n_trades <= 0:
                    scenarios.append(
                        {
                            "label": label,
                            "error": "Simulation counts must be greater than zero.",
                        }
                    )
                    continue

                start, end = clip_range(start, end, len(df))
                if start >= end:
                    scenarios.append(
                        {
                            "label": label,
                            "error": "Range End must be greater than Range Start.",
                        }
                    )
                    continue

                display_label = build_scenario_label(
                    scenario_id=i,
                    n_trades=n_trades,
                    start=start,
                    end=end,
                    total_count=len(df),
                    start_date=start_date_raw,
                    end_date=end_date_raw,
                )
                form_data[i]["display_label"] = display_label

                df_range = df.iloc[start:end].copy()
                df_range = filter_df_by_date_range(
                    df_range,
                    start_date=start_date_raw,
                    end_date=end_date_raw,
                )

                profits = df_range["profit"].dropna().to_numpy(dtype=float)

                if len(profits) == 0:
                    scenarios.append(
                        {
                            "label": display_label,
                            "error": "No records matched filters.",
                        }
                    )
                    continue

                simulation_data = run_simulation(
                    profits=profits,
                    num_simulations=n_sim,
                    num_trades=n_trades,
                    include_curves=True,
                )

                curve_summary = build_equity_curve_summary(simulation_data["equity_curves"])

                band_chart = build_percentile_band_chart(
                    curve_summary,
                    title=f"{display_label} Distribution View",
                )

                histogram_chart = build_final_profit_histogram(
                    curve_summary,
                    title=f"{display_label} Final Profit Distribution",
                )

                scenarios.append(
                    {
                        "label": display_label,
                        "scenario_id": i,
                        "setup_note": build_setup_note(
                            n_sim=n_sim,
                            n_trades=n_trades,
                            start=start,
                            end=end,
                            start_date=start_date_raw,
                            end_date=end_date_raw,
                        ),
                        "min": simulation_data["min"],
                        "max": simulation_data["max"],
                        "mean": simulation_data["mean"],
                        "median": simulation_data["median"],
                        "p05": simulation_data["p05"],
                        "p95": simulation_data["p95"],
                        "prob_positive": simulation_data["prob_positive"],
                        "p10_final": curve_summary["p10_final"],
                        "p25_final": curve_summary["p25_final"],
                        "p50_final": curve_summary["p50_final"],
                        "p75_final": curve_summary["p75_final"],
                        "p90_final": curve_summary["p90_final"],
                        "positive_rate": curve_summary["positive_rate"],
                        "positive_count": curve_summary["positive_count"],
                        "path_count": curve_summary["path_count"],
                        "chart": band_chart,
                        "histogram_chart": histogram_chart,
                        "warning": build_simulation_warning(len(profits), n_sim, n_trades),
                        "filtered_trade_count": len(profits),
                        "range_start": start,
                        "range_end": end,
                        "start_date": start_date_raw,
                        "end_date": end_date_raw,
                        "num_simulations": n_sim,
                        "num_trades": n_trades,
                    }
                )

            except Exception as exc:
                scenarios.append(
                    {
                        "label": label,
                        "error": f"Error: {exc}",
                    }
                )

        successful_scenarios = [s for s in scenarios if not s.get("error")]

        best_scenario = None
        if successful_scenarios:
            prob_values = [s["prob_positive"] for s in successful_scenarios]
            median_values = [s["median"] for s in successful_scenarios]
            p05_values = [s["p05"] for s in successful_scenarios]

            for scenario in successful_scenarios:
                score = (
                    0.40 * normalize(scenario["prob_positive"], prob_values)
                    + 0.35 * normalize(scenario["p05"], p05_values)
                    + 0.25 * normalize(scenario["median"], median_values)
                )
                scenario["decision_score"] = score * 100

            ranked = sorted(
                successful_scenarios,
                key=lambda s: (
                    s["decision_score"],
                    s["prob_positive"],
                    s["p05"],
                    s["median"],
                ),
                reverse=True,
            )

            best_scenario = ranked[0]
            runner_up = ranked[1] if len(ranked) > 1 else None

            for rank, scenario in enumerate(ranked, start=1):
                scenario["rank"] = rank
                scenario["is_best"] = rank == 1

                if scenario["is_best"]:
                    scenario["status_label"] = "Most defensible"
                    scenario["status_tone"] = "success"
                elif rank == 2 and scenario["decision_score"] >= 55:
                    scenario["status_label"] = "Balanced alternative"
                    scenario["status_tone"] = "info"
                elif scenario["prob_positive"] >= 60:
                    scenario["status_label"] = "Watchlist"
                    scenario["status_tone"] = "warning"
                else:
                    scenario["status_label"] = "Fragile setup"
                    scenario["status_tone"] = "danger"

                scenario["delta_note"] = build_delta_note(scenario, best_scenario)

            best_scenario["summary_reason"] = build_best_summary(best_scenario, runner_up)

            error_scenarios = [s for s in scenarios if s.get("error")]
            scenarios = ranked + error_scenarios

            logger.info(
                "scenario_compare_completed | user=%s | successful_scenarios=%s | best_scenario=%s",
                request.user.username,
                len(successful_scenarios),
                best_scenario["label"] if best_scenario else "none",
            )

        return render_scenario_page(
            {
                "trade_count": trade_count,
                "date_start": date_start,
                "date_end": date_end,
                "form_data": form_data,
                "scenarios": scenarios,
                "dataset_meta": dataset_meta,
                "best_scenario": best_scenario,
            },
            df=df,
        )

    df = load_uploaded_df_from_session(request)
    if df is not None and not df.empty:
        trade_count, date_start, date_end = get_dataset_meta(df)
        dataset_meta = _normalize_scenario_dataset_meta(
            _normalize_dataset_meta(load_dataset_meta_from_session(request), df=df),
            trade_count=trade_count,
            date_start=date_start,
            date_end=date_end,
        )

        return render_scenario_page(
            {
                "trade_count": trade_count,
                "date_start": date_start,
                "date_end": date_end,
                "dataset_meta": dataset_meta,
            },
            df=df,
        )

    return render_scenario_page({})
