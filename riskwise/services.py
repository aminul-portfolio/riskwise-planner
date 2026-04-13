from __future__ import annotations

import base64
import io
import json
import logging
import re
from io import BytesIO
from typing import Any

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from django.apps import apps
from django.db import transaction
from django.utils.text import slugify


APP_LABEL = "riskwise"

SESSION_DF_KEY = "riskwise_uploaded_df"
SESSION_META_KEY = "riskwise_dataset_meta"

logger = logging.getLogger("riskwise")

PROFIT_ALIASES = [
    "profit",
    "pnl",
    "net_profit",
    "net_pnl",
    "pl",
    "p_l",
    "gain_loss",
    "profit_loss",
]

DATE_ALIASES = [
    "date",
    "trade_date",
    "datetime",
    "timestamp",
    "open_time",
    "open_date",
    "time",
]

SESSION_ALIASES = [
    "session",
    "market_session",
    "trading_session",
]

SYMBOL_ALIASES = ["symbol", "instrument", "asset", "pair", "ticker"]
SIDE_ALIASES = ["side", "direction", "trade_type", "position"]
STATUS_ALIASES = ["status", "trade_status"]


def _normalise_column_name(name: Any) -> str:
    text = str(name).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value


def _find_first_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _find_profit_column(df: pd.DataFrame) -> str | None:
    return _find_first_column(df, PROFIT_ALIASES)


def _find_date_column(df: pd.DataFrame) -> str | None:
    return _find_first_column(df, DATE_ALIASES)


def _find_session_column(df: pd.DataFrame) -> str | None:
    return _find_first_column(df, SESSION_ALIASES)


def _normalise_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [_normalise_column_name(col) for col in df.columns]

    alias_map = {
        "profit": PROFIT_ALIASES,
        "date": DATE_ALIASES,
        "session": SESSION_ALIASES,
        "symbol": SYMBOL_ALIASES,
        "side": SIDE_ALIASES,
        "status": STATUS_ALIASES,
    }

    for target, aliases in alias_map.items():
        if target in df.columns:
            continue
        found = _find_first_column(df, aliases)
        if found and found != target:
            df = df.rename(columns={found: target})

    return df


def _read_uploaded_dataframe(uploaded_file) -> pd.DataFrame:
    filename = getattr(uploaded_file, "name", "uploaded_file")
    lower_name = filename.lower()

    if lower_name.endswith(".csv"):
        return pd.read_csv(uploaded_file)

    if lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
        return pd.read_excel(uploaded_file)

    raise ValueError("Unsupported file format. Please upload a CSV or Excel file.")


def _infer_session_from_hour(hour: int) -> str:
    if 0 <= hour < 8:
        return "Asia"
    if 8 <= hour < 13:
        return "London"
    if 13 <= hour < 21:
        return "New York"
    return "Off Hours"


def _ensure_session_column(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "session" in df.columns:
        df["session"] = df["session"].astype(str).str.strip()
        return df

    date_col = _find_date_column(df)
    if date_col is not None:
        dt = pd.to_datetime(df[date_col], errors="coerce")
        if dt.notna().any():
            df["session"] = dt.dt.hour.apply(
                lambda h: _infer_session_from_hour(int(h)) if pd.notna(h) else "Unknown"
            )
            return df

    df["session"] = "Unknown"
    return df


def _prepare_dataframe(uploaded_file) -> pd.DataFrame:
    filename = getattr(uploaded_file, "name", "uploaded_file")
    logger.info("prepare_dataframe_started | filename=%s", filename)

    df = _read_uploaded_dataframe(uploaded_file)

    if df.empty:
        raise ValueError("The uploaded file is empty.")

    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    df = _normalise_dataframe_columns(df)

    profit_col = _find_profit_column(df)
    if profit_col is None:
        raise ValueError(
            "A profit column was not found. Include a column such as profit, pnl, net_profit, or pl."
        )

    if profit_col != "profit":
        df = df.rename(columns={profit_col: "profit"})

    df["profit"] = pd.to_numeric(df["profit"], errors="coerce")
    df = df[df["profit"].notna()].copy()

    if df.empty:
        raise ValueError("No valid numeric profit values were found in the uploaded file.")

    date_col = _find_date_column(df)
    if date_col is not None:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        if date_col != "date":
            df = df.rename(columns={date_col: "date"})
            date_col = "date"
        df = df.sort_values(by=date_col, kind="stable", na_position="last").reset_index(drop=True)

    df = _ensure_session_column(df)

    logger.info(
        "prepare_dataframe_success | filename=%s | rows=%s | columns=%s",
        filename,
        len(df),
        list(df.columns),
    )
    return df.reset_index(drop=True)


def prepare_trade_import_dataframe(uploaded_file) -> pd.DataFrame:
    return _prepare_dataframe(uploaded_file)


def prepare_simulation_dataframe(uploaded_file) -> pd.DataFrame:
    return _prepare_dataframe(uploaded_file)


def save_uploaded_df_to_session(request, df: pd.DataFrame) -> None:
    serialised = df.to_json(orient="split", date_format="iso")
    request.session[SESSION_DF_KEY] = serialised
    request.session.modified = True


def load_uploaded_df_from_session(request) -> pd.DataFrame | None:
    serialised = request.session.get(SESSION_DF_KEY)
    if not serialised:
        return None

    try:
        df = pd.read_json(io.StringIO(serialised), orient="split")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df
    except Exception:
        logger.exception("load_uploaded_df_from_session_failed")
        return None


def clear_uploaded_dataset_from_session(request) -> None:
    request.session.pop(SESSION_DF_KEY, None)
    request.session.pop(SESSION_META_KEY, None)
    request.session.modified = True
    logger.info("clear_uploaded_dataset_from_session")


def get_dataset_meta(df: pd.DataFrame) -> tuple[int, str | None, str | None]:
    if df is None or df.empty:
        return 0, None, None

    date_col = _find_date_column(df)
    if date_col is None:
        return len(df), None, None

    dt = pd.to_datetime(df[date_col], errors="coerce").dropna()
    if dt.empty:
        return len(df), None, None

    return len(df), str(dt.min().date()), str(dt.max().date())


def build_dataset_meta(filename: str | None, df: pd.DataFrame) -> dict[str, Any]:
    trade_count, date_start, date_end = get_dataset_meta(df)
    return {
        "filename": filename,
        "source_file": filename,
        "trade_count": trade_count,
        "records_loaded": trade_count,
        "date_start": date_start,
        "date_end": date_end,
        "columns": list(df.columns) if df is not None else [],
        "has_profit": bool(df is not None and "profit" in df.columns),
    }


def save_dataset_meta_to_session(request, filename: str | None, df: pd.DataFrame) -> dict[str, Any]:
    meta = build_dataset_meta(filename, df)
    request.session[SESSION_META_KEY] = meta
    request.session.modified = True
    return meta


def load_dataset_meta_from_session(request) -> dict[str, Any] | None:
    return request.session.get(SESSION_META_KEY)


def _get_trade_model():
    try:
        return apps.get_model(APP_LABEL, "Trade")
    except LookupError:
        return None


def _trade_queryset_to_dataframe(user) -> pd.DataFrame | None:
    trade_model = _get_trade_model()
    if trade_model is None:
        return None

    concrete_fields = [
        field.name
        for field in trade_model._meta.concrete_fields
        if not field.many_to_many
    ]

    qs = trade_model.objects.all()
    if "user" in concrete_fields:
        qs = qs.filter(user=user)

    rows = list(qs.values(*concrete_fields))
    if not rows:
        return None

    df = pd.DataFrame(rows)
    df = _normalise_dataframe_columns(df)

    profit_col = _find_profit_column(df)
    if profit_col and profit_col != "profit":
        df = df.rename(columns={profit_col: "profit"})

    date_col = _find_date_column(df)
    if date_col and date_col != "date":
        df = df.rename(columns={date_col: "date"})

    if "profit" in df.columns:
        df["profit"] = pd.to_numeric(df["profit"], errors="coerce")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df = _ensure_session_column(df)
    return df


def get_active_planning_df(request) -> tuple[pd.DataFrame | None, dict[str, Any] | None]:
    df = load_uploaded_df_from_session(request)
    if df is not None and not df.empty:
        meta = load_dataset_meta_from_session(request)
        if not meta:
            meta = build_dataset_meta("Session Dataset", df)
        logger.info(
            "active_planning_df_from_session | user=%s | rows=%s",
            request.user.username,
            len(df),
        )
        return df, meta

    db_df = _trade_queryset_to_dataframe(request.user)
    if db_df is not None and not db_df.empty:
        logger.info(
            "active_planning_df_from_database | user=%s | rows=%s",
            request.user.username,
            len(db_df),
        )
        return db_df, build_dataset_meta("Database Trades", db_df)

    logger.info("active_planning_df_missing | user=%s", request.user.username)
    return None, None


def with_dataset_context(request, context: dict[str, Any], df: pd.DataFrame | None = None) -> dict[str, Any]:
    merged = dict(context)

    dataset_meta = merged.get("dataset_meta")
    if not dataset_meta:
        dataset_meta = load_dataset_meta_from_session(request)

    if not dataset_meta and df is not None and not df.empty:
        dataset_meta = build_dataset_meta("Active Dataset", df)

    merged["dataset_meta"] = dataset_meta
    merged["dataset_loaded"] = bool(dataset_meta)

    if dataset_meta:
        merged.setdefault("trade_count", dataset_meta.get("trade_count"))
        merged.setdefault("date_start", dataset_meta.get("date_start"))
        merged.setdefault("date_end", dataset_meta.get("date_end"))

    form_data = merged.get("form_data")
    if isinstance(form_data, dict):
        run_value = merged.get("settings_runs")
        if run_value in (None, ""):
            run_value = form_data.get("num_simulations") or form_data.get("simulation_runs")

        trade_value = merged.get("settings_trades")
        if trade_value in (None, ""):
            trade_value = form_data.get("num_trades") or form_data.get("trades_per_run")

        sample_value = merged.get("settings_sample_size")
        if sample_value in (None, ""):
            sample_value = merged.get("trade_count")

        run_int = safe_int(run_value, 0)
        trade_int = safe_int(trade_value, 0)
        sample_int = safe_int(sample_value, 0)

        merged.setdefault("settings_runs", f"{run_int:,}" if run_int else "—")
        merged.setdefault("settings_trades", f"{trade_int:,}" if trade_int else "—")
        merged.setdefault("settings_sample_size", f"{sample_int:,}" if sample_int else "—")
        merged.setdefault("settings_confidence", "Tail Review")

        # Backward compatibility for templates that still reference older fallback names.
        merged.setdefault("simulation_runs", merged["settings_runs"])
        merged.setdefault("trades_per_run", merged["settings_trades"])

    return merged


def _coerce_optional_datetime(value: Any):
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return None
    return dt.to_pydatetime()


def replace_user_trades_from_dataframe(user, df: pd.DataFrame) -> int:
    logger.info(
        "replace_user_trades_started | user=%s | incoming_rows=%s",
        getattr(user, "username", "unknown"),
        len(df),
    )

    trade_model = _get_trade_model()
    if trade_model is None:
        return len(df)

    df = df.copy()
    df.columns = [_normalise_column_name(col) for col in df.columns]

    concrete_fields = {
        field.name: field
        for field in trade_model._meta.concrete_fields
        if not field.auto_created
    }

    numeric_alias_map = {
        "profit": ["profit", "pnl", "net_profit", "net_pnl", "pl", "p_l"],
        "volume": ["volume", "lot_size", "lots", "size", "trade_size"],
        "lot_size": ["lot_size", "lots", "size", "trade_size", "volume"],
        "entry_price": ["entry_price", "entry", "open_price", "price", "open"],
        "entry": ["entry", "entry_price", "open_price", "price", "open"],
        "stop_loss": ["stop_loss", "sl"],
        "take_profit": ["take_profit", "tp"],
        "pip_value": ["pip_value", "pipvalue"],
        "stop_loss_pips": ["stop_loss_pips", "sl_pips", "stoploss_pips"],
        "risk_amount": ["risk_amount"],
        "risk_percent": ["risk_percent", "risk_pct"],
    }

    text_alias_map = {
        "symbol": ["symbol", "instrument", "asset", "pair", "ticker"],
        "side": ["side", "direction", "trade_type", "position"],
        "status": ["status", "trade_status"],
        "session": ["session", "market_session", "trading_session"],
        "notes": ["notes", "comment", "comments"],
    }

    def pick_value(row, aliases):
        for alias in aliases:
            if alias in row.index and pd.notna(row[alias]) and str(row[alias]).strip() != "":
                return row[alias]
        return None

    def set_default_if_required(kwargs, field_name, default_value):
        if field_name not in concrete_fields:
            return

        field = concrete_fields[field_name]

        already_present = field_name in kwargs and kwargs[field_name] not in (None, "")
        if already_present:
            return

        if getattr(field, "null", False):
            return

        if getattr(field, "has_default", lambda: False)():
            return

        kwargs[field_name] = default_value

    with transaction.atomic():
        qs = trade_model.objects.all()
        if "user" in concrete_fields:
            qs = qs.filter(user=user)
        qs.delete()

        objects = []

        for _, row in df.iterrows():
            kwargs: dict[str, Any] = {}

            if "user" in concrete_fields:
                kwargs["user"] = user

            for field_name, aliases in text_alias_map.items():
                if field_name in concrete_fields:
                    value = pick_value(row, aliases)
                    if value is not None:
                        kwargs[field_name] = str(value).strip()

            for field_name, aliases in numeric_alias_map.items():
                if field_name in concrete_fields:
                    value = pick_value(row, aliases)
                    if value is not None:
                        kwargs[field_name] = _safe_float(value)

            if "open_time" in concrete_fields:
                open_value = None
                for candidate in ["open_time", "date", "datetime", "timestamp", "time"]:
                    if candidate in row.index and pd.notna(row[candidate]):
                        open_value = row[candidate]
                        break
                if open_value is not None:
                    kwargs["open_time"] = _coerce_optional_datetime(open_value)

            if "close_time" in concrete_fields:
                close_value = None
                for candidate in ["close_time", "close_date"]:
                    if candidate in row.index and pd.notna(row[candidate]):
                        close_value = row[candidate]
                        break
                if close_value is not None:
                    kwargs["close_time"] = _coerce_optional_datetime(close_value)

            if "date" in concrete_fields and "date" in row.index and pd.notna(row["date"]):
                kwargs["date"] = _coerce_optional_datetime(row["date"])

            if "volume" in concrete_fields and "volume" not in kwargs:
                if "lot_size" in kwargs:
                    kwargs["volume"] = kwargs["lot_size"]

            if "entry_price" in concrete_fields and "entry_price" not in kwargs:
                if "entry" in kwargs:
                    kwargs["entry_price"] = kwargs["entry"]

            if "entry" in concrete_fields and "entry" not in kwargs:
                if "entry_price" in kwargs:
                    kwargs["entry"] = kwargs["entry_price"]

            set_default_if_required(kwargs, "volume", 0.0)
            set_default_if_required(kwargs, "entry_price", 0.0)
            set_default_if_required(kwargs, "entry", 0.0)
            set_default_if_required(kwargs, "profit", 0.0)

            set_default_if_required(kwargs, "symbol", "UNKNOWN")
            set_default_if_required(kwargs, "side", "UNKNOWN")
            set_default_if_required(kwargs, "status", "CLOSED")
            set_default_if_required(kwargs, "session", "Unknown")
            set_default_if_required(kwargs, "notes", "")

            objects.append(trade_model(**kwargs))

        if objects:
            trade_model.objects.bulk_create(objects, batch_size=500)

    logger.info(
        "replace_user_trades_success | user=%s | created_rows=%s",
        getattr(user, "username", "unknown"),
        len(df),
    )
    return len(df)


def clip_range(start: int, end: int, length: int) -> tuple[int, int]:
    if length <= 0:
        return 0, 0

    start = max(0, min(safe_int(start, 0), length))
    end = max(0, min(safe_int(end, length), length))

    if end < start:
        end = start

    return start, end


def filter_df_by_date_range(
    df: pd.DataFrame,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    date_col = _find_date_column(df)
    if date_col is None:
        return df

    filtered = df.copy()
    filtered[date_col] = pd.to_datetime(filtered[date_col], errors="coerce")

    if start_date:
        start_ts = pd.to_datetime(start_date, errors="coerce")
        if pd.notna(start_ts):
            filtered = filtered[filtered[date_col] >= start_ts]

    if end_date:
        end_ts = pd.to_datetime(end_date, errors="coerce")
        if pd.notna(end_ts):
            filtered = filtered[filtered[date_col] <= end_ts]

    return filtered.reset_index(drop=True)


def filter_df_by_session(
    df: pd.DataFrame,
    market_session: str | None,
    uk_start: str | None = None,
    uk_end: str | None = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    if not market_session or str(market_session).strip().lower() == "all":
        return df

    filtered = df.copy()
    session_label = str(market_session).strip().lower()

    date_col = _find_date_column(filtered)
    session_col = _find_session_column(filtered)

    if session_label in {"uk", "uk hours", "custom uk hours"} and date_col is not None:
        start_hour = safe_int(uk_start, 8)
        end_hour = safe_int(uk_end, 17)

        filtered[date_col] = pd.to_datetime(filtered[date_col], errors="coerce")
        hours = filtered[date_col].dt.hour

        if start_hour <= end_hour:
            mask = (hours >= start_hour) & (hours <= end_hour)
        else:
            mask = (hours >= start_hour) | (hours <= end_hour)

        return filtered[mask].reset_index(drop=True)

    if session_col is None:
        filtered = _ensure_session_column(filtered)
        session_col = "session"

    session_series = filtered[session_col].astype(str).str.strip().str.lower()
    return filtered[session_series == session_label].reset_index(drop=True)


def calculate_lot_size(lot_size: float, pip_distance: float, pip_value: float) -> dict[str, float]:
    lot_size = _safe_float(lot_size)
    pip_distance = abs(_safe_float(pip_distance))
    pip_value = abs(_safe_float(pip_value))

    risk_per_pip = lot_size * pip_value
    risk_amount = risk_per_pip * pip_distance

    return {
        "lot_size": round(lot_size, 4),
        "pip_distance": round(pip_distance, 2),
        "pip_value": round(pip_value, 4),
        "risk_per_pip": round(risk_per_pip, 2),
        "risk_amount": round(risk_amount, 2),
    }


def calculate_trade_risk(
    account_balance: float,
    lot_size: float,
    pip_value: float,
    stop_loss_pips: float,
) -> dict[str, float]:
    account_balance = max(_safe_float(account_balance), 0.0)
    lot_size = _safe_float(lot_size)
    pip_value = abs(_safe_float(pip_value))
    stop_loss_pips = abs(_safe_float(stop_loss_pips))

    risk_amount = lot_size * pip_value * stop_loss_pips
    risk_percent = (risk_amount / account_balance * 100) if account_balance > 0 else 0.0

    return {
        "account_balance": round(account_balance, 2),
        "lot_size": round(lot_size, 4),
        "pip_value": round(pip_value, 4),
        "stop_loss_pips": round(stop_loss_pips, 2),
        "risk_amount": round(risk_amount, 2),
        "risk_percent": round(risk_percent, 2),
    }


def build_trade_risk_warning(risk_percent: float) -> str:
    risk_percent = _safe_float(risk_percent)

    if risk_percent <= 1:
        return "Risk is within a conservative single-trade planning range."
    if risk_percent <= 2:
        return "Risk is controlled but should still align with your broader downside limit."
    if risk_percent <= 3:
        return "Risk is elevated for one trade and may need smaller sizing."
    return "Risk is high for a single trade and may expose the account to avoidable drawdown."


def calculate_strategy_risk(
    base_lot: float,
    win_rate: float,
    rr: float,
    volatility: float,
) -> dict[str, float | str]:
    base_lot = max(_safe_float(base_lot), 0.0)
    win_rate = min(max(_safe_float(win_rate), 0.0), 100.0)
    rr = max(_safe_float(rr), 0.0)
    volatility = max(_safe_float(volatility), 0.0)

    win_prob = win_rate / 100
    expectancy = (win_prob * rr) - (1 - win_prob)

    volatility_divisor = max(1.0, volatility)
    sizing_multiplier = max(0.25, min(1.5, 1 + expectancy)) / volatility_divisor
    recommended_lot = base_lot * sizing_multiplier

    if expectancy > 0.25:
        stance = "Positive expectancy baseline."
    elif expectancy >= 0:
        stance = "Marginal positive expectancy; keep sizing controlled."
    else:
        stance = "Negative expectancy baseline; reduce exposure or review the setup."

    return {
        "base_lot": round(base_lot, 4),
        "win_rate": round(win_rate, 2),
        "rr": round(rr, 2),
        "volatility": round(volatility, 2),
        "expectancy": round(expectancy, 4),
        "recommended_lot": round(recommended_lot, 4),
        "stance": stance,
    }


def calculate_sltp(
    entry: float,
    stop_loss: float,
    take_profit: float,
    lot_size: float,
    pip_value: float,
) -> dict[str, float]:
    entry = _safe_float(entry)
    stop_loss = _safe_float(stop_loss)
    take_profit = _safe_float(take_profit)
    lot_size = _safe_float(lot_size)
    pip_value = abs(_safe_float(pip_value))

    risk_pips = abs(entry - stop_loss)
    reward_pips = abs(take_profit - entry)
    rr_ratio = (reward_pips / risk_pips) if risk_pips > 0 else 0.0

    risk_amount = risk_pips * lot_size * pip_value
    reward_amount = reward_pips * lot_size * pip_value

    return {
        "entry": round(entry, 5),
        "stop_loss": round(stop_loss, 5),
        "take_profit": round(take_profit, 5),
        "risk_pips": round(risk_pips, 2),
        "reward_pips": round(reward_pips, 2),
        "rr_ratio": round(rr_ratio, 2),
        "risk_amount": round(risk_amount, 2),
        "reward_amount": round(reward_amount, 2),
    }


def run_simulation(
    profits: np.ndarray | list[float],
    num_simulations: int,
    num_trades: int,
    include_curves: bool = False,
) -> dict[str, Any]:
    profit_array = np.asarray(profits, dtype=float)
    profit_array = profit_array[~np.isnan(profit_array)]

    if profit_array.size == 0:
        raise ValueError("No valid profit values were provided for simulation.")

    num_simulations = max(safe_int(num_simulations, 0), 1)
    num_trades = max(safe_int(num_trades, 0), 1)

    logger.info(
        "run_simulation_started | sample_size=%s | num_simulations=%s | num_trades=%s | include_curves=%s",
        profit_array.size,
        num_simulations,
        num_trades,
        include_curves,
    )

    totals = np.zeros(num_simulations)
    equity_curves: list[list[float]] = []

    for i in range(num_simulations):
        sample = np.random.choice(profit_array, size=num_trades, replace=True)
        cumulative = np.cumsum(sample)
        totals[i] = cumulative[-1]

        if include_curves:
            equity_curves.append(cumulative.tolist())

    result = {
        "min": round(float(np.min(totals)), 2),
        "max": round(float(np.max(totals)), 2),
        "mean": round(float(np.mean(totals)), 2),
        "median": round(float(np.median(totals)), 2),
        "p05": round(float(np.percentile(totals, 5)), 2),
        "p95": round(float(np.percentile(totals, 95)), 2),
        "prob_positive": round(float(np.mean(totals > 0) * 100), 2),
    }

    if include_curves:
        result["equity_curves"] = equity_curves

    logger.info(
        "run_simulation_completed | min=%s | median=%s | p95=%s | prob_positive=%s",
        result["min"],
        result["median"],
        result["p95"],
        result["prob_positive"],
    )
    return result


def build_simulation_warning(sample_size: int, num_simulations: int, num_trades: int) -> str:
    sample_size = safe_int(sample_size, 0)
    num_simulations = safe_int(num_simulations, 0)
    num_trades = safe_int(num_trades, 0)

    if sample_size < 10:
        return "The filtered sample is very small, so the simulation should be treated as directional only."
    if num_trades > sample_size * 5:
        return "The requested number of simulated trades is large relative to the filtered sample and may overstate confidence."
    if num_simulations < 100:
        return "A low number of simulations can make percentile and probability estimates less stable."
    return "Simulation inputs look reasonable for exploratory downside planning."


def build_result_list(results: dict[str, Any]) -> list[dict[str, Any]]:
    label_map = {
        "min": "Minimum Outcome",
        "max": "Maximum Outcome",
        "mean": "Mean Outcome",
        "median": "Median Outcome",
        "p05": "5th Percentile",
        "p95": "95th Percentile",
        "prob_positive": "Probability Positive",
    }

    result_list = []

    for key in ["min", "max", "mean", "median", "p05", "p95", "prob_positive"]:
        if key not in results:
            continue

        value = results[key]
        display_value = f"{value:.2f}% " if key == "prob_positive" else f"{value:.2f}"
        if key == "prob_positive":
            display_value = f"{value:.2f}%"

        result_list.append(
            {
                "key": key,
                "label": label_map.get(key, key.replace("_", " ").title()),
                "value": value,
                "display_value": display_value,
            }
        )

    return result_list


def build_run_summary(
    df_range: pd.DataFrame,
    filtered_profit_count: int,
    range_start: int,
    range_end: int,
    session_name: str | None = None,
) -> dict[str, Any]:
    if df_range is None or df_range.empty or "profit" not in df_range.columns:
        return {
            "range_start": range_start,
            "range_end": range_end,
            "filtered_profit_count": filtered_profit_count,
            "session_name": session_name,
            "win_rate": 0.0,
            "average_profit": 0.0,
        }

    profits = pd.to_numeric(df_range["profit"], errors="coerce").dropna()
    win_rate = float((profits > 0).mean() * 100) if len(profits) else 0.0
    average_profit = float(profits.mean()) if len(profits) else 0.0

    return {
        "range_start": range_start,
        "range_end": range_end,
        "filtered_profit_count": int(filtered_profit_count),
        "session_name": session_name,
        "win_rate": round(win_rate, 2),
        "average_profit": round(average_profit, 2),
    }


def build_equity_curve_chart(equity_curves: list[list[float]], title: str = "Equity Curves") -> str:
    if not equity_curves:
        return ""

    fig, ax = plt.subplots(figsize=(10, 5))

    for curve in equity_curves:
        ax.plot(curve, linewidth=1, alpha=0.2)

    ax.set_title(title)
    ax.set_xlabel("Trade Number")
    ax.set_ylabel("Cumulative Profit")
    ax.grid(True, alpha=0.3)

    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=150)
    plt.close(fig)

    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def build_dashboard_interpretation(
    df: pd.DataFrame,
    max_drawdown: float,
    volatility: float,
    profit_factor: float | None,
) -> dict[str, str]:
    profits = pd.to_numeric(df["profit"], errors="coerce").dropna() if "profit" in df.columns else pd.Series(dtype=float)
    trade_count = len(profits)
    avg_profit = float(profits.mean()) if trade_count else 0.0
    max_drawdown_abs = abs(_safe_float(max_drawdown))
    volatility = abs(_safe_float(volatility))

    if profit_factor is None or profit_factor < 1:
        return {
            "primary_downside_concern": "The reference sample shows fragile or negative edge quality.",
            "planning_implication": "Future sizing should prioritise capital preservation because losses are outweighing gains in the current baseline.",
            "suggested_next_step": "Run scenario comparison with smaller size assumptions before committing capital.",
        }

    if max_drawdown_abs > max(volatility * 2, abs(avg_profit) * 5):
        return {
            "primary_downside_concern": "Drawdown depth is materially larger than the typical trade-to-trade dispersion.",
            "planning_implication": "Position sizing should be calibrated to survive clustered losses rather than average conditions.",
            "suggested_next_step": "Stress-test longer loss sequences in the simulation views and reduce exposure if needed.",
        }

    if volatility > max(abs(avg_profit), 1):
        return {
            "primary_downside_concern": "Outcome dispersion is elevated relative to the average trade result.",
            "planning_implication": "Use tighter risk caps because results may swing more widely than the average trade suggests.",
            "suggested_next_step": "Filter the reference set by date or session to identify whether instability is concentrated.",
        }

    return {
        "primary_downside_concern": "The reference sample is comparatively stable, but downside control still matters.",
        "planning_implication": "You can plan around a more balanced baseline while still respecting hard drawdown limits.",
        "suggested_next_step": "Use the simulation tools to confirm that the baseline remains acceptable under different sample slices.",
    }


def slug_filename(label: str, extension: str) -> str:
    extension = extension if extension.startswith(".") else f".{extension}"
    slug = slugify(label or "riskwise-export") or "riskwise-export"
    return f"{slug}{extension}"


def _encode_matplotlib_figure(fig) -> str:
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(
        buffer,
        format="png",
        dpi=150,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def build_equity_curve_summary(equity_curves):
    curves = np.asarray(equity_curves, dtype=float)

    if curves.ndim == 1:
        curves = curves.reshape(1, -1)

    x = np.arange(1, curves.shape[1] + 1)
    final_values = curves[:, -1]

    summary = {
        "x": x,
        "curves": curves,
        "final_values": final_values,
        "p10_path": np.percentile(curves, 10, axis=0),
        "p25_path": np.percentile(curves, 25, axis=0),
        "p50_path": np.percentile(curves, 50, axis=0),
        "p75_path": np.percentile(curves, 75, axis=0),
        "p90_path": np.percentile(curves, 90, axis=0),
        "p10_final": float(np.percentile(final_values, 10)),
        "p25_final": float(np.percentile(final_values, 25)),
        "p50_final": float(np.percentile(final_values, 50)),
        "p75_final": float(np.percentile(final_values, 75)),
        "p90_final": float(np.percentile(final_values, 90)),
        "best_path": curves[np.argmax(final_values)],
        "worst_path": curves[np.argmin(final_values)],
        "positive_count": int((final_values > 0).sum()),
        "path_count": int(len(final_values)),
        "positive_rate": float((final_values > 0).mean() * 100),
    }
    return summary


def build_percentile_band_chart(curve_summary, title="Stress-Test Distribution"):
    x = curve_summary["x"]
    p10 = curve_summary["p10_path"]
    p25 = curve_summary["p25_path"]
    p50 = curve_summary["p50_path"]
    p75 = curve_summary["p75_path"]
    p90 = curve_summary["p90_path"]
    best = curve_summary["best_path"]
    worst = curve_summary["worst_path"]

    fig, ax = plt.subplots(figsize=(10.5, 5.6), facecolor="#071423")
    ax.set_facecolor("#071423")

    ax.fill_between(x, p10, p90, alpha=0.14, label="10th–90th percentile")
    ax.fill_between(x, p25, p75, alpha=0.24, label="25th–75th percentile")

    ax.plot(x, best, linestyle="--", linewidth=1.2, label="Best final path")
    ax.plot(x, worst, linestyle="--", linewidth=1.2, label="Worst final path")
    ax.plot(x, p50, linewidth=2.4, label="Median path")

    ax.set_title(title, fontsize=15, color="white", pad=12)
    ax.set_xlabel("Trade Number", color="#c7d2e0")
    ax.set_ylabel("Cumulative Profit", color="#c7d2e0")
    ax.tick_params(colors="#b8c4d6")
    ax.grid(True, alpha=0.12)
    ax.legend(frameon=False, fontsize=9, loc="upper left", labelcolor="#d9e3f0")

    for spine in ax.spines.values():
        spine.set_color("#22324a")

    return _encode_matplotlib_figure(fig)


def build_final_profit_histogram(curve_summary, title="Final Profit Distribution"):
    final_values = curve_summary["final_values"]
    p10 = curve_summary["p10_final"]
    p50 = curve_summary["p50_final"]
    p90 = curve_summary["p90_final"]

    bins = min(24, max(10, int(np.sqrt(len(final_values)))))

    fig, ax = plt.subplots(figsize=(6.2, 5.0), facecolor="#071423")
    ax.set_facecolor("#071423")

    ax.hist(final_values, bins=bins, alpha=0.85)

    ax.axvline(p10, linestyle="--", linewidth=1.5, label=f"P10 {p10:,.2f}")
    ax.axvline(p50, linestyle="--", linewidth=1.8, label=f"Median {p50:,.2f}")
    ax.axvline(p90, linestyle="--", linewidth=1.5, label=f"P90 {p90:,.2f}")

    ax.set_title(title, fontsize=14, color="white", pad=10)
    ax.set_xlabel("Final Profit", color="#c7d2e0")
    ax.set_ylabel("Number of Simulations", color="#c7d2e0")
    ax.tick_params(colors="#b8c4d6")
    ax.grid(True, axis="y", alpha=0.12)
    ax.legend(frameon=False, fontsize=9, loc="upper left", labelcolor="#d9e3f0")

    for spine in ax.spines.values():
        spine.set_color("#22324a")

    return _encode_matplotlib_figure(fig)
