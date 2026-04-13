from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from ..forms import LotSizeForm, RiskPerTradeForm, SLTPForm, StrategyRiskForm
from ..services import (
    build_trade_risk_warning,
    calculate_lot_size,
    calculate_sltp,
    calculate_strategy_risk,
    calculate_trade_risk,
    with_dataset_context,
)
from .shared import (
    _build_lot_size_context,
    _build_sltp_context,
    _build_strategy_risk_context,
    _build_trade_risk_context,
)


@login_required
def lot_size_calculator(request):
    result = None
    form = LotSizeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        result = calculate_lot_size(
            lot_size=form.cleaned_data["lot_size"],
            pip_distance=form.cleaned_data["pip_distance"],
            pip_value=form.cleaned_data["pip_value"],
        )

    context = _build_lot_size_context(form, result)

    return render(
        request,
        "riskwise/lot_size.html",
        with_dataset_context(request, context),
    )



@login_required
def risk_per_trade_calculator(request):
    result = None
    risk_warning = None
    form = RiskPerTradeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        result = calculate_trade_risk(
            account_balance=form.cleaned_data["account_balance"],
            lot_size=form.cleaned_data["lot_size"],
            pip_value=form.cleaned_data["pip_value"],
            stop_loss_pips=form.cleaned_data["stop_loss_pips"],
        )
        risk_warning = build_trade_risk_warning(result["risk_percent"])

    context = _build_trade_risk_context(form, result, risk_warning)

    return render(
        request,
        "riskwise/risk_per_trade.html",
        with_dataset_context(request, context),
    )



@login_required
def strategy_risk_calculator(request):
    result = None
    form = StrategyRiskForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        result = calculate_strategy_risk(
            base_lot=form.cleaned_data["base_lot"],
            win_rate=form.cleaned_data["win_rate"],
            rr=form.cleaned_data["rr"],
            volatility=form.cleaned_data["volatility"],
        )

    context = _build_strategy_risk_context(form, result)

    return render(
        request,
        "riskwise/strategy_risk.html",
        with_dataset_context(request, context),
    )



@login_required
def sltp_calculator(request):
    result = None
    form = SLTPForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        result = calculate_sltp(
            entry=form.cleaned_data["entry"],
            stop_loss=form.cleaned_data["stop_loss"],
            take_profit=form.cleaned_data["take_profit"],
            lot_size=form.cleaned_data["lot_size"],
            pip_value=form.cleaned_data["pip_value"],
        )

    context = _build_sltp_context(form, result)

    return render(
        request,
        "riskwise/sltp.html",
        with_dataset_context(request, context),
    )

