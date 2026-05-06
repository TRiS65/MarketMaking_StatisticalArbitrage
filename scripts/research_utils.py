"""Shared minute-panel research utilities."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

from project_config import ETF, MINUTES_PER_DAY, PROCESSED, symbols


def load_panel() -> pd.DataFrame:
    panel = pd.read_parquet(PROCESSED / "research_panel.parquet")
    panel["minute"] = pd.to_datetime(panel["minute"])
    return panel[panel["symbol"].isin(symbols())].sort_values(["symbol", "minute"]).copy()


def pivot(panel: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in panel.columns:
        return pd.DataFrame()
    return panel.pivot(index="minute", columns="symbol", values=column).sort_index()


def align_intraday(frame: pd.DataFrame, ffill_limit: int = 5) -> pd.DataFrame:
    dates = sorted(pd.Series(frame.index.date.astype(str)).unique())
    if not dates:
        return frame
    parts = [pd.date_range(pd.Timestamp(f"{day} 09:30:00"), periods=MINUTES_PER_DAY, freq="min") for day in dates]
    full_index = parts[0].append(parts[1:]) if len(parts) > 1 else parts[0]
    aligned = frame.reindex(full_index)
    day_key = pd.Series(aligned.index.date.astype(str), index=aligned.index)
    return aligned.groupby(day_key, group_keys=False).ffill(limit=ffill_limit)


def make_views(panel: pd.DataFrame | None = None, cols: Iterable[str] | None = None, ffill_limit: int = 5) -> dict[str, pd.DataFrame]:
    panel = load_panel() if panel is None else panel
    cols = list(cols or ["bid", "ask", "mid", "microprice", "spread_bps", "bidsiz", "asksiz", "last_trade_price", "volume", "trade_count"])
    raw = {col: pivot(panel, col) for col in cols if col in panel.columns}
    views = {col: align_intraday(df, ffill_limit) for col, df in raw.items() if not df.empty}
    required = [s for s in symbols() if s in views["mid"].columns]
    common = views["mid"].dropna(subset=required).index
    for col in list(views):
        views[col] = views[col].loc[common].astype(float)
    return views


def continuous_mask(index: pd.Index) -> pd.Series:
    idx = pd.Series(index, index=index)
    return (idx.diff() == pd.Timedelta(minutes=1)) & (idx.dt.date == idx.shift(1).dt.date)


def log_returns(price: pd.DataFrame, clip_bps: float = 500.0) -> pd.DataFrame:
    ret = np.log(price.astype(float)).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    ret.loc[~continuous_mask(price.index).values, :] = 0.0
    return ret.clip(-(clip_bps / 1e4), clip_bps / 1e4)


def safe_half_life(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 250:
        return np.nan
    lag = s.shift(1).dropna()
    delta = s.diff().dropna()
    lag = lag.loc[delta.index]
    try:
        model = sm.OLS(delta.values, sm.add_constant(lag.values)).fit()
        phi = 1.0 + model.params[1]
    except Exception:
        return np.nan
    if phi <= 0 or phi >= 1:
        return np.nan
    return float(-np.log(2) / np.log(phi))


def safe_adf_pvalue(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 500:
        return np.nan
    try:
        return float(adfuller(s, maxlag=20, autolag="AIC")[1])
    except Exception:
        return np.nan


def residual_return(ret: pd.DataFrame, subset: tuple[str, ...], beta: Iterable[float], hedge_fraction: float = 1.0) -> pd.Series:
    b = np.nan_to_num(np.asarray(tuple(beta), dtype=float) * hedge_fraction, nan=0.0, posinf=0.0, neginf=0.0)
    x = np.nan_to_num(ret.loc[:, list(subset)].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        hedge = x @ b
    hedge = np.nan_to_num(hedge, nan=0.0, posinf=0.0, neginf=0.0)
    base = np.nan_to_num(ret[ETF].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    return pd.Series(base - hedge, index=ret.index)


def clipped_last_trade_price(views: dict[str, pd.DataFrame]) -> pd.DataFrame:
    mid = views["mid"]
    last = views.get("last_trade_price", pd.DataFrame(index=mid.index, columns=mid.columns, dtype=float)).reindex_like(mid)
    last = last.where(last > 0).ffill(limit=5)
    if "bid" in views and "ask" in views:
        last = last.clip(lower=views["bid"], upper=views["ask"], axis=0)
    return last.fillna(mid)


def estimate_ou(spread: pd.Series) -> dict[str, float]:
    s = spread.dropna()
    if len(s) < 250:
        return {"ou_phi": np.nan, "ou_mu": np.nan, "ou_sigma_eq": np.nan, "ou_half_life_minutes": np.nan}
    y = s.iloc[1:].to_numpy()
    x = s.iloc[:-1].to_numpy()
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if len(x) < 250:
        return {"ou_phi": np.nan, "ou_mu": np.nan, "ou_sigma_eq": np.nan, "ou_half_life_minutes": np.nan}
    model = sm.OLS(y, sm.add_constant(x)).fit()
    a, phi = float(model.params[0]), float(model.params[1])
    mu = a / (1.0 - phi) if abs(1.0 - phi) > 1e-12 else np.nan
    resid = y - (a + phi * x)
    sigma = float(np.std(resid, ddof=1))
    sigma_eq = sigma / np.sqrt(max(1e-12, 1.0 - phi * phi)) if abs(phi) < 1 else np.nan
    half = float(-np.log(2) / np.log(phi)) if 0 < phi < 1 else np.nan
    return {"ou_phi": phi, "ou_mu": mu, "ou_sigma_eq": sigma_eq, "ou_half_life_minutes": half}
