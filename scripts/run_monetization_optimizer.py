#!/usr/bin/env python3
"""Monetization optimizer for relative-value signals.

The professor-robustness layer shows that some XLK-vs-constituent signals exist
before costs or under low-cost execution, but most do not survive full taker
execution.  This script asks a narrower question:

    Can the gross/low-cost pair signals be monetized by selecting liquid signals,
    allocating capital across them like a Markowitz portfolio, and stress-testing
    execution with an Almgren-Chriss-inspired cost/risk buffer?

It is deliberately not another single-pair leaderboard.  Candidate formation and
portfolio weights use train/validation data only; test is the holdout.  If the
selected portfolio fails the holdout or execution stress, the decision is
explicitly no-trade.
"""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from project_config import ETF, FIGURES, OUTPUT, TABLES, ensure_output_dirs, split_dates
from research_utils import clipped_last_trade_price, log_returns, make_views
from run_professor_robustness import (
    build_spread,
    estimate_price_regression,
    estimate_return_beta,
    one_way_cost,
    position_path,
    sample_masks,
    zscore,
)

MAX_SYMBOL_SPREAD_BPS = 12.0
MAX_WEIGHT_PER_SIGNAL = 0.35
MIN_VALIDATION_TRADES = 5


@dataclass(frozen=True)
class Candidate:
    signal_id: str
    stock: str
    spread_type: str
    beta: float
    alpha: float
    entry_z: float
    exit_z: float
    median_stock_spread_bps: float
    train_half_life_minutes: float
    train_adf_p: float
    validation_quarter_net_bps: float
    validation_half_net_bps: float
    validation_last_trade_net_bps: float
    validation_trades: int


def safe_float(x, default=np.nan) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def max_drawdown_bps(ret: pd.Series) -> float:
    curve = 1e4 * ret.fillna(0.0).cumsum()
    dd = curve - curve.cummax()
    return float(dd.min()) if len(dd) else 0.0


def period_stats(frame: pd.DataFrame, prefix: str, mask: pd.Series) -> dict[str, float]:
    sub = frame.loc[mask]
    if sub.empty:
        return {
            f"{prefix}_gross_bps": 0.0,
            f"{prefix}_cost_bps": 0.0,
            f"{prefix}_net_bps": 0.0,
            f"{prefix}_trades": 0.0,
            f"{prefix}_max_drawdown_bps": 0.0,
        }
    return {
        f"{prefix}_gross_bps": float(1e4 * sub["gross_ret"].sum()),
        f"{prefix}_cost_bps": float(1e4 * sub["cost_ret"].sum()),
        f"{prefix}_net_bps": float(1e4 * sub["net_ret"].sum()),
        f"{prefix}_trades": float((sub["turnover"] > 0).sum()),
        f"{prefix}_max_drawdown_bps": max_drawdown_bps(sub["net_ret"]),
    }


def train_ou_metrics(path: pd.Series, train_mask: pd.Series) -> tuple[float, float]:
    # Prefer precomputed professor diagnostics; this fallback keeps the script
    # self-contained if the diagnostics table is missing.
    s = path.loc[train_mask].dropna()
    if len(s) < 500:
        return np.nan, np.nan
    lag = s.shift(1).dropna()
    diff = s.diff().dropna()
    lag = lag.loc[diff.index]
    if len(lag) < 500 or lag.var() <= 0:
        return np.nan, np.nan
    beta = np.cov(diff, lag, ddof=1)[0, 1] / np.var(lag, ddof=1)
    phi = 1.0 + beta
    half = float(-np.log(2.0) / np.log(phi)) if 0 < phi < 1 else np.nan
    return np.nan, half


def choose_candidates() -> list[Candidate]:
    selected_path = TABLES / "professor_selected_spread_rules.csv"
    robust_path = TABLES / "professor_cost_scenario_results.csv"
    diag_path = TABLES / "professor_ou_spread_diagnostics.csv"
    data_diag_path = TABLES / "minute_data_diagnostics.csv"
    if not selected_path.exists() or not robust_path.exists():
        raise FileNotFoundError("Run scripts/run_professor_robustness.py before monetization optimizer.")

    selected = pd.read_csv(selected_path)
    robust = pd.read_csv(robust_path)
    diag = pd.read_csv(diag_path) if diag_path.exists() else pd.DataFrame()
    data_diag = pd.read_csv(data_diag_path) if data_diag_path.exists() else pd.DataFrame()
    spread_map = (
        data_diag.set_index("symbol")["median_spread_bps"].to_dict()
        if not data_diag.empty and "median_spread_bps" in data_diag
        else {}
    )
    rows = []
    val = robust[robust["sample"].eq("validation")].copy()
    val_pivot = val.pivot_table(
        index=["stock", "pair", "spread_type", "entry_z", "exit_z"],
        columns="execution_scenario",
        values=["net_bps", "trades"],
        aggfunc="first",
    )
    val_pivot.columns = [f"{a}_{b}" for a, b in val_pivot.columns]
    val_pivot = val_pivot.reset_index()
    if not diag.empty:
        diag_key = diag[["stock", "spread_type", "train_adf_p", "train_half_life_minutes"]].copy()
    else:
        diag_key = pd.DataFrame(columns=["stock", "spread_type", "train_adf_p", "train_half_life_minutes"])
    merged = selected.merge(val_pivot, on=["stock", "pair", "spread_type", "entry_z", "exit_z"], how="left")
    merged = merged.merge(diag_key, on=["stock", "spread_type"], how="left")
    for _, r in merged.iterrows():
        stock = str(r["stock"])
        median_spread = safe_float(spread_map.get(stock, np.nan))
        validation_quarter = safe_float(r.get("net_bps_quarter_spread_cost"))
        validation_half = safe_float(r.get("net_bps_half_spread_taker_cost"))
        validation_last = safe_float(r.get("net_bps_clipped_last_trade_proxy"))
        validation_trades = int(safe_float(r.get("trades_quarter_spread_cost"), 0))
        if not np.isfinite(median_spread) or median_spread > MAX_SYMBOL_SPREAD_BPS:
            continue
        if validation_trades < MIN_VALIDATION_TRADES:
            continue
        if validation_quarter <= 0 and validation_last <= 0:
            continue
        # Keep half-spread negative candidates only if the validation evidence is
        # strong enough to justify a maker/taker monetization attempt.
        if validation_half < -150 and validation_quarter < 100:
            continue
        sid = f"{stock}_{r['spread_type']}_e{r['entry_z']}_x{r['exit_z']}"
        rows.append(
            Candidate(
                signal_id=sid,
                stock=stock,
                spread_type=str(r["spread_type"]),
                beta=safe_float(r["beta"]),
                alpha=safe_float(r.get("alpha", 0.0), 0.0),
                entry_z=safe_float(r["entry_z"]),
                exit_z=safe_float(r["exit_z"]),
                median_stock_spread_bps=median_spread,
                train_half_life_minutes=safe_float(r.get("train_half_life_minutes")),
                train_adf_p=safe_float(r.get("train_adf_p")),
                validation_quarter_net_bps=validation_quarter,
                validation_half_net_bps=validation_half,
                validation_last_trade_net_bps=validation_last,
                validation_trades=validation_trades,
            )
        )
    rows.sort(
        key=lambda c: (
            c.validation_quarter_net_bps
            + 0.25 * max(c.validation_last_trade_net_bps, 0)
            + 0.10 * c.validation_half_net_bps
            - 0.02 * max(c.train_half_life_minutes if np.isfinite(c.train_half_life_minutes) else 5000, 0)
        ),
        reverse=True,
    )
    return rows[:25]


def strategy_streams(candidates: list[Candidate]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    views = make_views()
    mid = views["mid"]
    spread_bps = views["spread_bps"]
    last_px = clipped_last_trade_price(views)
    log_mid = np.log(mid)
    log_last = np.log(last_px)
    ret_mid = log_returns(mid)
    ret_last = log_returns(last_px)
    train_mask = sample_masks(mid.index)["train"]

    gross_cols = {}
    turnover_cols = {}
    quote_cost_cols = {}
    last_trade_cols = {}
    for c in candidates:
        beta_return = estimate_return_beta(ret_mid, c.stock, train_mask)
        alpha_price, beta_price = estimate_price_regression(log_mid, c.stock, train_mask)
        spread, exec_res_mid, beta_used, _ = build_spread(
            log_mid, ret_mid, c.stock, c.spread_type, beta_return, alpha_price, beta_price
        )
        _, exec_res_last, _, _ = build_spread(log_last, ret_last, c.stock, c.spread_type, beta_return, alpha_price, beta_price)
        z = zscore(spread)
        pos = position_path(z, c.entry_z, c.exit_z)
        turnover = pos.diff().abs().fillna(pos.abs())
        gross_cols[c.signal_id] = pos.shift(1).fillna(0.0) * exec_res_mid.reindex(pos.index).fillna(0.0)
        turnover_cols[c.signal_id] = turnover
        # One unit here is the full quote boundary cost.  A spread_fraction of
        # 0.25 or 0.50 is applied later.
        quote_cost_cols[c.signal_id] = turnover * one_way_cost(spread_bps, c.stock, beta_used, 1.0).reindex(pos.index).fillna(0.0)
        last_trade_cols[c.signal_id] = pos.shift(1).fillna(0.0) * exec_res_last.reindex(pos.index).fillna(0.0)
    gross = pd.DataFrame(gross_cols, index=mid.index).fillna(0.0)
    turnover = pd.DataFrame(turnover_cols, index=mid.index).fillna(0.0)
    quote_cost = pd.DataFrame(quote_cost_cols, index=mid.index).fillna(0.0)
    last_trade_gross = pd.DataFrame(last_trade_cols, index=mid.index).fillna(0.0)
    return gross, turnover, quote_cost, last_trade_gross


def ac_buffer_decimal(gross: pd.DataFrame, turnover: pd.DataFrame, participation_rate: float, horizon_min: int) -> pd.DataFrame:
    # Almgren-Chriss inspired, intentionally conservative and transparent:
    # temporary impact grows with sqrt(participation), and timing-risk buffer
    # grows with residual one-minute volatility and sqrt(execution horizon).
    gross_bps = 1e4 * gross
    vol_bps = gross_bps.std().replace(0.0, np.nan).fillna(gross_bps.std().median())
    temporary_impact_bps = 2.5 * np.sqrt(participation_rate / 0.01)
    timing_risk_bps = 0.10 * vol_bps * np.sqrt(max(horizon_min, 1))
    buffer_bps = temporary_impact_bps + timing_risk_bps
    return turnover.mul(buffer_bps / 1e4, axis=1)


def daily_matrix(ret: pd.DataFrame) -> pd.DataFrame:
    dates = pd.Series(ret.index.date.astype(str), index=ret.index)
    return 1e4 * ret.groupby(dates).sum()


def optimize_weights(train_daily: pd.DataFrame, gamma: float) -> np.ndarray:
    n = train_daily.shape[1]
    if n == 0:
        return np.array([])
    mu = train_daily.mean().to_numpy(dtype=float)
    sigma = train_daily.cov().to_numpy(dtype=float)
    sigma = np.nan_to_num(sigma, nan=0.0, posinf=0.0, neginf=0.0)
    sigma = sigma + np.eye(n) * 1e-6

    def obj(w: np.ndarray) -> float:
        return float(-(mu @ w) + gamma * (w @ sigma @ w))

    bounds = [(0.0, MAX_WEIGHT_PER_SIGNAL) for _ in range(n)]
    constraints = [{"type": "ineq", "fun": lambda w: 1.0 - float(np.sum(w))}]
    x0 = np.repeat(min(1.0 / max(n, 1), MAX_WEIGHT_PER_SIGNAL), n)
    res = minimize(obj, x0, method="SLSQP", bounds=bounds, constraints=constraints, options={"maxiter": 500, "ftol": 1e-10})
    if not res.success:
        return np.zeros(n)
    w = np.clip(res.x, 0.0, MAX_WEIGHT_PER_SIGNAL)
    if w.sum() > 1.0:
        w = w / w.sum()
    return w


def portfolio_frame(gross: pd.DataFrame, quote_cost: pd.DataFrame, ac_buffer: pd.DataFrame, weights: np.ndarray, spread_fraction: float) -> pd.DataFrame:
    w = pd.Series(weights, index=gross.columns)
    frame = pd.DataFrame(index=gross.index)
    frame["gross_ret"] = gross.mul(w, axis=1).sum(axis=1)
    frame["cost_ret"] = (spread_fraction * quote_cost + ac_buffer).mul(w, axis=1).sum(axis=1)
    frame["net_ret"] = frame["gross_ret"] - frame["cost_ret"]
    frame["turnover"] = (quote_cost.ne(0.0).astype(float)).mul(w, axis=1).sum(axis=1)
    return frame


def main() -> None:
    ensure_output_dirs()
    candidates = choose_candidates()
    if not candidates:
        decision = pd.DataFrame(
            [{"decision": "no_trade", "reason": "no liquid validation-positive pair signals", "test_net_bps": 0.0}]
        )
        decision.to_csv(TABLES / "monetization_selection.csv", index=False)
        print("[monetization] no candidates")
        return

    candidate_df = pd.DataFrame([c.__dict__ for c in candidates])
    candidate_df.to_csv(TABLES / "monetization_candidate_strategies.csv", index=False)

    gross, turnover, quote_cost, last_trade_gross = strategy_streams(candidates)
    train_end, validation_end, test_end = split_dates()
    masks = sample_masks(gross.index)

    core_names = {"AMD", "AAPL", "NVDA", "PLTR", "INTC"}
    core_candidates = []
    for stock in core_names:
        stock_rows = [c for c in candidates if c.stock == stock]
        if stock_rows:
            stock_rows.sort(key=lambda c: c.validation_quarter_net_bps, reverse=True)
            core_candidates.append(stock_rows[0])
    ou_candidates = [
        c
        for c in candidates
        if np.isfinite(c.train_half_life_minutes)
        and c.train_half_life_minutes <= 3900
        and (not np.isfinite(c.train_adf_p) or c.train_adf_p <= 0.50)
    ]
    candidate_sets = {
        "liquid_validation": candidates[:15],
        "ou_filtered": ou_candidates,
        "core_liquid_pairs": core_candidates,
    }
    candidate_sets = {k: v for k, v in candidate_sets.items() if v}
    rows = []
    frames: dict[str, pd.DataFrame] = {}
    weights_by_name: dict[str, np.ndarray] = {}
    columns_by_name: dict[str, list[str]] = {}
    gammas = [0.0, 0.001, 0.005, 0.01, 0.05, 0.10, 0.25]
    execution_grid = []
    for spread_fraction in [0.25, 0.35, 0.50]:
        for participation_rate in [0.001, 0.005, 0.010]:
            for horizon_min in [1, 5, 15]:
                execution_grid.append((spread_fraction, participation_rate, horizon_min))

    for spread_fraction, participation_rate, horizon_min in execution_grid:
        ac_buf = ac_buffer_decimal(gross, turnover, participation_rate, horizon_min)
        for set_name, set_candidates in candidate_sets.items():
            cols = [c.signal_id for c in set_candidates if c.signal_id in gross.columns]
            if not cols:
                continue
            g = gross[cols]
            qc = quote_cost[cols]
            ab = ac_buf[cols]
            lt = last_trade_gross[cols]
            net_stream = g - spread_fraction * qc - ab
            train_daily = daily_matrix(net_stream.loc[masks["train"]])
            for gamma in gammas:
                weights = optimize_weights(train_daily, gamma)
                name = f"{set_name}_sf{spread_fraction:.2f}_pr{participation_rate:.3f}_h{horizon_min}_g{gamma:g}"
                frame = portfolio_frame(g, qc, ab, weights, spread_fraction)
                frames[name] = frame
                weights_by_name[name] = weights
                columns_by_name[name] = cols
                row = {
                    "strategy": name,
                    "candidate_set": set_name,
                    "spread_fraction": spread_fraction,
                    "participation_rate": participation_rate,
                    "execution_horizon_min": horizon_min,
                    "markowitz_gamma": gamma,
                    "active_signals": int((weights > 1e-6).sum()),
                    "gross_leverage": float(weights.sum()),
                    "largest_weight": float(weights.max()) if len(weights) else 0.0,
                }
                for sample, mask in masks.items():
                    row.update(period_stats(frame, sample, mask))
                row["validation_score"] = (
                    row["validation_net_bps"]
                    + 0.25 * row["train_net_bps"]
                    + 0.20 * row["validation_max_drawdown_bps"]
                    - 0.05 * row["validation_cost_bps"]
                )
                rows.append(row)

    frontier = pd.DataFrame(rows).sort_values("validation_score", ascending=False)
    frontier.to_csv(TABLES / "monetization_markowitz_frontier.csv", index=False)
    eligible = frontier[
        (frontier["train_net_bps"] > 0)
        & (frontier["validation_net_bps"] > 0)
        & (frontier["validation_trades"] >= 10)
        & (frontier["active_signals"] >= 2)
    ].copy()
    if eligible.empty:
        selected = frontier.iloc[0]
        decision_label = "no_trade"
        reason = "no Markowitz portfolio passed train/validation monetization gates"
    else:
        selected = eligible.sort_values("validation_score", ascending=False).iloc[0]
        passes_holdout = (
            selected["test_net_bps"] > 0
            and selected["test_max_drawdown_bps"] > -250
            and selected["spread_fraction"] <= 0.35
        )
        decision_label = "active_candidate" if passes_holdout else "no_trade"
        reason = (
            "selected on train/validation and passes test execution audit"
            if passes_holdout
            else "train/validation-selected monetization portfolio loses test or fails drawdown/execution stress"
        )

    selected_name = str(selected["strategy"])
    selected_weights = weights_by_name[selected_name]
    selected_cols = columns_by_name[selected_name]
    weights_base = candidate_df[candidate_df["signal_id"].isin(selected_cols)].copy()
    weights_df = weights_base[["signal_id", "stock", "spread_type", "median_stock_spread_bps", "train_half_life_minutes"]].copy()
    weights_df["weight"] = selected_weights
    weights_df = weights_df.sort_values("weight", ascending=False)
    weights_df.to_csv(TABLES / "monetization_selected_weights.csv", index=False)

    # Last-trade proxy audit on the same selected weights.  This is a fill proxy,
    # not the selection criterion.
    w = pd.Series(selected_weights, index=selected_cols)
    last_frame = pd.DataFrame(index=gross.index)
    last_frame["gross_ret"] = last_trade_gross[selected_cols].mul(w, axis=1).sum(axis=1)
    last_frame["cost_ret"] = 0.0
    last_frame["net_ret"] = last_frame["gross_ret"]
    last_frame["turnover"] = turnover[selected_cols].mul(w, axis=1).sum(axis=1)
    last_trade_test = period_stats(last_frame, "test", masks["test"])["test_net_bps"]

    decision = pd.DataFrame(
        [
            {
                "decision": decision_label,
                "reason": reason,
                "selected_strategy": selected_name,
                "candidate_set": selected["candidate_set"],
                "spread_fraction": selected["spread_fraction"],
                "participation_rate": selected["participation_rate"],
                "execution_horizon_min": selected["execution_horizon_min"],
                "markowitz_gamma": selected["markowitz_gamma"],
                "active_signals": selected["active_signals"],
                "gross_leverage": selected["gross_leverage"],
                "train_net_bps": selected["train_net_bps"],
                "validation_net_bps": selected["validation_net_bps"],
                "test_net_bps": selected["test_net_bps"],
                "test_max_drawdown_bps": selected["test_max_drawdown_bps"],
                "test_last_trade_proxy_bps": last_trade_test,
            }
        ]
    )
    decision.to_csv(TABLES / "monetization_selection.csv", index=False)

    top_plot = frontier.head(20).copy()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.scatter(top_plot["validation_net_bps"], top_plot["test_net_bps"], s=40 + 80 * top_plot["gross_leverage"], c=top_plot["spread_fraction"], cmap="viridis")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("validation net bps")
    ax.set_ylabel("test net bps")
    ax.set_title("Monetization frontier: validation-selected portfolios vs test")
    fig.tight_layout()
    fig.savefig(FIGURES / "monetization_frontier.png", dpi=180)
    plt.close(fig)

    report = (
        "# Monetization Optimizer\n\n"
        "This experiment treats validation-positive liquid pair signals as strategy return streams, then allocates across them with a long-only Markowitz/QP-style optimizer.  Execution is stressed with an Almgren-Chriss-inspired buffer: quoted-spread fraction, square-root participation impact, and execution-horizon timing risk.\n\n"
        "## Decision\n\n"
        + decision.to_markdown(index=False)
        + "\n\n## Selected Weights\n\n"
        + weights_df.head(12).to_markdown(index=False)
        + "\n\n## Top Frontier Rows\n\n"
        + frontier.head(15).to_markdown(index=False)
        + "\n\n## Interpretation\n\n"
        "A positive validation portfolio is not sufficient.  Monetization requires the same allocation to remain positive under the untouched test window and under realistic execution stress.  If the selected row is diagnostic_only or no_trade, the correct conclusion is that prediction exists in pockets, but monetization remains unproven.\n"
    )
    (OUTPUT / "monetization_report.md").write_text(report)
    print("[monetization] decision")
    print(decision.to_string(index=False))


if __name__ == "__main__":
    main()
