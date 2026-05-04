#!/usr/bin/env python3
"""Bid/ask-aware execution audit for the XLK-only timing extension.

This keeps the existing timing signal and position path from
`timing_extension_backtest.parquet`, but replaces the half-spread approximation
with exact ask/bid boundary costs for XLK position changes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from execution_fills import (
    ETF,
    load_old_quotes,
    summarize_by_sample,
    xlk_transaction_cost_at_time,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"


def sample_name(ts: pd.Timestamp) -> str:
    if ts < pd.Timestamp("2026-02-01"):
        return "jan"
    if ts < pd.Timestamp("2026-03-01"):
        return "feb"
    if ts < pd.Timestamp("2026-04-01"):
        return "mar"
    return "other"


def main() -> None:
    path = PROCESSED / "timing_extension_backtest.parquet"
    if not path.exists():
        raise FileNotFoundError("Run `python3 scripts/run_timing_extension.py` first.")

    quotes = load_old_quotes(PROCESSED, [ETF])
    bid, ask, mid = quotes["bid"], quotes["ask"], quotes["mid"]

    frame = pd.read_parquet(path)
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index().copy()
    frame["position"] = frame["position"].astype(float)
    prev = frame["position"].shift(1).fillna(0.0)
    delta = frame["position"] - prev
    frame["position_delta"] = delta
    frame["turnover_bidask"] = delta.abs()

    costs = []
    for ts, d in delta.items():
        if abs(d) <= 0:
            costs.append(0.0)
        else:
            costs.append(xlk_transaction_cost_at_time(bid, ask, mid, ts, float(d), etf=ETF))
    frame["cost_ret_old"] = frame.get("cost_ret", 0.0)
    frame["net_ret_old"] = frame.get("net_ret", frame["gross_ret"] - frame["cost_ret_old"])
    frame["cost_ret"] = pd.Series(costs, index=frame.index).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    frame["net_ret"] = frame["gross_ret"] - frame["cost_ret"]
    frame["cum_net_bps"] = 1e4 * frame["net_ret"].cumsum()
    frame["sample"] = [sample_name(ts) for ts in frame.index]

    out_path = PROCESSED / "timing_extension_bidask_backtest.parquet"
    frame.to_parquet(out_path)

    out = summarize_by_sample(frame)
    out.insert(0, "strategy", "timing_extension_actual_bidask_boundary_cost")
    out.to_csv(TABLES / "timing_extension_bidask_summary.csv", index=False)

    comp_rows = []
    for sample, part in frame.groupby("sample"):
        comp_rows.append(
            {
                "sample": sample,
                "old_gross_bps": 1e4 * part["gross_ret"].sum(),
                "old_cost_bps": 1e4 * part["cost_ret_old"].sum(),
                "old_net_bps": 1e4 * part["net_ret_old"].sum(),
                "new_gross_bps": 1e4 * part["gross_ret"].sum(),
                "new_bidask_cost_bps": 1e4 * part["cost_ret"].sum(),
                "new_bidask_net_bps": 1e4 * part["net_ret"].sum(),
                "turnover": float(part["turnover_bidask"].sum()),
            }
        )
    pd.DataFrame(comp_rows).to_csv(TABLES / "timing_extension_bidask_comparison.csv", index=False)

    print("[timing-bidask] summary")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
