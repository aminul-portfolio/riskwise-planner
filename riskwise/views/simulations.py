from __future__ import annotations

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

        results_data = {
            "min": simulation_data["min"],
            "max": simulation_data["max"],
            "mean": simulation_data["mean"],
            "median": simulation_data["median"],
            "p05": simulation_data["p05"],
            "p95": simulation_data["p95"],
            "prob_positive": simulation_data["prob_positive"],
        }

        result_list = build_result_list(results_data)

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

        avg_profit_per_trade = float(np.mean(profits)) if len(profits) > 0 else 0.0

        history_parameters = {
            **form_data,
            "dataset_meta": dataset_meta,
            "run_type": "stress_test",
        }

        SimulationHistory.objects.create(
            user=request.user,
            label="Stress-Test Plan",
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
            "suggested_next_step": "Compare alternative scenarios next to see how the baseline behaves under different assumptions.",
            "message": None,
            "has_active_dataset": True,
            "has_simulation_result": True,

            # top KPI strip
            "median_final_profit": f"{p50_final:,.2f}",
            "p10_final_profit": f"{p10_final:,.2f}",
            "p90_final_profit": f"{p90_final:,.2f}",
            "positive_outcomes_pct": f"{positive_rate:.1f}",
            "positive_outcomes_label": f"{positive_count} out of {path_count} paths",

            # settings / review
            "settings_runs": f"{n_sim:,}",
            "settings_trades": f"{n_trades:,}",
            "settings_sample_size": f"{len(profits):,}",

            # 5 percentile tiles
            "percentile_1_label": "P10",
            "percentile_1_value": f"{p10_final:,.2f}",
            "percentile_2_label": "P25",
            "percentile_2_value": f"{p25_final:,.2f}",
            "percentile_3_label": "Median",
            "percentile_3_value": f"{p50_final:,.2f}",
            "percentile_4_label": "P75",
            "percentile_4_value": f"{p75_final:,.2f}",
            "percentile_5_label": "P90",
            "percentile_5_value": f"{p90_final:,.2f}",
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
        }
        base_context.update(context)
        return render(
            request,
            template_name,
            with_dataset_context(request, base_context, df=df),
        )

    if request.method == "POST":
        if "reset" in request.POST:
            clear_uploaded_dataset_from_session(request)
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
                            "label": label,
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
                    title=f"{label} Distribution View",
                )

                histogram_chart = build_final_profit_histogram(
                    curve_summary,
                    title=f"{label} Final Profit Distribution",
                )

                scenarios.append(
                    {
                        "label": label,
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
                    }
                )

            except Exception as exc:
                scenarios.append(
                    {
                        "label": label,
                        "error": f"Error: {exc}",
                    }
                )

        return render_scenario_page(
            {
                "trade_count": trade_count,
                "date_start": date_start,
                "date_end": date_end,
                "form_data": form_data,
                "scenarios": scenarios,
                "dataset_meta": dataset_meta,
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

