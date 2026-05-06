#!/usr/bin/env python3
"""Robust XLK optimizer and sanity-test suite.

This is a second-stage optimizer for the TRiS65/MarketMaking_StatisticalArbitrage
repository.  It deliberately separates two claims:

1. Market-neutral ETF-basket arbitrage:
   trade XLK against a synthetic sparse basket and pay both ETF and constituent
   spread costs.
2. XLK-only timing:
   use the sparse basket microprice premium as a fair-value signal, but execute
   only XLK.  This can be profitable, but it is not market-neutral ETF arbitrage.

The suite follows the design lessons from the IMC Prosperity basket write-up:
fixed thresholds are tested alongside z-scores, parameter "islands" are preferred
over single peaks, persistent premiums are removed with a running center, partial
hedges are allowed, and no-trade remains an explicit benchmark.

Inputs:
    data/processed/research_panel.parquet
    output/tables/selected_xlk_holdings.csv   optional, for official weights

Outputs:
    output/tables/robust_alpha_candidates.csv
    output/tables/robust_alpha_grid.csv
    output/tables/robust_alpha_family_stability.csv
    output/tables/robust_alpha_selection.csv
    output/tables/robust_alpha_controls.csv
    output/tables/robust_alpha_cost_sensitivity.csv
    output/robust_alpha_memo.md
    output/figures/robust_alpha_selected_cumulative.png

Example:
    python3 scripts/run_robust_alpha_suite.py --root . --quick
    python3 scripts/run_robust_alpha_suite.py --root . --top-candidates 40 --n-shifts 500
"""

from __future__ import annotations

import argparse
import itertools
import math
import warnings
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller

from project_config import ETF, constituents as project_constituents, split_dates, symbols as project_symbols

CONSTITUENTS = project_constituents()
SYMBOLS = project_symbols()
MINUTES_PER_DAY = 390
ANN_FACTOR = 252 * MINUTES_PER_DAY
CURRENT_REPO_SPARSE = ("MSFT", "NVDA", "ORCL", "CRM", "AMD")


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
    threshold_mode: str       # fixed_bps or zscore
    center_mode: str          # mean, median, ewma
    entry: float
    exit_band: float
    hedge_fraction: float     # 0 = XLK-only timing; 1 = full residual hedge
    orientation: int          # +1 = contrarian residual; -1 = flipped
    cost_gate_mult: float
    center_window: int
    trade_start: str
    trade_end: str
    max_hold_minutes: int

    @property
    def family(self) -> str:
        return "xlk_only_timing" if self.hedge_fraction == 0 else "partial_or_full_hedge"

    @property
    def name(self) -> str:
        gate = "nogate" if self.cost_gate_mult <= 0 else f"gate{self.cost_gate_mult:g}"
        side = "contra" if self.orientation == 1 else "flip"
        return (
            f"{self.family}_{self.candidate.signal_view}_{self.candidate.hedge_method}_"
            f"k{len(self.candidate.subset)}_{self.threshold_mode}_{self.center_mode}_"
            f"e{self.entry:g}_x{self.exit_band:g}_h{self.hedge_fraction:g}_"
            f"{side}_{gate}_cw{self.center_window}_mh{self.max_hold_minutes}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Robust optimizer for XLK sparse-basket signals")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--panel", type=Path, default=None)
    parser.add_argument("--test-start", type=str, default=None)
    parser.add_argument("--min-subset-size", type=int, default=2)
    parser.add_argument("--max-subset-size", type=int, default=6)
    parser.add_argument("--top-candidates", type=int, default=30)
    parser.add_argument("--min-train-trades", type=int, default=8)
    parser.add_argument("--max-train-trades", type=int, default=250)
    parser.add_argument("--ffill-limit", type=int, default=5)
    parser.add_argument("--return-clip-bps", type=float, default=500.0)
    parser.add_argument("--n-shifts", type=int, default=300)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--no-plots", action="store_true")
    return parser.parse_args()


def ensure_dirs(root: Path) -> tuple[Path, Path, Path, Path]:
    output = root / "output"
    tables = output / "tables"
    figures = output / "figures"
    processed = root / "data" / "processed"
    for path in [output, tables, figures, processed]:
        path.mkdir(parents=True, exist_ok=True)
    return output, tables, figures, processed


def load_panel(root: Path, panel_path: Path | None) -> pd.DataFrame:
    path = panel_path or (root / "data" / "processed" / "research_panel.parquet")
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run scripts/build_dataset.py first, or pass --panel /path/to/research_panel.parquet."
        )
    panel = pd.read_parquet(path)
    needed = {"minute", "symbol", "mid", "microprice", "spread_bps"}
    missing = needed - set(panel.columns)
    if missing:
        raise ValueError(f"research_panel.parquet is missing columns: {sorted(missing)}")
        panel = panel[panel["symbol"].isin(SYMBOLS)].copy()
    panel["minute"] = pd.to_datetime(panel["minute"])
    return panel.sort_values(["symbol", "minute"])


def pivot(panel: pd.DataFrame, column: str) -> pd.DataFrame:
    if column not in panel.columns:
        return pd.DataFrame()
    return panel.pivot(index="minute", columns="symbol", values=column).sort_index()


def align_intraday(frame: pd.DataFrame, ffill_limit: int) -> pd.DataFrame:
    dates = sorted(pd.Series(frame.index.date.astype(str)).unique())
    if not dates:
        return frame
    parts = [pd.date_range(pd.Timestamp(f"{d} 09:30:00"), periods=MINUTES_PER_DAY, freq="min") for d in dates]
    full_index = parts[0].append(parts[1:]) if len(parts) > 1 else parts[0]
    aligned = frame.reindex(full_index)
    day_key = pd.Series(aligned.index.date.astype(str), index=aligned.index)
    return aligned.groupby(day_key, group_keys=False).ffill(limit=ffill_limit)


def make_views(panel: pd.DataFrame, ffill_limit: int) -> dict[str, pd.DataFrame]:
    raw = {c: pivot(panel, c) for c in ["mid", "microprice", "spread_bps", "bidsiz", "asksiz", "volume"]}
    aligned = {c: align_intraday(df, ffill_limit) for c, df in raw.items() if not df.empty}
    common = aligned["mid"].dropna(subset=SYMBOLS).index
    for c in list(aligned):
        aligned[c] = aligned[c].loc[common].astype(float)
    return aligned


def continuous_mask(index: pd.Index) -> pd.Series:
    s = pd.Series(index, index=index)
    return (s.diff() == pd.Timedelta(minutes=1)) & (s.dt.date == s.shift(1).dt.date)


def clean_returns(price: pd.DataFrame, clip_bps: float) -> pd.DataFrame:
    ret = np.log(price.astype(float)).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    ret.loc[~continuous_mask(price.index).values, :] = 0.0
    clip = clip_bps / 1e4
    return ret.clip(-clip, clip)


def signal_price_views(views: dict[str, pd.DataFrame], quick: bool) -> dict[str, pd.DataFrame]:
    """Build fair-value signal prices without treating microprice as executable."""
    mid = views["mid"]
    micro = views["microprice"]
    gap = np.log(micro / mid).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    out: dict[str, pd.DataFrame] = {"mid": mid}

    spread = views.get("spread_bps", pd.DataFrame(1.0, index=mid.index, columns=mid.columns))
    spread_conf = (1.0 / (1.0 + (spread / 10.0).clip(lower=0.0))).clip(0.0, 1.0)

    if "bidsiz" in views and "asksiz" in views:
        total = views["bidsiz"] + views["asksiz"]
        base = total.rolling(MINUTES_PER_DAY, min_periods=60).median().shift(1)
        size_conf = (total / base).replace([np.inf, -np.inf], np.nan).clip(0.0, 2.0) / 2.0
        size_conf = size_conf.fillna(0.5)
    else:
        size_conf = pd.DataFrame(0.5, index=mid.index, columns=mid.columns)

    confidence = (spread_conf * size_conf).clip(0.0, 1.0).fillna(0.25)
    shrinkages = [0.50] if quick else [0.25, 0.50, 0.75, 1.00]
    for shrink in shrinkages:
        out[f"micro_shrink_{shrink:g}"] = mid * np.exp(gap * shrink)
        out[f"micro_conf_{shrink:g}"] = mid * np.exp(gap * shrink * confidence)
    return out


def load_official_weights(root: Path) -> pd.Series | None:
    candidates = [
        root / "output" / "tables" / "selected_xlk_holdings.csv",
        root / "selected_xlk_holdings.csv",
        Path("/mnt/data/selected_xlk_holdings.csv"),
    ]
    for path in candidates:
        if path.exists():
            df = pd.read_csv(path)
            if {"symbol", "basket_weight"}.issubset(df.columns):
                return df.set_index("symbol")["basket_weight"].reindex(CONSTITUENTS).dropna().astype(float)
    return None


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
        raw = official_weights.loc[list(subset)].to_numpy(float)
        if raw.sum() <= 0:
            return None
        return tuple((raw / raw.sum()).tolist())

    x = (1e4 * ret.loc[train_mask, list(subset)]).clip(-500, 500).to_numpy(float)
    y = (1e4 * ret.loc[train_mask, ETF]).clip(-500, 500).to_numpy(float)
    valid = np.isfinite(x).all(axis=1) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if len(y) < 1000:
        return None

    ridge = 1e-2 if method == "ridge_pos" else 5e-2
    try:
        beta = np.linalg.solve((x.T @ x) / len(y) + ridge * np.eye(len(subset)), (x.T @ y) / len(y))
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
    x = np.nan_to_num(ret.loc[:, list(subset)].to_numpy(float), nan=0.0, posinf=0.0, neginf=0.0)
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        hedge = x @ b
    hedge = np.nan_to_num(hedge, nan=0.0, posinf=0.0, neginf=0.0)
    base = np.nan_to_num(ret[ETF].to_numpy(float), nan=0.0, posinf=0.0, neginf=0.0)
    return pd.Series(base - hedge, index=ret.index)


def one_way_cost_ret(spread_bps: pd.DataFrame, subset: tuple[str, ...], beta: Iterable[float], hedge_fraction: float) -> pd.Series:
    cost_bps = spread_bps[ETF].astype(float) / 2.0
    for s, b in zip(subset, beta):
        cost_bps = cost_bps + abs(float(b) * hedge_fraction) * spread_bps[s].astype(float) / 2.0
    return (cost_bps / 1e4).replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)


def half_life(series: pd.Series) -> float:
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
    top_n: int,
    quick: bool,
) -> tuple[list[CandidateSpec], pd.DataFrame]:
    methods = ["ridge_pos"] if quick else ["ridge_pos", "ridge_pos_sum1", "official_subset"]
    signal_names = list(signal_returns.keys())
    if quick:
        signal_names = [name for name in signal_names if name in {"mid", "micro_shrink_0.5", "micro_conf_0.5"}]

    # Searching all 2-6 name subsets of top20 is not laptop-friendly.  Keep the
    # optimizer on the largest holdings while pair/diagnostic scripts still audit
    # every top20 name individually.
    search_universe = CONSTITUENTS[:12]
    if quick:
        preset = [
            tuple(search_universe[:3]),
            tuple(search_universe[:4]),
            tuple(search_universe[:5]),
            tuple(s for s in ("NVDA", "AMD", "PLTR") if s in search_universe),
            tuple(s for s in ("NVDA", "AMD", "PLTR", "LRCX", "AMAT") if s in search_universe),
        ]
        subset_pool = [p for p in preset if min_size <= len(p) <= max_size]
    else:
        subset_pool = []
        for k in range(min_size, max_size + 1):
            subset_pool.extend(itertools.combinations(search_universe, k))
    if set(CURRENT_REPO_SPARSE).issubset(set(CONSTITUENTS)) and CURRENT_REPO_SPARSE not in subset_pool:
        subset_pool.append(CURRENT_REPO_SPARSE)

    rows: list[dict] = []
    specs: dict[tuple[str, str, str, str], CandidateSpec] = {}
    for signal_view in signal_names:
        ret = signal_returns[signal_view]
        for subset in subset_pool:
            for method in methods:
                beta = estimate_beta(ret, subset, train_mask, method, official_weights)
                if beta is None:
                    continue
                spread = residual_ret(ret, subset, beta, 1.0).cumsum()
                train_spread = spread.loc[train_mask]
                adf = adf_pvalue(train_spread)
                hl = half_life(train_spread)
                std_bps = float(1e4 * train_spread.std())
                cost_bps = float(1e4 * one_way_cost_ret(spread_bps, subset, beta, 1.0).loc[train_mask].mean())
                if not np.isfinite(adf) or not np.isfinite(hl) or not np.isfinite(std_bps) or std_bps <= 0:
                    continue
                score = adf + 0.00035 * hl + 0.00050 * std_bps + 0.025 * cost_bps
                spec = CandidateSpec(signal_view, method, subset, beta)
                key = (signal_view, method, spec.subset_text, spec.beta_text)
                specs[key] = spec
                rows.append(
                    {
                        "signal_view": signal_view,
                        "hedge_method": method,
                        "subset": spec.subset_text,
                        "k": len(subset),
                        "betas": spec.beta_text,
                        "sum_beta": float(np.sum(beta)),
                        "train_adf_p": adf,
                        "train_half_life_minutes": hl,
                        "train_std_bps": std_bps,
                        "full_hedge_avg_oneway_cost_bps": cost_bps,
                        "candidate_score_low_is_good": score,
                    }
                )

    table = pd.DataFrame(rows)
    if table.empty:
        return [], table
    table = table.sort_values("candidate_score_low_is_good").reset_index(drop=True)
    candidates = []
    for _, row in table.head(top_n).iterrows():
        key = (row["signal_view"], row["hedge_method"], row["subset"], row["betas"])
        candidates.append(specs[key])
    return candidates, table


def center_and_score(spread: pd.Series, threshold_mode: str, center_mode: str, window: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    minp = max(60, min(window // 2, MINUTES_PER_DAY))
    if center_mode == "mean":
        center = spread.rolling(window, min_periods=minp).mean().shift(1)
    elif center_mode == "median":
        center = spread.rolling(window, min_periods=minp).median().shift(1)
    elif center_mode == "ewma":
        center = spread.ewm(span=window, adjust=False, min_periods=minp).mean().shift(1)
    else:
        raise ValueError(f"unknown center mode {center_mode}")

    deviation = spread - center
    if threshold_mode == "fixed_bps":
        score = 1e4 * deviation
    elif threshold_mode == "zscore":
        mad = deviation.abs().rolling(window, min_periods=minp).median().shift(1)
        robust_std = (1.4826 * mad).replace(0.0, np.nan)
        score = deviation / robust_std
    else:
        raise ValueError(f"unknown threshold mode {threshold_mode}")
    return center, deviation, score


def build_position(
    score: pd.Series,
    deviation: pd.Series,
    cost: pd.Series,
    rule: RuleSpec,
) -> pd.Series:
    dates = pd.Series(score.index.date.astype(str), index=score.index)
    tod = pd.Series(score.index.strftime("%H:%M"), index=score.index)
    tradable = (tod >= rule.trade_start) & (tod <= rule.trade_end)
    pos = np.zeros(len(score), dtype=float)
    current = 0.0
    entry_i = -1

    sv = score.to_numpy(float)
    dv = deviation.to_numpy(float)
    cv = cost.to_numpy(float)

    for i, val in enumerate(sv):
        if i > 0 and dates.iloc[i] != dates.iloc[i - 1]:
            current = 0.0
            entry_i = -1

        if not tradable.iloc[i]:
            if current != 0.0 and tod.iloc[i] > rule.trade_end:
                current = 0.0
                entry_i = -1
            pos[i] = current
            continue

        if np.isfinite(val):
            dev_bps = abs(dv[i]) * 1e4 if np.isfinite(dv[i]) else 0.0
            roundtrip_cost_bps = 2.0 * 1e4 * cv[i] if np.isfinite(cv[i]) else np.inf
            allowed = rule.cost_gate_mult <= 0 or dev_bps > rule.cost_gate_mult * roundtrip_cost_bps

            # Base contrarian rule:
            #   spread premium > threshold -> short residual;
            #   spread discount < -threshold -> long residual.
            high_entry = -1.0 * rule.orientation
            low_entry = 1.0 * rule.orientation

            if current == 0.0 and allowed:
                if val > rule.entry:
                    current = high_entry
                    entry_i = i
                elif val < -rule.entry:
                    current = low_entry
                    entry_i = i
            elif current > 0:
                if val > -rule.exit_band or (rule.max_hold_minutes > 0 and i - entry_i >= rule.max_hold_minutes):
                    current = 0.0
                    entry_i = -1
            elif current < 0:
                if val < rule.exit_band or (rule.max_hold_minutes > 0 and i - entry_i >= rule.max_hold_minutes):
                    current = 0.0
                    entry_i = -1

        if i < len(score) - 1 and dates.iloc[i + 1] != dates.iloc[i]:
            current = 0.0
            entry_i = -1
        pos[i] = current

    return pd.Series(pos, index=score.index)


def make_frame(
    rule: RuleSpec,
    signal_returns: dict[str, pd.DataFrame],
    exec_ret: pd.DataFrame,
    spread_bps: pd.DataFrame,
    test_start: pd.Timestamp,
    cost_multiplier: float = 1.0,
    override_position: pd.Series | None = None,
) -> pd.DataFrame:
    cand = rule.candidate
    signal_spread = residual_ret(signal_returns[cand.signal_view], cand.subset, cand.beta, 1.0).cumsum()
    exec_res = residual_ret(exec_ret, cand.subset, cand.beta, rule.hedge_fraction)
    one_way = one_way_cost_ret(spread_bps, cand.subset, cand.beta, rule.hedge_fraction)
    center, deviation, score = center_and_score(signal_spread, rule.threshold_mode, rule.center_mode, rule.center_window)
    position = build_position(score, deviation, one_way, rule) if override_position is None else override_position.reindex(score.index).fillna(0.0)
    turnover = position.diff().abs().fillna(position.abs())
    gross = position.shift(1).fillna(0.0) * exec_res
    cost = cost_multiplier * turnover * one_way
    net = gross - cost

    frame = pd.DataFrame(
        {
            "signal_spread": signal_spread,
            "center": center,
            "deviation": deviation,
            "score": score,
            "position": position,
            "turnover": turnover,
            "gross_ret": gross,
            "cost_ret": cost,
            "net_ret": net,
            "sample": np.where(signal_spread.index < test_start, "train", "test"),
        },
        index=signal_spread.index,
    )
    frame["cum_net_bps"] = 1e4 * frame["net_ret"].cumsum()
    return frame


def max_drawdown_bps(net_ret: pd.Series) -> float:
    pnl = 1e4 * net_ret.cumsum()
    return float((pnl - pnl.cummax()).min()) if len(pnl) else 0.0


def sharpe_ann(net_ret: pd.Series) -> float:
    std = net_ret.std()
    if not np.isfinite(std) or std <= 0:
        return np.nan
    return float(np.sqrt(ANN_FACTOR) * net_ret.mean() / std)


def period_metrics(frame: pd.DataFrame, sample: str) -> dict[str, float]:
    part = frame[frame["sample"] == sample]
    if part.empty:
        return {
            f"{sample}_observations": 0,
            f"{sample}_trades": 0.0,
            f"{sample}_avg_abs_position": 0.0,
            f"{sample}_gross_bps": 0.0,
            f"{sample}_cost_bps": 0.0,
            f"{sample}_net_bps": 0.0,
            f"{sample}_sharpe_ann": np.nan,
            f"{sample}_max_drawdown_bps": 0.0,
            f"{sample}_long_gross_bps": 0.0,
            f"{sample}_short_gross_bps": 0.0,
        }
    prev_pos = part["position"].shift(1).fillna(0.0)
    return {
        f"{sample}_observations": int(len(part)),
        f"{sample}_trades": float((part["turnover"] > 0).sum()),
        f"{sample}_avg_abs_position": float(part["position"].abs().mean()),
        f"{sample}_gross_bps": float(1e4 * part["gross_ret"].sum()),
        f"{sample}_cost_bps": float(1e4 * part["cost_ret"].sum()),
        f"{sample}_net_bps": float(1e4 * part["net_ret"].sum()),
        f"{sample}_sharpe_ann": sharpe_ann(part["net_ret"]),
        f"{sample}_max_drawdown_bps": max_drawdown_bps(part["net_ret"]),
        f"{sample}_long_gross_bps": float(1e4 * part.loc[prev_pos > 0, "gross_ret"].sum()),
        f"{sample}_short_gross_bps": float(1e4 * part.loc[prev_pos < 0, "gross_ret"].sum()),
    }


def fold_metrics(train_frame: pd.DataFrame, n_folds: int = 4) -> dict[str, float]:
    if train_frame.empty:
        return {"fold_median_net_bps": 0.0, "fold_min_net_bps": 0.0, "fold_std_net_bps": 0.0, "fold_positive_rate": 0.0}
    dates = pd.Index(sorted(pd.Series(train_frame.index.date.astype(str)).unique()))
    pieces = np.array_split(dates.to_numpy(), min(n_folds, max(1, len(dates))))
    vals = []
    for arr in pieces:
        day_mask = pd.Series(train_frame.index.date.astype(str), index=train_frame.index).isin(arr)
        vals.append(float(1e4 * train_frame.loc[day_mask, "net_ret"].sum()))
    x = np.asarray(vals, float)
    return {
        "fold_median_net_bps": float(np.median(x)),
        "fold_min_net_bps": float(np.min(x)),
        "fold_std_net_bps": float(np.std(x, ddof=1)) if len(x) > 1 else 0.0,
        "fold_positive_rate": float((x > 0).mean()),
    }


def month_metrics(frame: pd.DataFrame) -> dict[str, float]:
    train = frame[frame["sample"] == "train"]
    if train.empty:
        return {"train_month_positive_rate": 0.0, "train_month_min_net_bps": 0.0, "train_month_median_net_bps": 0.0}
    month = pd.Series(train.index.to_period("M").astype(str), index=train.index)
    vals = train.groupby(month)["net_ret"].sum() * 1e4
    return {
        "train_month_positive_rate": float((vals > 0).mean()) if len(vals) else 0.0,
        "train_month_min_net_bps": float(vals.min()) if len(vals) else 0.0,
        "train_month_median_net_bps": float(vals.median()) if len(vals) else 0.0,
    }


def summarize(rule: RuleSpec, frame: pd.DataFrame) -> dict:
    out: dict[str, object] = {
        "strategy": rule.name,
        "family": rule.family,
        "signal_view": rule.candidate.signal_view,
        "hedge_method": rule.candidate.hedge_method,
        "subset": rule.candidate.subset_text,
        "betas": rule.candidate.beta_text,
        "threshold_mode": rule.threshold_mode,
        "center_mode": rule.center_mode,
        "entry": rule.entry,
        "exit_band": rule.exit_band,
        "hedge_fraction": rule.hedge_fraction,
        "orientation": rule.orientation,
        "cost_gate_mult": rule.cost_gate_mult,
        "center_window": rule.center_window,
        "trade_start": rule.trade_start,
        "trade_end": rule.trade_end,
        "max_hold_minutes": rule.max_hold_minutes,
    }
    out.update(period_metrics(frame, "train"))
    out.update(period_metrics(frame, "test"))
    out.update(fold_metrics(frame[frame["sample"] == "train"]))
    out.update(month_metrics(frame))
    return out


def build_rules(candidates: list[CandidateSpec], quick: bool) -> list[RuleSpec]:
    if quick:
        fixed_entries = [50.0]
        fixed_exits = [25.0]
        z_entries = [3.0]
        z_exits = [0.5]
        hedge_fractions = [0.0, 1.0]
        center_modes = ["mean"]
        windows = [MINUTES_PER_DAY * 5]
        gates = [0.0]
        holds = [180]
        orientations = [1, -1]
    else:
        fixed_entries = [25.0, 35.0, 50.0, 65.0, 80.0, 110.0]
        fixed_exits = [0.0, 15.0, 25.0, 35.0]
        z_entries = [2.5, 3.0, 3.5, 4.0]
        z_exits = [0.0, 0.5, 1.0]
        hedge_fractions = [0.0, 0.25, 0.5, 0.75, 1.0]
        center_modes = ["mean", "median", "ewma"]
        windows = [MINUTES_PER_DAY * 3, MINUTES_PER_DAY * 5, MINUTES_PER_DAY * 10]
        gates = [0.0, 1.0, 1.5, 2.0]
        holds = [0, 90, 180, 300]
        orientations = [1, -1]

    rules: list[RuleSpec] = []
    for cand in candidates:
        for center_mode in center_modes:
            for window in windows:
                for hedge_fraction in hedge_fractions:
                    for gate in gates:
                        for hold in holds:
                            for orientation in orientations:
                                for entry in fixed_entries:
                                    for exit_band in fixed_exits:
                                        if exit_band >= entry:
                                            continue
                                        rules.append(
                                            RuleSpec(
                                                candidate=cand,
                                                threshold_mode="fixed_bps",
                                                center_mode=center_mode,
                                                entry=entry,
                                                exit_band=exit_band,
                                                hedge_fraction=hedge_fraction,
                                                orientation=orientation,
                                                cost_gate_mult=gate,
                                                center_window=window,
                                                trade_start="09:35",
                                                trade_end="15:45",
                                                max_hold_minutes=hold,
                                            )
                                        )
                                for entry in z_entries:
                                    for exit_band in z_exits:
                                        if exit_band >= entry:
                                            continue
                                        rules.append(
                                            RuleSpec(
                                                candidate=cand,
                                                threshold_mode="zscore",
                                                center_mode=center_mode,
                                                entry=entry,
                                                exit_band=exit_band,
                                                hedge_fraction=hedge_fraction,
                                                orientation=orientation,
                                                cost_gate_mult=gate,
                                                center_window=window,
                                                trade_start="09:35",
                                                trade_end="15:45",
                                                max_hold_minutes=hold,
                                            )
                                        )
    return rules


def base_selection_score(row: dict, min_trades: int, max_trades: int) -> float:
    trades = float(row.get("train_trades", 0.0))
    if trades < min_trades or trades > max_trades:
        return -np.inf
    train_net = float(row.get("train_net_bps", 0.0))
    fold_median = float(row.get("fold_median_net_bps", 0.0))
    fold_min = float(row.get("fold_min_net_bps", 0.0))
    fold_std = float(row.get("fold_std_net_bps", 0.0))
    month_median = float(row.get("train_month_median_net_bps", 0.0))
    month_min = float(row.get("train_month_min_net_bps", 0.0))
    month_positive = float(row.get("train_month_positive_rate", 0.0))
    fold_positive = float(row.get("fold_positive_rate", 0.0))
    dd = float(row.get("train_max_drawdown_bps", 0.0))  # negative
    cost = float(row.get("train_cost_bps", 0.0))
    return (
        0.45 * train_net
        + 0.80 * fold_median
        + 0.35 * fold_min
        + 0.35 * month_median
        + 0.25 * month_min
        + 30.0 * fold_positive
        + 40.0 * month_positive
        - 0.30 * fold_std
        + 0.20 * dd
        - 0.04 * cost
    )


def evaluate_grid(
    rules: list[RuleSpec],
    signal_returns: dict[str, pd.DataFrame],
    exec_ret: pd.DataFrame,
    spread_bps: pd.DataFrame,
    test_start: pd.Timestamp,
    min_train_trades: int,
    max_train_trades: int,
) -> tuple[pd.DataFrame, dict[str, RuleSpec]]:
    rows: list[dict] = []
    lookup: dict[str, RuleSpec] = {}
    for i, rule in enumerate(rules, start=1):
        try:
            frame = make_frame(rule, signal_returns, exec_ret, spread_bps, test_start)
            row = summarize(rule, frame)
            row["base_train_selection_score"] = base_selection_score(row, min_train_trades, max_train_trades)
            rows.append(row)
            lookup[rule.name] = rule
        except Exception as exc:
            warnings.warn(f"Skipping {rule.name}: {exc}")
        if i % 1000 == 0:
            print(f"[grid] evaluated {i:,}/{len(rules):,} rule specs")
    grid = pd.DataFrame(rows)
    if grid.empty:
        raise RuntimeError("No rules completed. Check data or lower filters.")
    family_cols = [
        "family",
        "signal_view",
        "hedge_method",
        "subset",
        "threshold_mode",
        "center_mode",
        "hedge_fraction",
        "orientation",
        "cost_gate_mult",
    ]
    family = (
        grid.groupby(family_cols)
        .agg(
            family_median_train_net_bps=("train_net_bps", "median"),
            family_mean_train_net_bps=("train_net_bps", "mean"),
            family_std_train_net_bps=("train_net_bps", "std"),
            family_positive_rate=("train_net_bps", lambda x: float((x > 0).mean())),
            family_rule_count=("train_net_bps", "size"),
        )
        .reset_index()
    )
    grid = grid.merge(family, on=family_cols, how="left")
    grid["family_std_train_net_bps"] = grid["family_std_train_net_bps"].fillna(0.0)
    grid["final_train_selection_score"] = (
        grid["base_train_selection_score"].replace(-np.inf, np.nan).fillna(-1e12)
        + 0.55 * grid["family_median_train_net_bps"]
        + 25.0 * grid["family_positive_rate"]
        - 0.12 * grid["family_std_train_net_bps"]
    )
    grid = grid.sort_values("final_train_selection_score", ascending=False).reset_index(drop=True)
    return grid, lookup


def rule_passes(row: pd.Series, min_train_trades: int) -> tuple[bool, str]:
    if not np.isfinite(float(row.get("final_train_selection_score", -np.inf))):
        return False, "selection score is not finite"
    if float(row.get("train_trades", 0.0)) < min_train_trades:
        return False, "not enough train trades"
    if float(row.get("train_net_bps", 0.0)) <= 0:
        return False, "train net P&L is not positive"
    if float(row.get("fold_positive_rate", 0.0)) < 0.50:
        return False, "too few positive train folds"
    if float(row.get("train_month_positive_rate", 0.0)) < 0.50:
        return False, "too few positive train months"
    if float(row.get("family_positive_rate", 0.0)) < 0.45:
        return False, "parameter family is not stable"
    return True, "passed train-only robustness filters"


def shift_position_within_days(position: pd.Series, rng: np.random.Generator) -> pd.Series:
    out_parts = []
    date_key = pd.Series(position.index.date.astype(str), index=position.index)
    for _, part in position.groupby(date_key):
        values = part.to_numpy(float)
        if len(values) <= 1:
            out_parts.append(part)
            continue
        shift = int(rng.integers(1, len(values)))
        out_parts.append(pd.Series(np.roll(values, shift), index=part.index))
    return pd.concat(out_parts).sort_index()


def recompute_with_position(base_frame: pd.DataFrame, exec_res: pd.Series, one_way: pd.Series, position: pd.Series, test_start: pd.Timestamp, cost_multiplier: float = 1.0) -> pd.DataFrame:
    pos = position.reindex(base_frame.index).fillna(0.0)
    turnover = pos.diff().abs().fillna(pos.abs())
    gross = pos.shift(1).fillna(0.0) * exec_res.reindex(base_frame.index).fillna(0.0)
    cost = cost_multiplier * turnover * one_way.reindex(base_frame.index).fillna(0.0)
    net = gross - cost
    frame = base_frame.copy()
    frame["position"] = pos
    frame["turnover"] = turnover
    frame["gross_ret"] = gross
    frame["cost_ret"] = cost
    frame["net_ret"] = net
    frame["sample"] = np.where(frame.index < test_start, "train", "test")
    frame["cum_net_bps"] = 1e4 * frame["net_ret"].cumsum()
    return frame


def selected_control_tables(
    rule: RuleSpec,
    selected_frame: pd.DataFrame,
    signal_returns: dict[str, pd.DataFrame],
    exec_ret: pd.DataFrame,
    spread_bps: pd.DataFrame,
    test_start: pd.Timestamp,
    n_shifts: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cand = rule.candidate
    exec_res = residual_ret(exec_ret, cand.subset, cand.beta, rule.hedge_fraction)
    one_way = one_way_cost_ret(spread_bps, cand.subset, cand.beta, rule.hedge_fraction)
    pos = selected_frame["position"]

    controls = []
    def add_control(name: str, frame: pd.DataFrame) -> None:
        controls.append(
            {
                "control": name,
                "train_net_bps": float(1e4 * frame.loc[frame["sample"] == "train", "net_ret"].sum()),
                "test_net_bps": float(1e4 * frame.loc[frame["sample"] == "test", "net_ret"].sum()),
                "test_trades": float((frame.loc[frame["sample"] == "test", "turnover"] > 0).sum()),
                "test_avg_abs_position": float(frame.loc[frame["sample"] == "test", "position"].abs().mean()),
            }
        )

    add_control("selected", selected_frame)
    add_control("sign_flip", recompute_with_position(selected_frame, exec_res, one_way, -pos, test_start))
    add_control("active_always_long", recompute_with_position(selected_frame, exec_res, one_way, pos.abs(), test_start))
    add_control("active_always_short", recompute_with_position(selected_frame, exec_res, one_way, -pos.abs(), test_start))

    rng = np.random.default_rng(seed)
    shift_test_nets = []
    for j in range(n_shifts):
        shifted = shift_position_within_days(pos, rng)
        f = recompute_with_position(selected_frame, exec_res, one_way, shifted, test_start)
        shift_test_nets.append(float(1e4 * f.loc[f["sample"] == "test", "net_ret"].sum()))
    selected_test = float(1e4 * selected_frame.loc[selected_frame["sample"] == "test", "net_ret"].sum())
    shift_arr = np.asarray(shift_test_nets, dtype=float)
    p_value = float((1 + np.sum(shift_arr >= selected_test)) / (len(shift_arr) + 1)) if len(shift_arr) else np.nan
    controls.extend(
        [
            {"control": "circular_shift_mean", "train_net_bps": np.nan, "test_net_bps": float(np.mean(shift_arr)) if len(shift_arr) else np.nan, "test_trades": np.nan, "test_avg_abs_position": np.nan},
            {"control": "circular_shift_p95", "train_net_bps": np.nan, "test_net_bps": float(np.percentile(shift_arr, 95)) if len(shift_arr) else np.nan, "test_trades": np.nan, "test_avg_abs_position": np.nan},
            {"control": "selected_vs_circular_pvalue", "train_net_bps": np.nan, "test_net_bps": p_value, "test_trades": np.nan, "test_avg_abs_position": np.nan},
        ]
    )

    cost_rows = []
    for mult in [1.0, 1.5, 2.0, 3.0, 4.0]:
        f = recompute_with_position(selected_frame, exec_res, one_way, pos, test_start, cost_multiplier=mult)
        for sample in ["train", "test"]:
            part = f[f["sample"] == sample]
            cost_rows.append(
                {
                    "cost_multiplier": mult,
                    "sample": sample,
                    "gross_bps": float(1e4 * part["gross_ret"].sum()),
                    "cost_bps": float(1e4 * part["cost_ret"].sum()),
                    "net_bps": float(1e4 * part["net_ret"].sum()),
                }
            )
    return pd.DataFrame(controls), pd.DataFrame(cost_rows)


def write_outputs(
    output: Path,
    tables: Path,
    figures: Path,
    candidates: pd.DataFrame,
    grid: pd.DataFrame,
    family: pd.DataFrame,
    selection: pd.DataFrame,
    controls: pd.DataFrame,
    cost_sens: pd.DataFrame,
    selected_frame: pd.DataFrame | None,
    test_start: pd.Timestamp,
    no_plots: bool,
) -> None:
    candidates.to_csv(tables / "robust_alpha_candidates.csv", index=False)
    grid.to_csv(tables / "robust_alpha_grid.csv", index=False)
    family.to_csv(tables / "robust_alpha_family_stability.csv", index=False)
    selection.to_csv(tables / "robust_alpha_selection.csv", index=False)
    controls.to_csv(tables / "robust_alpha_controls.csv", index=False)
    cost_sens.to_csv(tables / "robust_alpha_cost_sensitivity.csv", index=False)

    if selected_frame is not None and not no_plots:
        plt.figure(figsize=(10, 4.8))
        plt.plot(selected_frame.index, selected_frame["cum_net_bps"], label="selected active rule")
        plt.axvline(test_start, linestyle="--", linewidth=1.0, label="test start")
        plt.axhline(0, linewidth=0.8)
        plt.title("Robust Alpha Suite: Selected Rule Cumulative Net P&L")
        plt.ylabel("basis points of ETF notional")
        plt.legend()
        plt.tight_layout()
        plt.savefig(figures / "robust_alpha_selected_cumulative.png", dpi=180)
        plt.close()

    top_cols = [
        "strategy", "family", "signal_view", "subset", "threshold_mode", "center_mode",
        "entry", "exit_band", "hedge_fraction", "orientation", "train_trades",
        "train_net_bps", "train_month_positive_rate", "fold_positive_rate",
        "test_trades", "test_net_bps", "final_train_selection_score",
    ]
    top_text = grid[top_cols].head(12).to_string(index=False)
    memo = f"""# Robust XLK Optimization Memo

Test start: `{test_start.date()}`.

## Selected decision

{selection.to_string(index=False)}

## Top train-selected rules

```
{top_text}
```

## How to read this

The suite distinguishes **market-neutral ETF-basket arbitrage** from **XLK-only timing**.  If the selected rule has `hedge_fraction = 0`, it is a timing strategy that executes only XLK; it should not be marketed as a hedged ETF arbitrage.  If `hedge_fraction > 0`, it trades the residual and pays basket-side spread costs.

The optimizer selects only from train-period evidence.  March/test P&L is reported afterward.  Keep `no_trade` as the decision if no active rule passes train net, fold stability, monthly stability, trade-count, and parameter-family filters.

## Sanity controls

```
{controls.to_string(index=False)}
```

## Cost sensitivity

```
{cost_sens.to_string(index=False)}
```
"""
    (output / "robust_alpha_memo.md").write_text(memo)


def run(args: argparse.Namespace) -> pd.DataFrame:
    root = args.root.resolve()
    output, tables, figures, processed = ensure_dirs(root)
    test_start = pd.Timestamp(args.test_start) if args.test_start else split_dates()[1]
    panel = load_panel(root, args.panel.resolve() if args.panel else None)
    views = make_views(panel, args.ffill_limit)

    prices = signal_price_views(views, quick=args.quick)
    signal_returns = {name: clean_returns(px, args.return_clip_bps) for name, px in prices.items()}
    exec_ret = clean_returns(views["mid"], args.return_clip_bps)
    spread_bps = views["spread_bps"]
    train_mask = exec_ret.index < test_start
    official = load_official_weights(root)

    candidates, cand_table = build_candidates(
        signal_returns=signal_returns,
        spread_bps=spread_bps,
        train_mask=train_mask,
        official_weights=official,
        min_size=args.min_subset_size,
        max_size=args.max_subset_size,
        top_n=args.top_candidates,
        quick=args.quick,
    )
    if not candidates:
        raise RuntimeError("No valid candidates. Check symbol coverage and data quality.")

    rules = build_rules(candidates, quick=args.quick)
    print(f"[setup] candidates={len(candidates)}, rules={len(rules):,}")
    grid, lookup = evaluate_grid(
        rules=rules,
        signal_returns=signal_returns,
        exec_ret=exec_ret,
        spread_bps=spread_bps,
        test_start=test_start,
        min_train_trades=args.min_train_trades,
        max_train_trades=args.max_train_trades,
    )
    family_cols = [
        "family", "signal_view", "hedge_method", "subset", "threshold_mode", "center_mode",
        "hedge_fraction", "orientation", "cost_gate_mult",
    ]
    family = (
        grid.groupby(family_cols)
        .agg(
            family_median_train_net_bps=("train_net_bps", "median"),
            family_mean_train_net_bps=("train_net_bps", "mean"),
            family_std_train_net_bps=("train_net_bps", "std"),
            family_positive_rate=("train_net_bps", lambda x: float((x > 0).mean())),
            family_rule_count=("strategy", "size"),
        )
        .reset_index()
    )

    best = grid.iloc[0]
    active_ok, reason = rule_passes(best, args.min_train_trades)
    selected_frame = None
    controls = pd.DataFrame()
    cost_sens = pd.DataFrame()

    if active_ok:
        selected_rule = lookup[str(best["strategy"])]
        selected_frame = make_frame(selected_rule, signal_returns, exec_ret, spread_bps, test_start)
        selected_frame.to_parquet(processed / "robust_alpha_selected_backtest.parquet")
        controls, cost_sens = selected_control_tables(
            rule=selected_rule,
            selected_frame=selected_frame,
            signal_returns=signal_returns,
            exec_ret=exec_ret,
            spread_bps=spread_bps,
            test_start=test_start,
            n_shifts=args.n_shifts if not args.quick else min(args.n_shifts, 100),
            seed=args.seed,
        )
        decision = "active_rule"
        selected_strategy = str(best["strategy"])
        train_net = float(best["train_net_bps"])
        test_net = float(best["test_net_bps"])
    else:
        decision = "no_trade"
        selected_strategy = "literature_no_trade"
        train_net = 0.0
        test_net = 0.0
        controls = pd.DataFrame(
            [{"control": "no_active_rule_selected", "train_net_bps": 0.0, "test_net_bps": 0.0, "test_trades": 0.0, "test_avg_abs_position": 0.0}]
        )
        cost_sens = pd.DataFrame(
            [{"cost_multiplier": m, "sample": s, "gross_bps": 0.0, "cost_bps": 0.0, "net_bps": 0.0} for m in [1.0, 1.5, 2.0, 3.0, 4.0] for s in ["train", "test"]]
        )

    selection = pd.DataFrame(
        [
            {
                "decision": decision,
                "selected_strategy": selected_strategy,
                "reason": reason,
                "train_net_bps": train_net,
                "test_net_bps": test_net,
                "benchmark_no_trade_train_bps": 0.0,
                "benchmark_no_trade_test_bps": 0.0,
                "economic_label": "XLK-only timing" if active_ok and float(best["hedge_fraction"]) == 0 else ("market-neutral/partial hedge" if active_ok else "no-trade"),
            }
        ]
    )

    write_outputs(
        output=output,
        tables=tables,
        figures=figures,
        candidates=cand_table,
        grid=grid,
        family=family,
        selection=selection,
        controls=controls,
        cost_sens=cost_sens,
        selected_frame=selected_frame,
        test_start=test_start,
        no_plots=args.no_plots,
    )
    return selection


def main() -> None:
    args = parse_args()
    selection = run(args)
    print("[robust-alpha] selected decision")
    print(selection.to_string(index=False))


if __name__ == "__main__":
    main()
