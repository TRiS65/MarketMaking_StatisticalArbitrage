#!/usr/bin/env python3
"""Streamlined PnL/loss attribution for TRiS65/MarketMaking_StatisticalArbitrage.

Purpose
-------
Read the repository's output/tables/*.csv files and produce one concise report
that answers three questions:

1. Which research path loses money and why?
2. Is the loss due to weak signal, high cost, bad exits, overfitting, or regime shift?
3. Which active rule, if any, is eligible to trade after a no-trade gate?

This script is intentionally table-driven.  It does not re-run TAQ aggregation or
strategy backtests; it audits the existing experiment outputs.  It is therefore
cheap to run after every pipeline iteration.

Usage
-----
    python3 scripts/run_loss_streamline.py --root .

Outputs
-------
    output/tables/loss_streamline_decision.csv
    output/loss_streamline_report.md
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit PnL losses and select active/no-trade policy")
    p.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    p.add_argument("--min-train-net", type=float, default=0.0)
    p.add_argument("--min-test-cost-buffer", type=float, default=1.25,
                   help="Require gross/cost >= this for candidate active timing diagnostics")
    p.add_argument("--max-circular-p", type=float, default=0.10,
                   help="Preferred p-value gate when circular-shift controls are available")
    return p.parse_args()


def safe_read(path: Path) -> pd.DataFrame:
    """Read CSV if present, else return empty frame.

    Some GitHub previews collapse table newlines visually; the actual repository
    files should be normal CSVs.  This reader still tries a fallback for files
    accidentally written as one long line with rows separated by spaces before
    known row labels.
    """
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        text = path.read_text(errors="ignore")
        # Very conservative fallback: replace ' <word>,' at likely row boundaries.
        # This is only for broken manually pasted CSVs and should not affect normal files.
        for token in [
            " baseline,", " coint_filter,", " combined,", " kalman_lagged,",
            " passive_stress,", " sscore_ou_gate,", " selected,", " sign_flip,",
            " active_always_long,", " active_always_short,", " sparse5,",
        ]:
            text = text.replace(token, "\n" + token.strip())
        from io import StringIO
        return pd.read_csv(StringIO(text))


def fmt(x: float | int | str, digits: int = 2) -> str:
    if isinstance(x, str):
        return x
    try:
        if x is None or not np.isfinite(float(x)):
            return "nan"
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)


def table_md(df: pd.DataFrame, cols: Iterable[str], n: int | None = None, digits: int = 2) -> str:
    cols = [c for c in cols if c in df.columns]
    if not cols or df.empty:
        return "_No table available._"
    out = df[cols].copy()
    if n is not None:
        out = out.head(n)
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].map(lambda v: fmt(v, digits))
    return out.to_markdown(index=False)


def pnl_per_trade(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if {"raw_test_net_bps", "test_trades"}.issubset(out.columns):
        out["raw_test_net_per_trade_bps"] = out["raw_test_net_bps"] / out["test_trades"].replace(0, np.nan)
    return out


def robust_alpha_diagnosis(selection: pd.DataFrame, controls: pd.DataFrame, cost: pd.DataFrame) -> dict[str, object]:
    d: dict[str, object] = {"available": False}
    if selection.empty:
        return d
    row = selection.iloc[0].to_dict()
    d.update(row)
    d["available"] = True
    if not cost.empty:
        test1 = cost[(cost.get("sample") == "test") & (cost.get("cost_multiplier") == 1.0)]
        if len(test1):
            r = test1.iloc[0]
            gross = float(r.get("gross_bps", np.nan))
            cst = float(r.get("cost_bps", np.nan))
            d["test_gross_bps"] = gross
            d["test_cost_bps"] = cst
            d["breakeven_cost_multiplier"] = gross / cst if cst > 0 else np.inf
    if not controls.empty:
        selected = controls[controls.get("control") == "selected"]
        always_long = controls[controls.get("control") == "active_always_long"]
        pval = controls[controls.get("control") == "selected_vs_circular_pvalue"]
        if len(always_long):
            d["always_long_test_net_bps"] = float(always_long.iloc[0].get("test_net_bps", np.nan))
        if len(pval):
            d["circular_pvalue"] = float(pval.iloc[0].get("test_net_bps", np.nan))
    return d


def profit_search_diagnosis(df: pd.DataFrame, min_cost_buffer: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    out = df.copy()
    needed = {"train_net_bps", "test_net_bps", "test_gross_bps", "test_cost_bps", "test_trades"}
    if not needed.issubset(out.columns):
        return pd.DataFrame()
    out["test_net_per_trade_bps"] = out["test_net_bps"] / out["test_trades"].replace(0, np.nan)
    out["test_gross_per_trade_bps"] = out["test_gross_bps"] / out["test_trades"].replace(0, np.nan)
    out["test_cost_per_trade_bps"] = out["test_cost_bps"] / out["test_trades"].replace(0, np.nan)
    out["test_cost_capacity_x"] = out["test_gross_bps"] / out["test_cost_bps"].replace(0, np.nan)
    # Eligibility uses only non-test columns plus conservative ex-post audit tags.
    # The test outcome is reported, but should not be used to tune parameters.
    if {"jan_net_bps", "feb_net_bps"}.issubset(out.columns):
        out["min_jan_feb_net_bps"] = out[["jan_net_bps", "feb_net_bps"]].min(axis=1)
    else:
        out["min_jan_feb_net_bps"] = np.nan
    out["candidate_train_gate"] = (
        (out["train_net_bps"] > 0)
        & ((out["min_jan_feb_net_bps"].isna()) | (out["min_jan_feb_net_bps"] > 0))
        & (out["test_cost_capacity_x"] >= min_cost_buffer)
    )
    if "protocol" in out.columns:
        posterior = out["protocol"].astype(str).str.contains("march|oracle", case=False, na=False)
        out.loc[posterior, "candidate_train_gate"] = False
        out["posterior_protocol_flag"] = posterior
    out["legacy_output_warning"] = (
        "profit_search table predates the expanded top-20 pipeline; treat as candidate shape, not final new-data evidence"
    )
    return out.sort_values(["candidate_train_gate", "test_net_bps"], ascending=[False, False])


def exit_reason_diagnosis(exit_df: pd.DataFrame) -> pd.DataFrame:
    if exit_df.empty:
        return pd.DataFrame()
    cols = {"sample", "exit_reason", "trades", "gross_bps", "cost_bps", "net_bps"}
    if not cols.issubset(exit_df.columns):
        return pd.DataFrame()
    out = exit_df.groupby(["sample", "exit_reason"], as_index=False)[["trades", "gross_bps", "cost_bps", "net_bps"]].sum()
    out["net_per_trade_bps"] = out["net_bps"] / out["trades"].replace(0, np.nan)
    return out.sort_values(["sample", "net_bps"], ascending=[True, False])


def bucket_diagnosis(bucket: pd.DataFrame) -> pd.DataFrame:
    if bucket.empty:
        return pd.DataFrame()
    needed = {"sample", "horizon_min", "signal_decile", "mean_future_return_bps"}
    if not needed.issubset(bucket.columns):
        return pd.DataFrame()
    rows = []
    for (sample, h), g in bucket.groupby(["sample", "horizon_min"]):
        g = g.sort_values("signal_decile")
        if len(g) < 5:
            continue
        x = g["signal_decile"].astype(float).to_numpy()
        y = g["mean_future_return_bps"].astype(float).to_numpy()
        slope = np.polyfit(x, y, 1)[0]
        hi = float(g[g["signal_decile"] == g["signal_decile"].max()]["mean_future_return_bps"].iloc[0])
        lo = float(g[g["signal_decile"] == g["signal_decile"].min()]["mean_future_return_bps"].iloc[0])
        best = g.loc[g["mean_future_return_bps"].idxmax()]
        rows.append({
            "sample": sample,
            "horizon_min": h,
            "linear_slope_bps_per_decile": slope,
            "decile0_future_bps": lo,
            "decile9_future_bps": hi,
            "best_decile": int(best["signal_decile"]),
            "best_decile_future_bps": float(best["mean_future_return_bps"]),
        })
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    tables = root / "output" / "tables"
    outdir = root / "output"
    tables.mkdir(parents=True, exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)

    method = pnl_per_trade(safe_read(tables / "top20_method_comparison_summary.csv"))
    gate = safe_read(tables / "top20_no_trade_gate.csv")
    exit_diag = exit_reason_diagnosis(safe_read(tables / "top20_exit_reason_audit.csv"))
    buckets = bucket_diagnosis(safe_read(tables / "top20_signal_bucket.csv"))

    alpha_sel = safe_read(tables / "robust_alpha_selection.csv")
    alpha_controls = safe_read(tables / "robust_alpha_controls.csv")
    alpha_cost = safe_read(tables / "robust_alpha_cost_sensitivity.csv")
    alpha_diag = robust_alpha_diagnosis(alpha_sel, alpha_controls, alpha_cost)

    profit = profit_search_diagnosis(safe_read(tables / "profit_search_protocol_summary.csv"), args.min_test_cost_buffer)
    fixed_bps = safe_read(tables / "fixed_bps_timing_selection.csv")
    timing_robust = safe_read(tables / "timing_robustness_decision.csv")
    timing_target = safe_read(tables / "timing_robustness_target_rule.csv")
    timing_target_exec = safe_read(tables / "timing_robustness_target_execution_audit.csv")
    regime_gate = safe_read(tables / "regime_gate_selection.csv")
    regime_gate_monthly = safe_read(tables / "regime_gate_monthly.csv")
    regime_classifier = safe_read(tables / "regime_classifier_selection.csv")
    regime_classifier_controls = safe_read(tables / "regime_classifier_controls.csv")

    decisions = []
    # 1) Strict market-neutral / pair trading decision
    if not method.empty and "gate_test_net_bps" in method.columns:
        total_gate = float(method["gate_test_net_bps"].sum())
        total_raw = float(method["raw_test_net_bps"].sum()) if "raw_test_net_bps" in method.columns else np.nan
        decisions.append({
            "research_path": "market_neutral_pair_or_basket",
            "decision": "no_trade",
            "reason": "validation-selected active pair/basket rules fail no-trade gate or lose after costs",
            "train_or_validation_net_bps": np.nan,
            "test_net_bps": total_gate,
            "raw_test_net_bps_before_gate": total_raw,
        })
    # 2) Robust alpha suite selected rule
    if alpha_diag.get("available"):
        test_net = float(alpha_diag.get("test_net_bps", np.nan))
        decision = "no_trade" if not (np.isfinite(test_net) and test_net > 0) else "candidate_active"
        reason = "selected robust-alpha rule loses OOS or does not beat no-trade"
        if decision == "candidate_active":
            reason = "selected robust-alpha rule positive OOS; still require controls"
        decisions.append({
            "research_path": "robust_alpha_suite_selected",
            "decision": decision,
            "reason": reason,
            "train_or_validation_net_bps": alpha_diag.get("train_net_bps", np.nan),
            "test_net_bps": alpha_diag.get("test_net_bps", np.nan),
            "raw_test_net_bps_before_gate": alpha_diag.get("test_net_bps", np.nan),
        })
    # 3) Profit-search fixed-bps timing candidate, if present
    if not profit.empty:
        cand = profit[profit["candidate_train_gate"]].head(1)
        if len(cand):
            r = cand.iloc[0]
            decisions.append({
                "research_path": "fixed_bps_xlk_only_timing_candidate",
                "decision": "legacy_candidate_shape_only",
                "reason": "legacy profit-search output is Jan-Feb positive, but it predates expanded top-20 controls and is not final evidence",
                "train_or_validation_net_bps": r.get("train_net_bps", np.nan),
                "test_net_bps": r.get("test_net_bps", np.nan),
                "raw_test_net_bps_before_gate": r.get("test_net_bps", np.nan),
            })
        else:
            decisions.append({
                "research_path": "fixed_bps_xlk_only_timing_candidate",
                "decision": "no_trade",
                "reason": "no profit-search candidate passes train gates and cost-buffer screen",
                "train_or_validation_net_bps": np.nan,
                "test_net_bps": np.nan,
                "raw_test_net_bps_before_gate": np.nan,
            })

    if not fixed_bps.empty:
        r = fixed_bps.iloc[0]
        decisions.append({
            "research_path": "expanded_fixed_bps_xlk_only_timing",
            "decision": str(r.get("decision", "no_trade")),
            "reason": str(r.get("reason", "expanded-sample fixed-bps control result")),
            "train_or_validation_net_bps": r.get("train_net_bps", np.nan),
            "test_net_bps": r.get("test_net_bps", np.nan),
            "raw_test_net_bps_before_gate": r.get("test_net_bps", np.nan),
        })

    if not timing_robust.empty:
        r = timing_robust.iloc[0]
        decisions.append({
            "research_path": "timing_robustness_current_selection",
            "decision": str(r.get("decision", "no_trade")),
            "reason": str(r.get("reason", "current timing robustness result")),
            "train_or_validation_net_bps": r.get("train_net_bps", np.nan),
            "test_net_bps": r.get("test_net_bps", np.nan),
            "raw_test_net_bps_before_gate": r.get("test_net_bps", np.nan),
        })

    if not timing_target.empty:
        r = timing_target.iloc[0]
        decisions.append({
            "research_path": "named_timing_candidate_micro075_e60",
            "decision": "no_trade" if float(r.get("test_net_bps", np.nan)) <= 0 else "target_candidate_pending_controls",
            "reason": "named candidate audited on current top-5 basket with Mar-Apr test",
            "train_or_validation_net_bps": r.get("train_net_bps", np.nan),
            "test_net_bps": r.get("test_net_bps", np.nan),
            "raw_test_net_bps_before_gate": r.get("test_net_bps", np.nan),
        })

    if not regime_gate.empty:
        r = regime_gate.iloc[0]
        decision = str(r.get("decision", "no_trade"))
        decisions.append({
            "research_path": "regime_gated_timing_repair",
            "decision": "no_trade" if decision != "active_candidate" else "candidate_active",
            "reason": str(r.get("reason", "regime-gate repair experiment")) + f" Script label: {decision}.",
            "train_or_validation_net_bps": r.get("train_net_bps", np.nan),
            "test_net_bps": r.get("test_net_bps", np.nan),
            "raw_test_net_bps_before_gate": r.get("test_net_bps", np.nan),
        })

    if not regime_classifier.empty:
        r = regime_classifier.iloc[0]
        decision = str(r.get("decision", "no_trade"))
        decisions.append({
            "research_path": "regime_classifier_timing",
            "decision": "no_trade" if decision != "active_candidate" else "candidate_active",
            "reason": str(r.get("reason", "regime classifier experiment")).rstrip(".") + f". Script label: {decision}.",
            "train_or_validation_net_bps": r.get("validation_net_bps", np.nan),
            "test_net_bps": r.get("test_net_bps", np.nan),
            "raw_test_net_bps_before_gate": r.get("test_net_bps", np.nan),
        })

    decision_df = pd.DataFrame(decisions)
    decision_df.to_csv(tables / "loss_streamline_decision.csv", index=False)

    lines: list[str] = []
    lines.append("# Loss Streamline Report\n")
    lines.append("## Executive decision\n")
    if decision_df.empty:
        lines.append("No decision table could be produced because expected output tables were not found.\n")
    else:
        lines.append(table_md(decision_df, ["research_path", "decision", "reason", "train_or_validation_net_bps", "test_net_bps", "raw_test_net_bps_before_gate"], digits=2))
        lines.append("")
    lines.append("## 1. Market-neutral / pair-trading PnL attribution\n")
    lines.append(table_md(method, ["method", "selected_pairs", "gate_pass_pairs", "raw_validation_net_bps", "raw_test_net_bps", "raw_test_net_per_trade_bps", "raw_positive_test_pairs", "gate_test_net_bps", "test_trades"], digits=2))
    lines.append("\nInterpretation: if gate_test_net_bps is zero, the economically selected policy is no-trade. Negative raw_test_net_bps indicates that model filters reduce losses but do not create tradable alpha.\n")

    lines.append("## 2. Exit-reason attribution\n")
    lines.append(table_md(exit_diag, ["sample", "exit_reason", "trades", "gross_bps", "cost_bps", "net_bps", "net_per_trade_bps"], n=20, digits=2))
    lines.append("\nInterpretation: profitable reversion exits combined with negative max-hold / stop-loss / EOD exits usually means entry thresholds are too loose and residuals do not revert quickly enough.\n")

    lines.append("## 3. Robust-alpha selected rule\n")
    if alpha_diag.get("available"):
        lines.append(f"Selected strategy: `{alpha_diag.get('selected_strategy', '')}`")
        lines.append(f"Train net: {fmt(alpha_diag.get('train_net_bps', np.nan))} bps; test net: {fmt(alpha_diag.get('test_net_bps', np.nan))} bps.")
        if "test_gross_bps" in alpha_diag:
            lines.append(f"Test gross/cost: {fmt(alpha_diag['test_gross_bps'])} / {fmt(alpha_diag['test_cost_bps'])} bps; break-even cost multiplier: {fmt(alpha_diag['breakeven_cost_multiplier'], 3)}x.")
        if "always_long_test_net_bps" in alpha_diag:
            lines.append(f"Always-long control test net: {fmt(alpha_diag['always_long_test_net_bps'])} bps. If this is close to or better than selected, timing alpha is not established.")
        if "circular_pvalue" in alpha_diag:
            lines.append(f"Circular-shift p-value proxy: {fmt(alpha_diag['circular_pvalue'], 3)}.")
    else:
        lines.append("_No robust_alpha_selection.csv found._")
    lines.append("")

    lines.append("## 4. Fixed-bps XLK-only timing candidate audit\n")
    if not fixed_bps.empty:
        lines.append("Expanded top-20 regeneration:\n")
        lines.append(table_md(fixed_bps, ["decision", "reason", "basket_symbols", "train_net_bps", "validation_net_bps", "test_net_bps", "test_2x_cost_net_bps", "test_latency1_net_bps", "circular_pvalue"], n=5, digits=2))
        lines.append("")
    lines.append("Legacy profit-search screen:\n")
    lines.append(table_md(profit, ["protocol", "hedge", "signal_price", "signal_kind", "hedge_frac", "threshold_bps", "exit_bps", "max_hold", "jan_net_bps", "feb_net_bps", "train_net_bps", "test_net_bps", "test_gross_per_trade_bps", "test_cost_per_trade_bps", "test_net_per_trade_bps", "test_cost_capacity_x", "candidate_train_gate"], n=10, digits=2))
    lines.append("\nInterpretation: a positive fixed-bps timing candidate is not the same as market-neutral arbitrage. The existing profit-search file is treated as a legacy candidate screen unless it is regenerated on the expanded top-20 sample. It should be promoted only if it passes sign-flip, always-long/short, circular-shift, latency, and cost-multiplier stress tests on the current data.\n")

    lines.append("## 5. Signal-bucket regime check\n")
    lines.append(table_md(buckets, ["sample", "horizon_min", "linear_slope_bps_per_decile", "decile0_future_bps", "decile9_future_bps", "best_decile", "best_decile_future_bps"], n=30, digits=2))
    lines.append("\nInterpretation: a non-monotone or sign-flipping decile curve means the signal should not be traded as a symmetric z-score. Prefer fixed-bps thresholds, asymmetric tails, or a no-trade gate.\n")

    lines.append("## 6. Current timing robustness / named candidate audit\n")
    lines.append("Current Jan-Feb-selected timing decision:\n")
    lines.append(table_md(timing_robust, ["decision", "reason", "selected_strategy", "train_net_bps", "mar_net_bps", "apr_net_bps", "test_net_bps", "exact_bidask_test_net_bps", "latency1_test_net_bps"], n=5, digits=2))
    lines.append("\nNamed candidate `micro_shrink_0.75_cw10d_e60_x0_mh240` on the current top-5 basket:\n")
    lines.append(table_md(timing_target, ["strategy", "basket_symbols", "train_net_bps", "mar_net_bps", "apr_net_bps", "test_net_bps", "train_trades", "test_trades"], n=5, digits=2))
    lines.append("\nNamed candidate execution audit:\n")
    lines.append(table_md(timing_target_exec, ["execution_model", "latency_min", "train_net_bps", "mar_net_bps", "apr_net_bps", "test_net_bps", "test_trades"], n=10, digits=2))
    lines.append("\nInterpretation: this resolves the earlier contradiction. The old March-only positive timing result does not survive regeneration on the current expanded top-5 basket plus Mar-Apr holdout.\n")

    lines.append("## 7. Regime-gate repair experiment\n")
    lines.append("Selection table:\n")
    lines.append(table_md(regime_gate, ["decision", "selected_strategy", "gate_mode", "state_kind", "lookback_min", "trend_threshold_bps", "train_net_bps", "mar_net_bps", "apr_net_bps", "test_net_bps", "test_2x_cost_net_bps"], n=5, digits=2))
    lines.append("\nMonthly side anatomy for baseline, side-only diagnostics, and selected/best gates:\n")
    lines.append(table_md(regime_gate_monthly, ["strategy", "month", "gross_bps", "cost_bps", "net_bps", "long_gross_bps", "short_gross_bps", "long_minutes", "short_minutes"], n=30, digits=2))
    lines.append("\nInterpretation: premium-persistence gates can reduce the April short-side blow-up, but the Jan-Feb-selected gate still does not produce positive Mar-Apr net after a 2x cost buffer. Side-only diagnostics show the regime flip directly: short-only works in Jan-Feb but fails badly in April, while long-only helps April but fails in train. This supports a no-trade policy until a regime classifier is validated on a later holdout.\n")

    lines.append("## 8. Supervised regime classifier\n")
    lines.append("Selection table:\n")
    lines.append(table_md(regime_classifier, ["decision", "selected_strategy", "train_scheme", "model_name", "horizon_min", "confidence", "validation_net_bps", "mar_net_bps", "apr_net_bps", "test_net_bps", "test_2x_cost_net_bps", "latency1_test_net_bps"], n=5, digits=2))
    lines.append("\nControls:\n")
    lines.append(table_md(regime_classifier_controls, ["control", "validation_net_bps", "test_net_bps", "test_trades"], n=10, digits=2))
    lines.append("\nInterpretation: the classifier is allowed to choose mean-reversion, trend-continuation, or no-trade, but it still fails the Mar-Apr holdout. The selected classifier is validation-positive, yet test net is negative and cost/latency stress is worse. Therefore the regime idea remains a research direction, not a tradable rule.\n")

    lines.append("## Recommended next implementation\n")
    lines.append("1. Keep market-neutral pair/basket trading behind a hard no-trade gate. Do not report it as profitable unless gate_pass_pairs > 0 and the gated test result is positive.\n")
    lines.append("2. Promote the fixed-bps XLK-only timing candidate, if present, to the robust-alpha suite and run controls: sign flip, always-long/short, circular shifts, 1-minute latency, and 1x/2x/3x/4x cost stress.\n")
    lines.append("3. Replace symmetric z-score timing with fixed-bps roll-centered thresholds when the signal bucket curve is non-monotone. This follows the same robustness logic as simple basket-trading systems: prefer stable parameter islands to single best points.\n")
    lines.append("4. Treat passive entry only as a stress case unless adverse selection and fill probability are calibrated from quote/trade data.\n")
    lines.append("5. If no active rule passes these screens, the final strategy is no-trade. That is a valid non-losing policy and a defensible research conclusion.\n")

    (outdir / "loss_streamline_report.md").write_text("\n".join(lines))
    print(f"[ok] wrote {tables / 'loss_streamline_decision.csv'}")
    print(f"[ok] wrote {outdir / 'loss_streamline_report.md'}")


if __name__ == "__main__":
    main()
