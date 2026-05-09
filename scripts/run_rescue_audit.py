#!/usr/bin/env python3
"""Narrow final rescue audit.

This script deliberately avoids another broad parameter search.  It implements
the two remaining defensible profitability checks:

1. Re-audit only professor-leaderboard pair candidates with positive gross /
   low-cost evidence.
2. Re-read the existing regime-gate grid as a no-short-into-uptrend walk-forward
   test, distinguishing validation-selected evidence from test-oracle rows.

The output is meant to decide whether any path deserves future event-level TAQ
execution work.  It is not a new final alpha claim.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from project_config import ETF, OUTPUT, TABLES, ensure_output_dirs, split_dates
from research_utils import clipped_last_trade_price, log_returns, make_views
from run_professor_robustness import (
    build_spread,
    estimate_price_regression,
    estimate_return_beta,
    position_path,
    sample_masks,
    zscore,
)


def select_pair_candidates() -> pd.DataFrame:
    leaderboard = pd.read_csv(TABLES / "professor_test_leaderboard.csv")
    selected = pd.read_csv(TABLES / "professor_selected_spread_rules.csv")
    merged = leaderboard.merge(
        selected[["stock", "spread_type", "beta", "alpha"]],
        on=["stock", "spread_type"],
        how="left",
    )
    candidates = merged[
        (merged["no_cost_midpoint"] > 50.0)
        & (merged["quarter_spread_cost"] > 25.0)
        & (merged["clipped_last_trade_proxy"] > 50.0)
        & (merged["half_spread_taker_cost"] > -5.0)
    ].copy()
    candidates["reason"] = np.where(
        candidates["half_spread_taker_cost"] >= 0.0,
        "half_spread_positive",
        "near_breakeven_half_spread",
    )
    return candidates.sort_values("quarter_spread_cost", ascending=False).head(8)


def exact_pair_cost(
    pos: pd.Series,
    beta: float,
    bid: pd.DataFrame,
    ask: pd.DataFrame,
    mid: pd.DataFrame,
    stock: str,
) -> pd.Series:
    delta = pos.diff().fillna(pos).reindex(mid.index).fillna(0.0)
    xlk_buy = np.log(ask[ETF] / mid[ETF]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    xlk_sell = np.log(mid[ETF] / bid[ETF]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    stock_buy = np.log(ask[stock] / mid[stock]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    stock_sell = np.log(mid[stock] / bid[stock]).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    inc = delta.clip(lower=0.0)
    dec = (-delta).clip(lower=0.0)
    return inc * (xlk_buy + abs(beta) * stock_sell) + dec * (xlk_sell + abs(beta) * stock_buy)


def delay_position(pos: pd.Series, latency_min: int) -> pd.Series:
    if latency_min <= 0:
        return pos.copy()
    delayed = pos.shift(latency_min).fillna(0.0)
    same_day = pos.index.to_series().dt.date == pos.index.to_series().shift(latency_min).dt.date
    delayed.loc[~same_day.values] = 0.0
    return delayed


def summarize_returns(frame: pd.DataFrame, sample: str, mask: pd.Series) -> dict:
    sub = frame.loc[mask]
    return {
        "sample": sample,
        "gross_bps": float(1e4 * sub["gross_ret"].sum()),
        "cost_bps": float(1e4 * sub["cost_ret"].sum()),
        "net_bps": float(1e4 * sub["net_ret"].sum()),
        "trades": int((sub["turnover"] > 0).sum()),
        "avg_abs_position": float(sub["position"].abs().mean()),
    }


def monthly_returns(frame: pd.DataFrame, prefix: dict) -> list[dict]:
    rows = []
    for month, sub in frame.groupby(frame.index.to_period("M")):
        rows.append(
            {
                **prefix,
                "month": str(month),
                "gross_bps": float(1e4 * sub["gross_ret"].sum()),
                "cost_bps": float(1e4 * sub["cost_ret"].sum()),
                "net_bps": float(1e4 * sub["net_ret"].sum()),
                "trades": int((sub["turnover"] > 0).sum()),
            }
        )
    return rows


def trade_concentration(frame: pd.DataFrame) -> dict:
    _, validation_end, test_end = split_dates()
    sub = frame.loc[(frame.index >= validation_end) & (frame.index < test_end)].copy()
    active = (sub["position"].shift(1).fillna(0.0).abs() > 0) | (sub["turnover"] > 0)
    starts = active & ~active.shift(1, fill_value=False)
    sub["trade_id"] = starts.cumsum()
    trades = sub.loc[active].groupby("trade_id")["net_ret"].sum()
    if trades.empty:
        return {"test_trade_segments": 0, "top5_abs_net_share": np.nan, "largest_trade_net_bps": np.nan}
    total_abs = trades.abs().sum()
    return {
        "test_trade_segments": int(len(trades)),
        "top5_abs_net_share": float(trades.abs().sort_values(ascending=False).head(5).sum() / total_abs) if total_abs > 0 else np.nan,
        "largest_trade_net_bps": float(1e4 * trades.iloc[trades.abs().argmax()]),
    }


def run_pair_rescue() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    views = make_views()
    mid = views["mid"]
    bid = views["bid"]
    ask = views["ask"]
    log_mid = np.log(mid)
    ret_mid = log_returns(mid)
    last_px = clipped_last_trade_price(views)
    log_last = np.log(last_px)
    ret_last = log_returns(last_px)
    train_mask = sample_masks(mid.index)["train"]

    candidates = select_pair_candidates()
    summary_rows: list[dict] = []
    monthly_rows: list[dict] = []
    concentration_rows: list[dict] = []

    masks = sample_masks(mid.index)
    for _, cand in candidates.iterrows():
        stock = str(cand["stock"])
        spread_type = str(cand["spread_type"])
        beta_return = estimate_return_beta(ret_mid, stock, train_mask)
        alpha_price, beta_price = estimate_price_regression(log_mid, stock, train_mask)
        beta = float(cand["beta"]) if np.isfinite(cand.get("beta", np.nan)) else (beta_price if spread_type == "price_regression_residual" else beta_return)
        alpha = float(cand["alpha"]) if np.isfinite(cand.get("alpha", np.nan)) else (alpha_price if spread_type == "price_regression_residual" else 0.0)
        spread, exec_mid, beta_used, _ = build_spread(log_mid, ret_mid, stock, spread_type, beta_return, alpha_price, beta_price)
        _, exec_last, _, _ = build_spread(log_last, ret_last, stock, spread_type, beta_return, alpha_price, beta_price)
        beta_used = beta if np.isfinite(beta) else beta_used
        z = zscore(spread)
        raw_pos = position_path(z, float(cand["entry_z"]), float(cand["exit_z"]))

        scenarios = []
        for latency in [0, 1, 2, 5]:
            pos = delay_position(raw_pos, latency)
            cost = exact_pair_cost(pos, beta_used, bid, ask, mid, stock)
            gross = pos.shift(1).fillna(0.0) * exec_mid.reindex(pos.index).fillna(0.0)
            turnover = pos.diff().abs().fillna(pos.abs())
            frame = pd.DataFrame(
                {
                    "position": pos,
                    "turnover": turnover,
                    "gross_ret": gross,
                    "cost_ret": cost,
                },
                index=pos.index,
            )
            frame["net_ret"] = frame["gross_ret"] - frame["cost_ret"]
            scenarios.append((f"exact_bidask_latency{latency}", frame))

        pos = raw_pos.copy()
        gross = pos.shift(1).fillna(0.0) * exec_last.reindex(pos.index).fillna(0.0)
        turnover = pos.diff().abs().fillna(pos.abs())
        last_frame = pd.DataFrame({"position": pos, "turnover": turnover, "gross_ret": gross, "cost_ret": 0.0}, index=pos.index)
        last_frame["net_ret"] = last_frame["gross_ret"]
        scenarios.append(("clipped_last_trade_proxy", last_frame))

        for scenario, frame in scenarios:
            base = {
                "pair": str(cand["pair"]),
                "stock": stock,
                "spread_type": spread_type,
                "entry_z": float(cand["entry_z"]),
                "exit_z": float(cand["exit_z"]),
                "execution_scenario": scenario,
            }
            for sample, mask in masks.items():
                summary_rows.append({**base, **summarize_returns(frame, sample, mask)})
            monthly_rows.extend(monthly_returns(frame, base))
            if scenario == "exact_bidask_latency0":
                concentration_rows.append({**base, **trade_concentration(frame)})

    summary = pd.DataFrame(summary_rows)
    monthly = pd.DataFrame(monthly_rows)
    concentration = pd.DataFrame(concentration_rows)
    test = summary[summary["sample"].eq("test")].copy()
    flags = (
        test.pivot_table(index=["pair", "stock", "spread_type"], columns="execution_scenario", values="net_bps", aggfunc="first")
        .reset_index()
    )
    flags["passes_rescue_gate"] = (
        (flags.get("exact_bidask_latency0", -np.inf) > 0)
        & (flags.get("exact_bidask_latency1", -np.inf) > 0)
        & (flags.get("clipped_last_trade_proxy", -np.inf) > 0)
    )
    flags.to_csv(TABLES / "rescue_pair_gate.csv", index=False)
    return summary, monthly, concentration


def run_no_short_audit() -> pd.DataFrame:
    path = TABLES / "regime_gate_grid.csv"
    if not path.exists():
        return pd.DataFrame()
    grid = pd.read_csv(path)
    family = grid[
        grid["gate_mode"].eq("short_uptrend")
        & grid["gate_action"].eq("flat")
        & grid["state_kind"].isin(["intraday_trend", "multi_day_trend", "multi_day_trend_premium"])
    ].copy()
    rows = []
    if family.empty:
        return pd.DataFrame()
    eligible = family[
        (family["train_net_bps"] > 0)
        & (family["validation_net_bps"] > 0)
        & (family["train_trades"] >= 20)
        & (family["validation_trades"] >= 5)
    ].copy()
    if eligible.empty:
        rows.append(
            {
                "selection_type": "walk_forward_selected",
                "decision": "no_trade",
                "reason": "No no-short-into-uptrend rule passed train/validation filters.",
            }
        )
    else:
        selected = eligible.sort_values("train_selection_score", ascending=False).iloc[0]
        rows.append(
            {
                "selection_type": "walk_forward_selected",
                "decision": "active_candidate" if selected["test_net_bps"] > 0 and selected["test_2x_cost_net_bps"] > 0 else "diagnostic_only",
                "reason": "selected on train/validation only; test is holdout",
                **selected.to_dict(),
            }
        )
    oracle = family.sort_values("test_net_bps", ascending=False).iloc[0]
    rows.append(
        {
            "selection_type": "test_oracle_not_selectable",
            "decision": "diagnostic_only",
            "reason": "best test row shown only to measure possible shape; not honest selection",
            **oracle.to_dict(),
        }
    )
    refs = family[
        ((family["state_kind"].eq("intraday_trend")) & (family["lookback_min"].isin([60, 120])) & (family["trend_threshold_bps"].isin([0.0, 25.0])))
        | ((family["state_kind"].eq("multi_day_trend")) & (family["lookback_min"].isin([390, 780])) & (family["trend_threshold_bps"].isin([0.0, 50.0])))
    ].head(8)
    for _, r in refs.iterrows():
        rows.append({"selection_type": "predefined_reference", "decision": "diagnostic_only", "reason": "predefined no-short stress row", **r.to_dict()})
    return pd.DataFrame(rows)


def main() -> None:
    ensure_output_dirs()
    summary, monthly, concentration = run_pair_rescue()
    summary.to_csv(TABLES / "rescue_pair_execution_summary.csv", index=False)
    monthly.to_csv(TABLES / "rescue_pair_monthly.csv", index=False)
    concentration.to_csv(TABLES / "rescue_pair_trade_concentration.csv", index=False)
    no_short = run_no_short_audit()
    no_short.to_csv(TABLES / "rescue_no_short_uptrend_audit.csv", index=False)
    compact_cols = [
        "selection_type",
        "decision",
        "reason",
        "strategy",
        "state_kind",
        "lookback_min",
        "trend_threshold_bps",
        "train_net_bps",
        "validation_net_bps",
        "test_net_bps",
        "test_2x_cost_net_bps",
        "mar_net_bps",
        "apr_net_bps",
    ]
    compact_no_short = no_short[[c for c in compact_cols if c in no_short.columns]].copy() if not no_short.empty else pd.DataFrame()
    compact_no_short.to_csv(TABLES / "rescue_no_short_uptrend_summary.csv", index=False)

    pair_gate = pd.read_csv(TABLES / "rescue_pair_gate.csv")
    report = [
        "# Narrow Rescue Audit",
        "",
        "This audit deliberately avoids broad parameter fishing.  It asks whether the remaining gross-positive pair candidates or a pre-defined no-short-into-uptrend timing rule deserve future event-level execution work.",
        "",
        "## Pair Rescue Gate",
        "",
        pair_gate.to_markdown(index=False),
        "",
        "A pair passes only if exact bid/ask latency-0, exact bid/ask latency-1, and clipped last-trade proxy are all positive in the metadata test window.",
        "",
        "## Trade Concentration",
        "",
        concentration.to_markdown(index=False) if not concentration.empty else "No concentration rows.",
        "",
        "## No-Short-Into-Uptrend Audit",
        "",
        compact_no_short.head(12).to_markdown(index=False) if not compact_no_short.empty else "No regime gate rows available.",
        "",
        "## Interpretation",
        "",
        "These are not final alpha claims.  If no row passes the rescue gate, the final policy remains no-trade.  If a row passes, the next step is raw-event validation around its actual signal timestamps, not another wider parameter grid.",
    ]
    (OUTPUT / "rescue_audit_report.md").write_text("\n".join(report))
    print(f"[ok] wrote {TABLES / 'rescue_pair_execution_summary.csv'}")
    print(f"[ok] wrote {TABLES / 'rescue_no_short_uptrend_audit.csv'}")


if __name__ == "__main__":
    main()
