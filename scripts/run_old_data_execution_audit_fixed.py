#!/usr/bin/env python3
"""Re-audit old pair-trading execution with consistent midpoint-plus-boundary-cost accounting.

Why this exists:
The current old-data pair module has an eye-catching XLK-ORCL result where
"actual bid/ask fills" are much larger than midpoint-no-cost P&L. That is a
red flag because explicit bid/ask execution should generally reduce P&L relative
to the same midpoint strategy, not increase it.

This script recomputes each logged trade as:

    midpoint_gross_bps over the actual trade holding window
    - entry/exit bid-ask boundary costs
    = bidask_net_bps

It then aggregates by pair/parameter/sample.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from execution_fills import (
    ETF,
    continuous_log_returns,
    load_old_quotes,
    residual_transaction_cost_at_time,
)

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"

CONSTITUENTS = ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "CSCO"]
SYMBOLS = [ETF] + CONSTITUENTS


def sample_name(ts: pd.Timestamp) -> str:
    if ts < pd.Timestamp("2026-02-01"):
        return "train"
    if ts < pd.Timestamp("2026-03-01"):
        return "validation"
    return "test"


def main() -> None:
    trade_path = TABLES / "old_pair_trade_log.csv"
    if not trade_path.exists():
        raise FileNotFoundError(
            f"Missing {trade_path}. Run `python3 scripts/run_old_data_method_upgrade.py` first."
        )

    quotes = load_old_quotes(PROCESSED, SYMBOLS)
    bid, ask, mid = quotes["bid"], quotes["ask"], quotes["mid"]
    ret = continuous_log_returns(mid)

    trades = pd.read_csv(trade_path)
    if trades.empty:
        print("[execution-audit-fixed] no trades to audit")
        return

    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    trades["exit_time"] = pd.to_datetime(trades["exit_time"])

    rows = []
    for _, tr in trades.iterrows():
        stock = str(tr["stock"])
        beta = float(tr["beta"])
        subset = [stock]
        betas = np.array([beta], dtype=float)
        entry = pd.Timestamp(tr["entry_time"])
        exit_ = pd.Timestamp(tr["exit_time"])
        direction = str(tr["direction"])

        if entry not in ret.index or exit_ not in ret.index:
            continue

        residual_ret = ret[ETF] - beta * ret[stock]
        # Current strategy convention: position established at entry_time and
        # closed at exit_time, so P&L is accumulated over (entry_time, exit_time].
        window = (residual_ret.index > entry) & (residual_ret.index <= exit_)
        midpoint_move = float(residual_ret.loc[window].sum())
        if direction == "short_residual":
            midpoint_gross = -midpoint_move
            entry_cost = residual_transaction_cost_at_time(bid, ask, mid, entry, subset, betas, residual_delta=-1.0)
            exit_cost = residual_transaction_cost_at_time(bid, ask, mid, exit_, subset, betas, residual_delta=+1.0)
        else:
            midpoint_gross = midpoint_move
            entry_cost = residual_transaction_cost_at_time(bid, ask, mid, entry, subset, betas, residual_delta=+1.0)
            exit_cost = residual_transaction_cost_at_time(bid, ask, mid, exit_, subset, betas, residual_delta=-1.0)

        total_cost = entry_cost + exit_cost
        if not np.isfinite(midpoint_gross) or not np.isfinite(total_cost):
            continue

        out = tr.to_dict()
        out["sample"] = sample_name(entry)
        out["fixed_midpoint_gross_bps"] = 1e4 * midpoint_gross
        out["fixed_bidask_cost_bps"] = 1e4 * total_cost
        out["fixed_bidask_net_bps"] = 1e4 * (midpoint_gross - total_cost)
        out["fixed_cost_exceeds_midpoint_flag"] = bool((midpoint_gross - total_cost) > midpoint_gross + 1e-12)
        rows.append(out)

    fixed = pd.DataFrame(rows)
    out_trade = TABLES / "old_pair_trade_log_execution_fixed.csv"
    fixed.to_csv(out_trade, index=False)

    group_cols = ["pair", "stock", "beta", "entry_z", "exit_z", "max_holding_minutes", "stop_z", "sample"]
    agg = (
        fixed.groupby(group_cols, dropna=False)
        .agg(
            gross_bps=("fixed_midpoint_gross_bps", "sum"),
            cost_bps=("fixed_bidask_cost_bps", "sum"),
            net_bps=("fixed_bidask_net_bps", "sum"),
            num_trades=("fixed_bidask_net_bps", "size"),
            win_rate=("fixed_bidask_net_bps", lambda s: float((s > 0).mean())),
            avg_holding_minutes=("holding_minutes", "mean"),
        )
        .reset_index()
    )
    out_grid = TABLES / "old_pair_leaderboard_execution_fixed.csv"
    agg.to_csv(out_grid, index=False)

    # Select February validation best per stock and report March.
    val = agg[(agg["sample"] == "validation") & (agg["num_trades"] >= 2)].copy()
    if val.empty:
        val = agg[agg["sample"] == "validation"].copy()
    selected = val.sort_values(["stock", "net_bps", "num_trades"], ascending=[True, False, False]).groupby("stock").head(1)
    merge_cols = ["pair", "stock", "beta", "entry_z", "exit_z", "max_holding_minutes", "stop_z"]
    test = agg[agg["sample"] == "test"]
    leaderboard = selected[merge_cols + ["net_bps", "num_trades"]].rename(
        columns={"net_bps": "validation_net_bps", "num_trades": "validation_trades"}
    ).merge(
        test[merge_cols + ["gross_bps", "cost_bps", "net_bps", "num_trades", "win_rate", "avg_holding_minutes"]],
        on=merge_cols,
        how="left",
    )
    leaderboard = leaderboard.rename(
        columns={
            "gross_bps": "test_gross_bps",
            "cost_bps": "test_cost_bps",
            "net_bps": "test_net_bps",
            "num_trades": "test_trades",
        }
    ).sort_values("test_net_bps", ascending=False)
    leaderboard.to_csv(TABLES / "old_pair_validation_selected_execution_fixed.csv", index=False)

    print(f"[execution-audit-fixed] wrote {out_trade.relative_to(ROOT)}")
    print(f"[execution-audit-fixed] wrote {out_grid.relative_to(ROOT)}")
    print("[execution-audit-fixed] validation-selected March leaderboard")
    print(leaderboard.to_string(index=False))


if __name__ == "__main__":
    main()
