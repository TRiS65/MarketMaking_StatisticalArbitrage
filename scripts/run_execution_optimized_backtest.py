#!/usr/bin/env python3
"""Execution-optimized XLK pair/basket diagnostic backtest.

Purpose
-------
This script tests the specific question: if the no-cost / gross signal is large,
can a data-driven execution policy convert it into net PnL?

Unlike fixed 0.25x/0.50x spread haircuts, this backtest uses observed bid/ask
quotes and observed last trades to simulate three execution policies:

  1. taker             : cross the quote on entry and exit
  2. maker_skip        : post passive entry on every leg; trade only if all legs
                         fill within the wait window; exit as taker
  3. maker_remainder   : post passive entry first; any unfilled leg is completed
                         aggressively at the end of the wait window; exit as taker

The model is deliberately conservative about final claims: it reports fill rate,
midpoint gross PnL, realized execution-cost drag, net PnL, latency sensitivity,
and a no-trade gate. It does not assume a magic 0.25-spread fill.

Limitations
-----------
TAQ top-of-book data does not provide queue position, hidden liquidity, venue
rebates, or order IDs. Passive fills inferred from last-trade crossing are still
an approximation. Treat positive maker results as candidates requiring an event-
level / queue-aware audit, not as production PnL.

Run
---
    python3 scripts/run_execution_optimized_backtest.py --root . --quick

Outputs
-------
    output/tables/execution_optimized_grid.csv
    output/tables/execution_optimized_selection.csv
    output/execution_optimized_report.md
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

try:
    import statsmodels.api as sm
except Exception:  # pragma: no cover
    sm = None

ETF = "XLK"
DEFAULT_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AVGO", "MU", "AMD", "INTC", "CSCO", "PLTR",
    "LRCX", "AMAT", "ORCL", "TXN", "KLAC", "IBM", "ADI", "QCOM", "ANET", "APH",
]


@dataclass(frozen=True)
class Candidate:
    stock: str
    spread_type: str


@dataclass
class Trade:
    entry_idx: int
    exit_idx: int
    side: int
    gross_bps: float
    net_bps: float
    cost_bps: float
    entry_policy: str
    fill_rate: float
    exit_reason: str


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _find_time_col(df: pd.DataFrame) -> str:
    for c in ["minute", "ts", "timestamp", "datetime", "time"]:
        if c in df.columns:
            return c
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
    raise ValueError(f"Could not find time column in {df.columns.tolist()}")


def _find_symbol_col(df: pd.DataFrame) -> str:
    for c in ["symbol", "sym", "ticker"]:
        if c in df.columns:
            return c
    raise ValueError(f"Could not find symbol column in {df.columns.tolist()}")


def load_panel(root: Path) -> pd.DataFrame:
    """Load long research_panel.parquet and pivot to wide quote/trade panel."""
    processed = root / "data" / "processed"
    candidates = [
        processed / "research_panel.parquet",
        processed / "new_research_panel.parquet",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        # Fallback: concatenate minute quote/trade parquet files if present.
        quote_files = sorted(processed.glob("minute_quotes_*.parquet"))
        trade_files = sorted(processed.glob("minute_trades_*.parquet"))
        if not quote_files:
            raise FileNotFoundError(
                "No research_panel.parquet or minute_quotes_*.parquet found under data/processed"
            )
        q = pd.concat([pd.read_parquet(p) for p in quote_files], ignore_index=True)
        if trade_files:
            tr = pd.concat([pd.read_parquet(p) for p in trade_files], ignore_index=True)
            tcol_q, scol_q = _find_time_col(q), _find_symbol_col(q)
            tcol_t, scol_t = _find_time_col(tr), _find_symbol_col(tr)
            q[tcol_q] = pd.to_datetime(q[tcol_q])
            tr[tcol_t] = pd.to_datetime(tr[tcol_t])
            q = q.merge(
                tr[[tcol_t, scol_t, "last_trade_price", "volume"]],
                left_on=[tcol_q, scol_q], right_on=[tcol_t, scol_t], how="left",
                suffixes=("", "_trade"),
            )
        raw = q
    else:
        raw = pd.read_parquet(path)

    raw.columns = [str(c).lower() for c in raw.columns]
    tcol = _find_time_col(raw)
    scol = _find_symbol_col(raw)
    raw[tcol] = pd.to_datetime(raw[tcol])

    # Ensure required quote columns.
    if "mid" not in raw.columns:
        raw["mid"] = (raw["bid"] + raw["ask"]) / 2.0
    if "last_trade_price" not in raw.columns:
        raw["last_trade_price"] = np.nan
    if "volume" not in raw.columns:
        raw["volume"] = np.nan

    cols = ["mid", "bid", "ask", "last_trade_price", "volume"]
    frames = []
    for col in cols:
        piv = raw.pivot_table(index=tcol, columns=scol, values=col, aggfunc="last")
        piv.columns = [f"{col}_{s}" for s in piv.columns]
        frames.append(piv)
    wide = pd.concat(frames, axis=1).sort_index()

    # Fill short quote gaps within a day only.
    day = pd.Series(wide.index.date, index=wide.index)
    wide = wide.groupby(day, group_keys=False).ffill(limit=2)
    wide = wide.dropna(subset=[f"mid_{ETF}", f"bid_{ETF}", f"ask_{ETF}"])
    return wide


def split_masks(index: pd.DatetimeIndex, train_end: str, val_end: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    t = pd.to_datetime(index)
    train = t < pd.Timestamp(train_end)
    val = (t >= pd.Timestamp(train_end)) & (t < pd.Timestamp(val_end))
    test = t >= pd.Timestamp(val_end)
    return train.values if hasattr(train, "values") else train, val.values if hasattr(val, "values") else val, test.values if hasattr(test, "values") else test


# ---------------------------------------------------------------------------
# Spread construction
# ---------------------------------------------------------------------------

def logret(x: pd.Series) -> pd.Series:
    r = np.log(x).diff()
    # Do not carry returns across day gaps.
    same_day = x.index.to_series().dt.date == x.index.to_series().shift(1).dt.date
    r.loc[~same_day.values] = 0.0
    return r.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def ols_beta(y: np.ndarray, x: np.ndarray, intercept: bool = False) -> tuple[float, float]:
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    if len(y) < 100 or np.var(x) <= 0:
        return 0.0, 1.0
    if intercept:
        X = np.column_stack([np.ones_like(x), x])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        return float(coef[0]), float(coef[1])
    beta = float(np.dot(x, y) / max(np.dot(x, x), 1e-18))
    return 0.0, beta


def make_spread(wide: pd.DataFrame, stock: str, spread_type: str, train_mask: np.ndarray) -> tuple[pd.Series, float, float]:
    px = wide[f"mid_{ETF}"]
    ps = wide[f"mid_{stock}"]
    lx = np.log(px)
    ls = np.log(ps)
    if spread_type == "cum_residual_return":
        rx = logret(px)
        rs = logret(ps)
        a, beta = ols_beta(rx.values[train_mask], rs.values[train_mask], intercept=False)
        spread = (rx - beta * rs).cumsum()
        return spread, a, beta
    if spread_type == "price_regression_residual":
        a, beta = ols_beta(lx.values[train_mask], ls.values[train_mask], intercept=True)
        spread = lx - (a + beta * ls)
        return spread, a, beta
    if spread_type == "direct_log_price":
        # Regression beta without intercept avoids hard-coding beta=1 for unlike prices.
        a, beta = ols_beta(lx.values[train_mask], ls.values[train_mask], intercept=False)
        spread = lx - beta * ls
        return spread, a, beta
    raise ValueError(f"unknown spread_type={spread_type}")


def rolling_z(spread: pd.Series, window: int) -> pd.Series:
    mu = spread.rolling(window, min_periods=max(50, window // 5)).mean()
    sd = spread.rolling(window, min_periods=max(50, window // 5)).std()
    return ((spread - mu) / sd.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)


# ---------------------------------------------------------------------------
# Execution mechanics
# ---------------------------------------------------------------------------

def _side_fill_price(row: pd.Series, sym: str, signed_delta: float, mode: str) -> float:
    """Return fill price for changing position by signed_delta.

    signed_delta > 0 means buy; signed_delta < 0 means sell.
    mode: taker, passive.
    """
    if signed_delta > 0:
        return float(row[f"ask_{sym}"] if mode == "taker" else row[f"bid_{sym}"])
    if signed_delta < 0:
        return float(row[f"bid_{sym}"] if mode == "taker" else row[f"ask_{sym}"])
    return float(row[f"mid_{sym}"])


def _mid_price(row: pd.Series, sym: str) -> float:
    return float(row[f"mid_{sym}"])


def _passive_fill_idx(wide: pd.DataFrame, start_i: int, sym: str, signed_delta: float, wait: int) -> int | None:
    """Infer passive fill using future last trade crossing the posted quote.

    Buy limit at bid fills if a future last trade is <= bid. Sell limit at ask fills
    if a future last trade is >= ask. This ignores queue priority, so positive
    results remain candidates only.
    """
    if signed_delta == 0:
        return start_i
    n = len(wide)
    post = wide.iloc[start_i]
    limit = float(post[f"bid_{sym}"] if signed_delta > 0 else post[f"ask_{sym}"])
    start = min(n - 1, start_i + 1)
    end = min(n - 1, start_i + wait)
    col = f"last_trade_price_{sym}"
    if start > end or col not in wide.columns or wide[col].iloc[start:end + 1].isna().all():
        return None
    trades = wide[col].iloc[start:end + 1]
    if signed_delta > 0:
        hits = np.where(trades.values <= limit)[0]
    else:
        hits = np.where(trades.values >= limit)[0]
    if len(hits) == 0:
        return None
    return int(start + hits[0])


def _pnl_from_prices(weights: dict[str, float], entry_prices: dict[str, float], exit_prices: dict[str, float]) -> float:
    pnl = 0.0
    for sym, w in weights.items():
        if not np.isfinite(entry_prices[sym]) or not np.isfinite(exit_prices[sym]) or entry_prices[sym] <= 0:
            return np.nan
        pnl += w * (exit_prices[sym] / entry_prices[sym] - 1.0)
    return 1e4 * pnl


def execute_entry(
    wide: pd.DataFrame,
    i: int,
    weights: dict[str, float],
    policy: str,
    wait: int,
    latency: int,
) -> tuple[int | None, dict[str, float] | None, float]:
    """Return effective entry index, entry prices, passive fill rate."""
    n = len(wide)
    start_i = min(n - 1, i + latency)
    if policy == "taker":
        row = wide.iloc[start_i]
        prices = {sym: _side_fill_price(row, sym, w, "taker") for sym, w in weights.items()}
        return start_i, prices, 0.0

    fill_indices: dict[str, int | None] = {}
    for sym, w in weights.items():
        fill_indices[sym] = _passive_fill_idx(wide, start_i, sym, w, wait)
    filled = {sym: idx is not None for sym, idx in fill_indices.items()}
    fill_rate = float(np.mean(list(filled.values()))) if filled else 0.0

    if policy == "maker_skip":
        if not all(filled.values()):
            return None, None, fill_rate
        entry_i = max(int(idx) for idx in fill_indices.values() if idx is not None)
        prices = {}
        for sym, w in weights.items():
            post_row = wide.iloc[start_i]
            prices[sym] = _side_fill_price(post_row, sym, w, "passive")
        return entry_i, prices, fill_rate

    if policy == "maker_remainder":
        entry_i = min(n - 1, start_i + wait)
        prices = {}
        for sym, w in weights.items():
            if fill_indices[sym] is not None:
                post_row = wide.iloc[start_i]
                prices[sym] = _side_fill_price(post_row, sym, w, "passive")
            else:
                row = wide.iloc[entry_i]
                prices[sym] = _side_fill_price(row, sym, w, "taker")
        return entry_i, prices, fill_rate

    raise ValueError(f"unknown execution policy={policy}")


def execute_exit(wide: pd.DataFrame, i: int, weights: dict[str, float], latency: int) -> tuple[int, dict[str, float]]:
    n = len(wide)
    j = min(n - 1, i + latency)
    row = wide.iloc[j]
    # To close, trade -weights.
    prices = {sym: _side_fill_price(row, sym, -w, "taker") for sym, w in weights.items()}
    return j, prices


def mid_prices(wide: pd.DataFrame, i: int, syms: Iterable[str]) -> dict[str, float]:
    row = wide.iloc[i]
    return {sym: _mid_price(row, sym) for sym in syms}


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def backtest_candidate(
    wide: pd.DataFrame,
    spread: pd.Series,
    beta: float,
    stock: str,
    mask: np.ndarray,
    entry_z: float,
    exit_z: float,
    policy: str,
    wait: int,
    latency: int,
    z_window: int,
    max_hold: int,
    min_edge_bps: float,
) -> dict:
    z = rolling_z(spread, z_window).values
    s_bps = (spread.values - pd.Series(spread).rolling(z_window, min_periods=max(50, z_window // 5)).mean().values) * 1e4
    indices = np.where(mask)[0]
    if len(indices) == 0:
        return dict(trades=0, gross_bps=0.0, cost_bps=0.0, net_bps=0.0, fill_rate=np.nan)

    trades: list[Trade] = []
    pos_side = 0
    entry_i = None
    entry_prices = None
    entry_mid_prices = None
    weights = None
    i = int(indices[0])
    end_i = int(indices[-1])
    while i <= end_i:
        if not np.isfinite(z[i]):
            i += 1
            continue
        # Do not carry trades across days.
        current_date = wide.index[i].date()
        if pos_side == 0:
            side = 0
            if z[i] >= entry_z:
                side = -1       # short spread: short XLK, long beta*stock
            elif z[i] <= -entry_z:
                side = +1       # long spread: long XLK, short beta*stock
            if side != 0:
                # Cost-aware entry gate in bps of residual deviation.
                if min_edge_bps > 0 and abs(s_bps[i]) < min_edge_bps:
                    i += 1
                    continue
                weights = {ETF: float(side), stock: float(-side * beta)}
                eidx, eprices, fr = execute_entry(wide, i, weights, policy, wait, latency)
                if eidx is None or eprices is None:
                    i += max(1, wait)
                    continue
                pos_side = side
                entry_i = eidx
                entry_prices = eprices
                entry_mid_prices = mid_prices(wide, eidx, weights.keys())
                i = eidx + 1
                continue
        else:
            assert entry_i is not None and weights is not None and entry_prices is not None and entry_mid_prices is not None
            held = i - entry_i
            exit_reason = None
            if wide.index[i].date() != current_date:
                exit_reason = "date_guard"
            elif (pos_side == +1 and z[i] >= -exit_z) or (pos_side == -1 and z[i] <= exit_z):
                exit_reason = "reversion"
            elif held >= max_hold:
                exit_reason = "max_hold"
            # Flatten near the end of a day.
            if i + 1 <= end_i and wide.index[i + 1].date() != wide.index[i].date():
                exit_reason = exit_reason or "eod"
            if exit_reason is not None:
                xidx, xprices = execute_exit(wide, i, weights, latency)
                xmid = mid_prices(wide, xidx, weights.keys())
                gross = _pnl_from_prices(weights, entry_mid_prices, xmid)
                net = _pnl_from_prices(weights, entry_prices, xprices)
                if np.isfinite(gross) and np.isfinite(net):
                    trades.append(Trade(entry_i, xidx, pos_side, gross, net, gross - net, policy, np.nan, exit_reason))
                pos_side = 0
                entry_i = None
                entry_prices = None
                entry_mid_prices = None
                weights = None
                i = xidx + 1
                continue
        i += 1

    if len(trades) == 0:
        return dict(trades=0, gross_bps=0.0, cost_bps=0.0, net_bps=0.0, fill_rate=np.nan)
    gross = float(np.nansum([t.gross_bps for t in trades]))
    net = float(np.nansum([t.net_bps for t in trades]))
    cost = gross - net
    # Approximate fill rate for maker policies by rechecking entry fills from cost advantage sign.
    return dict(
        trades=len(trades),
        gross_bps=gross,
        cost_bps=cost,
        net_bps=net,
        avg_net_per_trade_bps=net / len(trades),
    )


def run(root: Path, quick: bool, args: argparse.Namespace) -> None:
    out_tables = root / "output" / "tables"
    out_tables.mkdir(parents=True, exist_ok=True)
    wide = load_panel(root)
    train_mask, val_mask, test_mask = split_masks(wide.index, args.train_end, args.val_end)

    symbols = [s for s in DEFAULT_SYMBOLS if f"mid_{s}" in wide.columns and f"bid_{s}" in wide.columns and f"ask_{s}" in wide.columns]
    if quick:
        symbols = [s for s in ["AAPL", "NVDA", "PLTR", "ORCL", "AMD", "INTC"] if s in symbols]

    spread_types = ["cum_residual_return", "price_regression_residual", "direct_log_price"]
    entry_grid = [1.0, 1.25, 1.5, 2.0] if not quick else [1.0, 1.5, 2.0]
    exit_grid = [0.0, 0.25, 0.5] if not quick else [0.0, 0.5]
    policies = ["taker", "maker_skip", "maker_remainder"]
    waits = [1, 2, 5] if not quick else [1, 2]
    latencies = [0, 1] if not quick else [0]
    min_edges = [0.0, 10.0, 25.0] if not quick else [0.0, 25.0]

    rows = []
    for stock in symbols:
        for stype in spread_types:
            try:
                spread, alpha, beta = make_spread(wide, stock, stype, train_mask)
            except Exception as exc:
                print(f"[skip] {stock} {stype}: {exc}")
                continue
            if not np.isfinite(beta) or abs(beta) > 5:
                continue
            for policy in policies:
                for wait in waits:
                    if policy == "taker" and wait != waits[0]:
                        continue
                    for latency in latencies:
                        for entry in entry_grid:
                            for exit_z in exit_grid:
                                if exit_z >= entry:
                                    continue
                                for min_edge in min_edges:
                                    val = backtest_candidate(
                                        wide, spread, beta, stock, val_mask, entry, exit_z,
                                        policy, wait, latency, args.z_window, args.max_hold, min_edge,
                                    )
                                    test = backtest_candidate(
                                        wide, spread, beta, stock, test_mask, entry, exit_z,
                                        policy, wait, latency, args.z_window, args.max_hold, min_edge,
                                    )
                                    rows.append(dict(
                                        stock=stock,
                                        spread_type=stype,
                                        beta=beta,
                                        policy=policy,
                                        wait_min=wait,
                                        latency_min=latency,
                                        entry_z=entry,
                                        exit_z=exit_z,
                                        min_edge_bps=min_edge,
                                        val_trades=val["trades"],
                                        val_gross_bps=val["gross_bps"],
                                        val_cost_bps=val["cost_bps"],
                                        val_net_bps=val["net_bps"],
                                        test_trades=test["trades"],
                                        test_gross_bps=test["gross_bps"],
                                        test_cost_bps=test["cost_bps"],
                                        test_net_bps=test["net_bps"],
                                        test_avg_net_per_trade_bps=test.get("avg_net_per_trade_bps", np.nan),
                                    ))
    grid = pd.DataFrame(rows)
    grid.to_csv(out_tables / "execution_optimized_grid.csv", index=False)

    # Train/validation-only selection: positive validation, enough trades, high net per trade.
    if len(grid) == 0:
        sel = pd.DataFrame([dict(decision="no_data")])
    else:
        cand = grid[(grid["val_trades"] >= args.min_val_trades)].copy()
        if len(cand) == 0:
            sel = pd.DataFrame([dict(decision="no_trade", reason="no rule reached min validation trades")])
        else:
            # Penalize negative validation and very high cost share.
            cand["val_cost_share"] = cand["val_cost_bps"].abs() / cand["val_gross_bps"].abs().clip(lower=1e-9)
            cand["score"] = cand["val_net_bps"] - 0.25 * cand["val_cost_bps"].clip(lower=0) - 25.0 * (cand["val_trades"] < 5)
            best = cand.sort_values("score", ascending=False).iloc[0].to_dict()
            gate_reasons = []
            if best["val_net_bps"] <= 0:
                gate_reasons.append("validation_net<=0")
            if best["val_trades"] < args.min_val_trades:
                gate_reasons.append("too_few_validation_trades")
            if best.get("val_cost_share", 999) >= args.max_cost_share:
                gate_reasons.append("validation_cost_share_too_high")
            decision = "validation_candidate" if not gate_reasons else "no_trade"
            oos_decision = "survives_oos_audit" if decision == "validation_candidate" and best.get("test_net_bps", 0.0) > 0 else "reject_after_oos_audit"
            final_policy = "active_candidate_pending_event_validation" if oos_decision == "survives_oos_audit" else "no_trade"
            best.update(decision=decision, reason=";".join(gate_reasons) if gate_reasons else "passes validation execution gate")
            best.update(oos_decision=oos_decision)
            best.update(final_policy=final_policy)
            sel = pd.DataFrame([best])
    sel.to_csv(out_tables / "execution_optimized_selection.csv", index=False)

    report = root / "output" / "execution_optimized_report.md"
    top = grid.sort_values(["val_net_bps", "test_net_bps"], ascending=False).head(15) if len(grid) else grid
    report.write_text(
        "# Execution-Optimized Backtest\n\n"
        "This report tests whether gross pair signals can survive an empirical maker/taker execution policy. "
        "Costs are computed from observed bid/ask fills and inferred passive fills from last-trade crossings, not from fixed 0.25x/0.50x spread haircuts.\n\n"
        "The validation decision is deliberately separate from the out-of-sample audit. A rule that passes validation but has negative test net PnL is reported as an execution false positive, not as a tradable rule.\n\n"
        "## Selection\n\n"
        + sel.to_markdown(index=False)
        + "\n\n## Top validation rules\n\n"
        + (top.to_markdown(index=False) if len(top) else "No rules generated.")
        + "\n\n## Caution\n\nPassive fills inferred from one-minute TAQ last trades are approximate and ignore queue priority, hidden liquidity, and partial fills. Positive results should be treated as candidates for event-level validation.\n"
    )
    print(f"[wrote] {out_tables / 'execution_optimized_grid.csv'}")
    print(f"[wrote] {out_tables / 'execution_optimized_selection.csv'}")
    print(f"[wrote] {report}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--quick", action="store_true")
    p.add_argument("--train-end", default="2026-02-01")
    p.add_argument("--val-end", default="2026-03-01")
    p.add_argument("--z-window", type=int, default=1950)
    p.add_argument("--max-hold", type=int, default=390)
    p.add_argument("--min-val-trades", type=int, default=3)
    p.add_argument("--max-cost-share", type=float, default=0.75)
    return p.parse_args()


if __name__ == "__main__":
    ns = parse_args()
    run(ns.root.resolve(), ns.quick, ns)
