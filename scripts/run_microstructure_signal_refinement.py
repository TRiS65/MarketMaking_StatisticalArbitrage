#!/usr/bin/env python3
"""Lecture-driven microstructure refinement for XLK-only timing.

This script turns the Baruch microstructure lecture ideas into a lightweight,
auditable experiment on the expanded TAQ panel:

- order book imbalance and microprice premium;
- Lee-Ready style signed trade/order-flow proxy;
- spread and volatility state filters;
- Kyle-style impact/liquidity proxy;
- execution-aware thresholding on predicted XLK returns.

It is intentionally simple: a ridge linear predictor is fit on train only, the
entry threshold is selected on validation, and test is reported once with
sign-flip / always-long / always-short controls.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from project_config import ETF, MINUTES_PER_DAY, PROCESSED, TABLES, OUTPUT, metadata


def load_wide(top_n: int) -> tuple[pd.DataFrame, pd.Series]:
    panel = pd.read_parquet(PROCESSED / "research_panel.parquet")
    panel["minute"] = pd.to_datetime(panel["minute"])
    holdings = pd.read_csv(TABLES / "selected_xlk_holdings.csv")
    holdings = holdings[holdings["used_in_clean_panel"].astype(bool)].head(top_n)
    weights = holdings.set_index("symbol")["basket_weight"].astype(float)
    weights = weights / weights.sum()
    cols = ["mid", "microprice", "spread_bps", "imbalance", "last_trade_price", "volume", "trade_count"]
    frames = []
    for c in cols:
        piv = panel.pivot(index="minute", columns="symbol", values=c).sort_index()
        piv.columns = [f"{c}_{s}" for s in piv.columns]
        frames.append(piv)
    wide = pd.concat(frames, axis=1).sort_index()

    dates = sorted(pd.Series(wide.index.date.astype(str)).unique())
    full = [pd.date_range(f"{d} 09:30:00", periods=MINUTES_PER_DAY, freq="min") for d in dates]
    full_index = full[0].append(full[1:])
    wide = wide.reindex(full_index)
    key = pd.Series(wide.index.date.astype(str), index=wide.index)
    quote_cols = [c for c in wide.columns if c.startswith(("mid_", "microprice_", "spread_bps_", "imbalance_"))]
    trade_cols = [c for c in wide.columns if c.startswith(("last_trade_price_", "volume_", "trade_count_"))]
    wide[quote_cols] = wide[quote_cols].groupby(key, group_keys=False).ffill(limit=5)
    wide[trade_cols] = wide[trade_cols].fillna(0.0)
    needed = [f"mid_{ETF}", f"microprice_{ETF}", f"spread_bps_{ETF}"] + [f"mid_{s}" for s in weights.index]
    wide = wide.dropna(subset=needed)
    return wide, weights


def logret(x: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    r = np.log(x.astype(float)).diff().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    idx = x.index.to_series()
    continuous = (idx.diff() == pd.Timedelta(minutes=1)) & (idx.dt.date == idx.shift(1).dt.date)
    r.loc[~continuous.values] = 0.0
    return r.clip(-0.05, 0.05)


def build_features(wide: pd.DataFrame, weights: pd.Series, horizon: int) -> pd.DataFrame:
    syms = weights.index.tolist()
    xlk_mid = wide[f"mid_{ETF}"]
    xlk_micro = wide[f"microprice_{ETF}"]
    mid = pd.DataFrame({s: wide[f"mid_{s}"] for s in syms})
    micro = pd.DataFrame({s: wide[f"microprice_{s}"] for s in syms})
    mid_ret = logret(mid)
    micro_ret = logret(micro)
    basket_mid_log = np.log(float(xlk_mid.iloc[0])) + (mid_ret * weights).sum(axis=1).cumsum()
    basket_micro_log = np.log(float(xlk_micro.iloc[0])) + (micro_ret * weights).sum(axis=1).cumsum()
    premium_mid_bps = 1e4 * (np.log(xlk_mid) - basket_mid_log)
    premium_micro_bps = 1e4 * (np.log(xlk_micro) - basket_micro_log)
    center = premium_micro_bps.rolling(10 * MINUTES_PER_DAY, min_periods=MINUTES_PER_DAY).mean().shift(1)
    roll_premium_bps = premium_micro_bps - center

    basket_imb = sum(weights[s] * wide.get(f"imbalance_{s}", pd.Series(0.0, index=wide.index)).fillna(0.0) for s in syms)
    xlk_imb = wide[f"imbalance_{ETF}"].fillna(0.0)
    xlk_spread = wide[f"spread_bps_{ETF}"].astype(float)
    xlk_ret = logret(xlk_mid)
    realized_vol_bps = 1e4 * xlk_ret.rolling(30, min_periods=10).std().shift(1)

    last = wide[f"last_trade_price_{ETF}"].replace(0, np.nan)
    signed = np.sign(last - xlk_mid).replace(0, np.nan).fillna(0.0)
    volume = wide[f"volume_{ETF}"].astype(float).fillna(0.0)
    signed_flow = signed * np.sqrt(volume.clip(lower=0.0))
    ofi_5 = signed_flow.rolling(5, min_periods=1).sum().shift(1)
    ofi_30 = signed_flow.rolling(30, min_periods=5).sum().shift(1)

    dollar_signed = signed * volume * xlk_mid
    kyle_num = xlk_ret.abs().rolling(60, min_periods=20).sum().shift(1)
    kyle_den = dollar_signed.abs().rolling(60, min_periods=20).sum().shift(1) / 1e6
    kyle_lambda = (1e4 * kyle_num / kyle_den.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)

    future_ret_bps = 1e4 * (np.log(xlk_mid.shift(-horizon)) - np.log(xlk_mid))
    same_day = wide.index.to_series().dt.date == wide.index.to_series().shift(-horizon).dt.date
    future_ret_bps.loc[~same_day.values] = np.nan

    feat = pd.DataFrame({
        "premium_mid_bps": premium_mid_bps,
        "premium_micro_bps": premium_micro_bps,
        "roll_premium_bps": roll_premium_bps,
        "xlk_micro_gap_bps": 1e4 * np.log(xlk_micro / xlk_mid),
        "xlk_imbalance": xlk_imb,
        "basket_imbalance": basket_imb,
        "imbalance_diff": xlk_imb - basket_imb,
        "xlk_spread_bps": xlk_spread,
        "realized_vol_bps": realized_vol_bps,
        "signed_flow_5": ofi_5,
        "signed_flow_30": ofi_30,
        "kyle_lambda_proxy": kyle_lambda,
        "target_future_ret_bps": future_ret_bps,
    }, index=wide.index)
    for lag in [1, 5, 15]:
        feat[f"xlk_ret_lag{lag}_bps"] = 1e4 * xlk_ret.shift(lag)
    return feat.replace([np.inf, -np.inf], np.nan).dropna()


def standardize(train: pd.DataFrame, other: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = train.replace([np.inf, -np.inf], np.nan).clip(-1e8, 1e8)
    other = other.replace([np.inf, -np.inf], np.nan).clip(-1e8, 1e8)
    mu = train.mean()
    sd = train.std().replace(0, np.nan)
    x_train = ((train - mu) / sd).replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-8, 8)
    x_other = ((other - mu) / sd).replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-8, 8)
    return x_train, x_other


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
    x1 = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(x1.shape[1]) * alpha
    penalty[0, 0] = 0.0
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return np.linalg.solve(x1.T @ x1 + penalty, x1.T @ y)


def predict(beta: np.ndarray, x: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return np.column_stack([np.ones(len(x)), x]) @ beta


def positions_from_pred(pred: pd.Series, threshold: float, edge_mult: float, spread: pd.Series) -> pd.Series:
    pos = pd.Series(0.0, index=pred.index)
    gate = pred.abs() > np.maximum(threshold, edge_mult * spread)
    pos.loc[gate & (pred > 0)] = 1.0
    pos.loc[gate & (pred < 0)] = -1.0
    return pos


def backtest(pos: pd.Series, wide: pd.DataFrame, cost_mult: float = 1.0, latency: int = 0) -> pd.DataFrame:
    p = pos.shift(latency).fillna(0.0)
    ret = logret(wide[f"mid_{ETF}"])
    turnover = p.diff().abs().fillna(p.abs())
    cost = turnover * (wide[f"spread_bps_{ETF}"] / 2.0) / 1e4 * cost_mult
    gross = p.shift(1).fillna(0.0) * ret
    return pd.DataFrame({"position": p, "turnover": turnover, "gross_ret": gross, "cost_ret": cost, "net_ret": gross - cost})


def stats(frame: pd.DataFrame, mask: pd.Series, label: str) -> dict:
    sub = frame.loc[mask]
    return {
        f"{label}_gross_bps": float(1e4 * sub["gross_ret"].sum()),
        f"{label}_cost_bps": float(1e4 * sub["cost_ret"].sum()),
        f"{label}_net_bps": float(1e4 * sub["net_ret"].sum()),
        f"{label}_trades": int((sub["turnover"] > 0).sum()),
        f"{label}_avg_abs_position": float(sub["position"].abs().mean()),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--alpha", type=float, default=25.0)
    ap.add_argument("--edge-mult", type=float, default=2.5)
    args = ap.parse_args()
    TABLES.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    wide, weights = load_wide(args.top_n)
    feat = build_features(wide, weights, args.horizon)
    meta = metadata()
    train_mask = feat.index < pd.Timestamp(meta["train_end"])
    val_mask = (feat.index >= pd.Timestamp(meta["train_end"])) & (feat.index < pd.Timestamp(meta["validation_end"]))
    test_mask = (feat.index >= pd.Timestamp(meta["validation_end"])) & (feat.index < pd.Timestamp(meta["test_end"]))

    y = feat["target_future_ret_bps"].replace([np.inf, -np.inf], np.nan).clip(-200, 200)
    cols = [c for c in feat.columns if c != "target_future_ret_bps"]
    x_train, x_all = standardize(feat.loc[train_mask, cols], feat[cols])
    beta = fit_ridge(x_train.to_numpy(), y.loc[train_mask].to_numpy(), args.alpha)
    pred = pd.Series(predict(beta, x_all.to_numpy()), index=feat.index)

    rows = []
    for threshold in [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0, 12.0]:
        pos = positions_from_pred(pred, threshold, args.edge_mult, wide.loc[pred.index, f"spread_bps_{ETF}"])
        bt = backtest(pos, wide.loc[pred.index])
        row = {"threshold_pred_bps": threshold}
        row.update(stats(bt, pd.Series(train_mask, index=feat.index), "train"))
        row.update(stats(bt, pd.Series(val_mask, index=feat.index), "validation"))
        row.update(stats(bt, pd.Series(test_mask, index=feat.index), "test"))
        rows.append(row)
    grid = pd.DataFrame(rows)
    valid = grid[(grid["validation_net_bps"] > 0) & (grid["validation_trades"] >= 10)].copy()
    if valid.empty:
        selected = grid.sort_values("validation_net_bps", ascending=False).iloc[0].copy()
        decision = "no_trade"
        reason = "no validation-positive threshold with enough trades"
    else:
        selected = valid.sort_values(["validation_net_bps", "validation_trades"], ascending=False).iloc[0].copy()
        decision = "candidate_active" if selected["test_net_bps"] > 0 else "no_trade"
        reason = "test_net_positive" if decision == "candidate_active" else "validation-positive but test-negative"

    threshold = float(selected["threshold_pred_bps"])
    pos = positions_from_pred(pred, threshold, args.edge_mult, wide.loc[pred.index, f"spread_bps_{ETF}"])
    controls = []
    for name, p in [
        ("selected", pos),
        ("sign_flip", -pos),
        ("active_always_long", pd.Series(np.where(pos != 0, 1.0, 0.0), index=pos.index)),
        ("active_always_short", pd.Series(np.where(pos != 0, -1.0, 0.0), index=pos.index)),
    ]:
        bt = backtest(p, wide.loc[pred.index])
        row = {"control": name}
        row.update(stats(bt, pd.Series(train_mask, index=feat.index), "train"))
        row.update(stats(bt, pd.Series(val_mask, index=feat.index), "validation"))
        row.update(stats(bt, pd.Series(test_mask, index=feat.index), "test"))
        controls.append(row)

    sens = []
    for cm in [1.0, 1.5, 2.0, 3.0]:
        for latency in [0, 1]:
            bt = backtest(pos, wide.loc[pred.index], cost_mult=cm, latency=latency)
            row = {"cost_multiplier": cm, "latency_min": latency}
            row.update(stats(bt, pd.Series(train_mask, index=feat.index), "train"))
            row.update(stats(bt, pd.Series(val_mask, index=feat.index), "validation"))
            row.update(stats(bt, pd.Series(test_mask, index=feat.index), "test"))
            sens.append(row)

    coef = pd.DataFrame({"feature": ["intercept"] + cols, "coef": beta})
    selection = pd.DataFrame([{
        "decision": decision,
        "reason": reason,
        "horizon_min": args.horizon,
        "top_n": args.top_n,
        "basket_symbols": " ".join(weights.index),
        "threshold_pred_bps": threshold,
        "edge_mult": args.edge_mult,
        "train_net_bps": selected["train_net_bps"],
        "validation_net_bps": selected["validation_net_bps"],
        "test_net_bps": selected["test_net_bps"],
        "test_trades": selected["test_trades"],
    }])

    grid.to_csv(TABLES / "microstructure_refinement_grid.csv", index=False)
    selection.to_csv(TABLES / "microstructure_refinement_selection.csv", index=False)
    pd.DataFrame(controls).to_csv(TABLES / "microstructure_refinement_controls.csv", index=False)
    pd.DataFrame(sens).to_csv(TABLES / "microstructure_refinement_cost_latency.csv", index=False)
    coef.sort_values("coef", key=lambda s: s.abs(), ascending=False).to_csv(TABLES / "microstructure_refinement_coefficients.csv", index=False)
    report = (
        "# Microstructure Signal Refinement\n\n"
        "Lecture-driven features: basket premium, quote imbalance, signed order-flow proxy, spread state, realized volatility, and Kyle-style liquidity proxy. "
        "The model is trained on train only; threshold is selected on validation.\n\n"
        "## Selection\n\n" + selection.to_markdown(index=False)
        + "\n\n## Controls\n\n" + pd.DataFrame(controls).to_markdown(index=False)
        + "\n\n## Top Coefficients\n\n" + coef.sort_values("coef", key=lambda s: s.abs(), ascending=False).head(12).to_markdown(index=False)
    )
    (OUTPUT / "microstructure_refinement_report.md").write_text(report)
    print(f"[ok] wrote {TABLES / 'microstructure_refinement_selection.csv'}")
    print(f"[ok] wrote {OUTPUT / 'microstructure_refinement_report.md'}")


if __name__ == "__main__":
    main()
