from __future__ import annotations

from decimal import Decimal, InvalidOperation

from ..services import get_dataset_meta


def _safe_decimal(value):
    if value in (None, "", "None"):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None



def _format_number(value, places=2, default="—"):
    number = _safe_decimal(value)
    if number is None:
        return default
    return f"{number:,.{places}f}"



def _format_percent(value, places=2, already_scaled=False, default="—"):
    number = _safe_decimal(value)
    if number is None:
        return default
    if not already_scaled:
        number *= 100
    return f"{number:,.{places}f}%"



def _format_int(value, default="—"):
    number = _safe_decimal(value)
    if number is None:
        return default
    return f"{int(number):,}"



def _clean_meta_dict(raw_dict, allowed_keys=None, label_map=None):
    """
    Converts raw metadata into a display-safe dictionary.
    - removes blank values
    - removes nested raw blobs
    - applies optional label mapping
    """
    if not isinstance(raw_dict, dict):
        return {}

    label_map = label_map or {}
    cleaned = {}

    for key, value in raw_dict.items():
        if allowed_keys and key not in allowed_keys:
            continue

        if value in (None, "", [], {}, ()):
            continue

        if isinstance(value, (dict, list, tuple, set)):
            continue

        label = label_map.get(key, key.replace("_", " ").title())
        cleaned[label] = value

    return cleaned


def _normalize_dataset_meta(dataset_meta, df=None):
    meta = dict(dataset_meta or {})

    row_count = len(df) if df is not None and not df.empty else None
    _, derived_start, derived_end = (
        get_dataset_meta(df) if df is not None and not df.empty else (0, None, None)
    )

    meta.setdefault("source_file", meta.get("filename"))
    meta.setdefault("records_loaded", meta.get("trade_count") or row_count)
    meta.setdefault("trade_count", meta.get("records_loaded") or row_count)
    meta.setdefault("date_start", meta.get("date_start") or derived_start)
    meta.setdefault("date_end", meta.get("date_end") or derived_end)

    return meta



def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default



def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default



def _format_metric_number(value, decimals=2):
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "0.00"



def _build_empty_dashboard_context(message, dataset_meta=None):
    dataset_meta = dataset_meta or {}

    return {
        "message": message,
        "dataset_meta": dataset_meta,
        "planning_reference_notice": (
            "This dashboard becomes active once a planning dataset is loaded into the current session."
        ),
        "what_this_suggests": (
            "Load a reference dataset first, then review downside depth, edge quality, and scenario resilience."
        ),
        "primary_downside_concern": "No active planning dataset is available yet.",
        "planning_implication": "Risk signals cannot be assessed until a valid reference dataset is loaded.",
        "suggested_next_step": "Upload a planning dataset to activate the baseline review surface.",
        "insight_items": [
            {
                "variant": "warning",
                "label": "Current status",
                "text": "No planning dataset is active in this session.",
            },
            {
                "variant": "primary",
                "label": "Suggested next step",
                "text": "Upload a valid planning dataset to unlock the dashboard metrics.",
            },
        ],
        "decision_state": {
            "label": "Inactive",
            "tone": "neutral",
            "headline": "Planning baseline not yet loaded",
            "summary": "No active dataset is available for downside and scenario review.",
            "recommended_action": "Upload a valid dataset to begin baseline assessment.",
            "sample_note": "No observed outcome sample is available yet.",
        },
        "decision_strip": [
            {
                "label": "Risk posture",
                "value": "Unknown",
                "tone": "neutral",
                "detail": "A baseline cannot be assessed until a dataset is loaded.",
            },
            {
                "label": "Edge quality",
                "value": "Unknown",
                "tone": "neutral",
                "detail": "Profit factor and win-rate signals are unavailable.",
            },
            {
                "label": "Sample quality",
                "value": "Inactive",
                "tone": "neutral",
                "detail": "No observed outcomes loaded in the current session.",
            },
        ],
        "kpi_panels": [
            {
                "label": "Max Drawdown",
                "value": "—",
                "subtext": "Requires an active reference dataset",
                "tone": "neutral",
            },
            {
                "label": "Profit Factor",
                "value": "—",
                "subtext": "Requires wins and losses from the current dataset",
                "tone": "neutral",
            },
            {
                "label": "Win Rate",
                "value": "—",
                "subtext": "Requires observed outcomes from the current dataset",
                "tone": "neutral",
            },
            {
                "label": "Trade Count",
                "value": "0",
                "subtext": "No active planning sample loaded",
                "tone": "neutral",
            },
        ],
        "risk_checks": [
            {
                "title": "Capital Preservation",
                "body": "No downside profile can be assessed until a reference dataset is available.",
                "tone": "neutral",
            },
            {
                "title": "Planning Implication",
                "body": "Use the upload surface to load observed outcomes before making a new allocation decision.",
                "tone": "neutral",
            },
            {
                "title": "Operating Note",
                "body": "This dashboard is designed as a planning aid, not a post-trade journal.",
                "tone": "neutral",
            },
        ],
        "suggested_actions": [
            "Upload a valid planning dataset.",
            "Review downside depth and edge quality once the baseline is active.",
            "Run stress testing after the baseline metrics are available.",
        ],
        "dashboard_sample_size": 0,
        "dashboard_profit_factor": "—",
        "dashboard_win_rate": "—",
    }



def _build_dashboard_decision_context(
    *,
    total_profit,
    win_rate,
    max_drawdown,
    avg_risk,
    volatility,
    downside_percentile,
    avg_win,
    avg_loss,
    profit_factor,
    trade_count,
    primary_downside_concern,
    planning_implication,
    suggested_next_step,
):
    total_profit = float(total_profit or 0)
    win_rate = float(win_rate or 0)
    max_drawdown = float(max_drawdown or 0)
    avg_risk = float(avg_risk or 0)
    volatility = float(volatility or 0)
    downside_percentile = float(downside_percentile or 0)
    avg_win = float(avg_win or 0)
    avg_loss = float(avg_loss or 0)
    trade_count = int(trade_count or 0)

    pf_value = None if profit_factor in (None, "") else float(profit_factor)
    pf_display = f"{pf_value:.2f}" if pf_value is not None else "N/A"

    drawdown_depth = abs(max_drawdown)
    drawdown_to_profit_ratio = None
    if total_profit > 0:
        drawdown_to_profit_ratio = drawdown_depth / total_profit

    if trade_count >= 100:
        sample_label = "Strong"
        sample_tone = "success"
        sample_note = "Observed sample size is strong enough to support a more credible planning baseline."
    elif trade_count >= 40:
        sample_label = "Usable"
        sample_tone = "info"
        sample_note = "Observed sample size is usable, but scenario assumptions should still remain conservative."
    else:
        sample_label = "Thin"
        sample_tone = "warning"
        sample_note = "Observed sample size is limited, so planning confidence should remain restrained."

    if pf_value is None:
        edge_label = "Unknown"
        edge_tone = "warning"
        edge_detail = "Profit factor is not yet available from the current outcome mix."
    elif pf_value >= 1.40 and total_profit > 0 and win_rate >= 50:
        edge_label = "Constructive"
        edge_tone = "success"
        edge_detail = "Observed outcomes show a healthier balance between gains and losses."
    elif pf_value >= 1.10 and total_profit >= 0:
        edge_label = "Mixed"
        edge_tone = "warning"
        edge_detail = "Edge quality is workable, but not strong enough for aggressive assumptions."
    else:
        edge_label = "Fragile"
        edge_tone = "danger"
        edge_detail = "Current edge quality does not support a confident risk expansion decision."

    if total_profit <= 0:
        posture_label = "Elevated"
        posture_tone = "danger"
        posture_headline = "Current planning baseline needs caution"
    elif drawdown_to_profit_ratio is not None and drawdown_to_profit_ratio <= 0.50 and edge_tone == "success":
        posture_label = "Controlled"
        posture_tone = "success"
        posture_headline = "Risk posture looks relatively controlled"
    elif drawdown_to_profit_ratio is not None and drawdown_to_profit_ratio <= 1.00:
        posture_label = "Watchlist"
        posture_tone = "warning"
        posture_headline = "Risk posture is usable, but needs monitoring"
    else:
        posture_label = "Elevated"
        posture_tone = "danger"
        posture_headline = "Risk posture is elevated versus current baseline quality"

    if sample_label == "Thin" and posture_tone == "success":
        posture_label = "Watchlist"
        posture_tone = "warning"
        posture_headline = "Baseline looks promising, but the sample is still too thin for confidence"

    decision_summary = (
        f"Total profit is {_format_metric_number(total_profit)}, "
        f"win rate is {win_rate:.1f}%, "
        f"profit factor is {pf_display}, "
        f"and max drawdown reached {_format_metric_number(drawdown_depth)}."
    )

    recommended_action = suggested_next_step or (
        "Run a stress test and compare scenario outcomes before committing additional capital."
    )

    decision_state = {
        "label": posture_label,
        "tone": posture_tone,
        "headline": posture_headline,
        "summary": decision_summary,
        "recommended_action": recommended_action,
        "sample_note": sample_note,
    }

    decision_strip = [
        {
            "label": "Risk posture",
            "value": posture_label,
            "tone": posture_tone,
            "detail": f"Drawdown depth {_format_metric_number(drawdown_depth)} against total profit {_format_metric_number(total_profit)}",
        },
        {
            "label": "Edge quality",
            "value": edge_label,
            "tone": edge_tone,
            "detail": edge_detail,
        },
        {
            "label": "Sample quality",
            "value": sample_label,
            "tone": sample_tone,
            "detail": f"{trade_count} observed outcomes in the current planning baseline",
        },
    ]

    kpi_panels = [
        {
            "label": "Max Drawdown",
            "value": _format_metric_number(drawdown_depth),
            "subtext": "Deepest cumulative downside observed in the loaded baseline",
            "tone": posture_tone,
        },
        {
            "label": "Profit Factor",
            "value": pf_display,
            "subtext": "Gross gains divided by gross losses in the current dataset",
            "tone": edge_tone,
        },
        {
            "label": "Win Rate",
            "value": f"{win_rate:.1f}%",
            "subtext": "Share of profitable outcomes in the loaded reference sample",
            "tone": "success" if win_rate >= 50 else "warning",
        },
        {
            "label": "Trade Count",
            "value": str(trade_count),
            "subtext": "Number of observed outcomes behind this planning baseline",
            "tone": sample_tone,
        },
    ]

    risk_checks = [
        {
            "title": "Primary Downside Concern",
            "body": primary_downside_concern,
            "tone": "danger",
        },
        {
            "title": "Planning Implication",
            "body": planning_implication,
            "tone": "warning",
        },
        {
            "title": "Operating Note",
            "body": (
                "Use this surface to calibrate future allocation and scenario assumptions, "
                "not to claim forward performance certainty."
            ),
            "tone": "neutral",
        },
    ]

    suggested_actions = [
        recommended_action,
        "Run Monte Carlo stress testing to see how the baseline behaves under weaker sequences.",
        "Use scenario comparison before increasing size or committing new capital.",
    ]

    if trade_count < 40:
        suggested_actions.append(
            "Collect a larger observed sample before relying too heavily on this planning baseline."
        )

    if pf_value is not None and pf_value < 1.10:
        suggested_actions.append(
            "Review edge quality before using this dataset to justify more aggressive risk assumptions."
        )

    return {
        "decision_state": decision_state,
        "decision_strip": decision_strip,
        "kpi_panels": kpi_panels,
        "risk_checks": risk_checks,
        "suggested_actions": suggested_actions,
        "dashboard_sample_size": trade_count,
        "dashboard_profit_factor": pf_display,
        "dashboard_win_rate": f"{win_rate:.1f}",
        "dashboard_total_profit": _format_metric_number(total_profit),
        "dashboard_drawdown_depth": _format_metric_number(drawdown_depth),
        "dashboard_avg_risk": _format_metric_number(avg_risk),
        "dashboard_volatility": _format_metric_number(volatility),
        "dashboard_downside_percentile": _format_metric_number(downside_percentile),
        "dashboard_avg_win": _format_metric_number(avg_win),
        "dashboard_avg_loss": _format_metric_number(avg_loss),
    }



def _trade_risk_tone(risk_percent):
    if risk_percent is None:
        return "neutral"
    if risk_percent >= 5:
        return "danger"
    if risk_percent >= 2:
        return "warning"
    return "success"



def _build_lot_size_context(form, result):
    context = {
        "form": form,
        "result": result,
        "result_ready": bool(result),
    }

    if result:
        context.update(
            {
                "result_headline": "Position sizing estimate ready",
                "result_summary": (
                    "Use this output as an exposure reference, then validate the same setup with trade-risk controls."
                ),
                "result_items": [
                    {
                        "label": "Lot Size",
                        "value": result.get("lot_size"),
                        "format": "number",
                    },
                    {
                        "label": "Pip Distance",
                        "value": result.get("pip_distance"),
                        "format": "number",
                    },
                    {
                        "label": "Risk per Pip",
                        "value": result.get("risk_per_pip"),
                        "format": "currency",
                    },
                    {
                        "label": "Risk Amount",
                        "value": result.get("risk_amount"),
                        "format": "currency",
                    },
                ],
                "suggested_next_step": "Review the same setup in Trade Risk Controls before committing capital.",
            }
        )

    return context



def _build_trade_risk_context(form, result, risk_warning):
    context = {
        "form": form,
        "result": result,
        "risk_warning": risk_warning,
        "result_ready": bool(result),
    }

    if result:
        risk_percent = result.get("risk_percent")
        context.update(
            {
                "result_headline": "Trade risk estimate ready",
                "result_summary": (
                    "Use the account-risk percentage to judge whether the planned trade fits your capital-preservation rules."
                ),
                "risk_tone": _trade_risk_tone(risk_percent),
                "suggested_next_step": "Cross-check this setup with SL / TP planning or Strategy Review before entry.",
            }
        )

    return context



def _build_strategy_risk_context(form, result):
    context = {
        "form": form,
        "result": result,
        "result_ready": bool(result),
    }

    if result:
        context.update(
            {
                "result_headline": "Strategy review ready",
                "result_summary": (
                    "Use this output to pressure-check whether the strategy profile still supports disciplined capital allocation."
                ),
                "suggested_next_step": "Validate individual setups with Trade Risk Controls and SL / TP planning.",
            }
        )

    return context



def _build_sltp_context(form, result):
    context = {
        "form": form,
        "result": result,
        "result_ready": bool(result),
    }

    if result:
        context.update(
            {
                "result_headline": "SL / TP plan ready",
                "result_summary": (
                    "Review downside, reward, and the risk-reward ratio together before approving the setup."
                ),
                "result_items": [
                    {
                        "label": "Risk Amount",
                        "value": result.get("risk_amount"),
                        "format": "currency",
                    },
                    {
                        "label": "Reward Amount",
                        "value": result.get("reward_amount"),
                        "format": "currency",
                    },
                    {
                        "label": "R:R Ratio",
                        "value": result.get("rr_ratio"),
                        "format": "number",
                    },
                ],
                "suggested_next_step": "Validate the same setup in Trade Risk Controls before entry.",
            }
        )

    return context



def _format_sim_metric(value, decimals=2, suffix=""):
    try:
        return f"{float(value):,.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return "—"



def _build_simulation_presentation_context(
    *,
    results_data=None,
    num_simulations=None,
    num_trades=None,
    sample_size=None,
    avg_profit_per_trade=None,
    summary=None,
):
    results_data = results_data or {}

    min_value = float(results_data.get("min", 0) or 0)
    max_value = float(results_data.get("max", 0) or 0)
    mean_value = float(results_data.get("mean", 0) or 0)
    median_value = float(results_data.get("median", 0) or 0)
    p05_value = float(results_data.get("p05", 0) or 0)
    p95_value = float(results_data.get("p95", 0) or 0)
    prob_positive = float(results_data.get("prob_positive", 0) or 0)

    num_simulations = int(num_simulations or 0)
    num_trades = int(num_trades or 0)
    sample_size = int(sample_size or 0)
    avg_profit_per_trade = float(avg_profit_per_trade or 0)

    if p05_value >= 0 and prob_positive >= 60 and median_value > 0:
        simulation_posture_label = "Controlled"
        simulation_posture_tone = "success"
        simulation_posture_detail = "Weaker simulated paths remain relatively constructive."
        simulation_headline = "Simulation profile looks relatively controlled"
        simulation_recommendation = "Proceed cautiously, then compare scenarios before increasing allocation."
        action_gate_label = "Proceed Cautiously"
        action_gate_tone = "success"
        action_gate_detail = "The simulated downside profile is constructive, but still needs scenario confirmation."
    elif median_value > 0 and prob_positive >= 45:
        simulation_posture_label = "Watchlist"
        simulation_posture_tone = "warning"
        simulation_posture_detail = "Base-case behaviour is workable, but tail outcomes still need review."
        simulation_headline = "Simulation profile is usable, but needs caution"
        simulation_recommendation = "Review tail outcomes carefully and compare alternative assumptions before sizing up."
        action_gate_label = "Review"
        action_gate_tone = "warning"
        action_gate_detail = "Do not rely on average simulated results alone before changing exposure."
    else:
        simulation_posture_label = "Elevated"
        simulation_posture_tone = "danger"
        simulation_posture_detail = "Left-tail outcomes imply materially higher pressure under weaker sequencing."
        simulation_headline = "Simulation profile suggests elevated downside pressure"
        simulation_recommendation = "Reduce risk assumptions or compare more conservative scenarios before new allocation."
        action_gate_label = "Reduce Risk"
        action_gate_tone = "danger"
        action_gate_detail = "Tail outcomes show that weaker sequences may stress the current plan too heavily."

    percentile_tone = "success" if p05_value >= 0 else ("warning" if median_value > 0 else "danger")
    key_downside_value = _format_sim_metric(p05_value)
    key_downside_detail = "5th percentile simulated outcome across runs."

    simulation_summary = (
        f"Median simulated outcome is {_format_sim_metric(median_value)}, "
        f"5th percentile outcome is {_format_sim_metric(p05_value)}, "
        f"and {prob_positive:.1f}% of runs finish positive."
    )

    simulation_sample_note = (
        f"Built from {sample_size:,} filtered outcomes, "
        f"{num_simulations:,} simulations, and {num_trades:,} trades per path."
        if sample_size and num_simulations and num_trades
        else None
    )

    simulation_downside_concern = (
        "The left tail of the distribution remains the main concern, especially when weaker paths cluster below the median."
        if p05_value < 0
        else "Tail outcomes remain relatively stable, but should still be checked before increasing allocation."
    )

    simulation_planning_implication = (
        "Sizing should be calibrated for downside resilience, not just for the average simulated outcome."
    )

    simulation_operating_note = (
        "This simulation is a planning aid for downside-aware decision-making, not a guarantee of future path behaviour."
    )

    return {
        "simulation_headline": simulation_headline,
        "simulation_summary": simulation_summary,
        "simulation_recommendation": simulation_recommendation,
        "simulation_sample_note": simulation_sample_note,
        "simulation_posture_label": simulation_posture_label,
        "simulation_posture_tone": simulation_posture_tone,
        "simulation_posture_detail": simulation_posture_detail,
        "percentile_tone": percentile_tone,
        "key_downside_value": key_downside_value,
        "key_downside_detail": key_downside_detail,
        "action_gate_label": action_gate_label,
        "action_gate_tone": action_gate_tone,
        "action_gate_detail": action_gate_detail,
        "rw_kpi_1_label": "Median Outcome",
        "rw_kpi_1_value": _format_sim_metric(median_value),
        "rw_kpi_1_subtext": "Typical simulated result across all runs",
        "rw_kpi_1_tone": "success" if median_value > 0 else "warning",
        "rw_kpi_2_label": "5th Percentile",
        "rw_kpi_2_value": _format_sim_metric(p05_value),
        "rw_kpi_2_subtext": "Tail-risk view for weaker simulated paths",
        "rw_kpi_2_tone": percentile_tone,
        "rw_kpi_3_label": "Positive Runs",
        "rw_kpi_3_value": _format_sim_metric(prob_positive, decimals=1, suffix="%"),
        "rw_kpi_3_subtext": "Share of simulations finishing positive",
        "rw_kpi_3_tone": "success" if prob_positive >= 50 else "warning",
        "rw_kpi_4_label": "Simulation Count",
        "rw_kpi_4_value": f"{num_simulations:,}" if num_simulations else "—",
        "rw_kpi_4_subtext": "Number of simulated paths used in this run",
        "rw_kpi_4_tone": "info",
        "simulation_downside_concern": simulation_downside_concern,
        "simulation_planning_implication": simulation_planning_implication,
        "simulation_operating_note": simulation_operating_note,
        "percentile_1_label": "P5",
        "percentile_1_value": _format_sim_metric(p05_value),
        "percentile_2_label": "Median",
        "percentile_2_value": _format_sim_metric(median_value),
        "percentile_3_label": "Mean",
        "percentile_3_value": _format_sim_metric(mean_value),
        "percentile_4_label": "P95",
        "percentile_4_value": _format_sim_metric(p95_value),
        "settings_runs": f"{num_simulations:,}" if num_simulations else "—",
        "settings_trades": f"{num_trades:,}" if num_trades else "—",
        "settings_confidence": "Tail Review",
        "settings_sample_size": f"{sample_size:,}" if sample_size else "—",
        "next_step_1": simulation_recommendation,
        "next_step_2": "Compare this run against alternative scenarios before changing size.",
        "next_step_3": "Use the dashboard and simulation together, not in isolation.",
        "simulation_min_value": _format_sim_metric(min_value),
        "simulation_max_value": _format_sim_metric(max_value),
        "simulation_mean_value": _format_sim_metric(mean_value),
        "simulation_median_value": _format_sim_metric(median_value),
        "simulation_p05_value": _format_sim_metric(p05_value),
        "simulation_p95_value": _format_sim_metric(p95_value),
        "simulation_prob_positive": _format_sim_metric(prob_positive, decimals=1, suffix="%"),
        "avg_profit_per_trade_display": _format_sim_metric(avg_profit_per_trade),
    }


def _default_simulation_form_data(trade_count=0):
    trade_count = _safe_int(trade_count, 0)
    suggested_trades = min(trade_count, 100) if trade_count else 100

    return {
        "num_simulations": 1000,
        "num_trades": suggested_trades,
        "range_start": 0,
        "range_end": trade_count,
        "start_date": "",
        "end_date": "",
    }



def _normalize_scenario_dataset_meta(dataset_meta, trade_count=None, date_start=None, date_end=None):
    dataset_meta = dict(dataset_meta or {})
    dataset_meta["source_file"] = dataset_meta.get("source_file") or dataset_meta.get("filename")
    dataset_meta["records_loaded"] = (
        dataset_meta.get("records_loaded")
        or dataset_meta.get("trade_count")
        or trade_count
    )
    dataset_meta["trade_count"] = dataset_meta.get("trade_count") or dataset_meta.get("records_loaded") or trade_count
    dataset_meta["date_start"] = dataset_meta.get("date_start") or date_start
    dataset_meta["date_end"] = dataset_meta.get("date_end") or date_end
    return dataset_meta


