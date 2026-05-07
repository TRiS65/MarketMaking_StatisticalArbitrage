#!/usr/bin/env python3
"""Expanded-sample controls for fixed-bps XLK-only sparse-basket timing.

This is the honest regeneration of the old profit-search candidate shape on the
new top-20 panel.  It does not trade the basket.  The basket is only a
microprice fair-value signal; execution and PnL are on XLK midpoint returns with
explicit XLK spread costs.

Outputs:
    output/tables/fixed_bps_timing_selection.csv
    output/tables/fixed_bps_timing_controls.csv
    output/tables/fixed_bps_timing_cost_sensitivity.csv
    output/tables/fixed_bps_timing_monthly.csv
    output/tables/fixed_bps_timing_trade_concentration.csv
    output/fixed_bps_timing_report.md
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from project_config import ETF, MINUTES_PER_DAY, PROCESSED, TABLES, OUTPUT, metadata


def load_panel(top_n: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    panel = pd.read_parquet(PROCESSED / "research_panel.parquet")
    panel["minute"] = pd.to_datetime(panel["minute"])
    holdings = pd.read_csv(TABLES / "selected_xlk_holdings.csv")
    holdings = holdings[holdings["used_in_clean_panel"].astype(bool)].head(top_n).copy()
    weights = holdings.set_index("symbol")["basket_weight"].astype(float)
    weights = weights / weights.sum()
    symbols = [ETF] + weights.index.tolist()

    mid = panel.pivot(index="minute", columns="symbol", values="mid").sort_index()
    micro = panel.pivot(index="minute", columns="symbol", values="microprice").sort_index()
    spread_bps = panel.pivot(index="minute", columns="symbol", values="spread_bps").sort_index()

    dates = sorted(pd.Series(mid.index.date.astype(str)).unique())
    full = [pd.date_range(f"{d} 09:30:00", periods=MINUTES_PER_DAY, freq="min") for d in dates]
    full_index = full[0].append(full[1:])

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
    return mid.loc[common].astype(float), micro.loc[common].astype(float), spread_bps.loc[common].astype(float), weights


def log_returns(px: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    ret = np.log(px.astype(float)).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    idx = px.index.to_series()
    continuous = (idx.diff() == pd.Timedelta(minutes=1)) & (idx.dt.date == idx.shift(1).dt.date)
    ret.loc[~continuous.values] = 0.0
    return ret.clip(-0.05, 0.05)


def build_signal(mid: pd.DataFrame, micro: pd.DataFrame, weights: pd.Series, center_days: int, signal_price: str) -> pd.Series:
    px = micro if signal_price == "micro" else mid
    ret = log_returns(px)
    basket_ret = (ret[weights.index] * weights).sum(axis=1)
    basket_log_value = np.log(float(px[ETF].iloc[0])) + basket_ret.cumsum()
    premium = np.log(px[ETF]) - basket_log_value
    center = premium.rolling(center_days * MINUTES_PER_DAY, min_periods=MINUTES_PER_DAY).mean().shift(1)
    return (1e4 * (premium - center)).replace([np.inf, -np.inf], np.nan)


def position_from_signal(signal_bps: pd.Series, entry_bps: float, exit_bps: float, max_hold: int) -> pd.Series:
    vals = signal_bps.to_numpy(float)
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
                if abs(x) <= exit_bps or hold >= max_hold:
                    current = 0.0
                    hold = 0
        if i < len(vals) - 1 and dates[i + 1] != dates[i]:
            current = 0.0
            hold = 0
        pos[i] = current
    return pd.Series(pos, index=signal_bps.index)


def backtest_position(
    pos: pd.Series,
    mid: pd.DataFrame,
    spread_bps: pd.DataFrame,
    cost_mult: float = 1.0,
    latency_min: int = 0,
) -> pd.DataFrame:
    exec_pos = pos.shift(latency_min).fillna(0.0)
    ret = log_returns(mid[ETF])
    gross = exec_pos.shift(1).fillna(0.0) * ret
    turnover = exec_pos.diff().abs().fillna(exec_pos.abs())
    cost = turnover * (spread_bps[ETF] / 2.0) / 1e4 * cost_mult
    net = gross - cost
    return pd.DataFrame({"position": exec_pos, "turnover": turnover, "gross_ret": gross, "cost_ret": cost, "net_ret": net})


def period_stats(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, prefix: str) -> dict:
    sub = frame.loc[(frame.index >= start) & (frame.index < end)]
    return {
        f"{prefix}_gross_bps": float(1e4 * sub["gross_ret"].sum()),
        f"{prefix}_cost_bps": float(1e4 * sub["cost_ret"].sum()),
        f"{prefix}_net_bps": float(1e4 * sub["net_ret"].sum()),
        f"{prefix}_trades": int((sub["turnover"] > 0).sum()),
        f"{prefix}_avg_abs_position": float(sub["position"].abs().mean()),
    }


def summarize(frame: pd.DataFrame, label: str) -> dict:
    meta = metadata()
    train_end = pd.Timestamp(meta["train_end"])
    val_end = pd.Timestamp(meta["validation_end"])
    test_end = pd.Timestamp(meta["test_end"])
    out = {"control": label}
    out.update(period_stats(frame, frame.index.min(), train_end, "train"))
    out.update(period_stats(frame, train_end, val_end, "validation"))
    out.update(period_stats(frame, val_end, test_end, "test"))
    return out


def monthly_stats(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month, sub in frame.groupby(frame.index.to_period("M")):
        rows.append({
            "month": str(month),
            "gross_bps": float(1e4 * sub["gross_ret"].sum()),
            "cost_bps": float(1e4 * sub["cost_ret"].sum()),
            "net_bps": float(1e4 * sub["net_ret"].sum()),
            "trades": int((sub["turnover"] > 0).sum()),
            "avg_abs_position": float(sub["position"].abs().mean()),
        })
    return pd.DataFrame(rows)


def trade_concentration(frame: pd.DataFrame) -> pd.DataFrame:
    trade_id = (frame["position"].ne(frame["position"].shift()) & frame["position"].ne(0)).cumsum()
    active = frame[frame["position"].ne(0)].copy()
    if active.empty:
        return pd.DataFrame([{"trades": 0}])
    active["trade_id"] = trade_id.loc[active.index]
    trades = active.groupby("trade_id", as_index=False).agg(net_bps=("net_ret", lambda s: 1e4 * s.sum()))
    total = float(trades["net_bps"].sum())
    top1 = float(trades["net_bps"].nlargest(1).sum())
    top5 = float(trades["net_bps"].nlargest(5).sum())
    return pd.DataFrame([{
        "trades": int(len(trades)),
        "total_trade_net_bps": total,
        "top1_trade_net_bps": top1,
        "top5_trade_net_bps": top5,
        "top1_share_of_positive_total": top1 / total if total > 0 else np.nan,
        "top5_share_of_positive_total": top5 / total if total > 0 else np.nan,
    }])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--signal-price", choices=["micro", "mid"], default="micro")
    p.add_argument("--center-days", type=int, default=10)
    p.add_argument("--entry-bps", type=float, default=50.0)
    p.add_argument("--exit-bps", type=float, default=25.0)
    p.add_argument("--max-hold", type=int, default=390)
    p.add_argument("--n-shifts", type=int, default=200)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    TABLES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    mid, micro, spread_bps, weights = load_panel(args.top_n)
    signal = build_signal(mid, micro, weights, args.center_days, args.signal_price)
    pos = position_from_signal(signal, args.entry_bps, args.exit_bps, args.max_hold)
    selected = backtest_position(pos, mid, spread_bps)

    controls = [summarize(selected, "selected")]
    controls.append(summarize(backtest_position(position_from_signal(-signal, args.entry_bps, args.exit_bps, args.max_hold), mid, spread_bps), "sign_flip"))
    controls.append(summarize(backtest_position(pd.Series(np.where(pos != 0, 1.0, 0.0), index=pos.index), mid, spread_bps), "active_always_long"))
    controls.append(summarize(backtest_position(pd.Series(np.where(pos != 0, -1.0, 0.0), index=pos.index), mid, spread_bps), "active_always_short"))

    rng = np.random.default_rng(20260507)
    test_start = pd.Timestamp(metadata()["validation_end"])
    selected_test = controls[0]["test_net_bps"]
    shifted = []
    valid_signal = signal.copy()
    for _ in range(args.n_shifts):
        k = int(rng.integers(MINUTES_PER_DAY, max(MINUTES_PER_DAY + 1, len(valid_signal) - MINUTES_PER_DAY)))
        shifted_signal = pd.Series(np.roll(valid_signal.to_numpy(), k), index=valid_signal.index)
        shifted_pos = position_from_signal(shifted_signal, args.entry_bps, args.exit_bps, args.max_hold)
        shifted_frame = backtest_position(shifted_pos, mid, spread_bps)
        shifted.append(float(1e4 * shifted_frame.loc[shifted_frame.index >= test_start, "net_ret"].sum()))
    controls.append({"control": "circular_shift_mean", "test_net_bps": float(np.mean(shifted)), "train_net_bps": np.nan, "validation_net_bps": np.nan})
    controls.append({"control": "circular_shift_p95", "test_net_bps": float(np.percentile(shifted, 95)), "train_net_bps": np.nan, "validation_net_bps": np.nan})
    controls.append({"control": "selected_vs_circular_pvalue", "test_net_bps": float(np.mean(np.array(shifted) >= selected_test)), "train_net_bps": np.nan, "validation_net_bps": np.nan})
    controls_df = pd.DataFrame(controls)

    cost_rows = []
    for cm in [1.0, 1.5, 2.0, 3.0, 4.0]:
        for latency in [0, 1]:
            frame = backtest_position(pos, mid, spread_bps, cost_mult=cm, latency_min=latency)
            row = summarize(frame, f"cost{cm:g}_latency{latency}")
            row.update(cost_multiplier=cm, latency_min=latency)
            cost_rows.append(row)
    cost_df = pd.DataFrame(cost_rows)
    monthly = monthly_stats(selected)
    concentration = trade_concentration(selected)

    sel = controls_df[controls_df["control"] == "selected"].iloc[0].to_dict()
    sign = controls_df[controls_df["control"] == "sign_flip"].iloc[0].to_dict()
    always_long = controls_df[controls_df["control"] == "active_always_long"].iloc[0].to_dict()
    always_short = controls_df[controls_df["control"] == "active_always_short"].iloc[0].to_dict()
    pval = float(controls_df[controls_df["control"] == "selected_vs_circular_pvalue"]["test_net_bps"].iloc[0])
    cost2 = cost_df[(cost_df["cost_multiplier"] == 2.0) & (cost_df["latency_min"] == 0)].iloc[0]
    lat1 = cost_df[(cost_df["cost_multiplier"] == 1.0) & (cost_df["latency_min"] == 1)].iloc[0]
    reasons = []
    if sel["train_net_bps"] <= 0 or sel["validation_net_bps"] <= 0:
        reasons.append("train_or_validation_net<=0")
    if sel["test_net_bps"] <= 0:
        reasons.append("test_net<=0")
    if cost2["test_net_bps"] <= 0:
        reasons.append("2x_cost_test<=0")
    if lat1["test_net_bps"] <= 0:
        reasons.append("latency1_test<=0")
    if sel["test_net_bps"] <= max(always_long["test_net_bps"], always_short["test_net_bps"]):
        reasons.append("does_not_beat_directional_control")
    if sign["test_net_bps"] >= sel["test_net_bps"]:
        reasons.append("sign_flip_not_worse")
    if pval > 0.10:
        reasons.append("circular_pvalue>0.10")
    decision = "candidate_active" if not reasons else "no_trade"
    selection = pd.DataFrame([{
        "decision": decision,
        "reason": ";".join(reasons) if reasons else "passes fixed-bps timing controls",
        "basket_symbols": " ".join(weights.index),
        "basket_weights": " ".join(f"{k}:{v:.4f}" for k, v in weights.items()),
        "signal_price": args.signal_price,
        "center_days": args.center_days,
        "entry_bps": args.entry_bps,
        "exit_bps": args.exit_bps,
        "max_hold": args.max_hold,
        "train_net_bps": sel["train_net_bps"],
        "validation_net_bps": sel["validation_net_bps"],
        "test_net_bps": sel["test_net_bps"],
        "test_trades": sel["test_trades"],
        "circular_pvalue": pval,
        "test_2x_cost_net_bps": cost2["test_net_bps"],
        "test_latency1_net_bps": lat1["test_net_bps"],
    }])

    selection.to_csv(TABLES / "fixed_bps_timing_selection.csv", index=False)
    controls_df.to_csv(TABLES / "fixed_bps_timing_controls.csv", index=False)
    cost_df.to_csv(TABLES / "fixed_bps_timing_cost_sensitivity.csv", index=False)
    monthly.to_csv(TABLES / "fixed_bps_timing_monthly.csv", index=False)
    concentration.to_csv(TABLES / "fixed_bps_timing_trade_concentration.csv", index=False)
    report = (
        "# Fixed-BPS XLK-Only Timing Controls\n\n"
        "This regenerates the old fixed-bps sparse-basket timing candidate shape on the expanded top-20 panel. "
        "It is a directional XLK-only timing test, not market-neutral arbitrage.\n\n"
        "## Selection\n\n"
        + selection.to_markdown(index=False)
        + "\n\n## Controls\n\n"
        + controls_df.to_markdown(index=False)
        + "\n\n## Monthly PnL\n\n"
        + monthly.to_markdown(index=False)
        + "\n\n## Trade Concentration\n\n"
        + concentration.to_markdown(index=False)
    )
    (OUTPUT / "fixed_bps_timing_report.md").write_text(report)
    print(f"[ok] wrote {TABLES / 'fixed_bps_timing_selection.csv'}")
    print(f"[ok] wrote {OUTPUT / 'fixed_bps_timing_report.md'}")


if __name__ == "__main__":
    main()
