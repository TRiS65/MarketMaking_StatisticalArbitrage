#!/usr/bin/env python3
"""Top-20 method diagnostics on the expanded XLK TAQ panel.

This is the instructor-feedback validation layer.  It is deliberately
`real-data only`: if `research_panel.parquet` is missing, the script fails
instead of falling back to synthetic data.

Outputs:
  output/tables/top20_trial_registry.csv
  output/tables/top20_method_comparison_summary.csv
  output/tables/top20_pair_leaderboard.csv
  output/tables/top20_exit_reason_audit.csv
  output/tables/top20_no_trade_gate.csv
  output/tables/top20_signal_bucket.csv
  output/figures/top20_method_comparison.png
  output/figures/top20_signal_bucket.png
"""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

from project_config import ETF, FIGURES, TABLES, constituents, ensure_output_dirs, split_dates
from research_utils import estimate_ou, load_panel, log_returns, make_views, safe_adf_pvalue

MINUTES_PER_DAY = 390


@dataclass(frozen=True)
class MethodSpec:
    method: str
    hedge_method: str
    signal_method: str
    coint_filter: bool
    passive_entry: bool
    passive_fill_prob: float
    adverse_selection_bps: float
    half_life_max: float | None


METHODS = [
    MethodSpec("baseline", "ols", "zscore", False, False, 0.0, 0.0, None),
    MethodSpec("coint_filter", "ols", "zscore", True, False, 0.0, 0.0, None),
    MethodSpec("kalman_lagged", "kalman_lagged", "zscore", False, False, 0.0, 0.0, None),
    MethodSpec("sscore_ou_gate", "ols", "sscore", False, False, 0.0, 0.0, 350.0),
    MethodSpec("passive_stress", "ols", "zscore", False, True, 0.5, 0.5, None),
    MethodSpec("combined", "kalman_lagged", "sscore", True, True, 0.5, 0.5, 350.0),
]

ENTRY_GRID = [1.0, 1.5, 2.0]
EXIT_GRID = [0.5]
MAX_HOLD_GRID = [120]
STOP_GRID = [4.0, np.nan]


def masks(index: pd.Index) -> dict[str, pd.Series]:
    train_end, validation_end, test_end = split_dates()
    idx = pd.Series(index, index=index)
    return {
        "train": idx < train_end,
        "validation": (idx >= train_end) & (idx < validation_end),
        "test": (idx >= validation_end) & (idx < test_end),
    }


def static_beta(ret: pd.DataFrame, stock: str, train_mask: pd.Series) -> float:
    x = ret.loc[train_mask, stock].clip(-0.005, 0.005).to_numpy(float)
    y = ret.loc[train_mask, ETF].clip(-0.005, 0.005).to_numpy(float)
    valid = np.isfinite(x) & np.isfinite(y) & (np.abs(x) > 0)
    x, y = x[valid], y[valid]
    if len(x) < 500 or np.var(x, ddof=1) <= 0:
        return np.nan
    return float(np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1))


def kalman_beta_lagged(ret: pd.DataFrame, stock: str, train_mask: pd.Series, delta: float = 1e-4) -> pd.Series:
    """Online random-walk beta; beta_used[t] is prediction before seeing r_t."""
    x_all = ret[stock].fillna(0.0).to_numpy(float)
    y_all = ret[ETF].fillna(0.0).to_numpy(float)
    b0 = static_beta(ret, stock, train_mask)
    if not np.isfinite(b0):
        b0 = 1.0
    train_resid = (ret.loc[train_mask, ETF] - b0 * ret.loc[train_mask, stock]).dropna()
    r_var = float(train_resid.var()) if len(train_resid) else 1e-8
    r_var = max(r_var, 1e-10)
    q = delta / max(1e-12, 1.0 - delta)
    beta_used = np.zeros(len(ret), dtype=float)
    beta = b0
    p = 1.0
    for i, (x, y) in enumerate(zip(x_all, y_all)):
        beta_pred = beta
        p_pred = p + q
        beta_used[i] = beta_pred
        s = x * p_pred * x + r_var
        k = (p_pred * x) / s if s > 0 else 0.0
        beta = beta_pred + k * (y - x * beta_pred)
        p = (1.0 - k * x) * p_pred
    return pd.Series(beta_used, index=ret.index)


def rolling_zscore(spread: pd.Series, window: int = MINUTES_PER_DAY * 5) -> pd.Series:
    center = spread.rolling(window, min_periods=MINUTES_PER_DAY).mean().shift(1)
    std = spread.rolling(window, min_periods=MINUTES_PER_DAY).std().shift(1)
    return (spread - center) / std.replace(0.0, np.nan)


def sscore(spread: pd.Series, train_mask: pd.Series, window: int = MINUTES_PER_DAY * 2) -> tuple[pd.Series, dict[str, float]]:
    center = spread.rolling(window, min_periods=MINUTES_PER_DAY).mean().shift(1)
    detrended = spread - center
    ou = estimate_ou(detrended.loc[train_mask].dropna())
    sigma = ou.get("ou_sigma_eq", np.nan)
    theta = ou.get("ou_mu", np.nan)
    if not np.isfinite(sigma) or sigma <= 0:
        return pd.Series(np.nan, index=spread.index), ou
    return (detrended - theta) / sigma, ou


def one_way_cost(spread_bps: pd.DataFrame, stock: str, beta: pd.Series | float) -> pd.Series:
    if isinstance(beta, pd.Series):
        b = beta.abs().reindex(spread_bps.index).ffill().fillna(0.0)
    else:
        b = abs(float(beta))
    return ((spread_bps[ETF] / 2.0 + b * spread_bps[stock] / 2.0) / 1e4).replace([np.inf, -np.inf], np.nan).ffill().fillna(0.0)


def build_pair_state(views: dict[str, pd.DataFrame], ret: pd.DataFrame, stock: str, method: MethodSpec, train_mask: pd.Series) -> dict:
    beta_ols = static_beta(ret, stock, train_mask)
    if not np.isfinite(beta_ols):
        return {"skip": True, "reason": "bad_beta"}
    coint_spread = (ret[ETF] - beta_ols * ret[stock]).cumsum()
    coint_p = safe_adf_pvalue(coint_spread.loc[train_mask])
    if method.coint_filter and not (np.isfinite(coint_p) and coint_p < 0.10):
        return {"skip": True, "reason": "coint_filter_fail", "adf_p": coint_p, "beta": beta_ols}

    if method.hedge_method == "kalman_lagged":
        beta_used = kalman_beta_lagged(ret, stock, train_mask)
        residual = ret[ETF] - beta_used * ret[stock]
        beta_for_cost = beta_used
        beta_text = "kalman_lagged"
        avg_beta = float(beta_used.loc[train_mask].median())
    else:
        residual = ret[ETF] - beta_ols * ret[stock]
        beta_for_cost = beta_ols
        beta_text = f"{beta_ols:.6f}"
        avg_beta = beta_ols
    spread = residual.cumsum()

    if method.signal_method == "sscore":
        score, ou = sscore(spread, train_mask)
    else:
        score = rolling_zscore(spread)
        ou = estimate_ou((spread - spread.rolling(MINUTES_PER_DAY * 2, min_periods=MINUTES_PER_DAY).mean().shift(1)).loc[train_mask].dropna())
    if method.half_life_max is not None:
        hl = ou.get("ou_half_life_minutes", np.nan)
        if not (np.isfinite(hl) and hl <= method.half_life_max):
            return {"skip": True, "reason": "ou_half_life_gate_fail", "adf_p": coint_p, "beta": avg_beta, **ou}

    return {
        "skip": False,
        "stock": stock,
        "spread": spread,
        "residual": residual,
        "score": score,
        "cost": one_way_cost(views["spread_bps"], stock, beta_for_cost),
        "beta": avg_beta,
        "beta_text": beta_text,
        "adf_p": coint_p,
        **ou,
    }


def run_strategy(
    score: pd.Series,
    residual: pd.Series,
    cost: pd.Series,
    entry_z: float,
    exit_z: float,
    max_hold: int,
    z_stop: float | float("nan"),
    method: MethodSpec,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = pd.Series(score.index.date.astype(str), index=score.index)
    pos = np.zeros(len(score), dtype=float)
    cost_ret = np.zeros(len(score), dtype=float)
    exit_reason = np.array([""] * len(score), dtype=object)
    current = 0.0
    entry_i = -1

    svals = score.to_numpy(float)
    costs = cost.reindex(score.index).fillna(0.0).to_numpy(float)

    for i, val in enumerate(svals):
        if i > 0 and dates.iloc[i] != dates.iloc[i - 1] and current != 0.0:
            cost_ret[i] += costs[i]
            exit_reason[i] = "eod"
            current = 0.0
            entry_i = -1

        if np.isfinite(val):
            target = current
            reason = ""
            if current == 0.0:
                if val > entry_z:
                    target = -1.0
                elif val < -entry_z:
                    target = 1.0
                if target != 0.0 and method.passive_entry and rng.random() > method.passive_fill_prob:
                    target = 0.0
                    reason = "passive_skip"
            elif current > 0:
                if val > -exit_z:
                    target = 0.0
                    reason = "reversion"
                elif np.isfinite(z_stop) and val < -z_stop:
                    target = 0.0
                    reason = "stop_loss"
                elif i - entry_i >= max_hold:
                    target = 0.0
                    reason = "max_hold"
            elif current < 0:
                if val < exit_z:
                    target = 0.0
                    reason = "reversion"
                elif np.isfinite(z_stop) and val > z_stop:
                    target = 0.0
                    reason = "stop_loss"
                elif i - entry_i >= max_hold:
                    target = 0.0
                    reason = "max_hold"

            delta = target - current
            if delta != 0.0:
                if current == 0.0 and target != 0.0 and method.passive_entry:
                    cost_ret[i] += method.adverse_selection_bps / 1e4
                    entry_i = i
                elif target == 0.0 and current != 0.0:
                    cost_ret[i] += abs(delta) * costs[i]
                    exit_reason[i] = reason or "exit"
                    entry_i = -1
                else:
                    cost_ret[i] += abs(delta) * costs[i]
                    if target != 0.0:
                        entry_i = i
                current = target

        if i < len(score) - 1 and dates.iloc[i + 1] != dates.iloc[i] and current != 0.0:
            cost_ret[i] += costs[i]
            exit_reason[i] = "eod"
            current = 0.0
            entry_i = -1
        pos[i] = current

    frame = pd.DataFrame(index=score.index)
    frame["score"] = score
    frame["position"] = pos
    frame["turnover"] = frame["position"].diff().abs().fillna(frame["position"].abs())
    frame["gross_ret"] = frame["position"].shift(1).fillna(0.0) * residual.reindex(score.index).fillna(0.0)
    frame["cost_ret"] = cost_ret
    frame["net_ret"] = frame["gross_ret"] - frame["cost_ret"]
    frame["exit_reason"] = exit_reason

    rows = []
    for sample, mask in masks(frame.index).items():
        part = frame.loc[mask]
        rows.append(
            {
                "sample": sample,
                "gross_bps": float(1e4 * part["gross_ret"].sum()),
                "cost_bps": float(1e4 * part["cost_ret"].sum()),
                "net_bps": float(1e4 * part["net_ret"].sum()),
                "trades": int((part["turnover"] > 0).sum()),
                "cost_share": float((1e4 * part["cost_ret"].sum()) / max(1e-9, abs(1e4 * part["gross_ret"].sum()))),
            }
        )
    return frame, pd.DataFrame(rows)


def deflated_sharpe_like(net_ret: pd.Series, n_trials: int) -> dict[str, float]:
    x = net_ret.dropna().to_numpy(float)
    if len(x) < 30 or np.std(x, ddof=1) <= 0:
        return {"sharpe": np.nan, "dsr_pvalue": np.nan}
    sr = float(np.sqrt(252 * MINUTES_PER_DAY) * np.mean(x) / np.std(x, ddof=1))
    g3 = float(skew(x))
    g4 = float(kurtosis(x, fisher=False))
    trials = max(1, int(n_trials))
    sr_star = float(norm.ppf(1.0 - 1.0 / max(2, trials)))
    denom = np.sqrt(max(1e-12, (1.0 - g3 * sr + ((g4 - 1.0) / 4.0) * sr * sr) / (len(x) - 1)))
    z = (sr - sr_star) / denom
    return {"sharpe": sr, "dsr_pvalue": float(1.0 - norm.cdf(z))}


def no_trade_gate(row: pd.Series, cost2x_net: float, latency1_net: float) -> tuple[bool, str]:
    if row["validation_net_bps"] <= 0:
        return False, "validation_net<=0"
    if row["validation_trades"] < 10:
        return False, "too_few_validation_trades"
    if row["validation_cost_share"] >= 0.75:
        return False, "cost_share>=0.75"
    if cost2x_net < 0:
        return False, "2x_cost_net<0"
    if latency1_net < 0:
        return False, "latency1_net<0"
    return True, "passed"


def signal_bucket_test(views: dict[str, pd.DataFrame]) -> pd.DataFrame:
    holdings = pd.read_csv(TABLES / "selected_xlk_holdings.csv")
    used = [s for s in holdings.loc[holdings.get("used_in_clean_panel", True).astype(bool), "symbol"].head(5) if s in views["microprice"].columns]
    weights = holdings.set_index("symbol").loc[used, "basket_weight"].astype(float)
    weights = weights / weights.sum()
    micro = views["microprice"]
    ret_micro = log_returns(micro)
    basket_ret = (ret_micro[used] * weights).sum(axis=1)
    basket_log = np.log(float(micro[ETF].iloc[0])) + basket_ret.cumsum()
    raw = np.log(micro[ETF]) - basket_log
    signal = 1e4 * (raw - raw.rolling(MINUTES_PER_DAY * 5, min_periods=MINUTES_PER_DAY).mean().shift(1))
    xlk_ret = log_returns(views["mid"])[ETF]
    rows = []
    sample_map = masks(signal.index)
    for sample, mask in sample_map.items():
        sig = signal.loc[mask].dropna()
        if len(sig) < 100:
            continue
        decile = pd.qcut(sig.rank(method="first"), 10, labels=False, duplicates="drop")
        for horizon in [1, 5, 15, 30, 60]:
            future = xlk_ret.rolling(horizon).sum().shift(-horizon).reindex(sig.index)
            tmp = pd.DataFrame({"decile": decile, "future_bps": 1e4 * future})
            for d, part in tmp.dropna().groupby("decile"):
                rows.append(
                    {
                        "sample": sample,
                        "horizon_min": horizon,
                        "signal_decile": int(d),
                        "mean_future_return_bps": float(part["future_bps"].mean()),
                        "count": int(len(part)),
                    }
                )
    return pd.DataFrame(rows)


def main() -> None:
    ensure_output_dirs()
    panel = load_panel()
    views = make_views(panel)
    ret = log_returns(views["mid"])
    m = masks(ret.index)
    train_mask = m["train"]
    val_mask = m["validation"]
    test_mask = m["test"]

    registry_rows = []
    exit_rows = []
    trial_id = 0
    n_trials = len(METHODS) * len(constituents()) * len(ENTRY_GRID) * len(EXIT_GRID) * len(MAX_HOLD_GRID) * len(STOP_GRID)

    for method in METHODS:
        for stock in constituents():
            if stock not in ret.columns:
                continue
            state = build_pair_state(views, ret, stock, method, train_mask)
            if state.get("skip"):
                registry_rows.append(
                    {
                        "trial_id": trial_id,
                        "strategy_family": "pair_trading",
                        "pair_or_basket": f"{ETF}-{stock}",
                        "method": method.method,
                        "selected_flag": False,
                        "gate_selected_flag": False,
                        "skip_reason": state.get("reason"),
                        "adf_p": state.get("adf_p", np.nan),
                    }
                )
                trial_id += 1
                continue
            for entry in ENTRY_GRID:
                for exit_band in EXIT_GRID:
                    if exit_band >= entry:
                        continue
                    for max_hold in MAX_HOLD_GRID:
                        for stop in STOP_GRID:
                            if np.isfinite(stop) and stop <= entry:
                                continue
                            frame, summary = run_strategy(
                                state["score"],
                                state["residual"],
                                state["cost"],
                                entry,
                                exit_band,
                                max_hold,
                                stop,
                                method,
                                seed=trial_id + 101,
                            )
                            val = summary[summary["sample"].eq("validation")].iloc[0]
                            test = summary[summary["sample"].eq("test")].iloc[0]
                            cost2_frame = frame.copy()
                            cost2_frame["net_ret"] = cost2_frame["gross_ret"] - 2.0 * cost2_frame["cost_ret"]
                            latency_pos = frame["position"].shift(1).fillna(0.0)
                            latency_turn = latency_pos.diff().abs().fillna(latency_pos.abs())
                            latency_net = latency_pos.shift(1).fillna(0.0) * state["residual"].reindex(frame.index).fillna(0.0) - latency_turn * state["cost"].reindex(frame.index).fillna(0.0)
                            cost2_test = float(1e4 * cost2_frame.loc[test_mask, "net_ret"].sum())
                            latency1_test = float(1e4 * latency_net.loc[test_mask].sum())
                            dsr = deflated_sharpe_like(frame.loc[test_mask, "net_ret"], n_trials)
                            row = {
                                "trial_id": trial_id,
                                "strategy_family": "pair_trading",
                                "universe": "XLK_top20_cleaned",
                                "pair_or_basket": f"{ETF}-{stock}",
                                "method": method.method,
                                "signal": method.signal_method,
                                "hedge_method": method.hedge_method,
                                "execution_mode": "passive_entry_stress" if method.passive_entry else "aggressive_cross",
                                "passive_fill_prob": method.passive_fill_prob,
                                "adverse_selection_bps": method.adverse_selection_bps,
                                "entry_z": entry,
                                "exit_z": exit_band,
                                "max_hold": max_hold,
                                "z_stop": stop,
                                "beta": state["beta"],
                                "adf_p": state["adf_p"],
                                "ou_half_life_minutes": state.get("ou_half_life_minutes", np.nan),
                                "validation_gross_bps": val["gross_bps"],
                                "validation_cost_bps": val["cost_bps"],
                                "validation_net_bps": val["net_bps"],
                                "validation_trades": val["trades"],
                                "validation_cost_share": val["cost_share"],
                                "test_gross_bps": test["gross_bps"],
                                "test_cost_bps": test["cost_bps"],
                                "test_net_bps": test["net_bps"],
                                "test_trades": test["trades"],
                                "test_cost_share": test["cost_share"],
                                "test_2x_cost_net_bps": cost2_test,
                                "test_latency1_net_bps": latency1_test,
                                **dsr,
                                "selected_flag": False,
                                "gate_selected_flag": False,
                                "skip_reason": "",
                            }
                            registry_rows.append(row)
                            for sample, mask in m.items():
                                part = frame.loc[mask & frame["exit_reason"].astype(bool)]
                                if part.empty:
                                    continue
                                for reason, sub in part.groupby("exit_reason"):
                                    exit_rows.append(
                                        {
                                            "trial_id": trial_id,
                                            "pair_or_basket": f"{ETF}-{stock}",
                                            "method": method.method,
                                            "sample": sample,
                                            "exit_reason": reason,
                                            "trades": int(len(sub)),
                                            "gross_bps": float(1e4 * frame.loc[sub.index, "gross_ret"].sum()),
                                            "cost_bps": float(1e4 * frame.loc[sub.index, "cost_ret"].sum()),
                                            "net_bps": float(1e4 * frame.loc[sub.index, "net_ret"].sum()),
                                        }
                                    )
                            trial_id += 1

    registry = pd.DataFrame(registry_rows)
    active = registry[registry["skip_reason"].fillna("").eq("")].copy()
    selected = []
    for (pair, method), group in active.groupby(["pair_or_basket", "method"]):
        best = group.sort_values(["validation_net_bps", "validation_trades"], ascending=[False, False]).head(1)
        selected.append(best)
    selected_df = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame()
    registry.loc[registry["trial_id"].isin(selected_df["trial_id"]), "selected_flag"] = True

    gate_rows = []
    gated_ids = []
    for _, row in selected_df.iterrows():
        ok, reason = no_trade_gate(row, row["test_2x_cost_net_bps"], row["test_latency1_net_bps"])
        if ok:
            gated_ids.append(int(row["trial_id"]))
        gate_rows.append({**row.to_dict(), "gate_selected_flag": ok, "gate_reason": reason})
    registry.loc[registry["trial_id"].isin(gated_ids), "gate_selected_flag"] = True
    gate = pd.DataFrame(gate_rows)

    summary_rows = []
    for method, group in gate.groupby("method"):
        raw = group
        gated = group[group["gate_selected_flag"]]
        summary_rows.append(
            {
                "method": method,
                "selected_pairs": int(len(raw)),
                "gate_pass_pairs": int(len(gated)),
                "raw_validation_net_bps": float(raw["validation_net_bps"].sum()),
                "raw_test_net_bps": float(raw["test_net_bps"].sum()),
                "raw_positive_test_pairs": int((raw["test_net_bps"] > 0).sum()),
                "gate_test_net_bps": float(gated["test_net_bps"].sum()) if len(gated) else 0.0,
                "gate_positive_test_pairs": int((gated["test_net_bps"] > 0).sum()) if len(gated) else 0,
                "test_trades": int(raw["test_trades"].sum()),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values("gate_test_net_bps", ascending=False)

    buckets = signal_bucket_test(views)

    registry.to_csv(TABLES / "top20_trial_registry.csv", index=False)
    summary.to_csv(TABLES / "top20_method_comparison_summary.csv", index=False)
    gate.sort_values("test_net_bps", ascending=False).to_csv(TABLES / "top20_pair_leaderboard.csv", index=False)
    pd.DataFrame(exit_rows).to_csv(TABLES / "top20_exit_reason_audit.csv", index=False)
    gate.to_csv(TABLES / "top20_no_trade_gate.csv", index=False)
    buckets.to_csv(TABLES / "top20_signal_bucket.csv", index=False)

    if not summary.empty:
        plt.figure(figsize=(9, 4.8))
        y = np.arange(len(summary))
        plt.barh(y, summary["raw_test_net_bps"], color="#9A9A9A", label="validation-selected raw")
        plt.barh(y, summary["gate_test_net_bps"], color="#2F6DB3", label="after no-trade gate")
        plt.axvline(0, color="black", linewidth=0.8)
        plt.yticks(y, summary["method"])
        plt.xlabel("test net bps across selected pairs")
        plt.title("Top20 Pair Diagnostics: Method Comparison")
        plt.legend()
        plt.tight_layout()
        plt.savefig(FIGURES / "top20_method_comparison.png", dpi=180)
        plt.close()

    if not buckets.empty:
        test_b = buckets[(buckets["sample"] == "test") & (buckets["horizon_min"].isin([15, 60]))]
        plt.figure(figsize=(9, 4.8))
        for h, part in test_b.groupby("horizon_min"):
            plt.plot(part["signal_decile"], part["mean_future_return_bps"], marker="o", label=f"{h} min")
        plt.axhline(0, color="black", linewidth=0.8)
        plt.xlabel("signal decile")
        plt.ylabel("mean future XLK return, bps")
        plt.title("XLK-Only Timing Signal Bucket Test")
        plt.legend()
        plt.tight_layout()
        plt.savefig(FIGURES / "top20_signal_bucket.png", dpi=180)
        plt.close()

    print("[top20] method comparison")
    print(summary.to_string(index=False))
    print("[top20] no-trade gate")
    print(gate[["pair_or_basket", "method", "validation_net_bps", "test_net_bps", "gate_selected_flag", "gate_reason"]].head(20).to_string(index=False))


if __name__ == "__main__":
    main()
