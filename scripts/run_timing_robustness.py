#!/usr/bin/env python3
"""Robustness grid for the XLK-only sparse-basket timing extension.

The broader experiment suite audits hedged ETF-basket arbitrage.  This script
audits the separate positive claim in the final report: use the sparse basket's
microprice premium as a timing signal, but execute only XLK.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output"
TABLES = OUTPUT / "tables"
ETF = "XLK"
MINUTES_PER_DAY = 390
SPARSE_WEIGHTS = pd.Series({"MSFT": 0.0797, "NVDA": 0.2257, "ORCL": 0.0745, "CRM": 0.0602, "AMD": 0.1074})


@dataclass(frozen=True)
class TimingRule:
    signal_view: str
    shrink: float
    center_days: int
    entry_bps: float
    exit_bps: float
    max_hold_minutes: int

    @property
    def name(self) -> str:
        return (
            f"{self.signal_view}_cw{self.center_days}d_"
            f"e{self.entry_bps:g}_x{self.exit_bps:g}_mh{self.max_hold_minutes}"
        )


def align_panel() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    panel = pd.read_parquet(PROCESSED / "research_panel.parquet")
    panel["minute"] = pd.to_datetime(panel["minute"])
    symbols = [ETF] + list(SPARSE_WEIGHTS.index)
    mid = panel.pivot(index="minute", columns="symbol", values="mid").sort_index()
    micro = panel.pivot(index="minute", columns="symbol", values="microprice").sort_index()
    spread_bps = panel.pivot(index="minute", columns="symbol", values="spread_bps").sort_index()
    dates = sorted(pd.Series(mid.index.date.astype(str)).unique())
    full_index = [pd.date_range(f"{day} 09:30:00", periods=MINUTES_PER_DAY, freq="min") for day in dates]
    full_index = full_index[0].append(full_index[1:])

    def fill(frame: pd.DataFrame) -> pd.DataFrame:
        aligned = frame.reindex(full_index)
        key = pd.Series(aligned.index.date.astype(str), index=aligned.index)
        return aligned.groupby(key, group_keys=False).ffill(limit=5)

    mid = fill(mid)
    micro = fill(micro)
    spread_bps = fill(spread_bps)
    common = mid.dropna(subset=symbols).index
    common = common.intersection(micro.dropna(subset=symbols).index)
    common = common.intersection(spread_bps.dropna(subset=[ETF]).index)
    return mid.loc[common].astype(float), micro.loc[common].astype(float), spread_bps.loc[common].astype(float)


def log_returns(px: pd.DataFrame) -> pd.DataFrame:
    ret = np.log(px.astype(float)).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    idx = px.index.to_series()
    continuous = (idx.diff() == pd.Timedelta(minutes=1)) & (idx.dt.date == idx.shift(1).dt.date)
    ret.loc[~continuous.values, :] = 0.0
    return ret.clip(-0.05, 0.05)


def signal_prices(mid: pd.DataFrame, micro: pd.DataFrame, shrink: float) -> pd.DataFrame:
    if shrink <= 0:
        return mid
    gap = np.log(micro / mid).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return mid * np.exp(shrink * gap)


def build_signal(mid: pd.DataFrame, micro: pd.DataFrame, rule: TimingRule) -> pd.Series:
    px = signal_prices(mid, micro, rule.shrink)
    ret = log_returns(px)
    basket_ret = (ret[list(SPARSE_WEIGHTS.index)] * SPARSE_WEIGHTS).sum(axis=1)
    basket_log_value = np.log(float(px[ETF].iloc[0])) + basket_ret.cumsum()
    raw_premium = np.log(px[ETF]) - basket_log_value
    center = raw_premium.rolling(rule.center_days * MINUTES_PER_DAY, min_periods=MINUTES_PER_DAY).mean().shift(1)
    return 1e4 * (raw_premium - center)


def position_from_signal(signal_bps: pd.Series, entry_bps: float, exit_bps: float, max_hold_minutes: int) -> pd.Series:
    vals = signal_bps.to_numpy(dtype=float)
    dates = pd.Series(signal_bps.index.date.astype(str), index=signal_bps.index).to_numpy()
    pos = np.zeros(len(signal_bps), dtype=float)
    current = 0.0
    hold = 0
    for i, x in enumerate(vals):
        if i > 0 and dates[i] != dates[i - 1]:
            current = 0.0
            hold = 0
        if np.isfinite(x):
            if current == 0.0:
                if x > entry_bps:
                    current = -1.0
                    hold = 0
                elif x < -entry_bps:
                    current = 1.0
                    hold = 0
            else:
                hold += 1
                if abs(x) <= exit_bps or hold >= max_hold_minutes:
                    current = 0.0
                    hold = 0
        if i < len(vals) - 1 and dates[i + 1] != dates[i]:
            current = 0.0
            hold = 0
        pos[i] = current
    return pd.Series(pos, index=signal_bps.index)


def backtest_rule(rule: TimingRule, mid: pd.DataFrame, micro: pd.DataFrame, spread_bps: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    signal = build_signal(mid, micro, rule)
    pos = position_from_signal(signal, rule.entry_bps, rule.exit_bps, rule.max_hold_minutes)
    ret = log_returns(mid)[ETF]
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * (spread_bps[ETF] / 2.0) / 1e4
    gross = pos.shift(1).fillna(0.0) * ret
    net = gross - cost
    frame = pd.DataFrame({"signal_bps": signal, "position": pos, "turnover": turnover, "gross_ret": gross, "cost_ret": cost, "net_ret": net})

    def period_stats(start: str, end: str, prefix: str) -> dict:
        sub = frame.loc[(frame.index >= start) & (frame.index < end)]
        return {
            f"{prefix}_gross_bps": float(1e4 * sub["gross_ret"].sum()),
            f"{prefix}_cost_bps": float(1e4 * sub["cost_ret"].sum()),
            f"{prefix}_net_bps": float(1e4 * sub["net_ret"].sum()),
            f"{prefix}_trades": int((sub["turnover"] > 0).sum()),
            f"{prefix}_avg_abs_position": float(sub["position"].abs().mean()),
        }

    out = {
        "strategy": rule.name,
        "signal_view": rule.signal_view,
        "shrink": rule.shrink,
        "center_days": rule.center_days,
        "entry_bps": rule.entry_bps,
        "exit_bps": rule.exit_bps,
        "max_hold_minutes": rule.max_hold_minutes,
    }
    out.update(period_stats("2026-01-01", "2026-02-01", "jan"))
    out.update(period_stats("2026-02-01", "2026-03-01", "feb"))
    out.update(period_stats("2026-03-01", "2026-04-01", "mar"))
    out["train_net_bps"] = out["jan_net_bps"] + out["feb_net_bps"]
    out["train_trades"] = out["jan_trades"] + out["feb_trades"]
    out["train_fold_positive_rate"] = float((out["jan_net_bps"] > 0) + (out["feb_net_bps"] > 0)) / 2.0
    out["all_net_bps"] = out["train_net_bps"] + out["mar_net_bps"]
    out["train_selection_score"] = (
        out["train_net_bps"]
        + 0.75 * min(out["jan_net_bps"], out["feb_net_bps"])
        + 25.0 * out["train_fold_positive_rate"]
        - 0.10 * (out["jan_cost_bps"] + out["feb_cost_bps"])
    )
    return frame, out


def build_rules() -> list[TimingRule]:
    rules = []
    views = [("mid", 0.0), ("micro_shrink_0.25", 0.25), ("micro_shrink_0.50", 0.50), ("micro_shrink_0.75", 0.75), ("micro", 1.0)]
    for name, shrink in views:
        for center_days in [3, 5, 10]:
            for entry in [30.0, 40.0, 50.0, 60.0, 75.0, 100.0]:
                exits = sorted({0.0, min(25.0, entry / 2.0), min(40.0, entry * 0.75)})
                for exit_bps in exits:
                    if exit_bps >= entry:
                        continue
                    for max_hold in [120, 240, 390]:
                        rules.append(TimingRule(name, shrink, center_days, entry, exit_bps, max_hold))
    return rules


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    mid, micro, spread_bps = align_panel()
    rows = []
    best_frame = None
    best_row = None
    for rule in build_rules():
        frame, row = backtest_rule(rule, mid, micro, spread_bps)
        rows.append(row)
    grid = pd.DataFrame(rows)
    train_valid = (grid["train_trades"].between(20, 140)) & (grid["train_net_bps"] > 0) & (grid["train_fold_positive_rate"] >= 1.0)
    stable = (
        grid.assign(train_valid=train_valid)
        .groupby(["signal_view", "center_days", "entry_bps"])
        .agg(
            rules=("strategy", "count"),
            valid_rules=("train_valid", "sum"),
            median_train_net_bps=("train_net_bps", "median"),
            p25_train_net_bps=("train_net_bps", lambda s: float(np.percentile(s, 25))),
            median_mar_net_bps=("mar_net_bps", "median"),
            positive_march_rate=("mar_net_bps", lambda s: float((s > 0).mean())),
        )
        .reset_index()
    )
    stable["train_island_score"] = (
        150.0 * stable["valid_rules"]
        + stable["median_train_net_bps"]
        + 0.50 * stable["p25_train_net_bps"]
    )
    stable = stable.sort_values(["train_island_score", "valid_rules"], ascending=False).reset_index(drop=True)

    selected = pd.DataFrame()
    eligible_islands = stable[(stable["valid_rules"] >= 4) & (stable["median_train_net_bps"] > 0)]
    if not eligible_islands.empty:
        island = eligible_islands.iloc[0]
        in_island = (
            (grid["signal_view"] == island["signal_view"])
            & (grid["center_days"] == island["center_days"])
            & (grid["entry_bps"] == island["entry_bps"])
            & train_valid
        )
        selected = grid.loc[in_island].sort_values("train_selection_score", ascending=False).head(1)

    if selected.empty:
        decision = pd.DataFrame([{"decision": "no_trade", "reason": "No XLK-only timing rule passed Jan-Feb train filters.", "train_net_bps": 0.0, "mar_net_bps": 0.0}])
    else:
        best_row = selected.iloc[0].to_dict()
        best_rule = TimingRule(
            signal_view=str(best_row["signal_view"]),
            shrink=float(best_row["shrink"]),
            center_days=int(best_row["center_days"]),
            entry_bps=float(best_row["entry_bps"]),
            exit_bps=float(best_row["exit_bps"]),
            max_hold_minutes=int(best_row["max_hold_minutes"]),
        )
        best_frame, _ = backtest_rule(best_rule, mid, micro, spread_bps)
        best_frame.to_parquet(PROCESSED / "timing_robustness_selected_backtest.parquet")
        decision = pd.DataFrame(
            [
                {
                    "decision": "active_xlk_timing",
                    "reason": "Selected by Jan-Feb stability island first; March is OOS.",
                    "selected_strategy": best_row["strategy"],
                    "train_net_bps": best_row["train_net_bps"],
                    "mar_net_bps": best_row["mar_net_bps"],
                    "all_net_bps": best_row["all_net_bps"],
                    "train_trades": best_row["train_trades"],
                    "mar_trades": best_row["mar_trades"],
                }
            ]
        )

    grid = grid.sort_values("train_selection_score", ascending=False).reset_index(drop=True)
    grid.to_csv(TABLES / "timing_robustness_grid.csv", index=False)
    decision.to_csv(TABLES / "timing_robustness_decision.csv", index=False)
    stable.to_csv(TABLES / "timing_robustness_stability.csv", index=False)
    print("[timing-robustness] decision")
    print(decision.to_string(index=False))
    print("[timing-robustness] top 10 train-selected grid rows")
    print(grid.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
