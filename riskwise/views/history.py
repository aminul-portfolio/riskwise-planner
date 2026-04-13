from __future__ import annotations

import base64
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from ..models import SimulationHistory
from ..services import slug_filename, with_dataset_context
from .shared import _format_int, _format_number, _format_percent

logger = logging.getLogger("riskwise")


def _clean_label(value, fallback="—"):
    if value in (None, "", "None"):
        return fallback
    return str(value).replace("_", " ").strip().title()


def _display_run_type(run):
    run_type = None
    if isinstance(getattr(run, "parameters", None), dict):
        run_type = run.parameters.get("run_type")
    return _clean_label(run_type, "Saved Run")


def _format_metric_value(key, value):
    if value in (None, "", [], {}, ()):
        return "—"

    percent_keys = {"prob_positive", "positive_rate", "win_rate", "risk_percent"}
    integer_keys = {
        "num_simulations",
        "num_trades",
        "range_start",
        "range_end",
        "trade_count",
        "records_loaded",
        "positive_count",
        "path_count",
        "filtered_profit_count",
    }

    if key in percent_keys:
        return _format_percent(value, places=2, already_scaled=True)
    if key in integer_keys:
        return _format_int(value)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return _format_number(value, places=2)
    if isinstance(value, str):
        return value
    return str(value)


def _preferred_result_value(results, *keys):
    if not isinstance(results, dict):
        return "—"

    for key in keys:
        if key in results and results[key] not in (None, ""):
            return _format_metric_value(key, results[key])

    return "—"


def _flatten_dict_for_display(data, parent_key=""):
    items = []

    if not isinstance(data, dict):
        return items

    for key, value in data.items():
        full_key = f"{parent_key}.{key}" if parent_key else key

        if isinstance(value, dict):
            items.extend(_flatten_dict_for_display(value, full_key))
        elif isinstance(value, list):
            if key == "columns":
                items.append(("Detected Columns", ", ".join(str(v) for v in value) if value else "—"))
            else:
                items.append((_clean_label(full_key), ", ".join(str(v) for v in value) if value else "—"))
        else:
            items.append((_clean_label(full_key), _format_metric_value(key, value)))

    return items


def _build_archive_card_context(run):
    params = run.parameters if isinstance(run.parameters, dict) else {}
    results = run.results if isinstance(run.results, dict) else {}
    dataset_meta = params.get("dataset_meta", {}) if isinstance(params.get("dataset_meta"), dict) else {}

    run.display_run_type = _display_run_type(run)
    run.display_source_file = dataset_meta.get("filename") or "—"
    run.display_num_simulations = _format_metric_value("num_simulations", params.get("num_simulations"))
    run.display_num_trades = _format_metric_value("num_trades", params.get("num_trades"))
    run.display_range = (
        f'{_format_metric_value("range_start", params.get("range_start"))} to '
        f'{_format_metric_value("range_end", params.get("range_end"))}'
        if params.get("range_start") is not None or params.get("range_end") is not None
        else "—"
    )

    run.display_date_range = (
        f'{dataset_meta.get("date_start", "—")} to {dataset_meta.get("date_end", "—")}'
        if dataset_meta.get("date_start") or dataset_meta.get("date_end")
        else "—"
    )

    run.display_median = _preferred_result_value(results, "p50_final", "median")
    run.display_tail_risk = _preferred_result_value(results, "p10_final", "p05")
    run.display_upper_band = _preferred_result_value(results, "p90_final", "p95")
    run.display_positive_rate = _preferred_result_value(results, "positive_rate", "prob_positive")
    run.display_p25 = _preferred_result_value(results, "p25_final")
    run.display_p75 = _preferred_result_value(results, "p75_final")

    run.has_chart_preview = bool(getattr(run, "chart_base64", None))
    return run


def _build_detail_context(run):
    params = run.parameters if isinstance(run.parameters, dict) else {}
    results = run.results if isinstance(run.results, dict) else {}
    dataset_meta = params.get("dataset_meta", {}) if isinstance(params.get("dataset_meta"), dict) else {}

    summary_items = [
        {"label": "Run Label", "value": run.label or "—"},
        {"label": "Run Type", "value": _display_run_type(run)},
        {"label": "Saved At", "value": run.created_at.strftime("%d %b %Y, %H:%M") if run.created_at else "—"},
        {"label": "Source File", "value": dataset_meta.get("filename", "—")},
        {"label": "Median Outcome", "value": _preferred_result_value(results, "p50_final", "median")},
        {"label": "Tail Risk", "value": _preferred_result_value(results, "p10_final", "p05")},
        {"label": "Upper Band", "value": _preferred_result_value(results, "p90_final", "p95")},
        {"label": "Positive %", "value": _preferred_result_value(results, "positive_rate", "prob_positive")},
    ]

    dataset_meta_items = [
        {"label": "Source File", "value": dataset_meta.get("filename", "—")},
        {"label": "Trade Count", "value": _format_metric_value("trade_count", dataset_meta.get("trade_count"))},
        {"label": "Start Date", "value": dataset_meta.get("date_start", "—")},
        {"label": "End Date", "value": dataset_meta.get("date_end", "—")},
        {"label": "Has Profit Field", "value": "Yes" if dataset_meta.get("has_profit") is True else ("No" if dataset_meta.get("has_profit") is False else "Unknown")},
        {"label": "Column Count", "value": _format_int(len(dataset_meta.get("columns", []))) if dataset_meta.get("columns") else "—"},
    ]

    params_items = _flatten_dict_for_display(params)
    results_items = _flatten_dict_for_display(results)

    return {
        "summary_items": summary_items,
        "dataset_meta_items": dataset_meta_items,
        "params_items": params_items,
        "results_items": results_items,
    }


@login_required
def simulation_history_view(request):
    query = request.GET.get("q", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    page_number = request.GET.get("page")

    qs = SimulationHistory.objects.filter(user=request.user)

    if query:
        qs = qs.filter(
            Q(label__icontains=query)
            | Q(parameters__icontains=query)
            | Q(results__icontains=query)
        )

    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    qs = qs.order_by("-created_at")
    paginator = Paginator(qs, 6)
    page_obj = paginator.get_page(page_number)
    history_items = [_build_archive_card_context(item) for item in page_obj]

    logger.info(
        "history_page_rendered | user=%s | query=%s | date_from=%s | date_to=%s | page=%s | count=%s",
        request.user.username,
        query or "none",
        date_from or "none",
        date_to or "none",
        page_obj.number,
        len(history_items),
    )

    return render(
        request,
        "riskwise/simulation_history.html",
        with_dataset_context(
            request,
            {
                "history_items": history_items,
                "simulations": history_items,
                "page_obj": page_obj,
                "query": query,
                "date_from": date_from,
                "date_to": date_to,
            },
        ),
    )


@login_required
def simulation_download_json_view(request, pk):
    sim = get_object_or_404(SimulationHistory, pk=pk, user=request.user)

    payload = {
        "label": sim.label,
        "created_at": sim.created_at.isoformat(),
        "parameters": sim.parameters,
        "results": sim.results,
    }

    logger.info(
        "history_download_json | user=%s | simulation_id=%s | label=%s",
        request.user.username,
        sim.pk,
        sim.label,
    )

    response = HttpResponse(
        json.dumps(payload, indent=2),
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="{slug_filename(sim.label, ".json")}"'
    return response


@login_required
def simulation_download_chart_view(request, pk):
    sim = get_object_or_404(SimulationHistory, pk=pk, user=request.user)

    if not sim.chart_base64:
        logger.warning(
            "history_download_chart_missing | user=%s | simulation_id=%s | label=%s",
            request.user.username,
            sim.pk,
            sim.label,
        )
        messages.error(request, "No saved chart is available for this planning run.")
        return redirect("simulation_detail", pk=sim.pk)

    logger.info(
        "history_download_chart | user=%s | simulation_id=%s | label=%s",
        request.user.username,
        sim.pk,
        sim.label,
    )

    image_data = base64.b64decode(sim.chart_base64)
    response = HttpResponse(image_data, content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="{slug_filename(sim.label, ".png")}"'
    return response


@login_required
def simulation_detail_view(request, pk):
    sim = get_object_or_404(SimulationHistory, pk=pk, user=request.user)
    detail_context = _build_detail_context(sim)

    logger.info(
        "history_detail_rendered | user=%s | simulation_id=%s | label=%s",
        request.user.username,
        sim.pk,
        sim.label,
    )

    return render(
        request,
        "riskwise/simulation_detail.html",
        with_dataset_context(
            request,
            {
                "sim": sim,
                "run": sim,
                "chart_base64": sim.chart_base64,
                "detail_title": sim.label,
                **detail_context,
            },
        ),
    )


@login_required
def simulation_delete_view(request, pk):
    sim = get_object_or_404(SimulationHistory, pk=pk, user=request.user)

    if request.method == "POST":
        deleted_label = sim.label
        deleted_id = sim.pk
        sim.delete()

        logger.info(
            "history_delete_success | user=%s | simulation_id=%s | label=%s",
            request.user.username,
            deleted_id,
            deleted_label,
        )
        messages.success(request, "Saved planning run deleted successfully.")
        return redirect("simulation_history")

    logger.info(
        "history_delete_confirm_rendered | user=%s | simulation_id=%s | label=%s",
        request.user.username,
        sim.pk,
        sim.label,
    )

    return render(
        request,
        "riskwise/simulation_confirm_delete.html",
        with_dataset_context(
            request,
            {
                "sim": sim,
                "run": sim,
            },
        ),
    )
