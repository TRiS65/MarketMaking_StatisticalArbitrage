#!/usr/bin/env python3
"""Method-upgrade experiments for the original Jan-Mar 2026 XLK universe.

This script intentionally works from the old minute quote/trade parquet files
instead of research_panel.parquet, so it can run even if the derived panel needs
to be rebuilt.  It implements the reusable pieces we want before the larger
WRDS universe arrives:

* Jan train / Feb validation / Mar test split.
* Pair trading for XLK versus each original constituent.
* Entry/exit z-score heatmaps with max-holding exits.
* Trade-level logs and validation-selected test evaluation.
* Bid/ask-aware execution approximation from NBBO quotes.
* Data, strategy, and selection-audit tables.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

ETF = "XLK"
CONSTITUENTS = ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "CSCO"]
SYMBOLS = [ETF] + CONSTITUENTS
MINUTES_PER_DAY = 390
ANN_FACTOR = 252 * MINUTES_PER_DAY

TRAIN_START = pd.Timestamp("2026-01-01")
VAL_START = pd.Timestamp("2026-02-01")
TEST_START = pd.Timestamp("2026-03-01")
END = pd.Timestamp("2026-04-01")


@dataclass(frozen=True)
class PairSpec:
    stock: str
    beta: float
    train_adf_p: float
    train_half_life_minutes: float

    @property
    def pair(self) -> str:
        return f"{ETF}-{self.stock}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run old-data pair/z-score method upgrades")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--center-window", type=int, default=MINUTES_PER_DAY * 5)
    parser.add_argument("--quick", action="store_true", help="Smaller grid for smoke tests")
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def setup(root: Path) -> tuple[Path, Path, Path]:
    processed = root / "data" / "processed"
    tables = root / "output" / "tables"
    figures = root / "output" / "figures"
    for path in [processed, tables, figures]:
        path.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")
    return processed, tables, figures


def load_old_panel(processed: Path) -> pd.DataFrame:
    quote_parts = []
    trade_parts = []
    for month in ["01", "02", "03"]:
        quote_path = processed / f"minute_quotes_2026_{month}.parquet"
        trade_path = processed / f"minute_trades_2026_{month}.parquet"
        if not quote_path.exists() or not trade_path.exists():
            raise FileNotFoundError(f"Missing old minute quote/trade parquet for month {month}")
        quote_parts.append(pd.read_parquet(quote_path))
        trade_parts.append(pd.read_parquet(trade_path))

    quotes = pd.concat(quote_parts, ignore_index=True)
    trades = pd.concat(trade_parts, ignore_index=True)
    quotes["minute"] = pd.to_datetime(quotes["minute"])
    trades["minute"] = pd.to_datetime(trades["minute"])

    panel = quotes.merge(trades, on=["symbol", "minute"], how="left")
    panel = panel[panel["symbol"].isin(SYMBOLS)].copy()
    panel["mid"] = (panel["bid"] + panel["ask"]) / 2.0
    panel["spread"] = panel["ask"] - panel["bid"]
    panel["spread_bps"] = 1e4 * panel["spread"] / panel["mid"]
    panel = panel.sort_values(["symbol", "minute"])
    return panel


def pivot(panel: pd.DataFrame, col: str) -> pd.DataFrame:
    return panel.pivot(index="minute", columns="symbol", values=col).sort_index()


def align_intraday(frame: pd.DataFrame) -> pd.DataFrame:
    dates = sorted(pd.Series(frame.index.date.astype(str)).unique())
    parts = [pd.date_range(f"{day} 09:30:00", periods=MINUTES_PER_DAY, freq="min") for day in dates]
    full_index = parts[0].append(parts[1:]) if len(parts) > 1 else parts[0]
    aligned = frame.reindex(full_index)
    day_key = pd.Series(aligned.index.date.astype(str), index=aligned.index)
    return aligned.groupby(day_key, group_keys=False).ffill(limit=5)


def make_views(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    views = {col: align_intraday(pivot(panel, col)) for col in ["bid", "ask", "mid", "spread_bps", "volume", "trade_count", "quote_updates"]}
    common = views["mid"].dropna(subset=SYMBOLS).index
    for col in list(views):
        views[col] = views[col].loc[common, SYMBOLS].astype(float)
    return views


def continuous_mask(index: pd.Index) -> pd.Series:
    idx = pd.Series(index, index=index)
    return (idx.diff() == pd.Timedelta(minutes=1)) & (idx.dt.date == idx.shift(1).dt.date)


def log_returns(price: pd.DataFrame) -> pd.DataFrame:
    ret = np.log(price).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    ret.loc[~continuous_mask(price.index).values, :] = 0.0
    return ret.clip(-0.05, 0.05)


def sample_name(ts: pd.Timestamp) -> str:
    if ts < VAL_START:
        return "train"
    if ts < TEST_START:
        return "validation"
    return "test"


def masks(index: pd.Index) -> dict[str, pd.Series]:
    idx = pd.Series(index, index=index)
    return {
        "train": (idx >= TRAIN_START) & (idx < VAL_START),
        "validation": (idx >= VAL_START) & (idx < TEST_START),
        "test": (idx >= TEST_START) & (idx < END),
    }


def estimate_pair_beta(ret: pd.DataFrame, stock: str) -> float:
    train = masks(ret.index)["train"]
    # Minute NBBO mid returns can contain quote-bounce outliers.  Estimate hedge
    # ratios on winsorized returns so a few wide-spread minutes do not collapse
    # the pair beta toward zero.
    x = ret.loc[train, stock].clip(-0.005, 0.005).to_numpy(dtype=float)
    y = ret.loc[train, ETF].clip(-0.005, 0.005).to_numpy(dtype=float)
    valid = np.isfinite(x) & np.isfinite(y) & (np.abs(x) > 0)
    x, y = x[valid], y[valid]
    if len(x) < 500 or np.var(x) <= 0:
        return np.nan
    return float(np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1))


def residual_ret(ret: pd.DataFrame, stock: str, beta: float) -> pd.Series:
    return ret[ETF] - beta * ret[stock]


def one_way_cost_ret(spread_bps: pd.DataFrame, stock: str, beta: float) -> pd.Series:
    # One unit residual = one XLK leg plus beta stock leg.  Half spread is the
    # cost of opening or closing one side at bid/ask instead of midpoint.
    cost_bps = spread_bps[ETF] / 2.0 + abs(beta) * spread_bps[stock] / 2.0
    return (cost_bps / 1e4).replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)


def half_life_minutes(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 250:
        return np.nan
    lag = s.shift(1).dropna()
    delta = s.diff().dropna()
    lag = lag.loc[delta.index]
    try:
        model = sm.OLS(delta.values, sm.add_constant(lag.values)).fit()
        phi = 1.0 + model.params[1]
    except Exception:
        return np.nan
    if phi <= 0 or phi >= 1:
        return np.nan
    return float(-np.log(2) / np.log(phi))


def adf_pvalue(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 500:
        return np.nan
    try:
        return float(adfuller(s, maxlag=20, autolag="AIC")[1])
    except Exception:
        return np.nan


def rolling_zscore(spread: pd.Series, center_window: int) -> pd.Series:
    min_periods = max(60, min(center_window // 2, MINUTES_PER_DAY))
    center = spread.rolling(center_window, min_periods=min_periods).mean().shift(1)
    std = spread.rolling(center_window, min_periods=min_periods).std().shift(1)
    return (spread - center) / std.replace(0.0, np.nan)


def run_z_strategy(
    z: pd.Series,
    exec_residual: pd.Series,
    one_way_cost: pd.Series,
    entry_z: float,
    exit_z: float,
    max_holding_minutes: int | None = None,
    stop_z: float | None = None,
    cost_multiplier: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if exit_z >= entry_z:
        raise ValueError("exit_z must be lower than entry_z")
    if stop_z is not None and stop_z <= entry_z:
        raise ValueError("stop_z must be greater than entry_z")

    dates = pd.Series(z.index.date.astype(str), index=z.index)
    pos = np.zeros(len(z), dtype=float)
    current = 0.0
    entry_i = -1
    trade_id = 0
    active_trade_id = 0
    row_trade_ids = np.zeros(len(z), dtype=int)
    trade_starts: dict[int, dict] = {}
    trade_rows: list[dict] = []

    z_values = z.to_numpy(dtype=float)
    for i, zi in enumerate(z_values):
        if i > 0 and dates.iloc[i] != dates.iloc[i - 1] and current != 0.0:
            trade_rows.append({**trade_starts[active_trade_id], "exit_time": z.index[i], "exit_z_observed": zi, "exit_reason": "eod"})
            current = 0.0
            entry_i = -1
            active_trade_id = 0

        if np.isfinite(zi):
            exit_reason = None
            if current == 0.0:
                if zi > entry_z:
                    current = -1.0
                    entry_i = i
                    trade_id += 1
                    active_trade_id = trade_id
                    trade_starts[active_trade_id] = {
                        "trade_id": active_trade_id,
                        "entry_time": z.index[i],
                        "direction": "short_residual",
                        "entry_z_observed": zi,
                    }
                elif zi < -entry_z:
                    current = 1.0
                    entry_i = i
                    trade_id += 1
                    active_trade_id = trade_id
                    trade_starts[active_trade_id] = {
                        "trade_id": active_trade_id,
                        "entry_time": z.index[i],
                        "direction": "long_residual",
                        "entry_z_observed": zi,
                    }
            elif current == 1.0:
                if zi > -exit_z:
                    exit_reason = "normal_exit"
                elif stop_z is not None and zi < -stop_z:
                    exit_reason = "stop_z"
                elif max_holding_minutes is not None and i - entry_i >= max_holding_minutes:
                    exit_reason = "max_holding"
            elif current == -1.0:
                if zi < exit_z:
                    exit_reason = "normal_exit"
                elif stop_z is not None and zi > stop_z:
                    exit_reason = "stop_z"
                elif max_holding_minutes is not None and i - entry_i >= max_holding_minutes:
                    exit_reason = "max_holding"

            if exit_reason is not None:
                trade_rows.append({**trade_starts[active_trade_id], "exit_time": z.index[i], "exit_z_observed": zi, "exit_reason": exit_reason})
                current = 0.0
                entry_i = -1
                active_trade_id = 0

        if i < len(z) - 1 and dates.iloc[i + 1] != dates.iloc[i] and current != 0.0:
            trade_rows.append({**trade_starts[active_trade_id], "exit_time": z.index[i], "exit_z_observed": zi, "exit_reason": "eod"})
            current = 0.0
            entry_i = -1
            active_trade_id = 0

        pos[i] = current
        row_trade_ids[i] = active_trade_id

    frame = pd.DataFrame(index=z.index)
    frame["z"] = z
    frame["position"] = pos
    frame["turnover"] = frame["position"].diff().abs().fillna(frame["position"].abs())
    frame["gross_ret"] = frame["position"].shift(1).fillna(0.0) * exec_residual.reindex(frame.index)
    frame["cost_ret"] = cost_multiplier * frame["turnover"] * one_way_cost.reindex(frame.index)
    frame["net_ret"] = frame["gross_ret"] - frame["cost_ret"]
    frame["cum_net_bps"] = 1e4 * frame["net_ret"].cumsum()
    frame["trade_id"] = row_trade_ids
    frame["sample"] = [sample_name(ts) for ts in frame.index]

    trades = pd.DataFrame(trade_rows)
    if not trades.empty:
        trades["entry_time"] = pd.to_datetime(trades["entry_time"])
        trades["exit_time"] = pd.to_datetime(trades["exit_time"])
        trades["holding_minutes"] = ((trades["exit_time"] - trades["entry_time"]).dt.total_seconds() / 60.0).astype(float)
        trades["entry_z"] = entry_z
        trades["exit_z"] = exit_z
        trades["max_holding_minutes"] = -1 if max_holding_minutes is None else max_holding_minutes
        trades["stop_z"] = np.nan if stop_z is None else stop_z
        trades["sample"] = trades["entry_time"].map(sample_name)
        for col in ["gross_bps", "cost_bps", "net_bps"]:
            trades[col] = 0.0
        for idx, trade in trades.iterrows():
            window = (frame.index >= trade["entry_time"]) & (frame.index <= trade["exit_time"])
            trades.loc[idx, "gross_bps"] = 1e4 * frame.loc[window, "gross_ret"].sum()
            trades.loc[idx, "cost_bps"] = 1e4 * frame.loc[window, "cost_ret"].sum()
            trades.loc[idx, "net_bps"] = 1e4 * frame.loc[window, "net_ret"].sum()
    else:
        trades = pd.DataFrame(
            columns=[
                "trade_id",
                "entry_time",
                "exit_time",
                "direction",
                "entry_z_observed",
                "exit_z_observed",
                "exit_reason",
                "holding_minutes",
                "entry_z",
                "exit_z",
                "max_holding_minutes",
                "stop_z",
                "sample",
                "gross_bps",
                "cost_bps",
                "net_bps",
            ]
        )
    return frame, trades


def max_drawdown_bps(net_ret: pd.Series) -> float:
    pnl = 1e4 * net_ret.cumsum()
    return float((pnl - pnl.cummax()).min()) if len(pnl) else 0.0


def sharpe_or_tstat(net_ret: pd.Series) -> float:
    std = net_ret.std()
    if std is None or std <= 0 or not np.isfinite(std):
        return np.nan
    return float(np.sqrt(len(net_ret)) * net_ret.mean() / std)


def summarize_sample(frame: pd.DataFrame, trades: pd.DataFrame, sample: str) -> dict:
    part = frame[frame["sample"] == sample]
    trade_part = trades[trades["sample"] == sample] if not trades.empty else trades
    return {
        "gross_bps": float(1e4 * part["gross_ret"].sum()),
        "cost_bps": float(1e4 * part["cost_ret"].sum()),
        "net_bps": float(1e4 * part["net_ret"].sum()),
        "num_trades": int(len(trade_part)),
        "turnover": float(part["turnover"].sum()),
        "win_rate": float((trade_part["net_bps"] > 0).mean()) if len(trade_part) else np.nan,
        "avg_holding_minutes": float(trade_part["holding_minutes"].mean()) if len(trade_part) else np.nan,
        "max_drawdown_bps": max_drawdown_bps(part["net_ret"]),
        "sharpe_or_tstat": sharpe_or_tstat(part["net_ret"]),
    }


def run_grid(
    pair: PairSpec,
    ret: pd.DataFrame,
    spread_bps: pd.DataFrame,
    center_window: int,
    entry_grid: list[float],
    exit_grid: list[float],
    max_holding_grid: list[int | None],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[float, float, int], pd.DataFrame]]:
    res = residual_ret(ret, pair.stock, pair.beta)
    spread = res.cumsum()
    z = rolling_zscore(spread, center_window)
    cost = one_way_cost_ret(spread_bps, pair.stock, pair.beta)
    rows = []
    all_trades = []
    selected_frames: dict[tuple[float, float, int], pd.DataFrame] = {}
    for entry_z in entry_grid:
        for exit_z in exit_grid:
            if exit_z >= entry_z:
                continue
            for max_hold in max_holding_grid:
                frame, trades = run_z_strategy(z, res, cost, entry_z, exit_z, max_hold)
                hold_key = -1 if max_hold is None else int(max_hold)
                for sample in ["train", "validation", "test"]:
                    rec = {
                        "pair": pair.pair,
                        "stock": pair.stock,
                        "beta": pair.beta,
                        "entry_z": entry_z,
                        "exit_z": exit_z,
                        "max_holding_minutes": hold_key,
                        "sample": sample,
                    }
                    rec.update(summarize_sample(frame, trades, sample))
                    rows.append(rec)
                if not trades.empty:
                    t = trades.copy()
                    t.insert(0, "pair", pair.pair)
                    t.insert(1, "stock", pair.stock)
                    t.insert(2, "beta", pair.beta)
                    all_trades.append(t)
                selected_frames[(entry_z, exit_z, hold_key)] = frame
    grid = pd.DataFrame(rows)
    trades_out = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    return grid, trades_out, selected_frames


def select_best_validation(grid: pd.DataFrame) -> pd.DataFrame:
    val = grid[grid["sample"] == "validation"].copy()
    val = val[val["num_trades"] >= 2]
    if val.empty:
        val = grid[grid["sample"] == "validation"].copy()
    sort_cols = ["stock", "net_bps", "num_trades", "max_drawdown_bps"]
    val = val.sort_values(sort_cols, ascending=[True, False, False, False])
    return val.groupby("stock", as_index=False).head(1).reset_index(drop=True)


def make_pair_specs(ret: pd.DataFrame) -> list[PairSpec]:
    out = []
    train = masks(ret.index)["train"]
    for stock in CONSTITUENTS:
        beta = estimate_pair_beta(ret, stock)
        if not np.isfinite(beta):
            continue
        spread = residual_ret(ret, stock, beta).cumsum()
        train_spread = spread.loc[train]
        out.append(PairSpec(stock, beta, adf_pvalue(train_spread), half_life_minutes(train_spread)))
    return out


def write_data_diagnostics(panel: pd.DataFrame, views: dict[str, pd.DataFrame], tables: Path) -> None:
    total_minutes = len(views["mid"].index)
    rows = []
    for symbol in SYMBOLS:
        sub = panel[panel["symbol"] == symbol]
        spread = sub["spread_bps"].replace([np.inf, -np.inf], np.nan)
        rows.append(
            {
                "symbol": symbol,
                "valid_minutes": int(views["mid"][symbol].notna().sum()),
                "avg_spread_bps": float(spread.mean()),
                "median_spread_bps": float(spread.median()),
                "p95_spread_bps": float(spread.quantile(0.95)),
                "p99_spread_bps": float(spread.quantile(0.99)),
                "avg_volume": float(sub["volume"].mean()),
                "median_volume": float(sub["volume"].median()),
                "quote_updates": int(sub["quote_updates"].sum()),
                "trade_count": int(sub["trade_count"].sum()),
                "missing_rate": float(1.0 - views["mid"][symbol].notna().sum() / total_minutes),
            }
        )
    pd.DataFrame(rows).to_csv(tables / "old_data_diagnostics.csv", index=False)


def plot_heatmap(table: pd.DataFrame, value_col: str, title: str, output: Path) -> None:
    if table.empty:
        return
    pivoted = table.pivot_table(index="entry_z", columns="exit_z", values=value_col, aggfunc="max").sort_index(ascending=False)
    fig, ax = plt.subplots(figsize=(8.5, 5.8))
    im = ax.imshow(pivoted.to_numpy(dtype=float), aspect="auto", cmap="RdYlGn")
    ax.set_xticks(np.arange(len(pivoted.columns)))
    ax.set_xticklabels([f"{x:g}" for x in pivoted.columns])
    ax.set_yticks(np.arange(len(pivoted.index)))
    ax.set_yticklabels([f"{x:g}" for x in pivoted.index])
    ax.set_xlabel("exit z")
    ax.set_ylabel("entry z")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label=value_col)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_pair_leaderboard(leaderboard: pd.DataFrame, figures: Path) -> None:
    if leaderboard.empty:
        return
    ordered = leaderboard.sort_values("test_net_bps")
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.barh(ordered["pair"], ordered["test_net_bps"], color=np.where(ordered["test_net_bps"] >= 0, "#2f8f63", "#b84a4a"))
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("test net bps")
    ax.set_title("Pair Leaderboard: Validation-Selected Parameters, March Test")
    fig.tight_layout()
    fig.savefig(figures / "pair_leaderboard_test_net_bps.png", dpi=180)
    plt.close(fig)


def plot_cumulative(frame: pd.DataFrame, title: str, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(frame.index, frame["cum_net_bps"], linewidth=1.1)
    ax.axvline(VAL_START, color="black", linestyle="--", linewidth=0.9, label="validation start")
    ax.axvline(TEST_START, color="black", linestyle=":", linewidth=1.1, label="test start")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("cumulative net bps")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_z_with_trades(frame: pd.DataFrame, trades: pd.DataFrame, title: str, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(frame.index, frame["z"], linewidth=0.8, label="z-score")
    if not trades.empty:
        entries = trades["entry_time"]
        exits = trades["exit_time"]
        ax.scatter(entries, frame["z"].reindex(entries), s=16, marker="^", color="#2f8f63", label="entry")
        ax.scatter(exits, frame["z"].reindex(exits), s=16, marker="v", color="#b84a4a", label="exit")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_ylabel("z-score")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_drawdown(frame: pd.DataFrame, output: Path) -> None:
    pnl = 1e4 * frame["net_ret"].cumsum()
    dd = pnl - pnl.cummax()
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(dd.index, dd, color="#8b3a3a", linewidth=1.0)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("drawdown bps")
    ax.set_title("Drawdown Curve: Best Validation-Selected Pair")
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def execution_comparison(best: pd.Series, ret: pd.DataFrame, spread_bps: pd.DataFrame, center_window: int, figures: Path, tables: Path) -> None:
    stock = str(best["stock"])
    beta = float(best["beta"])
    entry_z = float(best["entry_z"])
    exit_z = float(best["exit_z"])
    hold = None if int(best["max_holding_minutes"]) < 0 else int(best["max_holding_minutes"])
    res = residual_ret(ret, stock, beta)
    z = rolling_zscore(res.cumsum(), center_window)
    cost = one_way_cost_ret(spread_bps, stock, beta)
    mid_frame, _ = run_z_strategy(z, res, cost, entry_z, exit_z, hold, cost_multiplier=0.0)
    bidask_frame, _ = run_z_strategy(z, res, cost, entry_z, exit_z, hold, cost_multiplier=1.0)
    rows = []
    for label, frame in [("midpoint_no_cost", mid_frame), ("bidask_aware", bidask_frame)]:
        for sample in ["validation", "test"]:
            part = frame[frame["sample"] == sample]
            rows.append(
                {
                    "execution_model": label,
                    "pair": f"{ETF}-{stock}",
                    "sample": sample,
                    "gross_bps": 1e4 * part["gross_ret"].sum(),
                    "cost_bps": 1e4 * part["cost_ret"].sum(),
                    "net_bps": 1e4 * part["net_ret"].sum(),
                    "turnover": part["turnover"].sum(),
                }
            )
    pd.DataFrame(rows).to_csv(tables / "midpoint_vs_bidask_execution_comparison.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(mid_frame.index, mid_frame["cum_net_bps"], label="midpoint no cost", linewidth=1.0)
    ax.plot(bidask_frame.index, bidask_frame["cum_net_bps"], label="bid/ask aware", linewidth=1.0)
    ax.axvline(TEST_START, color="black", linestyle=":", linewidth=1.0)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("cumulative bps")
    ax.set_title("Midpoint vs Bid/Ask-Aware Execution")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures / "midpoint_vs_bidask_execution_comparison.png", dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    processed, tables, figures = setup(args.root)
    panel = load_old_panel(processed)
    views = make_views(panel)
    write_data_diagnostics(panel, views, tables)

    mid = views["mid"]
    spread_bps = views["spread_bps"]
    ret = log_returns(mid)
    pairs = make_pair_specs(ret)

    entry_grid = [1.0, 1.5, 2.0, 2.5, 3.0] if args.quick else [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5]
    exit_grid = [0.0, 0.5, 1.0] if args.quick else [0.0, 0.25, 0.5, 0.75, 1.0, 1.25]
    max_holding_grid: list[int | None] = [None, 60, 120] if args.quick else [None, 30, 60, 120, 240]

    all_grid = []
    all_trades = []
    frame_lookup: dict[tuple[str, float, float, int], pd.DataFrame] = {}
    for pair in pairs:
        grid, trades, frames = run_grid(pair, ret, spread_bps, args.center_window, entry_grid, exit_grid, max_holding_grid)
        all_grid.append(grid)
        if not trades.empty:
            all_trades.append(trades)
        for key, frame in frames.items():
            frame_lookup[(pair.stock, *key)] = frame

    grid_table = pd.concat(all_grid, ignore_index=True) if all_grid else pd.DataFrame()
    trades_table = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    grid_table.to_csv(tables / "old_pair_zscore_grid.csv", index=False)
    trades_table.to_csv(tables / "old_pair_trade_log.csv", index=False)

    best_val = select_best_validation(grid_table)
    leaderboard_rows = []
    for _, best in best_val.iterrows():
        stock = str(best["stock"])
        key = (stock, float(best["entry_z"]), float(best["exit_z"]), int(best["max_holding_minutes"]))
        test = grid_table[
            (grid_table["stock"] == stock)
            & (grid_table["entry_z"] == best["entry_z"])
            & (grid_table["exit_z"] == best["exit_z"])
            & (grid_table["max_holding_minutes"] == best["max_holding_minutes"])
            & (grid_table["sample"] == "test")
        ].iloc[0]
        spec = next(p for p in pairs if p.stock == stock)
        leaderboard_rows.append(
            {
                "pair": spec.pair,
                "beta": spec.beta,
                "ADF p-value": spec.train_adf_p,
                "half-life": spec.train_half_life_minutes,
                "best validation entry_z": best["entry_z"],
                "best validation exit_z": best["exit_z"],
                "best validation max_holding_minutes": best["max_holding_minutes"],
                "validation net bps": best["net_bps"],
                "test net bps": test["net_bps"],
                "test trades": test["num_trades"],
                "test max drawdown": test["max_drawdown_bps"],
                "avg holding minutes": test["avg_holding_minutes"],
            }
        )
    leaderboard = pd.DataFrame(leaderboard_rows).sort_values("test net bps", ascending=False)
    leaderboard.to_csv(tables / "old_pair_leaderboard.csv", index=False)

    strategy_rows = []
    for _, row in leaderboard.iterrows():
        pair = row["pair"]
        stock = pair.split("-")[1]
        selected = best_val[best_val["stock"] == stock].iloc[0]
        chosen = grid_table[
            (grid_table["stock"] == stock)
            & (grid_table["entry_z"] == selected["entry_z"])
            & (grid_table["exit_z"] == selected["exit_z"])
            & (grid_table["max_holding_minutes"] == selected["max_holding_minutes"])
        ]
        rec = {
            "strategy": "pair_zscore",
            "universe": pair,
            "entry_z": selected["entry_z"],
            "exit_z": selected["exit_z"],
            "max_holding_minutes": selected["max_holding_minutes"],
        }
        for sample in ["train", "validation", "test"]:
            part = chosen[chosen["sample"] == sample].iloc[0]
            rec[f"{sample}_net_bps"] = part["net_bps"]
            if sample == "test":
                rec["num_trades"] = part["num_trades"]
                rec["avg_holding_minutes"] = part["avg_holding_minutes"]
                rec["max_drawdown_bps"] = part["max_drawdown_bps"]
                rec["turnover"] = part["turnover"]
                rec["cost_bps"] = part["cost_bps"]
                rec["gross_bps"] = part["gross_bps"]
        strategy_rows.append(rec)
    pd.DataFrame(strategy_rows).to_csv(tables / "old_strategy_diagnostics.csv", index=False)

    audit = pd.DataFrame(
        [
            {
                "strategy_name": "pair_zscore_validation_selected",
                "selected_using": "February 2026 validation net_bps with at least two validation trades when available",
                "tested_on": "March 2026 test",
                "is_test_selected": False,
                "valid_for_final_claim": True,
                "notes": "Jan 2026 estimates beta/diagnostics; Feb selects entry/exit/max-holding; Mar is held out.",
            },
            {
                "strategy_name": "pair_zscore_test_leaderboard_sort",
                "selected_using": "March 2026 test net_bps",
                "tested_on": "March 2026 test",
                "is_test_selected": True,
                "valid_for_final_claim": False,
                "notes": "Diagnostic ranking only; do not present as an ex ante selected final claim.",
            },
        ]
    )
    audit.to_csv(tables / "old_selection_audit.csv", index=False)

    if not args.no_plots and not leaderboard.empty:
        nvda_val = grid_table[(grid_table["stock"] == "NVDA") & (grid_table["sample"] == "validation") & (grid_table["max_holding_minutes"] == 120)]
        nvda_test = grid_table[(grid_table["stock"] == "NVDA") & (grid_table["sample"] == "test") & (grid_table["max_holding_minutes"] == 120)]
        nvda_count = nvda_val.copy()
        plot_heatmap(nvda_val, "net_bps", "XLK-NVDA Validation Net bps, max holding 120", figures / "heatmap_validation_net_bps.png")
        plot_heatmap(nvda_test, "net_bps", "XLK-NVDA Test Net bps, max holding 120", figures / "heatmap_test_net_bps.png")
        plot_heatmap(nvda_count, "num_trades", "XLK-NVDA Validation Trade Count, max holding 120", figures / "heatmap_trade_count.png")
        plot_pair_leaderboard(leaderboard.rename(columns={"test net bps": "test_net_bps"}), figures)

        best = leaderboard.iloc[0]
        stock = str(best["pair"]).split("-")[1]
        selected = best_val[best_val["stock"] == stock].iloc[0]
        key = (stock, float(selected["entry_z"]), float(selected["exit_z"]), int(selected["max_holding_minutes"]))
        best_frame = frame_lookup[key]
        best_trades = trades_table[
            (trades_table["stock"] == stock)
            & (trades_table["entry_z"] == selected["entry_z"])
            & (trades_table["exit_z"] == selected["exit_z"])
            & (trades_table["max_holding_minutes"] == selected["max_holding_minutes"])
        ]
        plot_cumulative(best_frame, f"{ETF}-{stock} Pair Cumulative Net P&L", figures / "pair_best_cumulative_pnl.png")
        plot_z_with_trades(best_frame[best_frame["sample"] == "test"], best_trades[best_trades["sample"] == "test"], f"{ETF}-{stock} Test Z-Score with Trades", figures / "pair_best_zscore_with_trades.png")
        plot_drawdown(best_frame, figures / "drawdown_curve_best_strategy.png")
        execution_comparison(selected, ret, spread_bps, args.center_window, figures, tables)

    print("[old-data-method-upgrade] wrote:")
    for name in [
        "old_data_diagnostics.csv",
        "old_pair_zscore_grid.csv",
        "old_pair_trade_log.csv",
        "old_pair_leaderboard.csv",
        "old_strategy_diagnostics.csv",
        "old_selection_audit.csv",
        "midpoint_vs_bidask_execution_comparison.csv",
    ]:
        print(f"  output/tables/{name}")


if __name__ == "__main__":
    main()
