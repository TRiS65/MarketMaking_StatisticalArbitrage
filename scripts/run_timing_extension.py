#!/usr/bin/env python3
"""Positive timing extension: sparse-basket microprice premium for XLK-only trading.

This extension does not replace the final market-neutral arbitrage analysis.  It
adds a second strategy class: use the sparse constituent basket as a fair-value
signal, but execute only XLK.  This is inspired by the diagnostic finding that
basket hedging added more tracking/cost noise than protection.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from project_config import ETF, TABLES as CONFIG_TABLES, project_window, split_dates

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output"
TABLES = OUTPUT / "tables"
FIGURES = OUTPUT / "figures"


def sparse_weights() -> pd.Series:
    path = CONFIG_TABLES / "selected_xlk_holdings.csv"
    if path.exists():
        df = pd.read_csv(path).head(5)
        w = df.set_index("symbol")["basket_weight"].astype(float)
        return w / w.sum()
    return pd.Series({"MSFT": 0.0797, "NVDA": 0.2257, "ORCL": 0.0745, "AMD": 0.1074})


SPARSE_WEIGHTS = sparse_weights()
START, END = project_window()
TRAIN_END, VALIDATION_END, TEST_END = split_dates()
PERIODS = {
    "train": (START, TRAIN_END),
    "validation": (TRAIN_END, VALIDATION_END),
    "test": (VALIDATION_END, TEST_END),
    "all": (START, END),
}


def setup() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")


def align_panel() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    panel = pd.read_parquet(PROCESSED / "research_panel.parquet")
    panel["minute"] = pd.to_datetime(panel["minute"])
    mid = panel.pivot(index="minute", columns="symbol", values="mid").sort_index()
    micro = panel.pivot(index="minute", columns="symbol", values="microprice").sort_index()
    spread_bps = panel.pivot(index="minute", columns="symbol", values="spread_bps").sort_index()
    dates = sorted(pd.Series(mid.index.date.astype(str)).unique())
    full_index = []
    for day in dates:
        full_index.append(pd.date_range(f"{day} 09:30:00", periods=390, freq="min"))
    full_index = full_index[0].append(full_index[1:])

    def fill(frame: pd.DataFrame) -> pd.DataFrame:
        aligned = frame.reindex(full_index)
        key = pd.Series(aligned.index.date.astype(str), index=aligned.index)
        return aligned.groupby(key, group_keys=False).ffill(limit=5)

    mid, micro, spread_bps = fill(mid), fill(micro), fill(spread_bps)
    common = mid.dropna(subset=[ETF] + list(SPARSE_WEIGHTS.index)).index
    common = common.intersection(micro.dropna(subset=[ETF] + list(SPARSE_WEIGHTS.index)).index)
    common = common.intersection(spread_bps.dropna(subset=[ETF]).index)
    return mid.loc[common].astype(float), micro.loc[common].astype(float), spread_bps.loc[common].astype(float)


def log_returns(px: pd.DataFrame) -> pd.DataFrame:
    ret = np.log(px).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    idx = px.index.to_series()
    continuous = (idx.diff() == pd.Timedelta(minutes=1)) & (idx.dt.date == idx.shift(1).dt.date)
    ret.loc[~continuous.values, :] = 0.0
    return ret.clip(-0.05, 0.05)


def build_signal(mid: pd.DataFrame, micro: pd.DataFrame) -> pd.DataFrame:
    ret_micro = log_returns(micro)
    basket_ret = (ret_micro[list(SPARSE_WEIGHTS.index)] * SPARSE_WEIGHTS).sum(axis=1)
    basket_log_value = np.log(float(micro[ETF].iloc[0])) + basket_ret.cumsum()
    raw_premium = np.log(micro[ETF]) - basket_log_value
    rolling_center = raw_premium.rolling(390 * 5, min_periods=390).mean().shift(1)
    signal = raw_premium - rolling_center
    out = pd.DataFrame(
        {
            "xlk_mid": mid[ETF],
            "xlk_micro": micro[ETF],
            "basket_log_value": basket_log_value,
            "raw_premium_bps": 1e4 * raw_premium,
            "rolling_center_bps": 1e4 * rolling_center,
            "signal_bps": 1e4 * signal,
        },
        index=mid.index,
    )
    out.to_parquet(PROCESSED / "timing_signal_panel.parquet")
    return out


def backtest(signal_panel: pd.DataFrame, mid: pd.DataFrame, spread_bps: pd.DataFrame) -> pd.DataFrame:
    ret_mid = log_returns(mid)[ETF]
    cost = (spread_bps[ETF] / 2.0) / 1e4
    vals = signal_panel["signal_bps"].to_numpy()
    dates = pd.Series(signal_panel.index.date.astype(str), index=signal_panel.index).to_numpy()
    pos = np.zeros(len(signal_panel))
    current = 0.0
    hold = 0
    for i, x in enumerate(vals):
        if i > 0 and dates[i] != dates[i - 1]:
            current = 0.0
            hold = 0
        if np.isfinite(x):
            if current == 0.0:
                if x > 50.0:
                    current = -1.0
                    hold = 0
                elif x < -50.0:
                    current = 1.0
                    hold = 0
            else:
                hold += 1
                if abs(x) <= 25.0 or hold >= 390:
                    current = 0.0
                    hold = 0
        if i < len(vals) - 1 and dates[i + 1] != dates[i]:
            current = 0.0
            hold = 0
        pos[i] = current

    frame = signal_panel.copy()
    frame["position"] = pos
    frame["turnover"] = frame["position"].diff().abs().fillna(frame["position"].abs())
    frame["xlk_ret_mid"] = ret_mid
    frame["gross_ret"] = frame["position"].shift(1).fillna(0.0) * frame["xlk_ret_mid"]
    frame["cost_ret"] = frame["turnover"] * cost.reindex(frame.index)
    frame["net_ret"] = frame["gross_ret"] - frame["cost_ret"]
    frame["cum_net_bps"] = 1e4 * frame["net_ret"].cumsum()
    frame["cum_gross_bps"] = 1e4 * frame["gross_ret"].cumsum()
    frame.to_parquet(PROCESSED / "timing_extension_backtest.parquet")
    return frame


def summarize(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    for period, (start, end) in PERIODS.items():
        sub = frame.loc[(frame.index >= start) & (frame.index < end)]
        prev_pos = sub["position"].shift(1).fillna(0.0)
        rows.append(
            {
                "period": period,
                "gross_bps": 1e4 * sub["gross_ret"].sum(),
                "cost_bps": 1e4 * sub["cost_ret"].sum(),
                "net_bps": 1e4 * sub["net_ret"].sum(),
                "trades": int((sub["turnover"] > 0).sum()),
                "avg_abs_position": sub["position"].abs().mean(),
                "avg_position": sub["position"].mean(),
                "long_minutes": int((sub["position"] > 0).sum()),
                "short_minutes": int((sub["position"] < 0).sum()),
                "long_gross_bps": 1e4 * sub.loc[prev_pos > 0, "gross_ret"].sum(),
                "short_gross_bps": 1e4 * sub.loc[prev_pos < 0, "gross_ret"].sum(),
                "xlk_buyhold_bps": 1e4 * sub["xlk_ret_mid"].sum(),
            }
        )
    summary = pd.DataFrame(rows)

    selected = frame
    controls = []
    for label, pos in {
        "selected": selected["position"],
        "sign_flip": -selected["position"],
        "active_always_long": selected["position"].abs(),
        "active_always_short": -selected["position"].abs(),
    }.items():
        turn = selected["turnover"] if label in {"selected", "sign_flip"} else pos.diff().abs().fillna(pos.abs())
        net = pos.shift(1).fillna(0.0) * selected["xlk_ret_mid"] - turn * selected["cost_ret"].where(selected["turnover"] > 0, 0.0).replace(0.0, np.nan).ffill().fillna(0.0)
        train = net.loc[net.index < VALIDATION_END]
        test = net.loc[(net.index >= VALIDATION_END) & (net.index < TEST_END)]
        controls.append({"control": label, "train_net_bps": 1e4 * train.sum(), "test_net_bps": 1e4 * test.sum(), "avg_pos_test": pos.loc[(pos.index >= VALIDATION_END) & (pos.index < TEST_END)].mean()})

    mar = frame.loc[(frame.index >= VALIDATION_END) & (frame.index < TEST_END)]
    rng = np.random.default_rng(11)
    vals = mar["position"].to_numpy()
    er = mar["xlk_ret_mid"].to_numpy()
    cost = ((mar["cost_ret"] / mar["turnover"]).replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)).to_numpy()
    obs = 1e4 * mar["net_ret"].sum()
    sims = []
    for _ in range(2000):
        shift = int(rng.integers(1, len(vals) - 1))
        shifted = np.roll(vals, shift)
        shifted_pos = pd.Series(shifted, index=mar.index)
        turn = shifted_pos.diff().abs().fillna(abs(shifted_pos.iloc[0])).to_numpy()
        net = shifted_pos.shift(1).fillna(0.0).to_numpy() * er - turn * cost
        sims.append(1e4 * net.sum())
    sims = np.array(sims)
    controls.extend(
        [
            {"control": "circular_shift_mean", "train_net_bps": np.nan, "test_net_bps": sims.mean(), "avg_pos_test": np.nan},
            {"control": "circular_shift_p95", "train_net_bps": np.nan, "test_net_bps": np.percentile(sims, 95), "avg_pos_test": np.nan},
            {"control": "selected_vs_circular_pvalue", "train_net_bps": np.nan, "test_net_bps": (sims >= obs).mean(), "avg_pos_test": np.nan},
        ]
    )
    controls_df = pd.DataFrame(controls)

    cost_rows = []
    for mult in [1.0, 1.5, 2.0, 3.0, 4.0]:
        for _, row in summary.iterrows():
            cost_rows.append(
                {
                    "cost_multiplier": mult,
                    "period": row["period"],
                    "gross_bps": row["gross_bps"],
                    "cost_bps": row["cost_bps"] * mult,
                    "net_bps": row["gross_bps"] - row["cost_bps"] * mult,
                }
            )
    cost_sensitivity = pd.DataFrame(cost_rows)
    return summary, controls_df, cost_sensitivity


def plots(frame: pd.DataFrame) -> None:
    plt.figure(figsize=(10, 4.8))
    plt.plot(frame.index, frame["cum_net_bps"], label="XLK timing net")
    plt.axvline(VALIDATION_END, color="black", linestyle="--", linewidth=1, label="test start")
    plt.axhline(0, color="black", linewidth=0.8)
    plt.title("Sparse-Basket Premium XLK Timing: Cumulative Net P&L")
    plt.ylabel("basis points")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "timing_extension_cumulative_net.png", dpi=180)
    plt.close()

    march = frame.loc[(frame.index >= VALIDATION_END) & (frame.index < TEST_END)]
    plt.figure(figsize=(10, 4.8))
    plt.plot(np.arange(len(march)), march["signal_bps"], linewidth=0.8, label="signal bps")
    plt.axhline(50, color="black", linestyle="--", linewidth=0.8)
    plt.axhline(-50, color="black", linestyle="--", linewidth=0.8)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.title("Timing Extension Signal, Test Session Sequence")
    plt.ylabel("premium signal, bps")
    plt.xlabel("March minute sequence")
    plt.tight_layout()
    plt.savefig(FIGURES / "timing_extension_signal_march.png", dpi=180)
    plt.close()


def main() -> None:
    setup()
    mid, micro, spread_bps = align_panel()
    signal = build_signal(mid, micro)
    frame = backtest(signal, mid, spread_bps)
    summary, controls, cost_sensitivity = summarize(frame)
    summary.to_csv(TABLES / "timing_extension_summary.csv", index=False)
    controls.to_csv(TABLES / "timing_extension_controls.csv", index=False)
    cost_sensitivity.to_csv(TABLES / "timing_extension_cost_sensitivity.csv", index=False)
    plots(frame)
    print("[timing] summary")
    print(summary.to_string(index=False))
    print("[timing] controls")
    print(controls.to_string(index=False))


if __name__ == "__main__":
    main()
