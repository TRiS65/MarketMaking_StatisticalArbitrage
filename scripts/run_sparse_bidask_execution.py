#!/usr/bin/env python3
"""Bid/ask-aware execution audit for the enhanced sparse market-neutral basket.

This keeps the selected position path and midpoint residual gross P&L from
`enhanced_sparse_backtest.parquet`, but replaces the old half-spread cost
approximation with exact bid/ask boundary costs at every residual position
change.

It can run on the existing old Jan-Mar quote parquet files.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from execution_fills import (
    ETF,
    load_old_quotes,
    parse_betas,
    residual_transaction_cost_at_time,
    summarize_by_sample,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"


def main() -> None:
    backtest_path = PROCESSED / "enhanced_sparse_backtest.parquet"
    summary_path = TABLES / "enhanced_backtest_summary.csv"
    if not backtest_path.exists():
        raise FileNotFoundError("Run `python3 scripts/run_final_analysis.py` first.")
    if not summary_path.exists():
        raise FileNotFoundError("Missing enhanced_backtest_summary.csv")

    summary = pd.read_csv(summary_path)
    active = summary[summary["strategy"] != "literature_no_trade"].copy()
    active = active[active["subset"].notna() & (active["subset"].astype(str).str.len() > 0)]
    if active.empty:
        raise ValueError("Could not find selected active sparse strategy in enhanced_backtest_summary.csv")

    subset, beta = parse_betas(active.iloc[0]["betas"])
    symbols = [ETF] + subset
    quotes = load_old_quotes(PROCESSED, symbols)
    bid, ask, mid = quotes["bid"], quotes["ask"], quotes["mid"]

    frame = pd.read_parquet(backtest_path)
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
            costs.append(residual_transaction_cost_at_time(bid, ask, mid, ts, subset, beta, residual_delta=float(d)))
    frame["cost_ret_old"] = frame.get("cost_ret", 0.0)
    frame["net_ret_old"] = frame.get("net_ret", frame.get("gross_ret", 0.0) - frame["cost_ret_old"])
    frame["cost_ret"] = pd.Series(costs, index=frame.index).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    frame["net_ret"] = frame["gross_ret"] - frame["cost_ret"]
    frame["cum_net_bps"] = 1e4 * frame["net_ret"].cumsum()
    frame["sample"] = frame["sample"].astype(str)

    out_path = PROCESSED / "enhanced_sparse_bidask_backtest.parquet"
    frame.to_parquet(out_path)

    out = summarize_by_sample(frame)
    out.insert(0, "strategy", "enhanced_sparse_actual_bidask_boundary_cost")
    out.insert(1, "subset", " ".join(subset))
    out.insert(2, "betas", " ".join(f"{s}:{b:.6f}" for s, b in zip(subset, beta)))
    out.to_csv(TABLES / "enhanced_sparse_bidask_summary.csv", index=False)

    # Also write old-vs-new cost comparison.
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
    pd.DataFrame(comp_rows).to_csv(TABLES / "enhanced_sparse_bidask_comparison.csv", index=False)

    print(f"[sparse-bidask] subset={' '.join(subset)}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
