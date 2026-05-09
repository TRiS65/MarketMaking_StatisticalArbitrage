#!/usr/bin/env python3
"""Trend/regime gates for XLK-only sparse-basket timing.

This is a repair experiment for the April failure diagnosed by
``run_regime_shift_diagnostics.py``.  The target timing rule is kept fixed:

    micro_shrink_0.75_cw10d_e60_x0_mh240

The experiment only changes the trade/no-trade policy around that signal.  It
tests whether a simple trend/persistence gate can prevent the strategy from
shorting XLK during a broad XLK + basket uptrend.  Selection is based only on
the metadata train/validation windows; the metadata test window remains an
out-of-sample audit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from project_config import ETF, FIGURES, OUTPUT, TABLES, split_dates
from run_timing_robustness import (
    TimingRule,
    align_panel,
    backtest_position,
    build_signal,
    load_weights,
    log_returns,
    summarize,
)


@dataclass(frozen=True)
class GateRule:
    mode: str
    lookback_min: int
    trend_threshold_bps: float
    action: str
    state_kind: str = "intraday_trend"

    @property
    def name(self) -> str:
        return (
            f"{self.mode}_{self.state_kind}_lb{self.lookback_min}_"
            f"thr{self.trend_threshold_bps:g}_{self.action}"
        )


def rolling_return_bps(px: pd.Series, lookback: int, same_day_only: bool) -> pd.Series:
    out = 1e4 * (np.log(px) - np.log(px.shift(lookback)))
    if same_day_only:
        same_day = px.index.to_series().dt.date == px.index.to_series().shift(lookback).dt.date
        out.loc[~same_day.values] = np.nan
    return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def regime_state(
    mid: pd.DataFrame,
    weights: pd.Series,
    signal_bps: pd.Series,
    lookback: int,
    threshold_bps: float,
    state_kind: str,
) -> pd.DataFrame:
    same_day_only = state_kind == "intraday_trend"
    xlk_ret = rolling_return_bps(mid[ETF], lookback, same_day_only=same_day_only)
    basket_ret_1m = (log_returns(mid[weights.index]) * weights).sum(axis=1)
    basket_log = basket_ret_1m.cumsum()
    basket_ret = 1e4 * (basket_log - basket_log.shift(lookback))
    if same_day_only:
        same_day = mid.index.to_series().dt.date == mid.index.to_series().shift(lookback).dt.date
        basket_ret.loc[~same_day.values] = np.nan
    basket_ret = basket_ret.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    signal_mean = signal_bps.rolling(lookback, min_periods=max(30, lookback // 4)).mean().shift(1).fillna(0.0)
    price_up = (xlk_ret > threshold_bps) & (basket_ret > threshold_bps)
    price_down = (xlk_ret < -threshold_bps) & (basket_ret < -threshold_bps)
    signal_up = signal_mean > threshold_bps
    signal_down = signal_mean < -threshold_bps
    if state_kind in {"intraday_trend", "multi_day_trend"}:
        uptrend = price_up
        downtrend = price_down
    elif state_kind == "premium_persistence":
        uptrend = signal_up
        downtrend = signal_down
    elif state_kind == "multi_day_trend_premium":
        uptrend = price_up & signal_up
        downtrend = price_down & signal_down
    else:
        raise ValueError(f"unknown state_kind={state_kind}")
    return pd.DataFrame(
        {
            "xlk_trend_bps": xlk_ret,
            "basket_trend_bps": basket_ret,
            "signal_mean_bps": signal_mean,
            "uptrend": uptrend,
            "downtrend": downtrend,
        },
        index=mid.index,
    )


def gated_position(signal_bps: pd.Series, gate: pd.DataFrame, rule: TimingRule, gate_rule: GateRule) -> pd.Series:
    vals = signal_bps.to_numpy(dtype=float)
    dates = pd.Series(signal_bps.index.date.astype(str), index=signal_bps.index).to_numpy()
    up = gate["uptrend"].to_numpy(dtype=bool)
    down = gate["downtrend"].to_numpy(dtype=bool)
    pos = np.zeros(len(signal_bps), dtype=float)
    current = 0.0
    hold = 0

    def transform(desired: float, i: int) -> float:
        if desired < 0 and up[i] and gate_rule.mode in {"short_uptrend", "two_sided", "flip_short_uptrend"}:
            if gate_rule.action == "flip" or gate_rule.mode == "flip_short_uptrend":
                return 1.0
            return 0.0
        if desired > 0 and down[i] and gate_rule.mode == "two_sided":
            return 0.0
        return desired

    for i, x in enumerate(vals):
        if i > 0 and dates[i] != dates[i - 1]:
            current = 0.0
            hold = 0
        if np.isfinite(x):
            if current == 0.0:
                desired = 0.0
                if x > rule.entry_bps:
                    desired = -1.0
                elif x < -rule.entry_bps:
                    desired = 1.0
                current = transform(desired, i)
                hold = 0 if current != 0.0 else hold
            else:
                hold += 1
                blocked = transform(current, i) == 0.0
                if blocked or abs(x) <= rule.exit_bps or hold >= rule.max_hold_minutes:
                    current = 0.0
                    hold = 0
        if i < len(vals) - 1 and dates[i + 1] != dates[i]:
            current = 0.0
            hold = 0
        pos[i] = current
    return pd.Series(pos, index=signal_bps.index)


def side_stats(frame: pd.DataFrame) -> dict:
    lag_pos = frame["position"].shift(1).fillna(0.0)
    long = frame.loc[lag_pos > 0]
    short = frame.loc[lag_pos < 0]
    return {
        "long_gross_bps": float(1e4 * long["gross_ret"].sum()),
        "short_gross_bps": float(1e4 * short["gross_ret"].sum()),
        "long_minutes": int((frame["position"] > 0).sum()),
        "short_minutes": int((frame["position"] < 0).sum()),
    }


def monthly_stats(frame: pd.DataFrame, strategy: str) -> pd.DataFrame:
    rows = []
    for month, sub in frame.groupby(frame.index.to_period("M")):
        row = {
            "strategy": strategy,
            "month": str(month),
            "gross_bps": float(1e4 * sub["gross_ret"].sum()),
            "cost_bps": float(1e4 * sub["cost_ret"].sum()),
            "net_bps": float(1e4 * sub["net_ret"].sum()),
            "trades": int((sub["turnover"] > 0).sum()),
        }
        row.update(side_stats(sub))
        rows.append(row)
    return pd.DataFrame(rows)


def evaluate_strategy(
    strategy_name: str,
    pos: pd.Series,
    mid: pd.DataFrame,
    spread_bps: pd.DataFrame,
    bid: pd.DataFrame,
    ask: pd.DataFrame,
    gate_rule: GateRule | None = None,
) -> tuple[pd.DataFrame, dict]:
    frame = backtest_position(pos, mid, spread_bps, bid=bid, ask=ask, cost_model="exact_bidask")
    row = {"strategy": strategy_name}
    if gate_rule is not None:
        row.update(
            {
                "gate_mode": gate_rule.mode,
                "state_kind": gate_rule.state_kind,
                "lookback_min": gate_rule.lookback_min,
                "trend_threshold_bps": gate_rule.trend_threshold_bps,
                "gate_action": gate_rule.action,
            }
        )
    else:
        row.update(
            {
                "gate_mode": "none",
                "state_kind": "none",
                "lookback_min": 0,
                "trend_threshold_bps": 0.0,
                "gate_action": "none",
            }
        )
    row.update(summarize(frame))
    _, validation_end, test_end = split_dates()
    test_slice = frame.loc[(frame.index >= validation_end) & (frame.index < test_end)]
    row.update(side_stats(test_slice))
    row["test_2x_cost_net_bps"] = float(
        1e4
        * (
            test_slice["gross_ret"].sum()
            - 2.0 * test_slice["cost_ret"].sum()
        )
    )
    row["train_selection_score"] = (
        row["train_net_bps"]
        + row["validation_net_bps"]
        - 0.10 * (row["train_cost_bps"] + row["validation_cost_bps"])
    )
    return frame, row


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    weights = load_weights(5)
    mid, micro, spread_bps, bid, ask = align_panel(weights)
    target = TimingRule("micro_shrink_0.75", 0.75, 10, 60.0, 0.0, 240)
    signal = build_signal(mid, micro, weights, target)

    baseline_gate = GateRule("none", 0, 0.0, "none")
    baseline_pos = gated_position(signal, regime_state(mid, weights, signal, 60, 0.0, "intraday_trend"), target, baseline_gate)
    frames: dict[str, pd.DataFrame] = {}
    rows = []
    base_frame, base_row = evaluate_strategy("baseline_no_gate", baseline_pos, mid, spread_bps, bid, ask, None)
    frames["baseline_no_gate"] = base_frame
    rows.append(base_row)
    long_only_frame, long_only_row = evaluate_strategy(
        "long_only_diagnostic", baseline_pos.clip(lower=0.0), mid, spread_bps, bid, ask, None
    )
    long_only_row["gate_mode"] = "long_only"
    short_only_frame, short_only_row = evaluate_strategy(
        "short_only_diagnostic", baseline_pos.clip(upper=0.0), mid, spread_bps, bid, ask, None
    )
    short_only_row["gate_mode"] = "short_only"
    frames["long_only_diagnostic"] = long_only_frame
    frames["short_only_diagnostic"] = short_only_frame
    rows.extend([long_only_row, short_only_row])

    gate_rules = []
    for mode in ["short_uptrend", "two_sided"]:
        for lookback in [30, 60, 120, 240]:
            for threshold in [0.0, 25.0, 50.0, 100.0, 150.0]:
                gate_rules.append(GateRule(mode, lookback, threshold, "flat", "intraday_trend"))
    for mode in ["short_uptrend", "two_sided"]:
        for lookback in [390, 780, 1950, 3900]:
            for threshold in [0.0, 50.0, 100.0, 200.0, 300.0]:
                gate_rules.append(GateRule(mode, lookback, threshold, "flat", "multi_day_trend"))
    for mode in ["short_uptrend", "two_sided"]:
        for lookback in [120, 390, 780, 1950]:
            for threshold in [0.0, 25.0, 50.0, 75.0, 100.0]:
                gate_rules.append(GateRule(mode, lookback, threshold, "flat", "premium_persistence"))
    for mode in ["short_uptrend", "two_sided"]:
        for lookback in [390, 780, 1950]:
            for threshold in [25.0, 50.0, 100.0, 200.0]:
                gate_rules.append(GateRule(mode, lookback, threshold, "flat", "multi_day_trend_premium"))
    for lookback in [60, 120, 240]:
        for threshold in [25.0, 50.0, 100.0]:
            gate_rules.append(GateRule("flip_short_uptrend", lookback, threshold, "flip", "intraday_trend"))
    for lookback in [390, 780, 1950]:
        for threshold in [50.0, 100.0, 200.0]:
            gate_rules.append(GateRule("flip_short_uptrend", lookback, threshold, "flip", "multi_day_trend_premium"))

    for gate_rule in gate_rules:
        gate = regime_state(mid, weights, signal, gate_rule.lookback_min, gate_rule.trend_threshold_bps, gate_rule.state_kind)
        pos = gated_position(signal, gate, target, gate_rule)
        frame, row = evaluate_strategy(gate_rule.name, pos, mid, spread_bps, bid, ask, gate_rule)
        row["blocked_short_frac"] = float(((baseline_pos < 0) & (pos >= 0)).mean())
        row["blocked_long_frac"] = float(((baseline_pos > 0) & (pos <= 0)).mean())
        frames[gate_rule.name] = frame
        rows.append(row)

    grid = pd.DataFrame(rows).sort_values("train_selection_score", ascending=False)
    grid.to_csv(TABLES / "regime_gate_grid.csv", index=False)

    eligible = grid[
        (grid["strategy"] != "baseline_no_gate")
        & (grid["train_net_bps"] > 0)
        & (grid["validation_net_bps"] > 0)
        & (grid["train_trades"] >= 20)
        & (grid["validation_trades"] >= 5)
    ].copy()
    if eligible.empty:
        decision = pd.DataFrame(
            [
                {
                    "decision": "no_trade",
                    "reason": "No regime gate passed train/validation selection filters.",
                    "selected_strategy": "",
                    "train_net_bps": 0.0,
                    "validation_net_bps": 0.0,
                    "test_net_bps": 0.0,
                    "test_2x_cost_net_bps": 0.0,
                }
            ]
        )
        selected_name = "baseline_no_gate"
    else:
        selected = eligible.sort_values("train_selection_score", ascending=False).iloc[0]
        selected_name = str(selected["strategy"])
        decision_label = "active_candidate" if selected["test_net_bps"] > 0 and selected["test_2x_cost_net_bps"] > 0 else "diagnostic_only"
        decision = pd.DataFrame(
            [
                {
                    "decision": decision_label,
                    "reason": "Selected on train/validation only; test is holdout audit.",
                    "selected_strategy": selected_name,
                    "gate_mode": selected["gate_mode"],
                    "state_kind": selected["state_kind"],
                    "lookback_min": selected["lookback_min"],
                    "trend_threshold_bps": selected["trend_threshold_bps"],
                    "gate_action": selected["gate_action"],
                    "train_net_bps": selected["train_net_bps"],
                    "validation_net_bps": selected["validation_net_bps"],
                    "jan_net_bps": selected["jan_net_bps"],
                    "feb_net_bps": selected["feb_net_bps"],
                    "mar_net_bps": selected["mar_net_bps"],
                    "apr_net_bps": selected["apr_net_bps"],
                    "test_net_bps": selected["test_net_bps"],
                    "test_2x_cost_net_bps": selected["test_2x_cost_net_bps"],
                    "test_trades": selected["test_trades"],
                    "short_gross_bps": selected["short_gross_bps"],
                    "short_minutes": selected["short_minutes"],
                }
            ]
        )
    decision.to_csv(TABLES / "regime_gate_selection.csv", index=False)

    names_for_monthly = ["baseline_no_gate", "long_only_diagnostic", "short_only_diagnostic", selected_name]
    best_test = grid[grid["strategy"] != "baseline_no_gate"].sort_values("test_net_bps", ascending=False).iloc[0]
    if str(best_test["strategy"]) not in names_for_monthly:
        names_for_monthly.append(str(best_test["strategy"]))
    names_for_monthly = list(dict.fromkeys(names_for_monthly))
    monthly = pd.concat([monthly_stats(frames[name], name) for name in names_for_monthly], ignore_index=True)
    monthly.to_csv(TABLES / "regime_gate_monthly.csv", index=False)

    controls = []
    for name in names_for_monthly:
        frame = frames[name]
        controls.append({"strategy": name, "control": "selected_path", **summarize(frame)})
        flipped = frame.copy()
        flipped["gross_ret"] = -flipped["gross_ret"]
        flipped["net_ret"] = flipped["gross_ret"] - flipped["cost_ret"]
        controls.append({"strategy": name, "control": "sign_flip_gross", **summarize(flipped)})
    pd.DataFrame(controls).to_csv(TABLES / "regime_gate_controls.csv", index=False)

    top = grid[["strategy", "train_net_bps", "mar_net_bps", "apr_net_bps", "test_net_bps"]].head(12)
    fig, ax = plt.subplots(figsize=(10, 6))
    plot = top.set_index("strategy")[["train_net_bps", "test_net_bps"]]
    plot.plot(kind="barh", ax=ax)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title("Regime gate candidates ranked by train/validation only")
    ax.set_xlabel("net bps")
    fig.tight_layout()
    fig.savefig(FIGURES / "regime_gate_comparison.png", dpi=180)
    plt.close(fig)

    report = (
        "# Regime Gate Experiments\n\n"
        "The target timing signal is fixed.  These experiments only test trade/no-trade gates around the April failure mode: shorting XLK while both XLK and the sparse basket are in an intraday uptrend.\n\n"
        "## Selection\n\n"
        + decision.to_markdown(index=False)
        + "\n\n## Top Train/Validation Ranked Gates\n\n"
        + grid.head(15).to_markdown(index=False)
        + "\n\n## Monthly Anatomy\n\n"
        + monthly.to_markdown(index=False)
        + "\n\n## Interpretation\n\n"
        "A useful gate should improve April by reducing short exposure without being selected using April. "
        "If the selected gate remains negative out of sample, the correct conclusion is still no-trade; the experiment still shows whether the loss stream is repairable by a simple trend filter or requires a deeper regime classifier.\n"
    )
    (OUTPUT / "regime_gate_report.md").write_text(report)
    print(f"[ok] wrote {TABLES / 'regime_gate_selection.csv'}")
    print(f"[ok] wrote {OUTPUT / 'regime_gate_report.md'}")


if __name__ == "__main__":
    main()
