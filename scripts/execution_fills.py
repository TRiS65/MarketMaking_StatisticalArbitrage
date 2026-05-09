#!/usr/bin/env python3
"""Reusable execution helpers for XLK minute quote parquet data.

These helpers use a consistent convention:

- Signal/position logic defines a desired residual position.
- Gross P&L is midpoint log-return P&L over the same position interval.
- Execution cost is computed from actual bid/ask quotes at position-change timestamps.
- For a positive residual delta, we buy residual: buy XLK at ask and sell/short the basket leg at bid.
- For a negative residual delta, we sell residual: sell/short XLK at bid and buy/cover the basket leg at ask.

This avoids comparing a minute-by-minute midpoint-return P&L with a different
entry/exit boundary log-spread P&L.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from project_config import ETF

MINUTES_PER_DAY = 390


def load_old_quotes(processed: Path, symbols: Iterable[str] | None = None) -> dict[str, pd.DataFrame]:
    quote_parts = []
    final_path = processed / "minute_quotes_finaldata.parquet"
    new_path = processed / "minute_quotes_new.parquet"
    if final_path.exists():
        quote_parts.append(pd.read_parquet(final_path))
    elif new_path.exists():
        quote_parts.append(pd.read_parquet(new_path))
    else:
        for month in ["01", "02", "03"]:
            path = processed / f"minute_quotes_2026_{month}.parquet"
            if not path.exists():
                raise FileNotFoundError(f"Missing {path}")
            quote_parts.append(pd.read_parquet(path))
    quotes = pd.concat(quote_parts, ignore_index=True)
    quotes["minute"] = pd.to_datetime(quotes["minute"])
    if symbols is not None:
        quotes = quotes[quotes["symbol"].isin(list(symbols))].copy()
    quotes["mid"] = (quotes["bid"] + quotes["ask"]) / 2.0
    quotes = quotes.sort_values(["symbol", "minute"])
    return {
        "bid": pivot_and_align(quotes, "bid"),
        "ask": pivot_and_align(quotes, "ask"),
        "mid": pivot_and_align(quotes, "mid"),
    }


def pivot_and_align(panel: pd.DataFrame, col: str) -> pd.DataFrame:
    frame = panel.pivot(index="minute", columns="symbol", values=col).sort_index()
    dates = sorted(pd.Series(frame.index.date.astype(str)).unique())
    if not dates:
        return frame
    parts = [pd.date_range(f"{day} 09:30:00", periods=MINUTES_PER_DAY, freq="min") for day in dates]
    full_index = parts[0].append(parts[1:]) if len(parts) > 1 else parts[0]
    aligned = frame.reindex(full_index)
    day_key = pd.Series(aligned.index.date.astype(str), index=aligned.index)
    return aligned.groupby(day_key, group_keys=False).ffill(limit=5)


def continuous_log_returns(mid: pd.DataFrame) -> pd.DataFrame:
    ret = np.log(mid.astype(float)).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    idx = pd.Series(mid.index, index=mid.index)
    continuous = (idx.diff() == pd.Timedelta(minutes=1)) & (idx.dt.date == idx.shift(1).dt.date)
    ret.loc[~continuous.values, :] = 0.0
    return ret.clip(-0.05, 0.05)


def _safe_log_ratio(num: float, den: float) -> float:
    if not np.isfinite(num) or not np.isfinite(den) or num <= 0 or den <= 0:
        return np.nan
    return float(np.log(num / den))


def residual_transaction_cost_at_time(
    bid: pd.DataFrame,
    ask: pd.DataFrame,
    mid: pd.DataFrame,
    timestamp: pd.Timestamp,
    subset: list[str],
    beta: np.ndarray,
    residual_delta: float,
    etf: str = ETF,
) -> float:
    """Exact log-return cost for changing residual position by residual_delta.

    residual_delta > 0 means buy residual:
        buy ETF at ask and sell/short beta-weighted stocks at bid.
    residual_delta < 0 means sell residual:
        sell/short ETF at bid and buy/cover beta-weighted stocks at ask.

    Returns decimal log-return cost, not bps.
    """
    if timestamp not in mid.index:
        return np.nan
    if not np.isfinite(residual_delta) or residual_delta == 0:
        return 0.0

    scale = abs(float(residual_delta))
    beta = np.asarray(beta, dtype=float)
    if residual_delta > 0:
        # Buy XLK at ask: cost = log(ask/mid).
        cost = _safe_log_ratio(ask.at[timestamp, etf], mid.at[timestamp, etf])
        # Sell/short basket stocks at bid: cost = beta * log(mid/bid).
        for s, b in zip(subset, beta):
            c = _safe_log_ratio(mid.at[timestamp, s], bid.at[timestamp, s])
            cost += abs(float(b)) * c
    else:
        # Sell/short XLK at bid: cost = log(mid/bid).
        cost = _safe_log_ratio(mid.at[timestamp, etf], bid.at[timestamp, etf])
        # Buy/cover basket stocks at ask: cost = beta * log(ask/mid).
        for s, b in zip(subset, beta):
            c = _safe_log_ratio(ask.at[timestamp, s], mid.at[timestamp, s])
            cost += abs(float(b)) * c
    return float(scale * cost)


def xlk_transaction_cost_at_time(
    bid: pd.DataFrame,
    ask: pd.DataFrame,
    mid: pd.DataFrame,
    timestamp: pd.Timestamp,
    position_delta: float,
    etf: str = ETF,
) -> float:
    """Exact log-return cost for changing an XLK-only position.

    position_delta > 0 means buy XLK at ask.
    position_delta < 0 means sell/short XLK at bid.
    """
    if timestamp not in mid.index:
        return np.nan
    if not np.isfinite(position_delta) or position_delta == 0:
        return 0.0
    if position_delta > 0:
        cost = _safe_log_ratio(ask.at[timestamp, etf], mid.at[timestamp, etf])
    else:
        cost = _safe_log_ratio(mid.at[timestamp, etf], bid.at[timestamp, etf])
    return float(abs(position_delta) * cost)


def parse_betas(beta_text: str) -> tuple[list[str], np.ndarray]:
    """Parse strings like 'MSFT:0.0797 NVDA:0.2257'."""
    symbols = []
    betas = []
    for token in str(beta_text).split():
        if ":" not in token:
            continue
        s, b = token.split(":", 1)
        symbols.append(s)
        betas.append(float(b))
    if not symbols:
        raise ValueError(f"Could not parse beta string: {beta_text!r}")
    return symbols, np.asarray(betas, dtype=float)


def summarize_by_sample(frame: pd.DataFrame, sample_col: str = "sample") -> pd.DataFrame:
    rows = []
    for sample, part in frame.groupby(sample_col):
        net = part["net_ret"]
        pnl_bps = 1e4 * net.cumsum()
        max_dd = float((pnl_bps - pnl_bps.cummax()).min()) if len(pnl_bps) else 0.0
        std = net.std()
        tstat = float(np.sqrt(len(net)) * net.mean() / std) if std and np.isfinite(std) and std > 0 else np.nan
        rows.append(
            {
                "sample": sample,
                "observations": len(part),
                "gross_bps": float(1e4 * part["gross_ret"].sum()),
                "cost_bps": float(1e4 * part["cost_ret"].sum()),
                "net_bps": float(1e4 * part["net_ret"].sum()),
                "turnover": float(part.get("turnover", pd.Series(index=part.index, dtype=float)).sum()),
                "trades": int((part.get("turnover", pd.Series(index=part.index, dtype=float)) > 0).sum()),
                "max_drawdown_bps": max_dd,
                "tstat_style": tstat,
            }
        )
    return pd.DataFrame(rows)
