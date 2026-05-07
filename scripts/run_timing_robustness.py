#!/usr/bin/env python3
"""Robustness grid for XLK-only sparse-basket timing on the expanded data.

This module audits the separate active timing claim:

    sparse/top-holdings basket microprice premium -> trade XLK only

It is not market-neutral arbitrage.  Selection uses Jan-Feb stability only; the
out-of-sample audit is March + April.  The selected rule then receives exact
XLK bid/ask boundary, latency, cost-stress, and directional controls.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from project_config import ETF, MINUTES_PER_DAY, PROCESSED, TABLES, OUTPUT, metadata


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


def load_weights(top_n: int = 5) -> pd.Series:
    holdings = pd.read_csv(TABLES / "selected_xlk_holdings.csv")
    holdings = holdings[holdings["used_in_clean_panel"].astype(bool)].head(top_n).copy()
    weights = holdings.set_index("symbol")["basket_weight"].astype(float)
    return weights / weights.sum()


def align_panel(weights: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    panel = pd.read_parquet(PROCESSED / "research_panel.parquet")
    panel["minute"] = pd.to_datetime(panel["minute"])
    symbols = [ETF] + list(weights.index)

    def pivot(col: str) -> pd.DataFrame:
        return panel.pivot(index="minute", columns="symbol", values=col).sort_index()

    mid = pivot("mid")
    micro = pivot("microprice")
    spread_bps = pivot("spread_bps")
    bid = pivot("bid")
    ask = pivot("ask")

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
    bid = fill(bid)
    ask = fill(ask)
    common = mid.dropna(subset=symbols).index
    common = common.intersection(micro.dropna(subset=symbols).index)
    common = common.intersection(spread_bps.dropna(subset=[ETF]).index)
    common = common.intersection(bid.dropna(subset=[ETF]).index)
    common = common.intersection(ask.dropna(subset=[ETF]).index)
    return (
        mid.loc[common, symbols].astype(float),
        micro.loc[common, symbols].astype(float),
        spread_bps.loc[common, [ETF]].astype(float),
        bid.loc[common, [ETF]].astype(float),
        ask.loc[common, [ETF]].astype(float),
    )


def log_returns(px: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    ret = np.log(px.astype(float)).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    idx = px.index.to_series()
    continuous = (idx.diff() == pd.Timedelta(minutes=1)) & (idx.dt.date == idx.shift(1).dt.date)
    ret.loc[~continuous.values] = 0.0
    return ret.clip(-0.05, 0.05)


def signal_prices(mid: pd.DataFrame, micro: pd.DataFrame, shrink: float) -> pd.DataFrame:
    if shrink <= 0:
        return mid
    gap = np.log(micro / mid).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return mid * np.exp(shrink * gap)


def build_signal(mid: pd.DataFrame, micro: pd.DataFrame, weights: pd.Series, rule: TimingRule) -> pd.Series:
    px = signal_prices(mid, micro, rule.shrink)
    ret = log_returns(px)
    basket_ret = (ret[weights.index] * weights).sum(axis=1)
    basket_log_value = np.log(float(px[ETF].iloc[0])) + basket_ret.cumsum()
    raw_premium = np.log(px[ETF]) - basket_log_value
    center = raw_premium.rolling(rule.center_days * MINUTES_PER_DAY, min_periods=MINUTES_PER_DAY).mean().shift(1)
    return (1e4 * (raw_premium - center)).replace([np.inf, -np.inf], np.nan)


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


def latency_position(pos: pd.Series, latency_min: int) -> pd.Series:
    if latency_min <= 0:
        return pos.copy()
    key = pd.Series(pos.index.date.astype(str), index=pos.index)
    return pos.groupby(key, group_keys=False).shift(latency_min).fillna(0.0)


def xlk_exact_cost(delta: pd.Series, bid: pd.DataFrame, ask: pd.DataFrame, mid: pd.DataFrame) -> pd.Series:
    mid_x = mid[ETF]
    buy_cost = np.log(ask[ETF] / mid_x).replace([np.inf, -np.inf], np.nan)
    sell_cost = np.log(mid_x / bid[ETF]).replace([np.inf, -np.inf], np.nan)
    return pd.Series(np.where(delta > 0, delta.abs() * buy_cost, delta.abs() * sell_cost), index=delta.index).fillna(0.0)


def backtest_position(
    pos: pd.Series,
    mid: pd.DataFrame,
    spread_bps: pd.DataFrame,
    bid: pd.DataFrame | None = None,
    ask: pd.DataFrame | None = None,
    cost_model: str = "halfspread",
    cost_multiplier: float = 1.0,
    latency_min: int = 0,
) -> pd.DataFrame:
    exec_pos = latency_position(pos, latency_min)
    ret = log_returns(mid[ETF])
    gross = exec_pos.shift(1).fillna(0.0) * ret
    turnover = exec_pos.diff().abs().fillna(exec_pos.abs())
    if cost_model == "halfspread":
        cost = turnover * (spread_bps[ETF] / 2.0) / 1e4
    elif cost_model == "exact_bidask":
        if bid is None or ask is None:
            raise ValueError("bid/ask required for exact_bidask cost model")
        cost = xlk_exact_cost(exec_pos.diff().fillna(exec_pos), bid, ask, mid)
    else:
        raise ValueError(f"unknown cost_model={cost_model}")
    cost = cost * cost_multiplier
    return pd.DataFrame(
        {
            "position": exec_pos,
            "turnover": turnover,
            "gross_ret": gross,
            "cost_ret": cost,
            "net_ret": gross - cost,
        }
    )


def period_stats(frame: pd.DataFrame, start: str | pd.Timestamp, end: str | pd.Timestamp, prefix: str) -> dict:
    sub = frame.loc[(frame.index >= pd.Timestamp(start)) & (frame.index < pd.Timestamp(end))]
    return {
        f"{prefix}_gross_bps": float(1e4 * sub["gross_ret"].sum()),
        f"{prefix}_cost_bps": float(1e4 * sub["cost_ret"].sum()),
        f"{prefix}_net_bps": float(1e4 * sub["net_ret"].sum()),
        f"{prefix}_trades": int((sub["turnover"] > 0).sum()),
        f"{prefix}_avg_abs_position": float(sub["position"].abs().mean()) if len(sub) else 0.0,
    }


def summarize(frame: pd.DataFrame) -> dict:
    meta = metadata()
    out = {}
    out.update(period_stats(frame, "2025-11-01", "2025-12-01", "nov"))
    out.update(period_stats(frame, "2025-12-01", "2026-01-01", "dec"))
    out.update(period_stats(frame, "2026-01-01", "2026-02-01", "jan"))
    out.update(period_stats(frame, "2026-02-01", "2026-03-01", "feb"))
    out.update(period_stats(frame, "2026-03-01", "2026-04-01", "mar"))
    out.update(period_stats(frame, "2026-04-01", "2026-05-01", "apr"))
    out.update(period_stats(frame, "2026-03-01", meta.get("test_end", "2026-05-01"), "test"))
    out["train_net_bps"] = out["jan_net_bps"] + out["feb_net_bps"]
    out["train_trades"] = out["jan_trades"] + out["feb_trades"]
    out["train_fold_positive_rate"] = float((out["jan_net_bps"] > 0) + (out["feb_net_bps"] > 0)) / 2.0
    out["all_net_bps"] = out["train_net_bps"] + out["test_net_bps"]
    return out


def backtest_rule(
    rule: TimingRule,
    mid: pd.DataFrame,
    micro: pd.DataFrame,
    spread_bps: pd.DataFrame,
    weights: pd.Series,
) -> tuple[pd.DataFrame, dict]:
    signal = build_signal(mid, micro, weights, rule)
    pos = position_from_signal(signal, rule.entry_bps, rule.exit_bps, rule.max_hold_minutes)
    frame = backtest_position(pos, mid, spread_bps, cost_model="halfspread")
    frame.insert(0, "signal_bps", signal)
    out = {
        "strategy": rule.name,
        "signal_view": rule.signal_view,
        "shrink": rule.shrink,
        "center_days": rule.center_days,
        "entry_bps": rule.entry_bps,
        "exit_bps": rule.exit_bps,
        "max_hold_minutes": rule.max_hold_minutes,
    }
    out.update(summarize(frame))
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


def trade_concentration(frame: pd.DataFrame) -> pd.DataFrame:
    entry = frame["position"].ne(0) & frame["position"].shift().fillna(0).eq(0)
    active = frame[frame["position"].ne(0)].copy()
    if active.empty:
        return pd.DataFrame([{"trades": 0}])
    active["trade_id"] = entry.cumsum().loc[active.index]
    trades = active.groupby("trade_id", as_index=False).agg(net_bps=("net_ret", lambda s: 1e4 * s.sum()))
    total = float(trades["net_bps"].sum())
    return pd.DataFrame(
        [
            {
                "trades": int(len(trades)),
                "total_trade_net_bps": total,
                "top1_trade_net_bps": float(trades["net_bps"].nlargest(1).sum()),
                "top5_trade_net_bps": float(trades["net_bps"].nlargest(5).sum()),
                "top5_share_of_positive_total": float(trades["net_bps"].nlargest(5).sum() / total) if total > 0 else np.nan,
            }
        ]
    )


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    weights = load_weights(top_n=5)
    mid, micro, spread_bps, bid, ask = align_panel(weights)

    rows = []
    for rule in build_rules():
        _, row = backtest_rule(rule, mid, micro, spread_bps, weights)
        rows.append(row)
    grid = pd.DataFrame(rows)
    train_valid = (grid["train_trades"].between(20, 160)) & (grid["train_net_bps"] > 0) & (grid["train_fold_positive_rate"] >= 1.0)
    stable = (
        grid.assign(train_valid=train_valid)
        .groupby(["signal_view", "center_days", "entry_bps"])
        .agg(
            rules=("strategy", "count"),
            valid_rules=("train_valid", "sum"),
            median_train_net_bps=("train_net_bps", "median"),
            p25_train_net_bps=("train_net_bps", lambda s: float(np.percentile(s, 25))),
            median_test_net_bps=("test_net_bps", "median"),
            positive_test_rate=("test_net_bps", lambda s: float((s > 0).mean())),
        )
        .reset_index()
    )
    stable["train_island_score"] = 150.0 * stable["valid_rules"] + stable["median_train_net_bps"] + 0.50 * stable["p25_train_net_bps"]
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

    selected_backtest_path = PROCESSED / "timing_robustness_selected_backtest.parquet"
    if selected.empty:
        if selected_backtest_path.exists():
            selected_backtest_path.unlink()
        decision = pd.DataFrame([{"decision": "no_trade", "reason": "No XLK-only timing rule passed Jan-Feb train filters.", "train_net_bps": 0.0, "test_net_bps": 0.0}])
        controls = pd.DataFrame()
        execution = pd.DataFrame()
        monthly = pd.DataFrame()
        concentration = pd.DataFrame()
    else:
        best = selected.iloc[0].to_dict()
        rule = TimingRule(str(best["signal_view"]), float(best["shrink"]), int(best["center_days"]), float(best["entry_bps"]), float(best["exit_bps"]), int(best["max_hold_minutes"]))
        signal = build_signal(mid, micro, weights, rule)
        pos = position_from_signal(signal, rule.entry_bps, rule.exit_bps, rule.max_hold_minutes)
        selected_frame = backtest_position(pos, mid, spread_bps, cost_model="halfspread")
        selected_frame.insert(0, "signal_bps", signal)
        selected_frame.to_parquet(selected_backtest_path)

        control_rows = []
        control_positions = {
            "selected": pos,
            "sign_flip": -pos,
            "active_always_long": pd.Series(np.where(pos != 0, 1.0, 0.0), index=pos.index),
            "active_always_short": pd.Series(np.where(pos != 0, -1.0, 0.0), index=pos.index),
        }
        for name, cpos in control_positions.items():
            row = {"control": name}
            row.update(summarize(backtest_position(cpos, mid, spread_bps, cost_model="halfspread")))
            control_rows.append(row)

        rng = np.random.default_rng(20260507)
        shifted = []
        for _ in range(200):
            k = int(rng.integers(MINUTES_PER_DAY, max(MINUTES_PER_DAY + 1, len(signal) - MINUTES_PER_DAY)))
            s = pd.Series(np.roll(signal.to_numpy(), k), index=signal.index)
            p = position_from_signal(s, rule.entry_bps, rule.exit_bps, rule.max_hold_minutes)
            shifted.append(summarize(backtest_position(p, mid, spread_bps, cost_model="halfspread"))["test_net_bps"])
        control_rows.extend(
            [
                {"control": "circular_shift_mean", "test_net_bps": float(np.mean(shifted))},
                {"control": "circular_shift_p95", "test_net_bps": float(np.percentile(shifted, 95))},
                {"control": "selected_vs_circular_pvalue", "test_net_bps": float(np.mean(np.asarray(shifted) >= best["test_net_bps"]))},
            ]
        )
        controls = pd.DataFrame(control_rows)

        exec_rows = []
        for model, latency in [("halfspread", 0), ("exact_bidask", 0), ("exact_bidask", 1), ("exact_bidask", 2), ("exact_bidask", 5)]:
            frame = backtest_position(pos, mid, spread_bps, bid=bid, ask=ask, cost_model=model, latency_min=latency)
            row = {"execution_model": model, "latency_min": latency}
            row.update(summarize(frame))
            exec_rows.append(row)
        execution = pd.DataFrame(exec_rows)

        cost_rows = []
        for cm in [1.0, 1.5, 2.0, 3.0, 4.0]:
            frame = backtest_position(pos, mid, spread_bps, bid=bid, ask=ask, cost_model="exact_bidask", cost_multiplier=cm)
            row = {"cost_multiplier": cm, "execution_model": "exact_bidask"}
            row.update(summarize(frame))
            cost_rows.append(row)
        cost_sensitivity = pd.DataFrame(cost_rows)
        cost_sensitivity.to_csv(TABLES / "timing_robustness_cost_sensitivity.csv", index=False)

        monthly_rows = []
        for month, part in selected_frame.groupby(selected_frame.index.to_period("M")):
            monthly_rows.append(
                {
                    "month": str(month),
                    "gross_bps": float(1e4 * part["gross_ret"].sum()),
                    "cost_bps": float(1e4 * part["cost_ret"].sum()),
                    "net_bps": float(1e4 * part["net_ret"].sum()),
                    "trades": int((part["turnover"] > 0).sum()),
                    "avg_abs_position": float(part["position"].abs().mean()),
                }
            )
        monthly = pd.DataFrame(monthly_rows)
        concentration = trade_concentration(selected_frame)

        exact0 = execution[(execution["execution_model"] == "exact_bidask") & (execution["latency_min"] == 0)].iloc[0]
        exact1 = execution[(execution["execution_model"] == "exact_bidask") & (execution["latency_min"] == 1)].iloc[0]
        sign = controls[controls["control"] == "sign_flip"].iloc[0]
        always_long = controls[controls["control"] == "active_always_long"].iloc[0]
        always_short = controls[controls["control"] == "active_always_short"].iloc[0]
        pval = float(controls[controls["control"] == "selected_vs_circular_pvalue"]["test_net_bps"].iloc[0])
        reasons = []
        if best["test_net_bps"] <= 0:
            reasons.append("halfspread_test<=0")
        if exact0["test_net_bps"] <= 0:
            reasons.append("exact_bidask_test<=0")
        if exact1["test_net_bps"] <= 0:
            reasons.append("latency1_test<=0")
        if best["test_net_bps"] <= max(always_long["test_net_bps"], always_short["test_net_bps"]):
            reasons.append("does_not_beat_directional_control")
        if sign["test_net_bps"] >= best["test_net_bps"]:
            reasons.append("sign_flip_not_worse")
        if pval > 0.10:
            reasons.append("circular_pvalue>0.10")

        decision_label = "candidate_active_xlk_timing" if not reasons else "no_trade"
        decision = pd.DataFrame(
            [
                {
                    "decision": decision_label,
                    "reason": ";".join(reasons) if reasons else "passes Mar-Apr exact execution/control audit",
                    "selected_strategy": best["strategy"],
                    "basket_symbols": " ".join(weights.index),
                    "basket_weights": " ".join(f"{k}:{v:.4f}" for k, v in weights.items()),
                    "train_net_bps": best["train_net_bps"],
                    "mar_net_bps": best["mar_net_bps"],
                    "apr_net_bps": best["apr_net_bps"],
                    "test_net_bps": best["test_net_bps"],
                    "all_net_bps": best["all_net_bps"],
                    "train_trades": best["train_trades"],
                    "test_trades": best["test_trades"],
                    "exact_bidask_test_net_bps": exact0["test_net_bps"],
                    "latency1_test_net_bps": exact1["test_net_bps"],
                    "circular_pvalue": pval,
                }
            ]
        )

    target_rule = TimingRule("micro_shrink_0.75", 0.75, 10, 60.0, 0.0, 240)
    target_signal = build_signal(mid, micro, weights, target_rule)
    target_pos = position_from_signal(target_signal, target_rule.entry_bps, target_rule.exit_bps, target_rule.max_hold_minutes)
    target_half = backtest_position(target_pos, mid, spread_bps, cost_model="halfspread")
    target_row = {
        "strategy": target_rule.name,
        "basket_symbols": " ".join(weights.index),
        "basket_weights": " ".join(f"{k}:{v:.4f}" for k, v in weights.items()),
    }
    target_row.update(summarize(target_half))
    target_df = pd.DataFrame([target_row])

    target_exec_rows = []
    for model, latency in [("halfspread", 0), ("exact_bidask", 0), ("exact_bidask", 1), ("exact_bidask", 2), ("exact_bidask", 5)]:
        frame = backtest_position(target_pos, mid, spread_bps, bid=bid, ask=ask, cost_model=model, latency_min=latency)
        row = {"strategy": target_rule.name, "execution_model": model, "latency_min": latency}
        row.update(summarize(frame))
        target_exec_rows.append(row)
    target_exec = pd.DataFrame(target_exec_rows)

    target_control_rows = []
    target_control_positions = {
        "target": target_pos,
        "target_sign_flip": -target_pos,
        "target_active_always_long": pd.Series(np.where(target_pos != 0, 1.0, 0.0), index=target_pos.index),
        "target_active_always_short": pd.Series(np.where(target_pos != 0, -1.0, 0.0), index=target_pos.index),
    }
    for name, cpos in target_control_positions.items():
        row = {"control": name}
        row.update(summarize(backtest_position(cpos, mid, spread_bps, cost_model="halfspread")))
        target_control_rows.append(row)
    target_controls = pd.DataFrame(target_control_rows)

    grid = grid.sort_values("train_selection_score", ascending=False).reset_index(drop=True)
    grid.to_csv(TABLES / "timing_robustness_grid.csv", index=False)
    stable.to_csv(TABLES / "timing_robustness_stability.csv", index=False)
    decision.to_csv(TABLES / "timing_robustness_decision.csv", index=False)
    controls.to_csv(TABLES / "timing_robustness_controls.csv", index=False)
    execution.to_csv(TABLES / "timing_robustness_execution_audit.csv", index=False)
    monthly.to_csv(TABLES / "timing_robustness_monthly.csv", index=False)
    concentration.to_csv(TABLES / "timing_robustness_trade_concentration.csv", index=False)
    target_df.to_csv(TABLES / "timing_robustness_target_rule.csv", index=False)
    target_exec.to_csv(TABLES / "timing_robustness_target_execution_audit.csv", index=False)
    target_controls.to_csv(TABLES / "timing_robustness_target_controls.csv", index=False)

    report = (
        "# Timing Robustness Audit\n\n"
        "Selection uses Jan-Feb stability only. Test is March + April. The strategy trades only XLK; the basket is a fair-value signal.\n\n"
        "## Decision\n\n"
        + decision.to_markdown(index=False)
        + "\n\n## Execution Audit\n\n"
        + (execution.to_markdown(index=False) if not execution.empty else "_No selected rule._")
        + "\n\n## Controls\n\n"
        + (controls.to_markdown(index=False) if not controls.empty else "_No selected rule._")
        + "\n\n## Target Rule Audit\n\n"
        + target_df.to_markdown(index=False)
        + "\n\n## Target Rule Execution Audit\n\n"
        + target_exec.to_markdown(index=False)
        + "\n\n## Target Rule Controls\n\n"
        + target_controls.to_markdown(index=False)
    )
    (OUTPUT / "timing_robustness_report.md").write_text(report)
    print("[timing-robustness] decision")
    print(decision.to_string(index=False))


if __name__ == "__main__":
    main()
