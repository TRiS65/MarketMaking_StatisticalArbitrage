#!/usr/bin/env python3
"""Literature-grounded robustness layer for the XLK stat-arb project.

This script keeps the original proposal results intact, then adds a more
research-grade specification motivated by the papers in the project folder:

* sparse mean-reverting portfolios instead of dense/static baskets,
* rolling/estimated hedge ratios rather than holdings-only weights,
* OU-style stationarity diagnostics,
* microprice signals with midpoint-executable P&L,
* proportional-cost no-trade gates and turnover accounting,
* a strict Jan-Feb train / March test split.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

from project_config import ETF, constituents as project_constituents, split_dates

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output"
TABLES = OUTPUT / "tables"
FIGURES = OUTPUT / "figures"

CONSTITUENTS = project_constituents()
TRAIN_END = split_dates()[1]


@dataclass
class Candidate:
    subset: tuple[str, ...]
    beta: np.ndarray
    train_adf_p: float
    train_half_life: float
    train_std_bps: float
    train_cost_bps: float
    score: float


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
        full_index.append(pd.date_range(pd.Timestamp(f"{day} 09:30:00"), periods=390, freq="min"))
    full_index = full_index[0].append(full_index[1:])

    def fill(frame: pd.DataFrame) -> pd.DataFrame:
        aligned = frame.reindex(full_index)
        key = pd.Series(aligned.index.date.astype(str), index=aligned.index)
        return aligned.groupby(key, group_keys=False).ffill(limit=5)

    mid = fill(mid)
    micro = fill(micro)
    spread_bps = fill(spread_bps)
    available = [s for s in [ETF] + CONSTITUENTS if s in mid.columns]
    common = mid.dropna(subset=available).index
    return mid.loc[common].astype(float), micro.loc[common].astype(float), spread_bps.loc[common].astype(float)


def clean_returns(price: pd.DataFrame) -> pd.DataFrame:
    ret = np.log(price.astype(float)).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    continuous = (price.index.to_series().diff() == pd.Timedelta(minutes=1)) & (
        price.index.to_series().dt.date == price.index.to_series().shift(1).dt.date
    )
    ret.loc[~continuous.values, :] = 0.0
    return ret.clip(lower=-0.05, upper=0.05)


def half_life(series: pd.Series) -> float:
    s = series.dropna()
    lag = s.shift(1).dropna()
    delta = s.diff().dropna()
    lag = lag.loc[delta.index]
    if len(delta) < 250:
        return np.nan
    model = sm.OLS(delta.values, sm.add_constant(lag.values)).fit()
    phi = 1.0 + model.params[1]
    if phi <= 0 or phi >= 1:
        return np.nan
    return float(-np.log(2) / np.log(phi))


def ridge_positive_beta(ret: pd.DataFrame, subset: tuple[str, ...], train_mask: np.ndarray) -> np.ndarray | None:
    x = (1e4 * ret.loc[train_mask, list(subset)]).clip(-500, 500).to_numpy(dtype=float)
    y = (1e4 * ret.loc[train_mask, ETF]).clip(-500, 500).to_numpy(dtype=float)
    valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if len(y) < 2_000:
        return None
    ridge = 1e-2
    xtx = x.T @ x / len(y)
    xty = x.T @ y / len(y)
    try:
        beta = np.linalg.solve(xtx + ridge * np.eye(len(subset)), xty)
    except np.linalg.LinAlgError:
        return None
    beta = np.clip(beta, 0.0, 1.0)
    if beta.sum() <= 0 or beta.sum() > 2.0:
        return None
    return beta


def residual(ret: pd.DataFrame, subset: tuple[str, ...], beta: np.ndarray) -> pd.Series:
    x = np.nan_to_num(ret[list(subset)].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    safe_beta = np.nan_to_num(beta.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        hedge = x @ safe_beta
    hedge = np.nan_to_num(hedge, nan=0.0, posinf=0.0, neginf=0.0)
    return ret[ETF] - pd.Series(hedge, index=ret.index)


def cost_series(spread_bps: pd.DataFrame, subset: tuple[str, ...], beta: np.ndarray) -> pd.Series:
    cost = spread_bps[ETF] / 2.0
    for symbol, weight in zip(subset, beta):
        cost = cost + abs(weight) * spread_bps[symbol] / 2.0
    return cost / 1e4


def evaluate_candidates(signal_ret: pd.DataFrame, spread_bps: pd.DataFrame) -> pd.DataFrame:
    train_mask = signal_ret.index < TRAIN_END
    rows: list[dict] = []
    candidates: list[Candidate] = []

    search_universe = CONSTITUENTS[:12]
    for k in range(2, 6):
        for subset in itertools.combinations(search_universe, k):
            beta = ridge_positive_beta(signal_ret, subset, train_mask)
            if beta is None:
                continue
            res_ret = residual(signal_ret, subset, beta)
            spread = res_ret.cumsum()
            train_spread = spread.loc[train_mask]
            try:
                adf_p = float(adfuller(train_spread.dropna(), maxlag=20, autolag="AIC")[1])
            except Exception:
                adf_p = np.nan
            hl = half_life(train_spread)
            std_bps = float(1e4 * train_spread.std())
            avg_cost_bps = float(1e4 * cost_series(spread_bps, subset, beta).loc[train_mask].mean())
            if not np.isfinite(adf_p) or not np.isfinite(hl):
                continue
            score = adf_p + 0.0005 * hl + 0.02 * avg_cost_bps
            rec = {
                "subset": " ".join(subset),
                "k": k,
                "betas": " ".join(f"{s}:{b:.4f}" for s, b in zip(subset, beta)),
                "sum_beta": float(beta.sum()),
                "train_adf_p": adf_p,
                "train_half_life_minutes": hl,
                "train_std_bps": std_bps,
                "train_avg_oneway_cost_bps": avg_cost_bps,
                "score": score,
            }
            rows.append(rec)
            candidates.append(Candidate(subset, beta, adf_p, hl, std_bps, avg_cost_bps, score))

    table = pd.DataFrame(rows).sort_values("score").reset_index(drop=True)
    table.to_csv(TABLES / "enhanced_sparse_candidates.csv", index=False)
    return table


def position_path(
    spread: pd.Series,
    cost: pd.Series,
    entry: float,
    exit_band: float,
    train_mask: np.ndarray,
    cost_gate: bool,
    gate_mult: float = 1.25,
    window: int = 390 * 5,
) -> pd.Series:
    mean = spread.rolling(window, min_periods=390).mean()
    std = spread.rolling(window, min_periods=390).std()
    z = (spread - mean) / std
    dates = pd.Series(spread.index.date.astype(str), index=spread.index)
    pos = np.zeros(len(spread))
    current = 0.0
    for i, zi in enumerate(z.to_numpy()):
        if i > 0 and dates.iloc[i] != dates.iloc[i - 1]:
            current = 0.0
        if np.isfinite(zi):
            expected_bps = abs(spread.iloc[i] - mean.iloc[i]) * 1e4 if np.isfinite(mean.iloc[i]) else 0.0
            roundtrip_bps = 2.0 * 1e4 * cost.iloc[i]
            trade_allowed = (not cost_gate) or (expected_bps > gate_mult * roundtrip_bps)
            if current == 0.0 and trade_allowed:
                if zi > entry:
                    current = -1.0
                elif zi < -entry:
                    current = 1.0
            elif current == 1.0 and zi > -exit_band:
                current = 0.0
            elif current == -1.0 and zi < exit_band:
                current = 0.0
        if i < len(spread) - 1 and dates.iloc[i + 1] != dates.iloc[i]:
            current = 0.0
        pos[i] = current
    return pd.Series(pos, index=spread.index)


def backtest_one(
    signal_ret: pd.DataFrame,
    exec_ret: pd.DataFrame,
    spread_bps: pd.DataFrame,
    subset: tuple[str, ...],
    beta: np.ndarray,
    entry: float,
    exit_band: float,
    cost_gate: bool,
    name: str,
) -> tuple[pd.DataFrame, dict]:
    signal_res_ret = residual(signal_ret, subset, beta)
    exec_res_ret = residual(exec_ret, subset, beta)
    spread = signal_res_ret.cumsum()
    cost = cost_series(spread_bps, subset, beta)
    train_mask = spread.index < TRAIN_END
    pos = position_path(spread, cost, entry, exit_band, train_mask, cost_gate)
    turnover = pos.diff().abs().fillna(pos.abs())
    gross = pos.shift(1).fillna(0.0) * exec_res_ret
    net = gross - turnover * cost
    frame = pd.DataFrame(
        {
            "spread": spread,
            "signal_residual_ret": signal_res_ret,
            "exec_residual_ret": exec_res_ret,
            "position": pos,
            "turnover": turnover,
            "cost_ret": turnover * cost,
            "gross_ret": gross,
            "net_ret": net,
            "sample": np.where(spread.index < TRAIN_END, "train", "test"),
        },
        index=spread.index,
    )
    frame["cum_net_bps"] = 1e4 * frame["net_ret"].cumsum()

    rows = []
    for sample, part in frame.groupby("sample"):
        ann = 252 * 390
        rows.append(
            {
                "strategy": name,
                "sample": sample,
                "subset": " ".join(subset),
                "betas": " ".join(f"{s}:{b:.4f}" for s, b in zip(subset, beta)),
                "entry_z": entry,
                "exit_z": exit_band,
                "cost_gate": cost_gate,
                "observations": len(part),
                "trades": float((part["turnover"] > 0).sum()),
                "avg_abs_position": float(part["position"].abs().mean()),
                "gross_bps": float(1e4 * part["gross_ret"].sum()),
                "cost_bps": float(1e4 * part["cost_ret"].sum()),
                "net_bps": float(1e4 * part["net_ret"].sum()),
                "sharpe_minute_ann": float(np.sqrt(ann) * part["net_ret"].mean() / part["net_ret"].std())
                if part["net_ret"].std() > 0
                else np.nan,
                "max_drawdown_bps": float((1e4 * part["net_ret"].cumsum() - 1e4 * part["net_ret"].cumsum().cummax()).min()),
            }
        )
    return frame, {"rows": rows}


def optimize_and_test(
    signal_ret: pd.DataFrame,
    exec_ret: pd.DataFrame,
    spread_bps: pd.DataFrame,
    candidates: pd.DataFrame,
) -> pd.DataFrame:
    best = candidates.iloc[0]
    subset = tuple(best["subset"].split())
    beta = np.array([float(x.split(":")[1]) for x in best["betas"].split()])

    train_results = []
    frames = {}
    for entry in [2.0, 2.5, 3.0, 3.5]:
        for exit_band in [0.0, 0.25, 0.5, 1.0]:
            for cost_gate in [False, True]:
                name = f"sparse_e{entry:g}_x{exit_band:g}_{'gate' if cost_gate else 'plain'}"
                frame, meta = backtest_one(signal_ret, exec_ret, spread_bps, subset, beta, entry, exit_band, cost_gate, name)
                rows = meta["rows"]
                train_row = [r for r in rows if r["sample"] == "train"][0]
                test_row = [r for r in rows if r["sample"] == "test"][0]
                train_results.append({**train_row, "test_net_bps_preview": test_row["net_bps"]})
                frames[name] = (frame, rows)

    grid = pd.DataFrame(train_results).sort_values(["net_bps", "trades"], ascending=[False, True]).reset_index(drop=True)
    selected = grid.iloc[0]["strategy"]
    selected_frame, selected_rows = frames[selected]
    selected_frame.to_parquet(PROCESSED / "enhanced_sparse_backtest.parquet")

    summary = pd.DataFrame(selected_rows)
    no_trade_rows = []
    for sample, part in selected_frame.groupby("sample"):
        no_trade_rows.append(
            {
                "strategy": "literature_no_trade",
                "sample": sample,
                "subset": "",
                "betas": "",
                "entry_z": np.nan,
                "exit_z": np.nan,
                "cost_gate": True,
                "observations": len(part),
                "trades": 0.0,
                "avg_abs_position": 0.0,
                "gross_bps": 0.0,
                "cost_bps": 0.0,
                "net_bps": 0.0,
                "sharpe_minute_ann": np.nan,
                "max_drawdown_bps": 0.0,
            }
        )
    summary = pd.concat([summary, pd.DataFrame(no_trade_rows)], ignore_index=True)
    summary.to_csv(TABLES / "enhanced_backtest_summary.csv", index=False)

    plt.figure(figsize=(10, 4.8))
    for strategy, frame in [("selected sparse", selected_frame)]:
        plt.plot(frame.index, frame["cum_net_bps"], label=strategy)
    plt.axvline(TRAIN_END, color="black", linestyle="--", linewidth=1, label="March test start")
    plt.axhline(0, color="black", linewidth=0.8)
    plt.title("Enhanced Sparse Hedge Strategy: Cumulative Net P&L")
    plt.ylabel("basis points of ETF notional")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "enhanced_sparse_cumulative_net.png", dpi=180)
    plt.close()

    return summary


def write_literature_notes() -> None:
    notes = """# Literature Integration Notes

This enhanced layer uses every paper supplied in the project folder as a design constraint.

| Paper | How it enters the implementation |
|---|---|
| d'Aspremont, *Identifying Small Mean Reverting Portfolios* | Search over small constituent subsets instead of forcing a dense basket; rank candidates by stationarity, half-life, and cost. |
| Kanamura, Rachev, Fabozzi, *A Profit Model for Spread Trading* | Treat spread trading as a first-passage/mean-reversion problem; require estimated spread movement to be large relative to trading cost. |
| Leung and Li, *Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit* | Use entry/exit bands rather than continuous trading, and choose thresholds on the training sample only. |
| Martin, *Optimal Multifactor Trading under Proportional Transaction Costs* | Add a no-trade buffer/cost gate so small target-position changes are ignored. |
| Gueant, Lehalle, Fernandez-Tapia, *Dealing with the Inventory Risk* | Track position, turnover, and end-of-day flattening; avoid interpreting raw signal quality without inventory risk. |
| Ghoshal and Roberts, *Optimal FX Market Making under Inventory Risk and Adverse Selection Constraints* | Treat adverse selection through conservative execution assumptions: crossing half-spreads and avoiding trades where signal is small versus cost. |
| Almgren, *Optimal Trading with Stochastic Liquidity and Volatility* | Let spread costs vary minute by minute through contemporaneous bid-ask spreads instead of using a constant fee. |
| Dare, *Statistical Arbitrage in the U.S. Treasury Futures Market* | Use a train/test statistical-arbitrage workflow: construct spread, test mean reversion, then evaluate out-of-sample trading. |

Main methodological changes: the original holdings-weight basket is an economic benchmark, but not necessarily the tradable mean-reverting portfolio; microprice is a fair-value signal rather than an executable fill.  The enhanced model estimates a sparse hedge portfolio on January-February 2026, uses microprice residuals for entry/exit signals, computes gross P&L on midpoint residual returns, and evaluates the selected rule in March 2026.
"""
    (OUTPUT / "literature_notes.md").write_text(notes)


def main() -> None:
    setup()
    mid, micro, spread_bps = align_panel()
    exec_ret = clean_returns(mid)
    signal_ret = clean_returns(micro)
    candidates = evaluate_candidates(signal_ret, spread_bps)
    summary = optimize_and_test(signal_ret, exec_ret, spread_bps, candidates)
    write_literature_notes()
    print("[enhanced] best sparse candidates")
    print(candidates.head(10).to_string(index=False))
    print("[enhanced] selected backtest")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
