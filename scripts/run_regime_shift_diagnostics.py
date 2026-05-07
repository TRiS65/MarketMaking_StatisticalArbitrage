#!/usr/bin/env python3
"""Regime-shift diagnostics for XLK sparse-basket timing.

The goal is explanatory, not another optimizer.  We measure whether the poor
expanded-sample performance comes from:

1. XLK/basket linkage instability;
2. signal-to-future-return sign changes;
3. higher volatility/spread/cost regimes;
4. side-specific exposure, e.g. long XLK vs short XLK months.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from project_config import ETF, MINUTES_PER_DAY, PROCESSED, TABLES, OUTPUT, FIGURES
from run_timing_robustness import (
    TimingRule,
    align_panel,
    backtest_position,
    build_signal,
    load_weights,
    log_returns,
    position_from_signal,
)


def future_return_bps(px: pd.Series, horizon: int) -> pd.Series:
    out = 1e4 * (np.log(px.shift(-horizon)) - np.log(px))
    same_day = px.index.to_series().dt.date == px.index.to_series().shift(-horizon).dt.date
    out.loc[~same_day.values] = np.nan
    return out.replace([np.inf, -np.inf], np.nan)


def safe_corr(a: pd.Series, b: pd.Series) -> float:
    ok = a.notna() & b.notna()
    if ok.sum() < 50 or a.loc[ok].std() <= 0 or b.loc[ok].std() <= 0:
        return np.nan
    return float(a.loc[ok].corr(b.loc[ok]))


def beta_and_resid(y: pd.Series, x: pd.Series) -> tuple[float, float, float]:
    ok = y.notna() & x.notna()
    if ok.sum() < 50 or x.loc[ok].var() <= 0:
        return np.nan, np.nan, np.nan
    beta = float(np.cov(y.loc[ok], x.loc[ok], ddof=0)[0, 1] / np.var(x.loc[ok]))
    resid = y.loc[ok] - beta * x.loc[ok]
    return beta, float(1e4 * resid.std()), float(y.loc[ok].corr(x.loc[ok]))


def decile_edge(signal: pd.Series, future: pd.Series) -> tuple[float, float, float]:
    df = pd.DataFrame({"signal": signal, "future": future}).dropna()
    if len(df) < 200:
        return np.nan, np.nan, np.nan
    df["decile"] = pd.qcut(df["signal"].rank(method="first"), 10, labels=False)
    low = float(df.loc[df["decile"] == 0, "future"].mean())
    high = float(df.loc[df["decile"] == 9, "future"].mean())
    # Contrarian premium timing wants low-signal future return > high-signal future return.
    return low, high, low - high


def monthly_pnl(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month, sub in frame.groupby(frame.index.to_period("M")):
        pos = sub["position"].shift(1).fillna(0.0)
        long = sub[pos > 0]
        short = sub[pos < 0]
        rows.append(
            {
                "month": str(month),
                "gross_bps": float(1e4 * sub["gross_ret"].sum()),
                "cost_bps": float(1e4 * sub["cost_ret"].sum()),
                "net_bps": float(1e4 * sub["net_ret"].sum()),
                "trades": int((sub["turnover"] > 0).sum()),
                "avg_abs_position": float(sub["position"].abs().mean()),
                "long_gross_bps": float(1e4 * long["gross_ret"].sum()),
                "short_gross_bps": float(1e4 * short["gross_ret"].sum()),
                "long_minutes": int((sub["position"] > 0).sum()),
                "short_minutes": int((sub["position"] < 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    weights = load_weights(5)
    mid, micro, spread_bps, bid, ask = align_panel(weights)
    rule = TimingRule("micro_shrink_0.75", 0.75, 10, 60.0, 0.0, 240)
    signal = build_signal(mid, micro, weights, rule)
    pos = position_from_signal(signal, rule.entry_bps, rule.exit_bps, rule.max_hold_minutes)
    frame = backtest_position(pos, mid, spread_bps, bid=bid, ask=ask, cost_model="exact_bidask")
    frame["signal_bps"] = signal

    xlk_ret = log_returns(mid[ETF])
    basket_ret = (log_returns(mid[weights.index]) * weights).sum(axis=1)
    xlk_future = {h: future_return_bps(mid[ETF], h) for h in [5, 15, 30, 60]}
    alpha_score = -signal

    market_rows = []
    ic_rows = []
    for month, ix in pd.Series(mid.index, index=mid.index).groupby(mid.index.to_period("M")).groups.items():
        y = xlk_ret.loc[ix]
        x = basket_ret.loc[ix]
        beta, resid_vol, corr = beta_and_resid(y, x)
        market_rows.append(
            {
                "month": str(month),
                "xlk_return_bps": float(1e4 * y.sum()),
                "basket_return_bps": float(1e4 * x.sum()),
                "xlk_basket_corr_1m": corr,
                "xlk_on_basket_beta_1m": beta,
                "residual_vol_bps_1m": resid_vol,
                "xlk_realized_vol_bps_1m": float(1e4 * y.std()),
                "median_xlk_spread_bps": float(spread_bps.loc[ix, ETF].median()),
                "p90_xlk_spread_bps": float(spread_bps.loc[ix, ETF].quantile(0.90)),
                "signal_mean_bps": float(signal.loc[ix].mean()),
                "signal_std_bps": float(signal.loc[ix].std()),
                "signal_p10_bps": float(signal.loc[ix].quantile(0.10)),
                "signal_p90_bps": float(signal.loc[ix].quantile(0.90)),
                "abs_signal_gt_60_frac": float((signal.loc[ix].abs() > 60).mean()),
            }
        )
        for h, fut in xlk_future.items():
            low, high, edge = decile_edge(signal.loc[ix], fut.loc[ix])
            pred = alpha_score.loc[ix]
            ok = pred.notna() & fut.loc[ix].notna()
            direction_acc = float((np.sign(pred.loc[ok]) * fut.loc[ix].loc[ok] > 0).mean()) if ok.sum() else np.nan
            ic_rows.append(
                {
                    "month": str(month),
                    "horizon_min": h,
                    "alpha_ic_corr": safe_corr(pred, fut.loc[ix]),
                    "direction_accuracy": direction_acc,
                    "low_signal_future_bps": low,
                    "high_signal_future_bps": high,
                    "contrarian_decile_edge_bps": edge,
                    "obs": int(ok.sum()),
                }
            )

    market = pd.DataFrame(market_rows)
    ic = pd.DataFrame(ic_rows)
    pnl = monthly_pnl(frame)

    train_months = ["2026-01", "2026-02"]
    test_months = ["2026-03", "2026-04"]
    summary_rows = []
    for metric in ["xlk_basket_corr_1m", "xlk_on_basket_beta_1m", "residual_vol_bps_1m", "median_xlk_spread_bps", "signal_std_bps"]:
        tr = market.loc[market["month"].isin(train_months), metric].mean()
        te = market.loc[market["month"].isin(test_months), metric].mean()
        summary_rows.append({"metric": metric, "train_avg": tr, "test_avg": te, "test_minus_train": te - tr})
    for h in [5, 15, 30, 60]:
        sub = ic[ic["horizon_min"] == h]
        tr = sub.loc[sub["month"].isin(train_months), "alpha_ic_corr"].mean()
        te = sub.loc[sub["month"].isin(test_months), "alpha_ic_corr"].mean()
        summary_rows.append({"metric": f"alpha_ic_{h}m", "train_avg": tr, "test_avg": te, "test_minus_train": te - tr})
        tr_edge = sub.loc[sub["month"].isin(train_months), "contrarian_decile_edge_bps"].mean()
        te_edge = sub.loc[sub["month"].isin(test_months), "contrarian_decile_edge_bps"].mean()
        summary_rows.append({"metric": f"contrarian_decile_edge_{h}m", "train_avg": tr_edge, "test_avg": te_edge, "test_minus_train": te_edge - tr_edge})
    summary = pd.DataFrame(summary_rows)

    market.to_csv(TABLES / "regime_monthly_market_state.csv", index=False)
    ic.to_csv(TABLES / "regime_signal_ic_by_month.csv", index=False)
    pnl.to_csv(TABLES / "regime_target_rule_monthly_pnl.csv", index=False)
    summary.to_csv(TABLES / "regime_shift_summary.csv", index=False)

    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    pnl.plot(x="month", y="net_bps", kind="bar", ax=axes[0], legend=False, color="#4C78A8")
    axes[0].axhline(0, color="black", linewidth=0.8)
    axes[0].set_title("Target timing rule monthly net P&L")
    axes[0].set_ylabel("bps")
    ic60 = ic[ic["horizon_min"] == 60]
    ic60.plot(x="month", y="alpha_ic_corr", kind="bar", ax=axes[1], legend=False, color="#F58518")
    axes[1].axhline(0, color="black", linewidth=0.8)
    axes[1].set_title("Alpha IC: -premium vs future 60-minute XLK return")
    axes[1].set_ylabel("corr")
    market.plot(x="month", y="residual_vol_bps_1m", kind="bar", ax=axes[2], legend=False, color="#54A24B")
    axes[2].set_title("XLK minus basket residual volatility")
    axes[2].set_ylabel("1m bps")
    fig.tight_layout()
    fig.savefig(FIGURES / "regime_shift_diagnostics.png", dpi=180)
    plt.close(fig)

    report = (
        "# Regime Shift Diagnostics\n\n"
        "This analysis checks whether the failed timing candidate is explained by a regime shift in the XLK/basket relation, signal direction, or execution state.\n\n"
        "## Summary: Train vs Test\n\n"
        + summary.to_markdown(index=False)
        + "\n\n## Monthly Market State\n\n"
        + market.to_markdown(index=False)
        + "\n\n## Monthly Signal IC\n\n"
        + ic.to_markdown(index=False)
        + "\n\n## Target Rule PnL Anatomy\n\n"
        + pnl.to_markdown(index=False)
        + "\n\n## Interpretation\n\n"
        "The poor result is consistent with regime instability, but not in the simple sense of wider XLK spreads. "
        "The key failure is that the basket-premium signal does not maintain a stable contrarian relationship with future XLK returns, and April contributes a large negative directional leg. "
        "The strict conclusion is still no-trade unless a future rule is explicitly gated by the detected regimes and validated on a later holdout.\n"
    )
    (OUTPUT / "regime_shift_report.md").write_text(report)
    print(f"[ok] wrote {TABLES / 'regime_shift_summary.csv'}")
    print(f"[ok] wrote {OUTPUT / 'regime_shift_report.md'}")


if __name__ == "__main__":
    main()
