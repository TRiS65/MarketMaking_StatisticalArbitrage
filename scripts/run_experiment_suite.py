#!/usr/bin/env python3
"""Walk-forward experiment suite for XLK ETF-basket statistical arbitrage.

This script is designed to replace one-off threshold tuning with a stricter,
IMC-style research workflow:

1. Generate many economically motivated candidates: sparse baskets, hedge
   estimators, microprice-shrinkage signal views, fixed-bps and z-score bands,
   partial hedging, cost gates, and time-of-day filters.
2. Select only on the configured training period and report the configured
   out-of-sample test.
3. Prefer stable parameter regions over single backtest peaks.
4. Compare every active rule against a no-trade benchmark.  If no active rule has
   robust positive training performance, the selected decision is explicitly
   no-trade.

Expected input:
    data/processed/research_panel.parquet

Expected columns in the panel:
    minute, symbol, mid, microprice, spread_bps
Optional columns used when available:
    bidsiz, asksiz, bid, ask, volume

Example:
    python3 scripts/run_experiment_suite.py \
        --root . \
        --test-start 2026-03-01 \
        --max-subset-size 6 \
        --min-train-trades 4
"""

from __future__ import annotations

import argparse
import itertools
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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


@dataclass(frozen=True)
class CandidateSpec:
    signal_view: str
    hedge_method: str
    subset: tuple[str, ...]
    beta: tuple[float, ...]

    @property
    def subset_text(self) -> str:
        return " ".join(self.subset)

    @property
    def beta_text(self) -> str:
        return " ".join(f"{s}:{b:.5f}" for s, b in zip(self.subset, self.beta))


@dataclass(frozen=True)
class RuleSpec:
    candidate: CandidateSpec
    threshold_mode: str
    entry: float
    exit_band: float
    hedge_fraction: float
    cost_gate_mult: float
    center_window: int
    trade_start: str
    trade_end: str
    max_hold_minutes: int

    @property
    def name(self) -> str:
        gate = "nogate" if self.cost_gate_mult <= 0 else f"gate{self.cost_gate_mult:g}"
        return (
            f"{self.candidate.signal_view}_{self.candidate.hedge_method}_"
            f"k{len(self.candidate.subset)}_{self.threshold_mode}_"
            f"e{self.entry:g}_x{self.exit_band:g}_h{self.hedge_fraction:g}_"
            f"{gate}_cw{self.center_window}_mh{self.max_hold_minutes}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Robust XLK stat-arb experiment suite")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--panel", type=Path, default=None, help="Optional explicit research_panel.parquet path")
    parser.add_argument("--test-start", type=str, default="2026-03-01")
    parser.add_argument("--max-subset-size", type=int, default=6)
    parser.add_argument("--min-subset-size", type=int, default=2)
    parser.add_argument("--min-train-trades", type=int, default=4)
    parser.add_argument("--max-train-trades", type=int, default=120)
    parser.add_argument("--ffill-limit", type=int, default=5)
    parser.add_argument("--return-clip-bps", type=float, default=500.0)
    parser.add_argument("--top-candidates", type=int, default=25)
    parser.add_argument("--quick", action="store_true", help="Smaller grid for quick iteration")
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def ensure_dirs(root: Path) -> tuple[Path, Path, Path]:
    output = root / "output"
    tables = output / "tables"
    figures = output / "figures"
    processed = root / "data" / "processed"
    for p in [output, tables, figures, processed]:
        p.mkdir(parents=True, exist_ok=True)
    return tables, figures, processed


def load_panel(root: Path, panel_path: Path | None) -> pd.DataFrame:
    path = panel_path or (root / "data" / "processed" / "research_panel.parquet")
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run scripts/build_dataset.py first, or pass --panel /path/to/research_panel.parquet."
        )
    panel = pd.read_parquet(path)
    required = {"minute", "symbol", "mid", "microprice", "spread_bps"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Panel is missing required columns: {sorted(missing)}")
    panel = panel.copy()
    panel["minute"] = pd.to_datetime(panel["minute"])
    panel = panel[panel["symbol"].isin(SYMBOLS)].sort_values(["symbol", "minute"])
    return panel


def pivot_panel(panel: pd.DataFrame, col: str) -> pd.DataFrame:
    if col not in panel.columns:
        return pd.DataFrame()
    return panel.pivot(index="minute", columns="symbol", values=col).sort_index()


def align_intraday(frame: pd.DataFrame, ffill_limit: int) -> pd.DataFrame:
    if frame.empty:
        return frame
    dates = sorted(pd.Series(frame.index.date.astype(str)).unique())
    full_index_parts = [pd.date_range(pd.Timestamp(f"{d} 09:30:00"), periods=MINUTES_PER_DAY, freq="min") for d in dates]
    full_index = full_index_parts[0].append(full_index_parts[1:]) if len(full_index_parts) > 1 else full_index_parts[0]
    aligned = frame.reindex(full_index)
    day_key = pd.Series(aligned.index.date.astype(str), index=aligned.index)
    return aligned.groupby(day_key, group_keys=False).ffill(limit=ffill_limit)


def aligned_views(panel: pd.DataFrame, ffill_limit: int) -> dict[str, pd.DataFrame]:
    raw = {col: pivot_panel(panel, col) for col in ["mid", "microprice", "spread_bps", "bidsiz", "asksiz", "volume"]}
    aligned = {col: align_intraday(df, ffill_limit) for col, df in raw.items() if not df.empty}
    common = aligned["mid"].dropna(subset=SYMBOLS).index
    for col in list(aligned):
        aligned[col] = aligned[col].loc[common].astype(float)
    return aligned


def continuous_mask(index: pd.Index) -> pd.Series:
    idx = pd.Series(index, index=index)
    return (idx.diff() == pd.Timedelta(minutes=1)) & (idx.dt.date == idx.shift(1).dt.date)


def clean_log_returns(price: pd.DataFrame, clip_bps: float) -> pd.DataFrame:
    ret = np.log(price.astype(float)).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    cont = continuous_mask(price.index)
    ret.loc[~cont.values, :] = 0.0
    clip = clip_bps / 1e4
    return ret.clip(lower=-clip, upper=clip)


def make_signal_price_views(views: dict[str, pd.DataFrame], quick: bool) -> dict[str, pd.DataFrame]:
    """Create signal prices.  Executable P&L should still use midpoint returns.

    The IMC write-up emphasizes robust fair-value proxies such as wall-mid.  We
    do not have full depth here, only NBBO and size, so the closest defensible
    analogue is a shrinkage microprice: keep the midpoint as the anchor and use
    only part of the microprice-midpoint gap.  This avoids treating a noisy top-
    of-book imbalance as an executable price.
    """
    mid = views["mid"]
    micro = views["microprice"]
    out: dict[str, pd.DataFrame] = {"mid": mid}
    shrink_values = [0.25, 0.50] if quick else [0.0, 0.25, 0.50, 0.75, 1.0]
    gap = np.log(micro / mid).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    # Confidence weighting: top-of-book microprice is less trusted when the spread
    # is wide or displayed size is very small versus its own recent history.
    spread = views.get("spread_bps", pd.DataFrame(index=mid.index, columns=mid.columns, data=1.0))
    spread_penalty = (1.0 / (1.0 + (spread / 10.0).clip(lower=0.0))).clip(0.0, 1.0)
    if "bidsiz" in views and "asksiz" in views:
        total_size = views["bidsiz"] + views["asksiz"]
        rolling_size = total_size.rolling(MINUTES_PER_DAY, min_periods=60).median().shift(1)
        size_conf = (total_size / rolling_size).replace([np.inf, -np.inf], np.nan).clip(0.0, 2.0) / 2.0
        size_conf = size_conf.fillna(0.5)
    else:
        size_conf = pd.DataFrame(0.5, index=mid.index, columns=mid.columns)
    confidence = (spread_penalty * size_conf).clip(0.0, 1.0).fillna(0.25)

    for shrink in shrink_values:
        if shrink == 0.0:
            continue
        out[f"micro_shrink_{shrink:g}"] = mid * np.exp(gap * shrink)
        out[f"micro_conf_{shrink:g}"] = mid * np.exp(gap * shrink * confidence)
    return out


def load_official_weights(root: Path) -> pd.Series | None:
    path = root / "output" / "tables" / "selected_xlk_holdings.csv"
    if not path.exists():
        path = root / "selected_xlk_holdings.csv"
    if not path.exists():
        return None
    weights = pd.read_csv(path)
    if "symbol" not in weights.columns or "basket_weight" not in weights.columns:
        return None
    s = weights.set_index("symbol")["basket_weight"].astype(float)
    return s.reindex(CONSTITUENTS).dropna()


def estimate_beta(
    ret: pd.DataFrame,
    subset: tuple[str, ...],
    train_mask: np.ndarray,
    method: str,
    official_weights: pd.Series | None,
) -> tuple[float, ...] | None:
    if method == "official_subset":
        if official_weights is None or not set(subset).issubset(set(official_weights.index)):
            return None
        raw = official_weights.loc[list(subset)].to_numpy(dtype=float)
        if raw.sum() <= 0:
            return None
        # Normalize inside the subset, then allow partial hedge experiments to
        # scale this later.
        return tuple((raw / raw.sum()).tolist())

    x = (1e4 * ret.loc[train_mask, list(subset)]).clip(-500, 500).to_numpy(dtype=float)
    y = (1e4 * ret.loc[train_mask, ETF]).clip(-500, 500).to_numpy(dtype=float)
    valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if len(y) < 1_000:
        return None
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    ridge = 1e-2 if method == "ridge_pos" else 5e-2
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        xtx = x.T @ x / len(y)
        xty = x.T @ y / len(y)
    if not np.isfinite(xtx).all() or not np.isfinite(xty).all():
        return None
    try:
        beta = np.linalg.solve(xtx + ridge * np.eye(len(subset)), xty)
    except np.linalg.LinAlgError:
        return None
    beta = np.nan_to_num(beta, nan=0.0, posinf=0.0, neginf=0.0)
    if method in {"ridge_pos", "ridge_pos_sum1"}:
        beta = np.clip(beta, 0.0, 1.25)
    if method == "ridge_pos_sum1":
        if beta.sum() <= 0:
            return None
        beta = beta / beta.sum()
    if beta.sum() <= 0 or beta.sum() > 2.5:
        return None
    return tuple(beta.astype(float).tolist())


def residual_ret(ret: pd.DataFrame, subset: tuple[str, ...], beta: Iterable[float], hedge_fraction: float = 1.0) -> pd.Series:
    b = np.nan_to_num(np.asarray(tuple(beta), dtype=float) * hedge_fraction, nan=0.0, posinf=0.0, neginf=0.0)
    x = ret.loc[:, list(subset)].to_numpy(dtype=float)
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        hedge = x @ b
    hedge = np.nan_to_num(hedge, nan=0.0, posinf=0.0, neginf=0.0)
    base = np.nan_to_num(ret[ETF].to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
    return pd.Series(base - hedge, index=ret.index)


def one_way_cost_ret(spread_bps: pd.DataFrame, subset: tuple[str, ...], beta: Iterable[float], hedge_fraction: float) -> pd.Series:
    cost = spread_bps[ETF].astype(float) / 2.0
    for symbol, b in zip(subset, beta):
        cost = cost + abs(float(b) * hedge_fraction) * spread_bps[symbol].astype(float) / 2.0
    return (cost / 1e4).replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)


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


def build_candidates(
    signal_returns: dict[str, pd.DataFrame],
    spread_bps: pd.DataFrame,
    train_mask: np.ndarray,
    official_weights: pd.Series | None,
    min_size: int,
    max_size: int,
    quick: bool,
    top_n: int,
) -> tuple[list[CandidateSpec], pd.DataFrame]:
    rows: list[dict] = []
    candidates: list[CandidateSpec] = []
    hedge_methods = ["ridge_pos", "ridge_pos_sum1"] if quick else ["ridge_pos", "ridge_pos_sum1", "official_subset"]
    signal_names = list(signal_returns.keys()) if not quick else [n for n in signal_returns if n in {"mid", "micro_shrink_0.5", "micro_conf_0.5"}]

    for signal_name in signal_names:
        ret = signal_returns[signal_name]
        for k in range(min_size, max_size + 1):
            for subset in itertools.combinations(CONSTITUENTS, k):
                for method in hedge_methods:
                    beta = estimate_beta(ret, subset, train_mask, method, official_weights)
                    if beta is None:
                        continue
                    res = residual_ret(ret, subset, beta, hedge_fraction=1.0)
                    spread = res.cumsum()
                    train_spread = spread.loc[train_mask]
                    hl = half_life_minutes(train_spread)
                    adf = adf_pvalue(train_spread)
                    std_bps = float(1e4 * train_spread.std())
                    cost_bps = float(1e4 * one_way_cost_ret(spread_bps, subset, beta, 1.0).loc[train_mask].mean())
                    if not np.isfinite(hl) or not np.isfinite(adf) or std_bps <= 0:
                        continue
                    # Low score is good: stationary, fast, not too noisy, cheap.
                    score = adf + 0.00035 * hl + 0.0005 * std_bps + 0.025 * cost_bps
                    spec = CandidateSpec(signal_name, method, subset, beta)
                    rows.append(
                        {
                            "signal_view": signal_name,
                            "hedge_method": method,
                            "subset": spec.subset_text,
                            "k": k,
                            "betas": spec.beta_text,
                            "sum_beta": float(np.sum(beta)),
                            "train_adf_p": adf,
                            "train_half_life_minutes": hl,
                            "train_std_bps": std_bps,
                            "train_avg_oneway_cost_bps_full_hedge": cost_bps,
                            "candidate_score_low_is_good": score,
                        }
                    )
                    candidates.append(spec)

    table = pd.DataFrame(rows)
    if table.empty:
        return [], table
    table = table.sort_values("candidate_score_low_is_good").reset_index(drop=True)
    # Reconstruct the sorted top candidate list from the table to avoid sorting a
    # separate list by object identity.
    key_to_spec = {(c.signal_view, c.hedge_method, c.subset_text, c.beta_text): c for c in candidates}
    sorted_candidates = []
    for _, row in table.head(top_n).iterrows():
        key = (row["signal_view"], row["hedge_method"], row["subset"], row["betas"])
        sorted_candidates.append(key_to_spec[key])
    return sorted_candidates, table


def make_center_and_score(spread: pd.Series, mode: str, center_window: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    minp = max(60, min(center_window // 2, MINUTES_PER_DAY))
    center = spread.rolling(center_window, min_periods=minp).median().shift(1)
    deviation = spread - center
    if mode == "fixed_bps":
        score = 1e4 * deviation
    elif mode == "zscore":
        mad = (spread - center).abs().rolling(center_window, min_periods=minp).median().shift(1)
        robust_std = 1.4826 * mad.replace(0.0, np.nan)
        score = deviation / robust_std
    else:
        raise ValueError(f"Unknown threshold mode: {mode}")
    return center, deviation, score


def position_path(
    score: pd.Series,
    deviation: pd.Series,
    one_way_cost: pd.Series,
    entry: float,
    exit_band: float,
    threshold_mode: str,
    cost_gate_mult: float,
    trade_start: str,
    trade_end: str,
    max_hold_minutes: int,
) -> pd.Series:
    dates = pd.Series(score.index.date.astype(str), index=score.index)
    tod = pd.Series(score.index.strftime("%H:%M"), index=score.index)
    tradable = (tod >= trade_start) & (tod <= trade_end)
    pos = np.zeros(len(score), dtype=float)
    current = 0.0
    entry_i = -1
    score_values = score.to_numpy(dtype=float)
    dev_values = deviation.to_numpy(dtype=float)
    cost_values = one_way_cost.to_numpy(dtype=float)

    for i, val in enumerate(score_values):
        if i > 0 and dates.iloc[i] != dates.iloc[i - 1]:
            current = 0.0
            entry_i = -1
        if not tradable.iloc[i]:
            if current != 0.0 and tod.iloc[i] > trade_end:
                current = 0.0
                entry_i = -1
            pos[i] = current
            continue
        if np.isfinite(val):
            dev_bps = abs(dev_values[i]) * 1e4 if np.isfinite(dev_values[i]) else 0.0
            roundtrip_cost_bps = 2.0 * 1e4 * cost_values[i] if np.isfinite(cost_values[i]) else np.inf
            trade_allowed = cost_gate_mult <= 0 or dev_bps > cost_gate_mult * roundtrip_cost_bps
            if current == 0.0 and trade_allowed:
                if val > entry:
                    current = -1.0
                    entry_i = i
                elif val < -entry:
                    current = 1.0
                    entry_i = i
            elif current == 1.0:
                if val > -exit_band or (max_hold_minutes > 0 and i - entry_i >= max_hold_minutes):
                    current = 0.0
                    entry_i = -1
            elif current == -1.0:
                if val < exit_band or (max_hold_minutes > 0 and i - entry_i >= max_hold_minutes):
                    current = 0.0
                    entry_i = -1
        if i < len(score) - 1 and dates.iloc[i + 1] != dates.iloc[i]:
            current = 0.0
            entry_i = -1
        pos[i] = current
    return pd.Series(pos, index=score.index)


def backtest_rule(
    rule: RuleSpec,
    signal_returns: dict[str, pd.DataFrame],
    exec_ret: pd.DataFrame,
    spread_bps: pd.DataFrame,
    test_start: pd.Timestamp,
) -> tuple[pd.DataFrame, dict]:
    cand = rule.candidate
    signal_ret = signal_returns[cand.signal_view]
    signal_res = residual_ret(signal_ret, cand.subset, cand.beta, hedge_fraction=1.0)
    signal_spread = signal_res.cumsum()
    exec_res = residual_ret(exec_ret, cand.subset, cand.beta, hedge_fraction=rule.hedge_fraction)
    one_way_cost = one_way_cost_ret(spread_bps, cand.subset, cand.beta, rule.hedge_fraction)
    center, deviation, score = make_center_and_score(signal_spread, rule.threshold_mode, rule.center_window)
    pos = position_path(
        score=score,
        deviation=deviation,
        one_way_cost=one_way_cost,
        entry=rule.entry,
        exit_band=rule.exit_band,
        threshold_mode=rule.threshold_mode,
        cost_gate_mult=rule.cost_gate_mult,
        trade_start=rule.trade_start,
        trade_end=rule.trade_end,
        max_hold_minutes=rule.max_hold_minutes,
    )
    turnover = pos.diff().abs().fillna(pos.abs())
    gross = pos.shift(1).fillna(0.0) * exec_res
    cost = turnover * one_way_cost
    net = gross - cost
    frame = pd.DataFrame(
        {
            "signal_spread": signal_spread,
            "center": center,
            "deviation": deviation,
            "score": score,
            "position": pos,
            "turnover": turnover,
            "gross_ret": gross,
            "cost_ret": cost,
            "net_ret": net,
            "sample": np.where(signal_spread.index < test_start, "train", "test"),
        },
        index=signal_spread.index,
    )
    frame["cum_net_bps"] = 1e4 * frame["net_ret"].cumsum()
    summary = summarize_rule(rule, frame, test_start)
    return frame, summary


def max_drawdown_bps(net_ret: pd.Series) -> float:
    pnl = 1e4 * net_ret.cumsum()
    return float((pnl - pnl.cummax()).min()) if len(pnl) else 0.0


def sharpe_ann(net_ret: pd.Series) -> float:
    std = net_ret.std()
    if std is None or std <= 0 or not np.isfinite(std):
        return np.nan
    return float(np.sqrt(ANN_FACTOR) * net_ret.mean() / std)


def summarize_rule(rule: RuleSpec, frame: pd.DataFrame, test_start: pd.Timestamp) -> dict:
    out: dict[str, object] = {
        "strategy": rule.name,
        "signal_view": rule.candidate.signal_view,
        "hedge_method": rule.candidate.hedge_method,
        "subset": rule.candidate.subset_text,
        "betas": rule.candidate.beta_text,
        "threshold_mode": rule.threshold_mode,
        "entry": rule.entry,
        "exit_band": rule.exit_band,
        "hedge_fraction": rule.hedge_fraction,
        "cost_gate_mult": rule.cost_gate_mult,
        "center_window": rule.center_window,
        "trade_start": rule.trade_start,
        "trade_end": rule.trade_end,
        "max_hold_minutes": rule.max_hold_minutes,
    }
    for sample in ["train", "test"]:
        part = frame[frame["sample"] == sample]
        prefix = f"{sample}_"
        out[prefix + "observations"] = int(len(part))
        out[prefix + "trades"] = float((part["turnover"] > 0).sum())
        out[prefix + "avg_abs_position"] = float(part["position"].abs().mean()) if len(part) else 0.0
        out[prefix + "gross_bps"] = float(1e4 * part["gross_ret"].sum())
        out[prefix + "cost_bps"] = float(1e4 * part["cost_ret"].sum())
        out[prefix + "net_bps"] = float(1e4 * part["net_ret"].sum())
        out[prefix + "sharpe_ann"] = sharpe_ann(part["net_ret"])
        out[prefix + "max_drawdown_bps"] = max_drawdown_bps(part["net_ret"])
    out.update(train_fold_metrics(frame[frame.index < test_start]))
    return out


def train_fold_metrics(train_frame: pd.DataFrame, n_folds: int = 4) -> dict[str, float]:
    if train_frame.empty:
        return {"fold_median_net_bps": 0.0, "fold_min_net_bps": 0.0, "fold_std_net_bps": 0.0, "fold_positive_rate": 0.0}
    dates = pd.Index(sorted(pd.Series(train_frame.index.date.astype(str)).unique()))
    if len(dates) < n_folds:
        n_folds = max(1, len(dates))
    fold_nets = []
    for arr in np.array_split(dates.to_numpy(), n_folds):
        if len(arr) == 0:
            continue
        mask = pd.Series(train_frame.index.date.astype(str), index=train_frame.index).isin(arr)
        fold_nets.append(float(1e4 * train_frame.loc[mask, "net_ret"].sum()))
    if not fold_nets:
        fold_nets = [0.0]
    vals = np.asarray(fold_nets, dtype=float)
    return {
        "fold_median_net_bps": float(np.median(vals)),
        "fold_min_net_bps": float(np.min(vals)),
        "fold_std_net_bps": float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0,
        "fold_positive_rate": float((vals > 0).mean()),
    }


def build_rule_grid(candidates: list[CandidateSpec], quick: bool) -> list[RuleSpec]:
    rules: list[RuleSpec] = []
    if quick:
        fixed_entries = [15.0, 25.0, 40.0]
        z_entries = [2.5, 3.5]
        hedge_fracs = [0.0, 0.5, 1.0]
        gate_mults = [0.0, 1.5]
        center_windows = [MINUTES_PER_DAY * 5]
        hold_times = [0, 120]
    else:
        fixed_entries = [10.0, 15.0, 20.0, 30.0, 40.0, 60.0, 90.0]
        z_entries = [2.0, 2.5, 3.0, 3.5, 4.0]
        hedge_fracs = [0.0, 0.25, 0.5, 0.75, 1.0]
        gate_mults = [0.0, 1.0, 1.5, 2.0]
        center_windows = [MINUTES_PER_DAY * 3, MINUTES_PER_DAY * 5, MINUTES_PER_DAY * 10]
        hold_times = [0, 60, 120, 240]

    for cand in candidates:
        for hedge_fraction in hedge_fracs:
            for gate in gate_mults:
                for center_window in center_windows:
                    for hold in hold_times:
                        for entry in fixed_entries:
                            # Exit at zero or small residual; in bps for fixed mode.
                            for exit_band in [0.0, min(10.0, entry / 3.0)]:
                                rules.append(
                                    RuleSpec(
                                        candidate=cand,
                                        threshold_mode="fixed_bps",
                                        entry=entry,
                                        exit_band=exit_band,
                                        hedge_fraction=hedge_fraction,
                                        cost_gate_mult=gate,
                                        center_window=center_window,
                                        trade_start="09:35",
                                        trade_end="15:45",
                                        max_hold_minutes=hold,
                                    )
                                )
                        for entry in z_entries:
                            for exit_band in [0.0, 0.5, 1.0]:
                                rules.append(
                                    RuleSpec(
                                        candidate=cand,
                                        threshold_mode="zscore",
                                        entry=entry,
                                        exit_band=exit_band,
                                        hedge_fraction=hedge_fraction,
                                        cost_gate_mult=gate,
                                        center_window=center_window,
                                        trade_start="09:35",
                                        trade_end="15:45",
                                        max_hold_minutes=hold,
                                    )
                                )
    return rules


def robust_selection_score(summary: dict, min_trades: int, max_trades: int) -> float:
    train_net = float(summary.get("train_net_bps", 0.0))
    train_trades = float(summary.get("train_trades", 0.0))
    fold_median = float(summary.get("fold_median_net_bps", 0.0))
    fold_min = float(summary.get("fold_min_net_bps", 0.0))
    fold_std = float(summary.get("fold_std_net_bps", 0.0))
    fold_positive = float(summary.get("fold_positive_rate", 0.0))
    dd = float(summary.get("train_max_drawdown_bps", 0.0))
    cost = float(summary.get("train_cost_bps", 0.0))

    if train_trades < min_trades or train_trades > max_trades:
        return -np.inf
    # Robustness, not peak-chasing: reward fold median and positive folds, penalize
    # the worst fold, dispersion, drawdown, and excessive cost.
    return (
        0.50 * train_net
        + 1.00 * fold_median
        + 0.40 * fold_min
        + 25.0 * fold_positive
        - 0.35 * fold_std
        + 0.20 * dd  # dd is negative
        - 0.05 * cost
    )


def run_experiments(
    root: Path,
    panel_path: Path | None,
    test_start: pd.Timestamp,
    min_subset_size: int,
    max_subset_size: int,
    min_train_trades: int,
    max_train_trades: int,
    ffill_limit: int,
    return_clip_bps: float,
    top_candidates: int,
    quick: bool,
    no_plots: bool,
) -> pd.DataFrame:
    tables, figures, processed = ensure_dirs(root)
    panel = load_panel(root, panel_path)
    views = aligned_views(panel, ffill_limit)
    signal_prices = make_signal_price_views(views, quick=quick)
    exec_ret = clean_log_returns(views["mid"], return_clip_bps)
    signal_returns = {name: clean_log_returns(price, return_clip_bps) for name, price in signal_prices.items()}
    train_mask = exec_ret.index < test_start
    official_weights = load_official_weights(root)

    candidates, cand_table = build_candidates(
        signal_returns=signal_returns,
        spread_bps=views["spread_bps"],
        train_mask=train_mask,
        official_weights=official_weights,
        min_size=min_subset_size,
        max_size=max_subset_size,
        quick=quick,
        top_n=top_candidates,
    )
    cand_table.to_csv(tables / "experiment_sparse_candidates.csv", index=False)
    if not candidates:
        raise RuntimeError("No valid candidates were generated. Check data quality and required symbols.")

    rules = build_rule_grid(candidates, quick=quick)
    summaries: list[dict] = []
    best_frame: pd.DataFrame | None = None
    best_summary: dict | None = None
    best_score = -np.inf
    total = len(rules)
    for j, rule in enumerate(rules, start=1):
        try:
            frame, summary = backtest_rule(rule, signal_returns, exec_ret, views["spread_bps"], test_start)
        except Exception as exc:
            warnings.warn(f"Skipping {rule.name}: {exc}")
            continue
        score = robust_selection_score(summary, min_train_trades, max_train_trades)
        summary["robust_train_selection_score"] = score
        summaries.append(summary)
        if score > best_score:
            best_score = score
            best_frame = frame
            best_summary = summary
        if j % 500 == 0:
            print(f"[grid] evaluated {j:,}/{total:,} rules; current best score={best_score:.2f}")

    grid = pd.DataFrame(summaries)
    if grid.empty:
        raise RuntimeError("All rules failed during backtest.")

    # Stability island: within each structural family, use median train performance
    # as a second score so we do not just select a single lucky threshold.
    family_cols = ["signal_view", "hedge_method", "subset", "threshold_mode", "hedge_fraction", "cost_gate_mult"]
    family = (
        grid.groupby(family_cols)
        .agg(
            family_median_train_net_bps=("train_net_bps", "median"),
            family_mean_train_net_bps=("train_net_bps", "mean"),
            family_std_train_net_bps=("train_net_bps", "std"),
            family_positive_rate=("train_net_bps", lambda s: float((s > 0).mean())),
        )
        .reset_index()
    )
    grid = grid.merge(family, on=family_cols, how="left")
    grid["family_std_train_net_bps"] = grid["family_std_train_net_bps"].fillna(0.0)
    grid["final_selection_score"] = (
        grid["robust_train_selection_score"].replace(-np.inf, np.nan).fillna(-1e12)
        + 0.50 * grid["family_median_train_net_bps"]
        - 0.15 * grid["family_std_train_net_bps"]
        + 20.0 * grid["family_positive_rate"]
    )
    grid = grid.sort_values("final_selection_score", ascending=False).reset_index(drop=True)
    grid.to_csv(tables / "experiment_rule_grid.csv", index=False)
    family.to_csv(tables / "experiment_family_stability.csv", index=False)

    selected = grid.iloc[0].to_dict()
    active_is_valid = (
        float(selected.get("train_net_bps", 0.0)) > 0
        and float(selected.get("fold_positive_rate", 0.0)) >= 0.50
        and float(selected.get("train_trades", 0.0)) >= min_train_trades
        and np.isfinite(float(selected.get("final_selection_score", -np.inf)))
    )

    decision_rows = []
    if not active_is_valid:
        decision_rows.append(
            {
                "decision": "no_trade",
                "reason": "No active rule passed train-only robustness filters.",
                "selected_strategy": "literature_no_trade",
                "train_net_bps": 0.0,
                "test_net_bps": 0.0,
                "test_trades": 0.0,
            }
        )
    else:
        decision_rows.append(
            {
                "decision": "active_rule",
                "reason": "Best rule passed train-only robustness filters; March remains honest OOS.",
                "selected_strategy": selected["strategy"],
                "train_net_bps": selected["train_net_bps"],
                "test_net_bps": selected["test_net_bps"],
                "test_trades": selected["test_trades"],
            }
        )

    decision_rows.append(
        {
            "decision": "benchmark",
            "reason": "Transaction-cost no-trade benchmark.",
            "selected_strategy": "literature_no_trade",
            "train_net_bps": 0.0,
            "test_net_bps": 0.0,
            "test_trades": 0.0,
        }
    )
    decision = pd.DataFrame(decision_rows)
    decision.to_csv(tables / "experiment_selected_decision.csv", index=False)

    if best_frame is not None and active_is_valid:
        best_frame.to_parquet(processed / "experiment_selected_backtest.parquet")
        if not no_plots:
            plt.figure(figsize=(10, 4.8))
            plt.plot(best_frame.index, best_frame["cum_net_bps"], label="selected active rule")
            plt.axvline(test_start, color="black", linestyle="--", linewidth=1.0, label="test start")
            plt.axhline(0, color="black", linewidth=0.8)
            plt.title("Selected Walk-Forward Rule: Cumulative Net P&L")
            plt.ylabel("basis points of ETF notional")
            plt.legend()
            plt.tight_layout()
            plt.savefig(figures / "experiment_selected_cumulative_net.png", dpi=180)
            plt.close()

    write_memo(tables, test_start, grid, decision)
    return decision


def write_memo(tables: Path, test_start: pd.Timestamp, grid: pd.DataFrame, decision: pd.DataFrame) -> None:
    top_cols = [
        "strategy",
        "signal_view",
        "hedge_method",
        "subset",
        "threshold_mode",
        "entry",
        "exit_band",
        "hedge_fraction",
        "cost_gate_mult",
        "train_trades",
        "train_net_bps",
        "fold_positive_rate",
        "test_trades",
        "test_net_bps",
        "final_selection_score",
    ]
    top = grid[top_cols].head(10).to_markdown(index=False)
    dec = decision.to_markdown(index=False)
    text = f"""# XLK Experiment Suite Memo

Test start: `{test_start.date()}`.

This run selects only from pre-test data.  The March/test columns are reported after selection and must not be used to choose another model.

## Selected decision

{dec}

## Top train-selected active rules

{top}

## Interpretation checklist

- If the selected decision is `no_trade`, the optimizer did its job: it refused to force a trade when the train-only evidence was not robust enough.
- If an active rule has positive March P&L but weak/negative training performance, keep it as a post-mortem diagnostic only.
- A positive active rule is more credible when train net, fold median net, and March net are all positive with moderate turnover and costs below gross edge.
"""
    (tables.parent / "experiment_suite_memo.md").write_text(text)


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    decision = run_experiments(
        root=root,
        panel_path=args.panel.resolve() if args.panel else None,
        test_start=pd.Timestamp(args.test_start),
        min_subset_size=args.min_subset_size,
        max_subset_size=args.max_subset_size,
        min_train_trades=args.min_train_trades,
        max_train_trades=args.max_train_trades,
        ffill_limit=args.ffill_limit,
        return_clip_bps=args.return_clip_bps,
        top_candidates=args.top_candidates,
        quick=args.quick,
        no_plots=args.no_plots,
    )
    print("[experiment-suite] selected decision")
    print(decision.to_string(index=False))


if __name__ == "__main__":
    main()
