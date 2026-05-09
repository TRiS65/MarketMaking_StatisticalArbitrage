#!/usr/bin/env python3
"""Supervised regime classifier for sparse-basket XLK timing.

The fixed gates in ``run_regime_gate_experiments.py`` diagnose the April
failure but still hard-code a regime rule.  This script instead learns a
three-state classifier from pre-holdout data:

    mean_reversion      -> trade the sparse-premium signal contrarian
    trend_continuation  -> trade the sparse-premium signal in the same direction
    no_trade            -> stay flat

The model is intentionally small and auditable.  Metadata train dates fit the
classifier, the validation split selects model/confidence threshold, and the
test split is reported as the untouched holdout.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, confusion_matrix

from project_config import ETF, FIGURES, MINUTES_PER_DAY, OUTPUT, TABLES, metadata
from run_timing_robustness import (
    TimingRule,
    align_panel,
    backtest_position,
    build_signal,
    load_weights,
    log_returns,
    summarize,
)

LABELS = {0: "no_trade", 1: "mean_reversion", 2: "trend_continuation"}


@dataclass(frozen=True)
class ClassifierSpec:
    train_scheme: str
    model_name: str
    horizon_min: int
    label_edge_bps: float
    confidence: float

    @property
    def name(self) -> str:
        return f"{self.train_scheme}_{self.model_name}_h{self.horizon_min}_edge{self.label_edge_bps:g}_p{self.confidence:g}"


def future_return_bps(px: pd.Series, horizon: int) -> pd.Series:
    out = 1e4 * (np.log(px.shift(-horizon)) - np.log(px))
    same_day = px.index.to_series().dt.date == px.index.to_series().shift(-horizon).dt.date
    out.loc[~same_day.values] = np.nan
    return out.replace([np.inf, -np.inf], np.nan)


def rolling_return_bps(px: pd.Series, lookback: int, same_day_only: bool = False) -> pd.Series:
    out = 1e4 * (np.log(px) - np.log(px.shift(lookback)))
    if same_day_only:
        same_day = px.index.to_series().dt.date == px.index.to_series().shift(lookback).dt.date
        out.loc[~same_day.values] = np.nan
    return out.replace([np.inf, -np.inf], np.nan)


def load_imbalance(symbols: list[str]) -> pd.DataFrame:
    panel = pd.read_parquet(TABLES.parents[1] / "data" / "processed" / "research_panel.parquet")
    panel["minute"] = pd.to_datetime(panel["minute"])
    imb = panel.pivot(index="minute", columns="symbol", values="imbalance").sort_index()
    dates = sorted(pd.Series(imb.index.date.astype(str)).unique())
    full = [pd.date_range(f"{d} 09:30:00", periods=MINUTES_PER_DAY, freq="min") for d in dates]
    full_index = full[0].append(full[1:])
    imb = imb.reindex(full_index)
    key = pd.Series(imb.index.date.astype(str), index=imb.index)
    return imb.groupby(key, group_keys=False).ffill(limit=5).reindex(columns=symbols)


def build_features(mid: pd.DataFrame, micro: pd.DataFrame, spread_bps: pd.DataFrame, signal: pd.Series, weights: pd.Series) -> pd.DataFrame:
    xlk_ret = log_returns(mid[ETF])
    basket_ret = (log_returns(mid[weights.index]) * weights).sum(axis=1)
    residual_ret = xlk_ret - basket_ret
    features = pd.DataFrame(index=signal.index)
    features["signal_bps"] = signal
    features["abs_signal_bps"] = signal.abs()
    features["signal_sign"] = np.sign(signal).fillna(0.0)
    for lb in [30, 60, 120, 390, 780, 1950]:
        same_day = lb < MINUTES_PER_DAY
        features[f"xlk_ret_{lb}m_bps"] = rolling_return_bps(mid[ETF], lb, same_day_only=same_day)
        basket_log = basket_ret.cumsum()
        br = 1e4 * (basket_log - basket_log.shift(lb))
        if same_day:
            same = mid.index.to_series().dt.date == mid.index.to_series().shift(lb).dt.date
            br.loc[~same.values] = np.nan
        features[f"basket_ret_{lb}m_bps"] = br
        features[f"resid_ret_{lb}m_bps"] = features[f"xlk_ret_{lb}m_bps"] - features[f"basket_ret_{lb}m_bps"]
    for lb in [60, 120, 390, 780]:
        features[f"signal_mean_{lb}m"] = signal.rolling(lb, min_periods=max(20, lb // 4)).mean().shift(1)
        features[f"signal_std_{lb}m"] = signal.rolling(lb, min_periods=max(20, lb // 4)).std().shift(1)
        features[f"signal_slope_{lb}m"] = signal - signal.shift(lb)
        features[f"xlk_vol_{lb}m_bps"] = 1e4 * xlk_ret.rolling(lb, min_periods=max(20, lb // 4)).std().shift(1)
        features[f"resid_vol_{lb}m_bps"] = 1e4 * residual_ret.rolling(lb, min_periods=max(20, lb // 4)).std().shift(1)
    features["xlk_spread_bps"] = spread_bps[ETF]
    features["spread_mean_120m"] = spread_bps[ETF].rolling(120, min_periods=30).mean().shift(1)
    micro_gap = 1e4 * np.log(micro[ETF] / mid[ETF])
    features["xlk_micro_gap_bps"] = micro_gap.replace([np.inf, -np.inf], np.nan)
    try:
        imb = load_imbalance([ETF] + list(weights.index)).reindex(features.index)
        features["xlk_imbalance"] = imb[ETF].fillna(0.0)
        features["basket_imbalance"] = (imb[weights.index].fillna(0.0) * weights).sum(axis=1)
        features["imbalance_diff"] = features["xlk_imbalance"] - features["basket_imbalance"]
    except Exception:
        features["xlk_imbalance"] = 0.0
        features["basket_imbalance"] = 0.0
        features["imbalance_diff"] = 0.0
    return features.replace([np.inf, -np.inf], np.nan)


def label_regime(signal: pd.Series, future_ret: pd.Series, entry_bps: float, edge_bps: float) -> pd.Series:
    desired_contrarian = pd.Series(0.0, index=signal.index)
    desired_contrarian.loc[signal > entry_bps] = -1.0
    desired_contrarian.loc[signal < -entry_bps] = 1.0
    payoff = desired_contrarian * future_ret
    label = pd.Series(0, index=signal.index, dtype=int)
    active = desired_contrarian != 0
    label.loc[active & (payoff > edge_bps)] = 1
    label.loc[active & (payoff < -edge_bps)] = 2
    return label


def make_model(model_name: str):
    if model_name == "rf_depth2":
        return RandomForestClassifier(n_estimators=160, max_depth=2, min_samples_leaf=200, class_weight="balanced_subsample", random_state=7, n_jobs=-1)
    if model_name == "rf_depth3":
        return RandomForestClassifier(n_estimators=160, max_depth=3, min_samples_leaf=160, class_weight="balanced_subsample", random_state=11, n_jobs=-1)
    if model_name == "rf_depth4":
        return RandomForestClassifier(n_estimators=180, max_depth=4, min_samples_leaf=140, class_weight="balanced_subsample", random_state=19, n_jobs=-1)
    raise ValueError(model_name)


def predict_labels(model, x: pd.DataFrame, confidence: float) -> pd.Series:
    proba = model.predict_proba(x)
    classes = list(model.classes_)
    label = pd.Series(0, index=x.index, dtype=int)
    best_pos = proba.argmax(axis=1)
    best_cls = np.array([classes[i] for i in best_pos], dtype=int)
    best_prob = proba.max(axis=1)
    confident = best_prob >= confidence
    label.loc[confident] = best_cls[confident]
    return label


def position_from_classifier(signal: pd.Series, pred_label: pd.Series, rule: TimingRule) -> pd.Series:
    vals = signal.to_numpy(dtype=float)
    labels = pred_label.reindex(signal.index).fillna(0).to_numpy(dtype=int)
    dates = pd.Series(signal.index.date.astype(str), index=signal.index).to_numpy()
    pos = np.zeros(len(signal), dtype=float)
    current = 0.0
    hold = 0
    for i, x in enumerate(vals):
        if i > 0 and dates[i] != dates[i - 1]:
            current = 0.0
            hold = 0
        desired = 0.0
        if np.isfinite(x) and abs(x) > rule.entry_bps:
            if labels[i] == 1:
                desired = -np.sign(x)
            elif labels[i] == 2:
                desired = np.sign(x)
        if current == 0.0:
            current = desired
            hold = 0 if current != 0.0 else hold
        else:
            hold += 1
            if desired == 0.0 or np.sign(desired) != np.sign(current) or abs(x) <= rule.exit_bps or hold >= rule.max_hold_minutes:
                current = 0.0
                hold = 0
        if i < len(vals) - 1 and dates[i + 1] != dates[i]:
            current = 0.0
            hold = 0
        pos[i] = current
    return pd.Series(pos, index=signal.index)


def period_mask(index: pd.Index, start: str, end: str) -> pd.Series:
    return pd.Series((index >= pd.Timestamp(start)) & (index < pd.Timestamp(end)), index=index)


def period_stats(frame: pd.DataFrame, start: str, end: str, prefix: str) -> dict:
    sub = frame.loc[(frame.index >= pd.Timestamp(start)) & (frame.index < pd.Timestamp(end))]
    return {
        f"{prefix}_gross_bps": float(1e4 * sub["gross_ret"].sum()),
        f"{prefix}_cost_bps": float(1e4 * sub["cost_ret"].sum()),
        f"{prefix}_net_bps": float(1e4 * sub["net_ret"].sum()),
        f"{prefix}_trades": int((sub["turnover"] > 0).sum()),
    }


def full_stats(frame: pd.DataFrame) -> dict:
    meta = metadata()
    sample_start = pd.Timestamp(meta.get("start", "2025-05-01"))
    train_end = pd.Timestamp(meta.get("train_end", "2026-02-01"))
    validation_end = pd.Timestamp(meta.get("validation_end", "2026-03-01"))
    test_end = pd.Timestamp(meta.get("test_end", meta.get("end", "2026-05-01")))
    out = {}
    for month_start in pd.date_range(sample_start.normalize().replace(day=1), test_end, freq="MS"):
        month = month_start.strftime("%Y-%m")
        month_end = month_start + pd.offsets.MonthBegin(1)
        out.update(period_stats(frame, month_start, month_end, month.replace("-", "_")))
    out.update(period_stats(frame, sample_start, train_end, "train"))
    out.update(period_stats(frame, train_end, validation_end, "validation"))
    out.update(period_stats(frame, validation_end, test_end, "test"))
    return out


def active_directional_control_stats(pos: pd.Series, mid: pd.DataFrame, spread_bps: pd.DataFrame, bid: pd.DataFrame, ask: pd.DataFrame) -> dict:
    active = pd.Series(np.where(pos != 0, 1.0, 0.0), index=pos.index)
    long_frame = backtest_position(active, mid, spread_bps, bid=bid, ask=ask, cost_model="exact_bidask")
    short_frame = backtest_position(-active, mid, spread_bps, bid=bid, ask=ask, cost_model="exact_bidask")
    long_stats = full_stats(long_frame)
    short_stats = full_stats(short_frame)
    return {
        "validation_always_long_net_bps": long_stats["validation_net_bps"],
        "validation_always_short_net_bps": short_stats["validation_net_bps"],
        "test_always_long_net_bps": long_stats["test_net_bps"],
        "test_always_short_net_bps": short_stats["test_net_bps"],
    }


def test_cost_latency(pos: pd.Series, mid: pd.DataFrame, spread_bps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cm in [1.0, 1.5, 2.0, 3.0]:
        for latency in [0, 1, 2]:
            frame = backtest_position(pos, mid, spread_bps, cost_model="halfspread", cost_multiplier=cm, latency_min=latency)
            row = {"cost_multiplier": cm, "latency_min": latency}
            row.update(full_stats(frame))
            rows.append(row)
    return pd.DataFrame(rows)


def monthly_side(frame: pd.DataFrame, strategy: str) -> pd.DataFrame:
    rows = []
    for month, sub in frame.groupby(frame.index.to_period("M")):
        lag = sub["position"].shift(1).fillna(0.0)
        long = sub.loc[lag > 0]
        short = sub.loc[lag < 0]
        rows.append(
            {
                "strategy": strategy,
                "month": str(month),
                "gross_bps": float(1e4 * sub["gross_ret"].sum()),
                "cost_bps": float(1e4 * sub["cost_ret"].sum()),
                "net_bps": float(1e4 * sub["net_ret"].sum()),
                "trades": int((sub["turnover"] > 0).sum()),
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
    features = build_features(mid, micro, spread_bps, signal, weights)

    feature_cols = [c for c in features.columns if c not in {"label", "future_ret_bps"}]
    meta = metadata()
    sample_start = pd.Timestamp(meta.get("start", "2025-05-01"))
    train_end = pd.Timestamp(meta.get("train_end", "2026-02-01"))
    validation_end = pd.Timestamp(meta.get("validation_end", "2026-03-01"))
    test_end = pd.Timestamp(meta.get("test_end", meta.get("end", "2026-05-01")))
    recent_1m_start = max(sample_start, train_end - pd.DateOffset(months=1))
    recent_3m_start = max(sample_start, train_end - pd.DateOffset(months=3))
    recent_6m_start = max(sample_start, train_end - pd.DateOffset(months=6))
    train_schemes = {
        "train_all": (features.index >= sample_start) & (features.index < train_end),
        "recent_6m": (features.index >= recent_6m_start) & (features.index < train_end),
        "recent_3m": (features.index >= recent_3m_start) & (features.index < train_end),
        "recent_1m": (features.index >= recent_1m_start) & (features.index < train_end),
    }
    validation = (features.index >= train_end) & (features.index < validation_end)
    test = (features.index >= validation_end) & (features.index < test_end)

    rows = []
    artifacts = {}
    for horizon in [30, 60, 120]:
        fut = future_return_bps(mid[ETF], horizon).reindex(features.index)
        for edge in [2.5, 5.0, 10.0]:
            y = label_regime(signal.reindex(features.index), fut, rule.entry_bps, edge)
            usable = features[feature_cols].notna().all(axis=1) & y.notna()
            for train_scheme, train in train_schemes.items():
                for model_name in ["rf_depth2", "rf_depth3", "rf_depth4"]:
                    x_train = features.loc[train & usable, feature_cols].clip(-1e6, 1e6)
                    y_train = y.loc[train & usable].astype(int)
                    if y_train.nunique() < 2 or len(y_train) < 500:
                        continue
                    model = make_model(model_name)
                    model.fit(x_train, y_train)
                    for conf in [0.40, 0.50, 0.60, 0.70]:
                        spec = ClassifierSpec(train_scheme, model_name, horizon, edge, conf)
                        pred = predict_labels(model, features.loc[usable, feature_cols].clip(-1e6, 1e6), conf)
                        pred = pred.reindex(features.index).fillna(0).astype(int)
                        pos = position_from_classifier(signal.reindex(features.index), pred, rule)
                        frame = backtest_position(pos, mid.reindex(features.index), spread_bps.reindex(features.index), bid=bid.reindex(features.index), ask=ask.reindex(features.index), cost_model="exact_bidask")
                        dir_stats = active_directional_control_stats(
                            pos,
                            mid.reindex(features.index),
                            spread_bps.reindex(features.index),
                            bid.reindex(features.index),
                            ask.reindex(features.index),
                        )
                        row = {
                            "strategy": spec.name,
                            "train_scheme": train_scheme,
                            "model_name": model_name,
                            "horizon_min": horizon,
                            "label_edge_bps": edge,
                            "confidence": conf,
                            "train_balanced_accuracy": balanced_accuracy_score(y.loc[train & usable], pred.loc[train & usable]) if (train & usable).sum() else np.nan,
                            "validation_balanced_accuracy": balanced_accuracy_score(y.loc[validation & usable], pred.loc[validation & usable]) if (validation & usable).sum() else np.nan,
                            "test_balanced_accuracy": balanced_accuracy_score(y.loc[test & usable], pred.loc[test & usable]) if (test & usable).sum() else np.nan,
                            "train_mr_frac": float((pred.loc[train] == 1).mean()),
                            "train_trend_frac": float((pred.loc[train] == 2).mean()),
                            "validation_mr_frac": float((pred.loc[validation] == 1).mean()),
                            "validation_trend_frac": float((pred.loc[validation] == 2).mean()),
                            "test_mr_frac": float((pred.loc[test] == 1).mean()),
                            "test_trend_frac": float((pred.loc[test] == 2).mean()),
                        }
                        row.update(full_stats(frame))
                        row.update(dir_stats)
                        row["validation_excess_vs_best_directional_bps"] = row["validation_net_bps"] - max(
                            row["validation_always_long_net_bps"], row["validation_always_short_net_bps"]
                        )
                        row["test_excess_vs_best_directional_bps"] = row["test_net_bps"] - max(
                            row["test_always_long_net_bps"], row["test_always_short_net_bps"]
                        )
                        row["validation_score"] = (
                            row["validation_net_bps"]
                            + row["validation_excess_vs_best_directional_bps"]
                            + 0.1 * row["validation_balanced_accuracy"] * 100.0
                            - 0.05 * row["validation_cost_bps"]
                        )
                        rows.append(row)
                        artifacts[spec.name] = {"frame": frame, "pos": pos, "pred": pred, "label": y, "model": model, "usable": usable, "train_mask": train}

    grid = pd.DataFrame(rows).sort_values("validation_score", ascending=False)
    grid.to_csv(TABLES / "regime_classifier_grid.csv", index=False)
    eligible = grid[
        (grid["validation_net_bps"] > 0)
        & (grid["validation_trades"] >= 10)
        & (grid["validation_balanced_accuracy"] > 0.34)
        & (grid["validation_excess_vs_best_directional_bps"] > 0)
    ].copy()
    if eligible.empty:
        selected = grid.sort_values("validation_score", ascending=False).iloc[0]
        decision_label = "no_trade"
        reason = "no classifier passes validation net/trade/accuracy filters"
    else:
        selected = eligible.sort_values("validation_score", ascending=False).iloc[0]
        decision_label = "active_candidate" if selected["test_net_bps"] > 0 else "diagnostic_only"
        reason = "selected on metadata validation only; test is holdout"

    selected_name = str(selected["strategy"])
    selected_art = artifacts[selected_name]
    selected_frame = selected_art["frame"]
    selected_pos = selected_art["pos"]
    selected_pred = selected_art["pred"]
    selected_label = selected_art["label"]
    usable = selected_art["usable"]
    selected_train_mask = selected_art["train_mask"]

    controls = []
    control_positions = {
        "selected_classifier": selected_pos,
        "sign_flip": -selected_pos,
        "classifier_active_always_long": pd.Series(np.where(selected_pos != 0, 1.0, 0.0), index=selected_pos.index),
        "classifier_active_always_short": pd.Series(np.where(selected_pos != 0, -1.0, 0.0), index=selected_pos.index),
    }
    for name, pos in control_positions.items():
        frame = backtest_position(pos, mid.reindex(features.index), spread_bps.reindex(features.index), bid=bid.reindex(features.index), ask=ask.reindex(features.index), cost_model="exact_bidask")
        row = {"control": name}
        row.update(full_stats(frame))
        controls.append(row)
    controls_df = pd.DataFrame(controls)

    cost_latency = test_cost_latency(selected_pos, mid.reindex(features.index), spread_bps.reindex(features.index))
    monthly = monthly_side(selected_frame, selected_name)
    monthly.to_csv(TABLES / "regime_classifier_monthly.csv", index=False)

    cm_rows = []
    for sample, mask in [("selected_train", selected_train_mask), ("validation", validation), ("test", test)]:
        ok = mask & usable
        labels = sorted(set(selected_label.loc[ok].astype(int).unique()).union(set(selected_pred.loc[ok].astype(int).unique())))
        cm = confusion_matrix(selected_label.loc[ok], selected_pred.loc[ok], labels=labels)
        for i, true_label in enumerate(labels):
            for j, pred_label in enumerate(labels):
                cm_rows.append({"sample": sample, "true_label": LABELS.get(int(true_label), str(true_label)), "pred_label": LABELS.get(int(pred_label), str(pred_label)), "count": int(cm[i, j])})
    pd.DataFrame(cm_rows).to_csv(TABLES / "regime_classifier_confusion.csv", index=False)

    decision = pd.DataFrame(
        [
            {
                "decision": decision_label,
                "reason": reason,
                "selected_strategy": selected_name,
                "train_scheme": selected["train_scheme"],
                "model_name": selected["model_name"],
                "horizon_min": selected["horizon_min"],
                "label_edge_bps": selected["label_edge_bps"],
                "confidence": selected["confidence"],
                "train_net_bps": selected["train_net_bps"],
                "validation_net_bps": selected["validation_net_bps"],
                "mar_net_bps": selected.get("2026_03_net_bps", np.nan),
                "apr_net_bps": selected.get("2026_04_net_bps", np.nan),
                "test_net_bps": selected["test_net_bps"],
                "test_trades": selected["test_trades"],
                "test_2x_cost_net_bps": float(cost_latency[(cost_latency["cost_multiplier"] == 2.0) & (cost_latency["latency_min"] == 0)]["test_net_bps"].iloc[0]),
                "latency1_test_net_bps": float(cost_latency[(cost_latency["cost_multiplier"] == 1.0) & (cost_latency["latency_min"] == 1)]["test_net_bps"].iloc[0]),
                "validation_balanced_accuracy": selected["validation_balanced_accuracy"],
                "test_balanced_accuracy": selected["test_balanced_accuracy"],
            }
        ]
    )
    decision.to_csv(TABLES / "regime_classifier_selection.csv", index=False)
    controls_df.to_csv(TABLES / "regime_classifier_controls.csv", index=False)
    cost_latency.to_csv(TABLES / "regime_classifier_cost_latency.csv", index=False)

    try:
        model = selected_art["model"]
        if hasattr(model, "named_steps"):
            clf = model.named_steps[list(model.named_steps)[-1]]
        else:
            clf = model
        if hasattr(clf, "feature_importances_"):
            importance = pd.DataFrame({"feature": feature_cols, "importance": clf.feature_importances_})
        elif hasattr(clf, "coef_"):
            importance = pd.DataFrame({"feature": feature_cols, "importance": np.abs(clf.coef_).mean(axis=0)})
        else:
            importance = pd.DataFrame({"feature": feature_cols, "importance": np.nan})
        importance.sort_values("importance", ascending=False).to_csv(TABLES / "regime_classifier_feature_importance.csv", index=False)
    except Exception:
        pd.DataFrame({"feature": feature_cols, "importance": np.nan}).to_csv(TABLES / "regime_classifier_feature_importance.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 6))
    plot = grid.head(12).set_index("strategy")[["validation_net_bps", "test_net_bps"]]
    plot.plot(kind="barh", ax=ax)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_title("Regime classifier candidates ranked on validation")
    ax.set_xlabel("net bps")
    fig.tight_layout()
    fig.savefig(FIGURES / "regime_classifier_comparison.png", dpi=180)
    plt.close(fig)

    report = (
        "# Regime Classifier Experiment\n\n"
        "The classifier predicts three states: no-trade, mean-reversion, or trend-continuation. "
        "The metadata train split fits the model, validation selects it, and test is the final holdout.\n\n"
        "## Selection\n\n"
        + decision.to_markdown(index=False)
        + "\n\n## Controls\n\n"
        + controls_df.to_markdown(index=False)
        + "\n\n## Cost / Latency\n\n"
        + cost_latency.to_markdown(index=False)
        + "\n\n## Monthly Anatomy\n\n"
        + monthly.to_markdown(index=False)
        + "\n\n## Interpretation\n\n"
        "If the selected classifier is positive in validation but negative in test, the regime idea is diagnostically useful but not yet a tradable active rule. "
        "If it is positive in test but fails controls or 2x cost/latency, it should remain a candidate rather than a final alpha claim.\n"
    )
    (OUTPUT / "regime_classifier_report.md").write_text(report)
    print(f"[ok] wrote {TABLES / 'regime_classifier_selection.csv'}")
    print(f"[ok] wrote {OUTPUT / 'regime_classifier_report.md'}")


if __name__ == "__main__":
    main()
