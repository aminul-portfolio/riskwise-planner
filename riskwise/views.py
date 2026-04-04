from io import BytesIO, StringIO
import base64
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    LotSizeForm,
    RiskPerTradeForm,
    ScreenshotForm,
    SLTPForm,
    StrategyRiskForm,
)
from .models import Screenshot, SimulationHistory, Trade


SESSION_DATASET_KEY = "uploaded_df"


def _normalise_columns(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def _read_uploaded_dataframe(uploaded_file):
    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")

    return _normalise_columns(df)


def _coalesce_column(df, target, candidates, default=None):
    """
    Ensure a target column exists by taking the first available candidate.
    """
    if target in df.columns:
        return df

    for candidate in candidates:
        if candidate in df.columns:
            df[target] = df[candidate]
            return df

    df[target] = default
    return df


def _attach_date_column(df):
    df = df.copy()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    elif "open" in df.columns:
        df["date"] = pd.to_datetime(df["open"], errors="coerce")
    elif "close" in df.columns:
        df["date"] = pd.to_datetime(df["close"], errors="coerce")
    else:
        df["date"] = pd.NaT

    return df


def _prepare_simulation_dataframe(uploaded_file):
    df = _read_uploaded_dataframe(uploaded_file)
    df = _attach_date_column(df)

    if "profit" not in df.columns:
        raise ValueError("Your file must have a 'profit' column.")

    df["profit"] = pd.to_numeric(df["profit"], errors="coerce")
    df = df.dropna(subset=["profit"]).copy()

    return df


def _save_uploaded_df_to_session(request, df):
    request.session[SESSION_DATASET_KEY] = df.to_json(orient="split", date_format="iso")
    request.session.modified = True


def _load_uploaded_df_from_session(request):
    raw = request.session.get(SESSION_DATASET_KEY)
    if not raw:
        return None

    # Primary format: new safe format
    try:
        df = pd.read_json(StringIO(raw), orient="split")
    except ValueError:
        # Fallback for older session values saved without orient="split"
        try:
            df = pd.read_json(StringIO(raw))
        except ValueError:
            return None

    df = _normalise_columns(df)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df = _attach_date_column(df)

    if "profit" in df.columns:
        df["profit"] = pd.to_numeric(df["profit"], errors="coerce")
        df = df.dropna(subset=["profit"]).copy()

    return df


def _get_dataset_meta(df):
    trade_count = len(df.index)
    date_start = None
    date_end = None

    if "date" in df.columns and df["date"].notna().any():
        dates = df["date"].dropna()
        date_start = dates.min().strftime("%Y-%m-%d %H:%M")
        date_end = dates.max().strftime("%Y-%m-%d %H:%M")

    return trade_count, date_start, date_end


def _clip_range(start, end, length):
    start = max(0, start)
    end = min(length, end)
    return start, end


def _build_equity_curve_chart(curves, title="Equity Curves"):
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("#111827")
    ax.set_facecolor("#0b1220")

    for curve in curves:
        ax.plot(curve, alpha=0.35, linewidth=0.8)

    ax.set_title(title, color="#e5e7eb", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Trade Number", color="#94a3b8", fontsize=10)
    ax.set_ylabel("Cumulative Profit", color="#94a3b8", fontsize=10)
    ax.tick_params(colors="#94a3b8", labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#243244")
    ax.grid(True, alpha=0.15, color="#94a3b8")

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", facecolor="#111827", dpi=120)
    buf.seek(0)
    chart_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()

    return chart_base64


def home(request):
    features = [
        {
            "title": "Upload Risk Dataset",
            "description": "Import CSV or Excel data to prepare position sizing, downside review, and simulation-backed planning surfaces.",
            "icon": "bi bi-upload",
            "color": "primary",
            "url": "/upload/",
            "button_text": "Upload Dataset",
        },
        {
            "title": "Capital Preservation Dashboard",
            "description": "Review downside-aware planning metrics, drawdown context, and risk signals in one place.",
            "icon": "bi bi-shield-check",
            "color": "success",
            "url": "/dashboard/",
            "button_text": "Open Risk Dashboard",
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
            "description": "Evaluate risk per trade using account balance, lot size, pip value, and stop-loss distance.",
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
            "description": "Stress-test risk assumptions through simulated outcome distributions and downside-aware planning review.",
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
            "title": "Simulation History",
            "description": "Review saved simulation runs for follow-up analysis, comparison, and audit-style tracking.",
            "icon": "bi bi-clock-history",
            "color": "secondary",
            "url": "/simulations/history/",
            "button_text": "Open History",
        },
    ]

    screenshots = Screenshot.objects.order_by("-uploaded_at")

    return render(
        request,
        "riskwise/home.html",
        {
            "features": features,
        },
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
            df = _read_uploaded_dataframe(uploaded_file)
        except ValueError as exc:
            return render(request, "riskwise/upload.html", {"error": str(exc)})
        except Exception as exc:
            return render(request, "riskwise/upload.html", {"error": f"Error reading file: {exc}"})

        # Map common source columns from trading exports
        df = _coalesce_column(df, "date", ["open", "close"], pd.NaT)
        df = _coalesce_column(df, "symbol", [], "UNKNOWN")
        df = _coalesce_column(df, "volume", [], 0)
        df = _coalesce_column(df, "entryprice", ["entry_price", "price"], 0)
        df = _coalesce_column(df, "exitprice", ["exit_price", "price_1"], 0)
        df = _coalesce_column(df, "profit", [], 0)
        df = _coalesce_column(df, "accounttype", ["account_type"], "Personal")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        df["entryprice"] = pd.to_numeric(df["entryprice"], errors="coerce").fillna(0)
        df["exitprice"] = pd.to_numeric(df["exitprice"], errors="coerce").fillna(0)
        df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0)
        df["symbol"] = df["symbol"].fillna("UNKNOWN").astype(str)
        df["accounttype"] = df["accounttype"].fillna("Personal").astype(str)

        trade_rows = []
        for _, row in df.iterrows():
            trade_date = row["date"].date() if pd.notnull(row["date"]) else None

            trade_rows.append(
                Trade(
                    user=request.user,
                    date=trade_date,
                    symbol=row["symbol"],
                    volume=row["volume"],
                    entry_price=row["entryprice"],
                    exit_price=row["exitprice"],
                    profit=row["profit"],
                    account_type=row["accounttype"].capitalize(),
                )
            )

        if trade_rows:
            Trade.objects.bulk_create(trade_rows)
            messages.success(request, f"{len(trade_rows)} trade records uploaded successfully.")
        else:
            messages.warning(request, "No rows were imported from the uploaded file.")

        return redirect("dashboard")

    return render(request, "riskwise/upload.html")


@login_required
def dashboard(request):
    trades = Trade.objects.filter(user=request.user).order_by("date", "id")

    if not trades.exists():
        return render(
            request,
            "riskwise/dashboard.html",
            {"message": "No trades uploaded yet."},
        )

    df = pd.DataFrame(list(trades.values()))

    if "profit" not in df.columns:
        return render(
            request,
            "riskwise/dashboard.html",
            {"message": "No profit data available."},
        )

    df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0)

    cumulative_profit = df["profit"].cumsum()
    running_peak = cumulative_profit.cummax()
    drawdown_series = cumulative_profit - running_peak

    wins = df[df["profit"] > 0]["profit"]
    losses = df[df["profit"] < 0]["profit"]

    total_profit = float(df["profit"].sum())
    win_rate = float((df["profit"] > 0).mean() * 100)
    max_drawdown = float(drawdown_series.min()) if not drawdown_series.empty else 0.0
    avg_risk = float(losses.mean()) if not losses.empty else 0.0
    volatility = float(df["profit"].std()) if len(df) > 1 else 0.0
    percentile_95 = float(np.percentile(df["profit"], 5)) if len(df) > 0 else 0.0
    avg_win = float(wins.mean()) if not wins.empty else 0.0
    avg_loss = float(losses.mean()) if not losses.empty else 0.0

    gross_profit = float(wins.sum()) if not wins.empty else 0.0
    gross_loss = abs(float(losses.sum())) if not losses.empty else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

    # Dataset provenance
    date_range_start = None
    date_range_end = None
    if "date" in df.columns:
        dates = pd.to_datetime(df["date"], errors="coerce").dropna()
        if not dates.empty:
            date_range_start = dates.min().strftime("%Y-%m-%d")
            date_range_end = dates.max().strftime("%Y-%m-%d")

    context = {
        "total_profit": total_profit,
        "win_rate": win_rate,
        "max_drawdown": max_drawdown,
        "avg_risk": avg_risk,
        "volatility": volatility,
        "percentile_95": percentile_95,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "trade_count": len(df),
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
    }
    return render(request, "riskwise/dashboard.html", context)


@login_required
def lot_size_calculator(request):
    result = None

    if request.method == "POST":
        form = LotSizeForm(request.POST)
        if form.is_valid():
            lot = form.cleaned_data["lot_size"]
            pip_distance = form.cleaned_data["pip_distance"]
            pip_value = form.cleaned_data["pip_value"]
            result = pip_distance * lot * pip_value
    else:
        form = LotSizeForm()

    return render(request, "riskwise/lot_size.html", {"form": form, "result": result})


@login_required
def risk_per_trade_calculator(request):
    result = None
    risk_warning = None

    if request.method == "POST":
        form = RiskPerTradeForm(request.POST)
        if form.is_valid():
            acc_balance = form.cleaned_data["account_balance"]
            lot = form.cleaned_data["lot_size"]
            pip_val = form.cleaned_data["pip_value"]
            sl_pips = form.cleaned_data["stop_loss_pips"]

            risk_amount = sl_pips * lot * pip_val
            risk_percent = (risk_amount / acc_balance) * 100 if acc_balance else None

            result = {
                "risk_amount": risk_amount,
                "risk_percent": risk_percent,
            }

            # Risk warning thresholds
            if risk_percent is not None:
                if risk_percent > 10:
                    risk_warning = {
                        "level": "high",
                        "message": "This trade risks over 10% of the account — this is well above standard capital preservation limits. Review position size before proceeding.",
                    }
                elif risk_percent > 5:
                    risk_warning = {
                        "level": "elevated",
                        "message": "This trade risks over 5% of the account — consider reducing position size to stay within common capital preservation thresholds.",
                    }
                elif risk_percent > 2:
                    risk_warning = {
                        "level": "caution",
                        "message": "This trade exceeds the commonly recommended 2% risk-per-trade guideline. Ensure this fits your broader risk plan.",
                    }
    else:
        form = RiskPerTradeForm()

    return render(request, "riskwise/risk_per_trade.html", {
        "form": form,
        "result": result,
        "risk_warning": risk_warning,
    })


@login_required
def strategy_risk_calculator(request):
    result = None

    if request.method == "POST":
        form = StrategyRiskForm(request.POST)
        if form.is_valid():
            base = form.cleaned_data["base_lot"]
            win = form.cleaned_data["win_rate"]
            rr = form.cleaned_data["rr"]
            vol = form.cleaned_data["volatility"]

            result = base * (win / 50) * (rr / 2) * (200 / vol) if vol else None
    else:
        form = StrategyRiskForm()

    return render(request, "riskwise/strategy_risk.html", {"form": form, "result": result})


@login_required
def sltp_calculator(request):
    result = None

    if request.method == "POST":
        form = SLTPForm(request.POST)
        if form.is_valid():
            entry = form.cleaned_data["entry"]
            sl = form.cleaned_data["stop_loss"]
            tp = form.cleaned_data["take_profit"]
            lot = form.cleaned_data["lot_size"]
            pip_value = form.cleaned_data["pip_value"]

            risk = abs(entry - sl) * lot * pip_value
            reward = abs(tp - entry) * lot * pip_value
            rr = reward / risk if risk != 0 else None

            result = {
                "risk": risk,
                "reward": reward,
                "rr": rr,
            }
    else:
        form = SLTPForm()

    return render(request, "riskwise/sltp.html", {"form": form, "result": result})


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

    if request.method == "POST":
        if "reset" in request.POST:
            request.session.pop(SESSION_DATASET_KEY, None)
            return render(
                request,
                "riskwise/monte_carlo.html",
                {
                    "instruction": "Form reset successfully.",
                    "form_data": {},
                },
            )

        if request.FILES.get("file"):
            uploaded_file = request.FILES["file"]

            try:
                df = _prepare_simulation_dataframe(uploaded_file)
            except ValueError as exc:
                return render(request, "riskwise/monte_carlo.html", {"instruction": str(exc)})
            except Exception as exc:
                return render(
                    request,
                    "riskwise/monte_carlo.html",
                    {"instruction": f"Error reading file: {exc}"},
                )

            _save_uploaded_df_to_session(request, df)
            trade_count, date_start, date_end = _get_dataset_meta(df)

            return render(
                request,
                "riskwise/monte_carlo.html",
                {
                    "trade_count": trade_count,
                    "date_start": date_start,
                    "date_end": date_end,
                    "form_data": {},
                },
            )

        df = _load_uploaded_df_from_session(request)
        if df is None or df.empty:
            instruction = "Please upload a data file first."
            return render(request, "riskwise/monte_carlo.html", {"instruction": instruction})

        trade_count, date_start, date_end = _get_dataset_meta(df)

        try:
            n_sim = int(request.POST.get("num_simulations", ""))
            n_trades = int(request.POST.get("num_trades", ""))
            if n_sim <= 0 or n_trades <= 0:
                raise ValueError
        except ValueError:
            instruction = "Please enter valid numbers for simulations and trades."
            return render(
                request,
                "riskwise/monte_carlo.html",
                {
                    "instruction": instruction,
                    "trade_count": trade_count,
                    "date_start": date_start,
                    "date_end": date_end,
                },
            )

        start = int(request.POST.get("range_start") or 0)
        end = int(request.POST.get("range_end") or len(df))
        start, end = _clip_range(start, end, len(df))

        if start >= end:
            instruction = "Range End must be greater than Range Start."
            return render(
                request,
                "riskwise/monte_carlo.html",
                {
                    "instruction": instruction,
                    "trade_count": trade_count,
                    "date_start": date_start,
                    "date_end": date_end,
                },
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

        if market_session != "All" and "date" in df_range.columns and df_range["date"].notna().any():
            if market_session == "UK":
                df_range = df_range[df_range["date"].dt.hour.between(8, 17)]
                if uk_start and uk_end:
                    try:
                        uk_start_int = int(uk_start)
                        uk_end_int = int(uk_end)
                        df_range = df_range[df_range["date"].dt.hour.between(uk_start_int, uk_end_int)]
                    except (TypeError, ValueError):
                        pass
            elif market_session == "US":
                df_range = df_range[df_range["date"].dt.hour.between(13, 22)]
            elif market_session == "Asia":
                df_range = df_range[df_range["date"].dt.hour.between(0, 7)]

        if start_date and end_date and "date" in df_range.columns:
            try:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                df_range = df_range[df_range["date"].between(start_dt, end_dt)]
            except Exception:
                pass

        profits_filtered = df_range["profit"].dropna().to_numpy()

        summary = {
            "range_start": start,
            "range_end": end,
            "session": market_session,
            "trade_count": len(profits_filtered),
            "date_start": None,
            "date_end": None,
        }

        if "date" in df_range.columns and df_range["date"].notna().any():
            filtered_dates = df_range["date"].dropna()
            summary["date_start"] = filtered_dates.min().strftime("%Y-%m-%d %H:%M")
            summary["date_end"] = filtered_dates.max().strftime("%Y-%m-%d %H:%M")

        if len(profits_filtered) == 0:
            instruction = "No trades matched your filters."
        else:
            ending_balances = []
            for _ in range(n_sim):
                sim = np.random.choice(profits_filtered, size=n_trades, replace=True)
                ending_balances.append(float(sim.sum()))

            results = {
                "min": float(np.min(ending_balances)),
                "max": float(np.max(ending_balances)),
                "median": float(np.median(ending_balances)),
                "prob_positive": float((np.array(ending_balances) > 0).mean() * 100),
                "trades_used": profits_filtered.tolist(),
            }

            result_list = [
                {
                    "key": "min",
                    "label": "Min Ending Balance",
                    "icon": "bi-currency-dollar",
                    "color": "danger",
                    "value": results["min"],
                    "is_percent": False,
                },
                {
                    "key": "max",
                    "label": "Max Ending Balance",
                    "icon": "bi-currency-dollar",
                    "color": "success",
                    "value": results["max"],
                    "is_percent": False,
                },
                {
                    "key": "median",
                    "label": "Median Ending Balance",
                    "icon": "bi-currency-dollar",
                    "color": "info",
                    "value": results["median"],
                    "is_percent": False,
                },
                {
                    "key": "prob_positive",
                    "label": "Probability of Profit",
                    "icon": "bi-emoji-smile",
                    "color": "primary",
                    "value": results["prob_positive"],
                    "is_percent": True,
                },
            ]

    else:
        df = _load_uploaded_df_from_session(request)
        if df is not None and not df.empty:
            trade_count, date_start, date_end = _get_dataset_meta(df)

    return render(
        request,
        "riskwise/monte_carlo.html",
        {
            "instruction": instruction,
            "results": results,
            "result_list": result_list,
            "trade_count": trade_count,
            "summary": summary,
            "form_data": form_data,
            "date_start": date_start,
            "date_end": date_end,
        },
    )


@login_required
def simulation_run_view(request):
    instruction = None
    trade_count = None
    result_list = []
    equity_curve_base64 = None
    date_start = None
    date_end = None
    form_data = {}
    summary = None

    if request.method == "POST":
        if "reset" in request.POST:
            request.session.pop(SESSION_DATASET_KEY, None)
            return render(
                request,
                "riskwise/simulation_run.html",
                {
                    "instruction": "Form reset successfully.",
                    "form_data": {},
                },
            )

        if request.FILES.get("file"):
            uploaded_file = request.FILES["file"]

            try:
                df = _prepare_simulation_dataframe(uploaded_file)
            except ValueError as exc:
                return render(request, "riskwise/simulation_run.html", {"instruction": str(exc)})
            except Exception as exc:
                return render(
                    request,
                    "riskwise/simulation_run.html",
                    {"instruction": f"Error reading file: {exc}"},
                )

            _save_uploaded_df_to_session(request, df)
            trade_count, date_start, date_end = _get_dataset_meta(df)

            return render(
                request,
                "riskwise/simulation_run.html",
                {
                    "trade_count": trade_count,
                    "date_start": date_start,
                    "date_end": date_end,
                    "form_data": {},
                },
            )

        df = _load_uploaded_df_from_session(request)
        if df is None or df.empty:
            return render(
                request,
                "riskwise/simulation_run.html",
                {"instruction": "Please upload a data file first."},
            )

        trade_count, date_start, date_end = _get_dataset_meta(df)

        try:
            n_sim = int(request.POST.get("num_simulations", ""))
            n_trades = int(request.POST.get("num_trades", ""))
            if n_sim <= 0 or n_trades <= 0:
                raise ValueError
        except ValueError:
            return render(
                request,
                "riskwise/simulation_run.html",
                {
                    "instruction": "Please enter valid numbers for simulations and trades.",
                    "trade_count": trade_count,
                    "date_start": date_start,
                    "date_end": date_end,
                },
            )

        start = int(request.POST.get("range_start") or 0)
        end = int(request.POST.get("range_end") or len(df))
        start, end = _clip_range(start, end, len(df))

        if start >= end:
            return render(
                request,
                "riskwise/simulation_run.html",
                {
                    "instruction": "Range End must be greater than Range Start.",
                    "trade_count": trade_count,
                    "date_start": date_start,
                    "date_end": date_end,
                },
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

        if start_date and end_date and "date" in df_range.columns:
            try:
                sd = pd.to_datetime(start_date)
                ed = pd.to_datetime(end_date)
                df_range = df_range[df_range["date"].between(sd, ed)]
            except Exception:
                pass

        profits = df_range["profit"].dropna().to_numpy()

        if len(profits) == 0:
            return render(
                request,
                "riskwise/simulation_run.html",
                {
                    "instruction": "No trades matched your filters.",
                    "trade_count": trade_count,
                    "form_data": form_data,
                    "date_start": date_start,
                    "date_end": date_end,
                },
            )

        ending_balances = []
        equity_curves = []

        for _ in range(n_sim):
            sim = np.random.choice(profits, size=n_trades, replace=True)
            ending_balances.append(float(sim.sum()))
            equity_curves.append(np.cumsum(sim))

        results_data = {
            "min": float(np.min(ending_balances)),
            "max": float(np.max(ending_balances)),
            "median": float(np.median(ending_balances)),
            "prob_positive": float((np.array(ending_balances) > 0).mean() * 100),
        }

        result_list = [
            {
                "label": "Min Ending Balance",
                "value": results_data["min"],
                "is_percent": False,
                "icon": "bi-currency-dollar",
                "color": "danger",
            },
            {
                "label": "Max Ending Balance",
                "value": results_data["max"],
                "is_percent": False,
                "icon": "bi-currency-dollar",
                "color": "success",
            },
            {
                "label": "Median Ending Balance",
                "value": results_data["median"],
                "is_percent": False,
                "icon": "bi-currency-dollar",
                "color": "info",
            },
            {
                "label": "Probability of Profit",
                "value": results_data["prob_positive"],
                "is_percent": True,
                "icon": "bi-emoji-smile",
                "color": "primary",
            },
        ]

        equity_curve_base64 = _build_equity_curve_chart(equity_curves, title="Equity Curves")

        summary = {
            "range_start": start,
            "range_end": end,
            "trade_count": len(profits),
            "date_start": None,
            "date_end": None,
        }

        if "date" in df_range.columns and df_range["date"].notna().any():
            filtered_dates = df_range["date"].dropna()
            summary["date_start"] = filtered_dates.min().strftime("%Y-%m-%d %H:%M")
            summary["date_end"] = filtered_dates.max().strftime("%Y-%m-%d %H:%M")

        SimulationHistory.objects.create(
            user=request.user,
            label="Monte Carlo Simulation",
            parameters=form_data,
            results=results_data,
            chart_base64=equity_curve_base64,
        )

        return render(
            request,
            "riskwise/simulation_run.html",
            {
                "trade_count": trade_count,
                "result_list": result_list,
                "equity_curve": equity_curve_base64,
                "form_data": form_data,
                "summary": summary,
                "date_start": date_start,
                "date_end": date_end,
            },
        )

    else:
        df = _load_uploaded_df_from_session(request)
        if df is not None and not df.empty:
            trade_count, date_start, date_end = _get_dataset_meta(df)

    return render(
        request,
        "riskwise/simulation_run.html",
        {
            "trade_count": trade_count,
            "date_start": date_start,
            "date_end": date_end,
            "form_data": form_data,
            "instruction": instruction,
        },
    )


@login_required
def simulation_scenario_view(request):
    instruction = None
    trade_count = None
    date_start = None
    date_end = None
    scenarios = []
    form_data = {}

    if request.method == "POST":
        if "reset" in request.POST:
            request.session.pop(SESSION_DATASET_KEY, None)
            return render(
                request,
                "riskwise/simulation_scenario.html",
                {
                    "instruction": "Form reset successfully.",
                    "form_data": {},
                },
            )

        if request.FILES.get("file"):
            uploaded_file = request.FILES["file"]

            try:
                df = _prepare_simulation_dataframe(uploaded_file)
            except ValueError as exc:
                return render(request, "riskwise/simulation_scenario.html", {"instruction": str(exc)})
            except Exception as exc:
                return render(
                    request,
                    "riskwise/simulation_scenario.html",
                    {"instruction": f"Error reading file: {exc}"},
                )

            _save_uploaded_df_to_session(request, df)
            trade_count, date_start, date_end = _get_dataset_meta(df)

            return render(
                request,
                "riskwise/simulation_scenario.html",
                {
                    "trade_count": trade_count,
                    "date_start": date_start,
                    "date_end": date_end,
                    "form_data": {},
                },
            )

        df = _load_uploaded_df_from_session(request)
        if df is None or df.empty:
            instruction = "Please upload a data file first."
            return render(request, "riskwise/simulation_scenario.html", {"instruction": instruction})

        trade_count, date_start, date_end = _get_dataset_meta(df)

        for i in ["1", "2", "3"]:
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
                    scenarios.append({"label": label, "error": "Skipped: No parameters."})
                    continue

                n_sim = int(n_sim_raw)
                n_trades = int(n_trades_raw)
                start = int(start_raw) if start_raw else 0
                end = int(end_raw) if end_raw else len(df)

                if n_sim <= 0 or n_trades <= 0:
                    scenarios.append({"label": label, "error": "Simulation counts must be greater than zero."})
                    continue

                start, end = _clip_range(start, end, len(df))
                if start >= end:
                    scenarios.append({"label": label, "error": "Range End must be greater than Range Start."})
                    continue

                df_range = df.iloc[start:end].copy()

                if start_date_raw and end_date_raw and "date" in df_range.columns:
                    try:
                        sd = pd.to_datetime(start_date_raw)
                        ed = pd.to_datetime(end_date_raw)
                        df_range = df_range[df_range["date"].between(sd, ed)]
                    except Exception:
                        pass

                profits = df_range["profit"].dropna().to_numpy()

                if len(profits) == 0:
                    scenarios.append({"label": label, "error": "No trades matched filters."})
                    continue

                ending_balances = []
                equity_curves = []

                for _ in range(n_sim):
                    sim = np.random.choice(profits, size=n_trades, replace=True)
                    ending_balances.append(float(sim.sum()))
                    equity_curves.append(np.cumsum(sim))

                chart = _build_equity_curve_chart(equity_curves, title=label)

                scenarios.append(
                    {
                        "label": label,
                        "min": float(np.min(ending_balances)),
                        "max": float(np.max(ending_balances)),
                        "median": float(np.median(ending_balances)),
                        "prob_positive": float((np.array(ending_balances) > 0).mean() * 100),
                        "chart": chart,
                    }
                )

            except Exception as exc:
                scenarios.append({"label": label, "error": f"Error: {exc}"})

        return render(
            request,
            "riskwise/simulation_scenario.html",
            {
                "trade_count": trade_count,
                "date_start": date_start,
                "date_end": date_end,
                "scenarios": scenarios,
                "form_data": form_data,
            },
        )

    else:
        df = _load_uploaded_df_from_session(request)
        if df is not None and not df.empty:
            trade_count, date_start, date_end = _get_dataset_meta(df)

    return render(
        request,
        "riskwise/simulation_scenario.html",
        {
            "instruction": instruction,
            "trade_count": trade_count,
            "date_start": date_start,
            "date_end": date_end,
            "form_data": form_data,
        },
    )


@login_required
def simulation_history_view(request):
    query = request.GET.get("q", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
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

    return render(
        request,
        "riskwise/simulation_history.html",
        {
            "simulations": page_obj,
            "page_obj": page_obj,
            "query": query,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@login_required
def simulation_download_json_view(request, pk):
    sim = get_object_or_404(SimulationHistory, pk=pk, user=request.user)
    response = HttpResponse(
        json.dumps(sim.results, indent=2),
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="{sim.label}.json"'
    return response


@login_required
def simulation_download_chart_view(request, pk):
    sim = get_object_or_404(SimulationHistory, pk=pk, user=request.user)
    image_data = base64.b64decode(sim.chart_base64)
    response = HttpResponse(image_data, content_type="image/png")
    response["Content-Disposition"] = f'attachment; filename="{sim.label}.png"'
    return response


@login_required
def simulation_detail_view(request, pk):
    sim = get_object_or_404(SimulationHistory, pk=pk, user=request.user)

    # Parse JSON fields into structured key-value pairs for clean rendering
    params_items = []
    if isinstance(sim.parameters, dict):
        params_items = list(sim.parameters.items())

    results_items = []
    if isinstance(sim.results, dict):
        results_items = list(sim.results.items())

    return render(request, "riskwise/simulation_detail.html", {
        "sim": sim,
        "params_items": params_items,
        "results_items": results_items,
    })


@login_required
def simulation_delete_view(request, pk):
    sim = get_object_or_404(SimulationHistory, pk=pk, user=request.user)

    if request.method == "POST":
        sim.delete()
        messages.success(request, "Simulation deleted successfully.")
        return redirect("simulation_history")

    return render(request, "riskwise/simulation_confirm_delete.html", {"sim": sim})