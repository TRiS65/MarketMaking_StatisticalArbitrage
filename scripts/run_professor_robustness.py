#!/usr/bin/env python3
"""Robustness checks requested after professor feedback.

This script isolates three issues that can change high-frequency TAQ results:

1. spread definition:
   - cumulative residual return spread;
   - direct log-price spread;
   - log-price regression residual with intercept.
2. transaction-cost scenarios:
   - no cost;
   - 0.25 x quoted spread;
   - 0.50 x quoted spread market-taker audit;
   - clipped last-trade price proxy.
3. OU / Avellaneda-Lee style diagnostics:
   - ADF p-value, half-life, OU equilibrium sigma, and s-score scale.

Selection is train/validation/test: estimate beta on train, choose pair/spread
threshold on validation, and report the final test sample separately.
"""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

from project_config import ETF, FIGURES, TABLES, constituents, ensure_output_dirs, split_dates
from research_utils import clipped_last_trade_price, log_returns, make_views, safe_adf_pvalue, safe_half_life, estimate_ou

MINUTES_PER_DAY = 390


@dataclass(frozen=True)
class RuleChoice:
    stock: str
    spread_type: str
    beta: float
    alpha: float
    entry_z: float
    exit_z: float
    validation_net_bps: float


def sample_masks(index: pd.Index) -> dict[str, pd.Series]:
    train_end, validation_end, test_end = split_dates()
    idx = pd.Series(index, index=index)
    return {
        "train": idx < train_end,
        "validation": (idx >= train_end) & (idx < validation_end),
        "test": (idx >= validation_end) & (idx < test_end),
    }


def continuous_diff(series: pd.Series) -> pd.Series:
    out = series.diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    idx = pd.Series(series.index, index=series.index)
    continuous = (idx.diff() == pd.Timedelta(minutes=1)) & (idx.dt.date == idx.shift(1).dt.date)
    out.loc[~continuous.values] = 0.0
    return out.clip(-0.05, 0.05)


def estimate_return_beta(ret: pd.DataFrame, stock: str, train_mask: pd.Series) -> float:
    x = ret.loc[train_mask, stock].clip(-0.005, 0.005).to_numpy(float)
    y = ret.loc[train_mask, ETF].clip(-0.005, 0.005).to_numpy(float)
    valid = np.isfinite(x) & np.isfinite(y) & (np.abs(x) > 0)
    x, y = x[valid], y[valid]
    if len(x) < 500 or np.var(x, ddof=1) <= 0:
        return np.nan
    return float(np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1))


def estimate_price_regression(log_price: pd.DataFrame, stock: str, train_mask: pd.Series) -> tuple[float, float]:
    y = log_price.loc[train_mask, ETF].to_numpy(float)
    x = log_price.loc[train_mask, stock].to_numpy(float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if len(x) < 500 or np.var(x, ddof=1) <= 0:
        return np.nan, np.nan
    model = sm.OLS(y, sm.add_constant(x)).fit()
    return float(model.params[0]), float(model.params[1])


def build_spread(
    log_price: pd.DataFrame,
    ret: pd.DataFrame,
    stock: str,
    spread_type: str,
    beta_return: float,
    alpha_price: float,
    beta_price: float,
) -> tuple[pd.Series, pd.Series, float, float]:
    if spread_type == "cum_residual_return":
        residual = ret[ETF] - beta_return * ret[stock]
        spread = residual.cumsum()
        return spread, residual, beta_return, 0.0
    if spread_type == "direct_log_price":
        spread = log_price[ETF] - beta_return * log_price[stock]
        spread = spread - spread.dropna().iloc[0]
        return spread, continuous_diff(spread), beta_return, 0.0
    if spread_type == "price_regression_residual":
        spread = log_price[ETF] - (alpha_price + beta_price * log_price[stock])
        return spread, continuous_diff(spread), beta_price, alpha_price
    raise ValueError(f"unknown spread type {spread_type}")


def zscore(spread: pd.Series, window: int = MINUTES_PER_DAY * 5) -> pd.Series:
    center = spread.rolling(window, min_periods=MINUTES_PER_DAY).mean().shift(1)
    std = spread.rolling(window, min_periods=MINUTES_PER_DAY).std().shift(1)
    return (spread - center) / std.replace(0.0, np.nan)


def position_path(z: pd.Series, entry: float, exit_band: float) -> pd.Series:
    dates = pd.Series(z.index.date.astype(str), index=z.index)
    pos = np.zeros(len(z), dtype=float)
    current = 0.0
    for i, zi in enumerate(z.to_numpy(float)):
        if i > 0 and dates.iloc[i] != dates.iloc[i - 1]:
            current = 0.0
        if np.isfinite(zi):
            if current == 0.0:
                if zi > entry:
                    current = -1.0
                elif zi < -entry:
                    current = 1.0
            elif current > 0 and zi > -exit_band:
                current = 0.0
            elif current < 0 and zi < exit_band:
                current = 0.0
        if i < len(z) - 1 and dates.iloc[i + 1] != dates.iloc[i]:
            current = 0.0
        pos[i] = current
    return pd.Series(pos, index=z.index)


def one_way_cost(spread_bps: pd.DataFrame, stock: str, beta: float, fraction: float) -> pd.Series:
    cost_bps = fraction * spread_bps[ETF] + abs(beta) * fraction * spread_bps[stock]
    return (cost_bps / 1e4).replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)


def summarize_frame(
    stock: str,
    spread_type: str,
    beta: float,
    entry: float,
    exit_band: float,
    pos: pd.Series,
    exec_residual: pd.Series,
    cost: pd.Series,
    scenario: str,
) -> list[dict]:
    turnover = pos.diff().abs().fillna(pos.abs())
    gross = pos.shift(1).fillna(0.0) * exec_residual.reindex(pos.index).fillna(0.0)
    cost_ret = turnover * cost.reindex(pos.index).fillna(0.0)
    net = gross - cost_ret
    rows = []
    for sample, mask in sample_masks(pos.index).items():
        rows.append(
            {
                "stock": stock,
                "pair": f"{ETF}-{stock}",
                "spread_type": spread_type,
                "execution_scenario": scenario,
                "beta": beta,
                "entry_z": entry,
                "exit_z": exit_band,
                "sample": sample,
                "gross_bps": float(1e4 * gross.loc[mask].sum()),
                "cost_bps": float(1e4 * cost_ret.loc[mask].sum()),
                "net_bps": float(1e4 * net.loc[mask].sum()),
                "trades": int((turnover.loc[mask] > 0).sum()),
                "avg_abs_position": float(pos.loc[mask].abs().mean()),
            }
        )
    return rows


def choose_rule_for_pair(
    stock: str,
    spread_type: str,
    spread: pd.Series,
    exec_residual: pd.Series,
    spread_bps: pd.DataFrame,
    beta: float,
    alpha: float,
) -> RuleChoice:
    z = zscore(spread)
    best = None
    for entry in [1.0, 1.25, 1.5, 2.0, 2.5]:
        for exit_band in [0.0, 0.25, 0.5]:
            if exit_band >= entry:
                continue
            pos = position_path(z, entry, exit_band)
            rows = summarize_frame(stock, spread_type, beta, entry, exit_band, pos, exec_residual, one_way_cost(spread_bps, stock, beta, 0.25), "validation_0.25x_spread")
            val = [r for r in rows if r["sample"] == "validation"][0]
            score = (val["net_bps"], -val["trades"])
            if best is None or score > best[0]:
                best = (score, entry, exit_band, val["net_bps"])
    if best is None:
        return RuleChoice(stock, spread_type, beta, alpha, 1.5, 0.5, 0.0)
    return RuleChoice(stock, spread_type, beta, alpha, best[1], best[2], best[3])


def main() -> None:
    ensure_output_dirs()
    views = make_views()
    mid = views["mid"]
    spread_bps = views["spread_bps"]
    last_px = clipped_last_trade_price(views)
    log_mid = np.log(mid)
    log_last = np.log(last_px)
    ret_mid = log_returns(mid)
    ret_last = log_returns(last_px)
    train_mask = sample_masks(mid.index)["train"]

    robustness_rows = []
    diagnostics_rows = []
    selected_rows = []
    choices = []

    for stock in constituents():
        if stock not in mid.columns:
            continue
        beta_return = estimate_return_beta(ret_mid, stock, train_mask)
        alpha_price, beta_price = estimate_price_regression(log_mid, stock, train_mask)
        if not np.isfinite(beta_return) or not np.isfinite(beta_price):
            continue
        for spread_type in ["cum_residual_return", "direct_log_price", "price_regression_residual"]:
            spread, exec_res_mid, beta_used, alpha_used = build_spread(log_mid, ret_mid, stock, spread_type, beta_return, alpha_price, beta_price)
            _, exec_res_last, _, _ = build_spread(log_last, ret_last, stock, spread_type, beta_return, alpha_price, beta_price)
            train_spread = spread.loc[train_mask]
            ou = estimate_ou(train_spread)
            diagnostics_rows.append(
                {
                    "stock": stock,
                    "pair": f"{ETF}-{stock}",
                    "spread_type": spread_type,
                    "beta_return": beta_return,
                    "alpha_price": alpha_price,
                    "beta_price": beta_price,
                    "train_adf_p": safe_adf_pvalue(train_spread),
                    "train_half_life_minutes": safe_half_life(train_spread),
                    **ou,
                    "train_spread_std_bps": float(1e4 * train_spread.std()),
                }
            )
            choice = choose_rule_for_pair(stock, spread_type, spread, exec_res_mid, spread_bps, beta_used, alpha_used)
            choices.append(choice)
            z = zscore(spread)
            pos = position_path(z, choice.entry_z, choice.exit_z)
            for scenario, exec_res, fraction in [
                ("no_cost_midpoint", exec_res_mid, 0.0),
                ("quarter_spread_cost", exec_res_mid, 0.25),
                ("half_spread_taker_cost", exec_res_mid, 0.50),
                ("clipped_last_trade_proxy", exec_res_last, 0.0),
            ]:
                robustness_rows.extend(
                    summarize_frame(
                        stock,
                        spread_type,
                        beta_used,
                        choice.entry_z,
                        choice.exit_z,
                        pos,
                        exec_res,
                        one_way_cost(spread_bps, stock, beta_used, fraction),
                        scenario,
                    )
                )
            selected_rows.append(
                {
                    "stock": stock,
                    "pair": f"{ETF}-{stock}",
                    "spread_type": spread_type,
                    "beta": beta_used,
                    "alpha": alpha_used,
                    "entry_z": choice.entry_z,
                    "exit_z": choice.exit_z,
                    "validation_net_bps_0.25x_spread": choice.validation_net_bps,
                }
            )

    diagnostics = pd.DataFrame(diagnostics_rows).sort_values(["train_adf_p", "train_half_life_minutes"])
    selected = pd.DataFrame(selected_rows).sort_values("validation_net_bps_0.25x_spread", ascending=False)
    robustness = pd.DataFrame(robustness_rows)
    test_summary = robustness[robustness["sample"].eq("test")].copy()
    leaderboard = (
        test_summary.pivot_table(
            index=["pair", "stock", "spread_type", "entry_z", "exit_z"],
            columns="execution_scenario",
            values="net_bps",
            aggfunc="first",
        )
        .reset_index()
        .sort_values("quarter_spread_cost", ascending=False)
    )

    diagnostics.to_csv(TABLES / "professor_ou_spread_diagnostics.csv", index=False)
    selected.to_csv(TABLES / "professor_selected_spread_rules.csv", index=False)
    robustness.to_csv(TABLES / "professor_cost_scenario_results.csv", index=False)
    leaderboard.to_csv(TABLES / "professor_test_leaderboard.csv", index=False)

    plt.figure(figsize=(10, 5))
    plot_df = leaderboard.head(12)
    x = np.arange(len(plot_df))
    width = 0.25
    for j, col in enumerate(["no_cost_midpoint", "quarter_spread_cost", "half_spread_taker_cost"]):
        if col in plot_df:
            plt.bar(x + (j - 1) * width, plot_df[col], width=width, label=col)
    plt.axhline(0, color="black", linewidth=0.8)
    plt.xticks(x, plot_df["pair"] + "\n" + plot_df["spread_type"].str.replace("_", "\n"), rotation=45, ha="right", fontsize=7)
    plt.ylabel("test net bps")
    plt.title("Professor Robustness: Test P&L by Cost Scenario")
    plt.legend()
    plt.tight_layout()
    plt.savefig(FIGURES / "professor_cost_scenario_leaderboard.png", dpi=180)
    plt.close()

    memo = f"""# Professor Feedback Robustness Memo

This run answers the main TAQ methodology questions raised in feedback:

- `r_XLK,t` is one-minute log return, not price.
- The old residual spread is compared against direct log-price spread and log-price regression residual.
- Gross/no-cost P&L is separated from 0.25-spread, 0.50-spread, and clipped last-trade execution proxies.
- OU/Avellaneda-Lee style diagnostics are reported as ADF p-value, half-life, equilibrium sigma, and s-score scale.

Best validation-selected test rows under the 0.25-spread scenario:

{leaderboard.head(12).to_markdown(index=False)}
"""
    (TABLES.parent / "professor_feedback_memo.md").write_text(memo)

    print("[professor] wrote robustness tables")
    print(leaderboard.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
