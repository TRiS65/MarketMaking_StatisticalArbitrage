#!/usr/bin/env python3
"""Generate the current new-data research report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from project_config import FIGURES, OUTPUT, TABLES, metadata

ROOT = Path(__file__).resolve().parents[1]


def read_optional(name: str) -> pd.DataFrame | None:
    path = TABLES / name
    return pd.read_csv(path) if path.exists() else None


def md_table(df: pd.DataFrame | None, cols: list[str] | None = None, max_rows: int = 12) -> str:
    if df is None or df.empty:
        return "_Not available yet._"
    view = df.head(max_rows) if cols is None else df.loc[:, [c for c in cols if c in df.columns]].head(max_rows)
    return view.to_markdown(index=False)


def fmt_table(df: pd.DataFrame, cols: list[str], digits: int = 2, max_rows: int = 12) -> list[list[str]]:
    cols = [c for c in cols if c in df.columns]
    out = [cols]
    for _, row in df[cols].head(max_rows).iterrows():
        vals = []
        for value in row:
            if isinstance(value, float):
                vals.append("" if pd.isna(value) else f"{value:.{digits}f}")
            else:
                vals.append("" if pd.isna(value) else str(value))
        out.append(vals)
    return out


def table_story(story, title: str, df: pd.DataFrame | None, cols: list[str], styles, digits: int = 2, max_rows: int = 12) -> None:
    if df is None or df.empty:
        return
    story.append(Paragraph(title, styles["Heading2"]))
    table = Table(fmt_table(df, cols, digits, max_rows=max_rows), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.2),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.15 * inch))


def markdown_report() -> Path:
    meta = metadata()
    holdings = read_optional("selected_xlk_holdings.csv")
    diagnostics = read_optional("minute_data_diagnostics.csv")
    sparse = read_optional("enhanced_backtest_summary.csv")
    sparse_bidask = read_optional("enhanced_sparse_bidask_comparison.csv")
    candidates = read_optional("enhanced_sparse_candidates.csv")
    professor = read_optional("professor_test_leaderboard.csv")
    professor_cost = read_optional("professor_cost_scenario_results.csv")
    professor_ou = read_optional("professor_ou_spread_diagnostics.csv")
    robust_selection = read_optional("robust_alpha_selection.csv")
    robust_controls = read_optional("robust_alpha_controls.csv")
    robust_cost = read_optional("robust_alpha_cost_sensitivity.csv")
    timing = read_optional("timing_extension_summary.csv")
    timing_bidask = read_optional("timing_extension_bidask_comparison.csv")
    top20_methods = read_optional("top20_method_comparison_summary.csv")
    top20_gate = read_optional("top20_no_trade_gate.csv")
    top20_buckets = read_optional("top20_signal_bucket.csv")
    top20_exits = read_optional("top20_exit_reason_audit.csv")
    empirical_symbol_costs = read_optional("empirical_symbol_costs.csv")
    empirical_latency = read_optional("empirical_taker_latency_costs.csv")
    empirical_passive = read_optional("empirical_passive_fill_model.csv")
    execution_selection = read_optional("execution_optimized_selection.csv")
    loss_decision = read_optional("loss_streamline_decision.csv")
    fixed_bps_selection = read_optional("fixed_bps_timing_selection.csv")
    fixed_bps_controls = read_optional("fixed_bps_timing_controls.csv")
    fixed_bps_monthly = read_optional("fixed_bps_timing_monthly.csv")
    micro_refine = read_optional("microstructure_refinement_horizon_summary.csv")
    micro_refine_controls = read_optional("microstructure_refinement_controls.csv")
    micro_refine_coef = read_optional("microstructure_refinement_coefficients.csv")
    timing_robust_decision = read_optional("timing_robustness_decision.csv")
    timing_robust_target = read_optional("timing_robustness_target_rule.csv")
    timing_robust_target_exec = read_optional("timing_robustness_target_execution_audit.csv")
    regime_summary = read_optional("regime_shift_summary.csv")
    regime_market = read_optional("regime_monthly_market_state.csv")
    regime_pnl = read_optional("regime_target_rule_monthly_pnl.csv")
    regime_gate_selection = read_optional("regime_gate_selection.csv")
    regime_gate_monthly = read_optional("regime_gate_monthly.csv")
    regime_classifier_selection = read_optional("regime_classifier_selection.csv")
    regime_classifier_controls = read_optional("regime_classifier_controls.csv")
    regime_classifier_monthly = read_optional("regime_classifier_monthly.csv")

    text = f"""# XLK Microstructure Statistical Arbitrage: New-Data Progress Report

## Dataset

- Raw data: `{meta.get('raw_dir', 'data/newdata')}`
- Sample: `{meta.get('start')}` to `{meta.get('end')}`
- Universe: `{meta.get('etf', 'XLK')}` + {len(meta.get('constituents', []))} constituents
- Requested-but-dropped symbols after quote/trade cleaning: `{', '.join(meta.get('dropped_requested_symbols', [])) or 'none'}`
- Split: train before `{meta.get('train_end')}`, validation before `{meta.get('validation_end')}`, test before `{meta.get('test_end')}`

## Main Research Position

The project now separates two claims:

1. **Market-neutral XLK-vs-basket arbitrage.** This remains the hard claim.  It must survive alternative spread definitions, explicit transaction-cost scenarios, and out-of-sample testing.
2. **Sparse-basket fair-value timing.** This is a different claim: the constituent basket is used as a signal, while only XLK is traded.

This language directly addresses the professor's concern that price definition, spread construction, and execution assumptions can dominate high-frequency results.

## Top Holdings Used

{md_table(holdings, ['symbol', 'name', 'official_weight_pct', 'basket_weight', 'used_in_clean_panel'], 25)}

## Data Diagnostics

{md_table(diagnostics, ['symbol', 'start', 'end', 'minutes', 'median_spread_bps', 'avg_volume', 'trade_count'], 25)}

## Professor Feedback Checks

The new `run_professor_robustness.py` module answers the main methodology questions:

- `r_XLK,t` is explicitly one-minute log return, not price.
- Cumulative residual-return spreads are compared against direct log-price spreads and log-price regression residuals.
- Gross/no-cost P&L is separated from 0.25-spread, 0.50-spread, and clipped last-trade execution proxies.
- OU / Avellaneda-Lee style diagnostics are reported for each spread.

Best validation-selected test rows:

{md_table(professor, max_rows=15)}

OU and stationarity diagnostics:

{md_table(professor_ou, ['pair', 'spread_type', 'train_adf_p', 'train_half_life_minutes', 'ou_half_life_minutes', 'train_spread_std_bps'], 15)}

## Top-20 Method Diagnostics

The new top-20 method diagnostic layer absorbs the methodology addendum critically rather than copying it wholesale.  It is real-data only, has no synthetic fallback, uses lagged Kalman beta, charges passive-entry adverse selection, writes every tried rule to a trial registry, and applies a no-trade selection gate.

{md_table(top20_methods)}

No-trade gate examples:

{md_table(top20_gate, ['pair_or_basket', 'method', 'validation_net_bps', 'test_net_bps', 'test_2x_cost_net_bps', 'test_latency1_net_bps', 'gate_selected_flag', 'gate_reason'], 15)}

Exit-reason audit:

{md_table(top20_exits, ['method', 'sample', 'exit_reason', 'trades', 'gross_bps', 'cost_bps', 'net_bps'], 15)}

XLK-only signal bucket test:

{md_table(top20_buckets, ['sample', 'horizon_min', 'signal_decile', 'mean_future_return_bps', 'count'], 20)}

## Empirical Execution Model

The execution upgrade replaces fixed 0.25/0.50-spread haircuts with quantities estimated from the cleaned TAQ panel.  It is still a minute-level proxy, not a queue-level production fill model.

Symbol-level cost summary:

{md_table(empirical_symbol_costs, ['symbol', 'median_spread_bps', 'p90_spread_bps', 'median_halfspread_bps', 'median_volume', 'median_trade_count'], 20)}

Latency taker-cost summary:

{md_table(empirical_latency, ['symbol', 'latency_min', 'buy_taker_cost_bps_median', 'sell_taker_cost_bps_median', 'roundtrip_two_leg_cost_bps_median'], 20)}

Passive touch-fill / markout proxy:

{md_table(empirical_passive, ['symbol', 'time_bucket', 'spread_bucket', 'imb_bucket', 'buy_bid_fill_prob', 'sell_ask_fill_prob', 'buy_passive_markout_cost_bps_median_if_filled', 'sell_passive_markout_cost_bps_median_if_filled'], 20)}

## Execution-Optimized Pair Backtest

The maker/taker execution backtest is intentionally treated as a candidate screen.  It uses observed bid/ask fills and last-trade crossing proxies.  Positive validation results are not considered tradable unless the out-of-sample audit survives.

{md_table(execution_selection, ['stock', 'spread_type', 'policy', 'val_trades', 'val_net_bps', 'test_trades', 'test_net_bps', 'decision', 'oos_decision', 'final_policy'], 10)}

## Loss Streamline Decision

{md_table(loss_decision, ['research_path', 'decision', 'reason', 'train_or_validation_net_bps', 'test_net_bps', 'raw_test_net_bps_before_gate'], 10)}

## Fixed-BPS Timing Controls on Expanded Data

This section regenerates the old fixed-bps sparse timing candidate shape on the expanded top-20 panel.  The old `profit_search_*` tables are legacy candidate screens; this is the current-data control result.

{md_table(fixed_bps_selection, ['decision', 'reason', 'basket_symbols', 'train_net_bps', 'validation_net_bps', 'test_net_bps', 'test_2x_cost_net_bps', 'test_latency1_net_bps', 'circular_pvalue'], 5)}

Controls:

{md_table(fixed_bps_controls, ['control', 'train_net_bps', 'validation_net_bps', 'test_net_bps', 'test_trades'], 10)}

Monthly PnL:

{md_table(fixed_bps_monthly, ['month', 'gross_bps', 'cost_bps', 'net_bps', 'trades'], 10)}

## Lecture-Driven Microstructure Refinement

The Baruch notes suggest a useful next layer: do not add a fancier spread model, but condition trading on order-flow, spread, volatility, and impact states.  I implemented a small ridge timing screen using basket premium, quote imbalance, Lee-Ready style signed flow, realized volatility, and a Kyle-style liquidity proxy.  It is trained on the train split only and threshold-selected on validation.

Horizon sweep:

{md_table(micro_refine, ['horizon_min', 'decision', 'reason', 'threshold_pred_bps', 'train_net_bps', 'validation_net_bps', 'test_net_bps', 'test_trades'], 10)}

Controls for the last run:

{md_table(micro_refine_controls, ['control', 'train_net_bps', 'validation_net_bps', 'test_net_bps', 'test_trades'], 10)}

Largest ridge coefficients:

{md_table(micro_refine_coef, ['feature', 'coef'], 12)}

## Current Timing Robustness Re-Audit

The previously highlighted `micro_shrink_0.75_cw10d_e60_x0_mh240` result was March-only and came from an older sparse basket convention.  The script now regenerates timing robustness on the current expanded clean top-5 holdings basket and evaluates the full March-April holdout.

Current Jan-Feb-selected decision:

{md_table(timing_robust_decision, ['decision', 'reason', 'selected_strategy', 'train_net_bps', 'mar_net_bps', 'apr_net_bps', 'test_net_bps', 'exact_bidask_test_net_bps', 'latency1_test_net_bps'], 5)}

Named candidate audit:

{md_table(timing_robust_target, ['strategy', 'basket_symbols', 'train_net_bps', 'mar_net_bps', 'apr_net_bps', 'test_net_bps', 'train_trades', 'test_trades'], 5)}

Named candidate execution audit:

{md_table(timing_robust_target_exec, ['execution_model', 'latency_min', 'train_net_bps', 'mar_net_bps', 'apr_net_bps', 'test_net_bps', 'test_trades'], 10)}

## Regime Shift Diagnostics

The regime-shift check asks whether poor timing performance comes from a broken XLK/basket linkage, wider execution costs, or a directional signal failure.  The expanded-sample evidence points mainly to signal-direction instability: XLK/basket correlation and beta do not collapse, but April is a strong XLK rally in which the positive premium stays persistent and the contrarian rule remains short XLK for too long.

Train-vs-test regime summary:

{md_table(regime_summary, ['metric', 'train_avg', 'test_avg', 'test_minus_train'], 20)}

Monthly market state:

{md_table(regime_market, ['month', 'xlk_return_bps', 'basket_return_bps', 'xlk_basket_corr_1m', 'xlk_on_basket_beta_1m', 'residual_vol_bps_1m', 'median_xlk_spread_bps', 'signal_std_bps', 'abs_signal_gt_60_frac'], 10)}

Named timing candidate monthly PnL anatomy:

{md_table(regime_pnl, ['month', 'gross_bps', 'cost_bps', 'net_bps', 'trades', 'long_gross_bps', 'short_gross_bps', 'long_minutes', 'short_minutes'], 10)}

## Regime-Gate Repair Experiments

The April diagnosis suggests a specific repair: prevent the contrarian rule from shorting XLK when the premium is persistent and/or both XLK and the sparse basket are trending upward.  The gate experiment keeps the target signal fixed and only changes the trade/no-trade overlay.  Gate selection uses January-February only; March-April remains holdout.

Selection:

{md_table(regime_gate_selection, ['decision', 'selected_strategy', 'gate_mode', 'state_kind', 'lookback_min', 'trend_threshold_bps', 'train_net_bps', 'mar_net_bps', 'apr_net_bps', 'test_net_bps', 'test_2x_cost_net_bps'], 5)}

Monthly side anatomy:

{md_table(regime_gate_monthly, ['strategy', 'month', 'gross_bps', 'cost_bps', 'net_bps', 'long_gross_bps', 'short_gross_bps', 'long_minutes', 'short_minutes'], 30)}

## Regime Classifier

The classifier version replaces fixed gates with a three-state supervised model: mean-reversion, trend-continuation, or no-trade.  January trains the classifier, February selects model/confidence settings, and March-April is the holdout.  Selection also requires the classifier to beat active always-long/always-short controls on validation, preventing a disguised directional rule from passing as regime intelligence.

Selection:

{md_table(regime_classifier_selection, ['decision', 'selected_strategy', 'train_scheme', 'model_name', 'horizon_min', 'label_edge_bps', 'confidence', 'validation_net_bps', 'mar_net_bps', 'apr_net_bps', 'test_net_bps', 'test_2x_cost_net_bps', 'latency1_test_net_bps'], 5)}

Controls:

{md_table(regime_classifier_controls, ['control', 'validation_net_bps', 'test_net_bps', 'test_trades'], 10)}

Monthly anatomy:

{md_table(regime_classifier_monthly, ['strategy', 'month', 'gross_bps', 'cost_bps', 'net_bps', 'long_gross_bps', 'short_gross_bps', 'long_minutes', 'short_minutes'], 10)}

## Sparse Market-Neutral Basket

{md_table(candidates, ['subset', 'k', 'betas', 'train_adf_p', 'train_half_life_minutes', 'train_avg_oneway_cost_bps', 'score'], 10)}

{md_table(sparse, ['strategy', 'sample', 'trades', 'gross_bps', 'cost_bps', 'net_bps', 'max_drawdown_bps'], 10)}

Bid/ask boundary audit:

{md_table(sparse_bidask)}

## Robust Alpha Suite

The robust alpha suite jointly tests XLK-only timing and partial/full hedge rules.  If the selected rule has `hedge_fraction = 0`, it is a timing strategy, not market-neutral arbitrage.

{md_table(robust_selection)}

Controls:

{md_table(robust_controls)}

Cost sensitivity:

{md_table(robust_cost)}

## XLK-Only Timing Extension

{md_table(timing, ['period', 'gross_bps', 'cost_bps', 'net_bps', 'trades', 'avg_abs_position', 'xlk_buyhold_bps'])}

Bid/ask boundary audit:

{md_table(timing_bidask)}

## Interpretation

The next report should avoid saying "ETF arbitrage is profitable" unless a market-neutral rule survives the new spread-construction and execution-cost checks.  The defensible framing is:

> Market-neutral XLK-vs-basket arbitrage is fragile under realistic TAQ execution assumptions.  The more promising direction is to use the sparse/top-holdings basket as a fair-value signal and trade XLK only, but the first new-data quick run does not yet prove a stable positive active strategy.  Report gross/no-cost, 0.25-spread, 0.50-spread, and last-trade proxy economics separately.

## Next Steps

1. Run the full grid overnight; the committed top-20 diagnostic grid is intentionally laptop-safe.
2. Improve passive execution with queue-depth and partial-fill modeling; the current passive mode is only a stress case.
3. Extend signal bucket tests into formal timing selection only if the decile relation is stable across train/validation/test.
4. Add portfolio-level drawdown / VaR constraints for correlated constituent losses.
5. Add a formal DSR / multiple-testing section using the trial registry as the denominator.
6. Regenerate the fixed-bps sparse5 timing candidate on the expanded top-20 sample before using it as final evidence; legacy profit-search outputs are candidate shapes only.
7. If pursuing a positive extension, move from linear microstructure timing to conditional gates: avoid high spread / high volatility states, trade only where order-flow and basket-premium signs agree, and validate on event-level fills.
8. Add a trend/regime gate before any contrarian XLK-only timing claim.  The April audit shows that persistent positive premium during an aligned XLK/basket rally can make the strategy short the ETF into a strong uptrend; this should trigger no-trade or one-sided trading restrictions.

## Reproducibility

```bash
python3 scripts/build_dataset.py --force
python3 scripts/run_newdata_pipeline.py --quick
```
"""
    out = OUTPUT / "research_report.md"
    out.write_text(text)
    return out


def pdf_report() -> Path:
    holdings = read_optional("selected_xlk_holdings.csv")
    diagnostics = read_optional("minute_data_diagnostics.csv")
    professor = read_optional("professor_test_leaderboard.csv")
    robust_selection = read_optional("robust_alpha_selection.csv")
    robust_controls = read_optional("robust_alpha_controls.csv")
    timing = read_optional("timing_extension_summary.csv")
    top20_methods = read_optional("top20_method_comparison_summary.csv")
    top20_gate = read_optional("top20_no_trade_gate.csv")
    sparse_bidask = read_optional("enhanced_sparse_bidask_comparison.csv")
    empirical_symbol_costs = read_optional("empirical_symbol_costs.csv")
    empirical_latency = read_optional("empirical_taker_latency_costs.csv")
    execution_selection = read_optional("execution_optimized_selection.csv")
    loss_decision = read_optional("loss_streamline_decision.csv")
    fixed_bps_selection = read_optional("fixed_bps_timing_selection.csv")
    micro_refine = read_optional("microstructure_refinement_horizon_summary.csv")
    timing_robust_decision = read_optional("timing_robustness_decision.csv")
    timing_robust_target = read_optional("timing_robustness_target_rule.csv")
    regime_summary = read_optional("regime_shift_summary.csv")
    regime_gate_selection = read_optional("regime_gate_selection.csv")
    regime_classifier_selection = read_optional("regime_classifier_selection.csv")

    styles = getSampleStyleSheet()
    out = OUTPUT / "research_report.pdf"
    doc = SimpleDocTemplate(out.as_posix(), pagesize=letter, rightMargin=0.5 * inch, leftMargin=0.5 * inch)
    story = [
        Paragraph("XLK Microstructure Statistical Arbitrage: New-Data Progress Report", styles["Title"]),
        Paragraph(
            "Market-neutral XLK-vs-basket arbitrage is audited separately from XLK-only sparse-basket fair-value timing.  The report emphasizes spread construction, gross/no-cost economics, transaction-cost scenarios, and last-trade execution proxies.",
            styles["BodyText"],
        ),
        Spacer(1, 0.18 * inch),
    ]
    table_story(story, "Top Holdings", holdings, ["symbol", "official_weight_pct", "basket_weight"], styles, 4, 25)
    table_story(story, "Data Diagnostics", diagnostics, ["symbol", "minutes", "median_spread_bps", "trade_count"], styles, 2, 25)
    table_story(story, "Professor Cost/Spread Leaderboard", professor, ["pair", "spread_type", "no_cost_midpoint", "quarter_spread_cost", "half_spread_taker_cost", "clipped_last_trade_proxy"], styles, 2, 12)
    table_story(story, "Sparse Bid/Ask Audit", sparse_bidask, ["sample", "old_net_bps", "new_bidask_cost_bps", "new_bidask_net_bps"], styles, 2, 8)
    table_story(story, "Robust Alpha Selection", robust_selection, ["decision", "economic_label", "selected_strategy", "train_net_bps", "test_net_bps"], styles, 2, 5)
    table_story(story, "Top-20 Method Diagnostics", top20_methods, ["method", "selected_pairs", "gate_pass_pairs", "raw_test_net_bps", "gate_test_net_bps", "test_trades"], styles, 2, 8)
    table_story(story, "No-Trade Gate Examples", top20_gate, ["pair_or_basket", "method", "validation_net_bps", "test_net_bps", "gate_selected_flag", "gate_reason"], styles, 2, 10)
    table_story(story, "Empirical Symbol Costs", empirical_symbol_costs, ["symbol", "median_spread_bps", "p90_spread_bps", "median_halfspread_bps", "median_volume"], styles, 2, 20)
    table_story(story, "Latency Taker Costs", empirical_latency, ["symbol", "latency_min", "buy_taker_cost_bps_median", "sell_taker_cost_bps_median"], styles, 2, 20)
    table_story(story, "Execution-Optimized Pair Audit", execution_selection, ["stock", "spread_type", "policy", "val_net_bps", "test_net_bps", "oos_decision", "final_policy"], styles, 2, 5)
    table_story(story, "Loss Streamline Decision", loss_decision, ["research_path", "decision", "test_net_bps"], styles, 2, 5)
    table_story(story, "Expanded Fixed-BPS Timing Controls", fixed_bps_selection, ["decision", "basket_symbols", "train_net_bps", "validation_net_bps", "test_net_bps", "circular_pvalue"], styles, 2, 5)
    table_story(story, "Microstructure Refinement Horizon Sweep", micro_refine, ["horizon_min", "decision", "train_net_bps", "validation_net_bps", "test_net_bps", "test_trades"], styles, 2, 8)
    table_story(story, "Current Timing Robustness Re-Audit", timing_robust_decision, ["decision", "reason", "train_net_bps", "test_net_bps"], styles, 2, 5)
    table_story(story, "Named Timing Candidate Re-Audit", timing_robust_target, ["strategy", "basket_symbols", "train_net_bps", "mar_net_bps", "apr_net_bps", "test_net_bps"], styles, 2, 5)
    table_story(story, "Regime Shift Summary", regime_summary, ["metric", "train_avg", "test_avg", "test_minus_train"], styles, 2, 12)
    table_story(story, "Regime-Gate Repair Selection", regime_gate_selection, ["decision", "selected_strategy", "gate_mode", "state_kind", "train_net_bps", "test_net_bps", "test_2x_cost_net_bps"], styles, 2, 5)
    table_story(story, "Regime Classifier Selection", regime_classifier_selection, ["decision", "selected_strategy", "train_scheme", "model_name", "validation_net_bps", "test_net_bps", "test_2x_cost_net_bps"], styles, 2, 5)
    table_story(story, "Robust Alpha Controls", robust_controls, ["control", "train_net_bps", "test_net_bps", "test_trades"], styles, 2, 8)
    table_story(story, "XLK-Only Timing", timing, ["period", "gross_bps", "cost_bps", "net_bps", "trades"], styles, 2, 8)
    for fig_name in ["professor_cost_scenario_leaderboard.png", "top20_method_comparison.png", "top20_signal_bucket.png", "regime_shift_diagnostics.png", "regime_gate_comparison.png", "regime_classifier_comparison.png", "robust_alpha_selected_cumulative.png", "timing_extension_cumulative_net.png"]:
        fig = FIGURES / fig_name
        if fig.exists():
            story.append(Image(fig.as_posix(), width=6.8 * inch, height=3.8 * inch))
            story.append(Spacer(1, 0.15 * inch))
    doc.build(story)
    return out


def main() -> None:
    md = markdown_report()
    pdf = pdf_report()
    print(f"[report] wrote {md.relative_to(ROOT)}")
    print(f"[report] wrote {pdf.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
