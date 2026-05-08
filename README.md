# Market Making and Statistical Arbitrage: XLK New-Data Study

This repository now targets the expanded WRDS TAQ dataset:

- sample: `2025-11-01` to `2026-05-01`
- frequency: raw millisecond TAQ, aggregated to one-minute regular-hours bars
- universe: `XLK` plus the top 20 names from the `0501` XLK holdings file
- raw data path: `data/newdata`

The project separates two claims:

1. **Market-neutral XLK-vs-basket arbitrage.** This is the strict arbitrage claim and must survive spread-construction checks and realistic execution costs.
2. **Sparse/top-holdings basket fair-value timing.** This uses the basket as a signal and trades only XLK. It is not market neutral.

The current research line follows the professor feedback: define variables precisely, compare spread constructions, separate gross/no-cost P&L from transaction costs, and test multiple execution assumptions.

## Main Workflow

Build the new minute panel from the raw gz files:

```bash
python3 scripts/build_dataset.py --force
```

Run the new-data research pipeline:

```bash
python3 scripts/run_newdata_pipeline.py --quick
```

The raw build scans more than 90GB of gzipped TAQ data, so it is intentionally separate from the experiment pipeline.

## Key Scripts

| Path | Purpose |
|---|---|
| `scripts/build_dataset.py` | DuckDB aggregation from raw TAQ quotes/trades into minute parquet and `research_panel.parquet` |
| `scripts/project_config.py` | Shared dataset metadata, universe, and split dates |
| `scripts/research_utils.py` | Shared panel alignment, returns, OU, last-trade proxy, and spread helpers |
| `scripts/run_professor_robustness.py` | Spread-definition and transaction-cost robustness requested by professor |
| `scripts/run_top20_method_diagnostics.py` | Real-only top-20 pair diagnostics with no-trade gate, lagged Kalman beta, passive stress, exit reasons, and signal buckets |
| `scripts/run_empirical_execution_model.py` | Empirical bid/ask, latency, passive-fill markout, and capacity cost calibration |
| `scripts/run_execution_optimized_backtest.py` | Minute-level maker/taker execution screen for pair candidates |
| `scripts/run_fixed_bps_timing_controls.py` | Expanded-sample controls for the fixed-bps XLK-only timing candidate shape |
| `scripts/run_timing_robustness.py` | Current top-5 XLK-only timing robustness with Mar-Apr holdout and exact bid/ask latency audit |
| `scripts/run_regime_shift_diagnostics.py` | Regime-shift audit explaining whether poor timing comes from linkage, costs, or signal direction |
| `scripts/run_regime_gate_experiments.py` | Trend/premium-persistence no-trade gates for the April timing failure |
| `scripts/run_regime_classifier.py` | Supervised mean-reversion / trend-continuation / no-trade classifier |
| `scripts/run_microstructure_signal_refinement.py` | Lecture-driven order-flow/spread/volatility/impact feature timing screen |
| `scripts/run_loss_streamline.py` | Table-driven loss attribution and active/no-trade policy summary |
| `scripts/run_robust_alpha_suite.py` | Joint optimizer for XLK-only timing and partial/full hedge variants |
| `scripts/run_final_analysis.py` | Sparse market-neutral basket benchmark |
| `scripts/run_timing_extension.py` | XLK-only timing extension using top-holdings basket premium |
| `scripts/run_timing_bidask_execution.py` | Bid/ask boundary-cost audit for timing path |
| `scripts/make_report.py` | Generates `output/research_report.md` and `.pdf` |

## Professor Feedback Implemented

### Variable Definition

`r_XLK,t` is one-minute log return:

```text
r_XLK,t = log(P_XLK,t) - log(P_XLK,t-1)
```

The original residual spread is not a raw `log(P_XLK) - log(P_stock)` difference. It is based on return regression:

```text
r_XLK,t = beta * r_stock,t + error_t
residual_ret_t = r_XLK,t - beta * r_stock,t
spread_t = cumulative residual_ret_t
```

### Spread Construction Robustness

`scripts/run_professor_robustness.py` compares:

```text
Spread A: cumulative residual return spread
Spread B: direct log-price spread
Spread C: log-price regression residual with intercept
```

Each spread receives ADF, half-life, and OU-style diagnostics.

### Execution-Cost Robustness

For the same signal path, the professor robustness script reports:

```text
0.00 x spread: no-cost signal diagnostic
0.25 x spread: mixed maker/taker scenario
0.50 x spread: aggressive taker scenario
last trade: clipped last-trade price proxy
```

This directly separates whether a signal exists from whether it survives realistic execution assumptions.

### Literature-Driven Next Layer

The new diagnostics include OU/Avellaneda-Lee style mean-reversion scores. The next implementation target is to turn these diagnostics into explicit s-score trading rules and to add dynamic hedge beta, likely rolling or Kalman-filter based.

## Main Outputs

| Path | Description |
|---|---|
| `data/processed/research_panel.parquet` | Cleaned one-minute research panel |
| `data/processed/dataset_metadata.json` | Dataset dates, universe, and split metadata |
| `output/tables/selected_xlk_holdings.csv` | Top-20 XLK holdings used in the new universe |
| `output/tables/minute_data_diagnostics.csv` | Symbol-level data quality diagnostics |
| `output/tables/professor_test_leaderboard.csv` | Validation-selected test results by spread and cost scenario |
| `output/tables/professor_cost_scenario_results.csv` | Full spread/cost scenario results |
| `output/tables/professor_ou_spread_diagnostics.csv` | ADF, half-life, and OU diagnostics |
| `output/tables/top20_trial_registry.csv` | Every top-20 pair-method trial and selection flag |
| `output/tables/top20_method_comparison_summary.csv` | Method ablation after validation selection and no-trade gate |
| `output/tables/top20_no_trade_gate.csv` | Why selected active pair rules are accepted or rejected |
| `output/tables/top20_exit_reason_audit.csv` | Reversion/max-hold/stop-loss/EOD exit reason P&L |
| `output/tables/top20_signal_bucket.csv` | Sparse-basket signal deciles vs future XLK returns |
| `output/tables/empirical_symbol_costs.csv` | Observed spread, volume, and trade-count execution-cost summary |
| `output/tables/empirical_taker_latency_costs.csv` | Quote-boundary taker cost using 0/1/2/5 minute latency quotes |
| `output/tables/empirical_passive_fill_model.csv` | Last-trade touch-fill and markout proxy by symbol/time/spread/imbalance bucket |
| `output/tables/execution_optimized_selection.csv` | Maker/taker execution-screen selection and OOS audit |
| `output/tables/fixed_bps_timing_selection.csv` | Expanded-sample fixed-bps timing decision and controls summary |
| `output/tables/timing_robustness_decision.csv` | Current Jan-Feb-selected timing decision with Mar-Apr holdout |
| `output/tables/timing_robustness_target_rule.csv` | Re-audit of `micro_shrink_0.75_cw10d_e60_x0_mh240` on the current top-5 basket |
| `output/tables/regime_shift_summary.csv` | Train/test regime diagnostics for XLK/basket linkage, spread, signal scale, and signal IC |
| `output/tables/regime_target_rule_monthly_pnl.csv` | Monthly gross/cost/net attribution for the named timing candidate |
| `output/tables/regime_gate_selection.csv` | Jan-Feb-selected regime gate and Mar-Apr holdout audit |
| `output/tables/regime_gate_monthly.csv` | Monthly side anatomy for baseline, side-only diagnostics, and selected/best gates |
| `output/tables/regime_classifier_selection.csv` | Supervised classifier selection and Mar-Apr holdout audit |
| `output/tables/regime_classifier_controls.csv` | Sign-flip and active directional controls for selected classifier |
| `output/tables/microstructure_refinement_horizon_summary.csv` | Order-flow/spread/volatility/impact timing horizon sweep |
| `output/tables/loss_streamline_decision.csv` | Final active/no-trade policy summary by research path |
| `output/tables/robust_alpha_selection.csv` | Train-only robust alpha selection decision |
| `output/tables/robust_alpha_controls.csv` | Sign-flip, always-long/short, circular-shift controls |
| `output/tables/robust_alpha_cost_sensitivity.csv` | Cost multiplier sensitivity |
| `output/research_report.md` | Current markdown report |
| `output/research_report.pdf` | Current PDF report |

## Current Reporting Language

Use this wording unless the new market-neutral results clearly overturn it:

> Market-neutral XLK-vs-basket arbitrage remains fragile under realistic TAQ execution assumptions. The more promising direction is to use the sparse/top-holdings basket as a fair-value signal and trade XLK only. This timing strategy is not market neutral, so it must be reported with directional controls, sign-flip controls, circular-shift tests, and cost-scenario sensitivity.

## New-Data Quick Results Snapshot

The first new-data quick run gives a more conservative conclusion than the old Jan-Mar sample:

| Experiment | Train / Validation | Test | Interpretation |
|---|---:|---:|---|
| Sparse market-neutral basket, half-spread approximation | train `+70.96` bps | test `-39.56` bps | Fails OOS |
| Sparse market-neutral basket, bid/ask boundary audit | train `-26.14` bps | test `-125.45` bps | Fails after stricter execution accounting |
| Fixed top-holdings XLK-only timing | validation `+205.74` bps | test `-852.43` bps | Old fixed timing rule does not transfer |
| Robust alpha quick selected XLK-only timing | train `+472.55` bps | test `-17.73` bps | Better than fixed rule, but no-trade still wins test |
| Top-20 pair method diagnostics after no-trade gate | varies | `0.00` bps | Every validation-selected pair method fails at least one gate |
| Execution-optimized pair screen | validation candidate `+3083.69` bps | test `-3416.85` bps | Validation false positive; final policy remains no-trade |
| Expanded fixed-bps XLK-only timing controls | train `-2115.46` bps, validation `-45.13` bps | test `-977.24` bps | Old fixed-bps candidate shape does not transfer |
| Current top-5 timing robustness re-audit | no Jan-Feb stability rule passes | `0.00` bps selected policy | No active timing rule selected |
| Named timing candidate `micro_shrink_0.75_cw10d_e60_x0_mh240` | train `-142.16` bps | Mar-Apr `-894.79` bps | March-only positive result does not survive April/current basket |
| Regime-shift audit | corr `0.655` train vs `0.634` test; beta `0.614` vs `0.617` | April short gross `-851` bps before costs | Linkage does not collapse; April is a directional/signal-regime failure |
| Regime-gate repair | selected Jan-Feb gate train `+373.61` bps | Mar-Apr `-131.36` bps, 2x cost `-210.74` bps | Premium-persistence gates reduce April damage but do not pass final active gate |
| Supervised regime classifier | Feb validation `+114.63` bps | Mar-Apr `-982.51` bps, 2x cost `-1790.10` bps | Learns some validation states but fails holdout and costs; no active claim |
| Microstructure feature timing refinement | no horizon passes validation gate | best reported test `+0.39` bps with validation `-40.85` bps | Order-flow/spread/volatility features do not rescue timing as a linear rule |

The professor robustness table does find pair/spread definitions where no-cost and 0.25-spread results are strongly positive, while 0.50-spread taker costs often erase the edge. That is the main empirical evidence that execution quality is now the central research question.

The top-20 method diagnostics absorb the methodology addendum conservatively:
there is no synthetic fallback, Kalman beta is lagged, passive entries include
adverse selection, and each trial is registered.  The combined filters reduce
some losses, but they do not create a tradable pair alpha in the expanded sample.
The no-trade gate rejects all selected pair rules.

The execution upgrade replaces fixed cost multipliers with observed bid/ask,
latency quotes, last-trade passive touch-fill proxies, markout, and capacity
stress.  It does not claim queue-level fills.  The quick maker/taker screen finds
a validation candidate, but it loses out of sample, so the execution-layer policy
also remains no-trade for market-neutral pair trading.

Legacy `profit_search_*` outputs identify a useful fixed-bps sparse5 timing
candidate shape, but those files predate the expanded top-20 pipeline.  They are
not final new-data evidence until regenerated and passed through sign-flip,
always-long/short, circular-shift, latency, and cost-stress controls.

The regenerated expanded-sample fixed-bps timing controls reject that candidate
shape: the current top-5 holdings basket loses in train, validation, and test;
the sign-flip and always-long controls are better on the test period.  Therefore
the current final policy remains no-trade for both strict arbitrage and the
tested active timing rule.

The Baruch lecture-note refinement was tested as a linear XLK-only timing model
using basket premium, quote imbalance, signed order flow, spread state,
realized volatility, and a Kyle-style liquidity proxy.  The useful takeaway is
diagnostic rather than profitable: the features highlight when costs and
volatility are hostile, but no tested horizon passes the validation gate.

The timing robustness script now resolves the earlier positive-candidate
conflict: the previously highlighted `micro_shrink_0.75_cw10d_e60_x0_mh240`
shape is explicitly re-audited on the current top-5 clean holdings basket and
the full March-April holdout.  It loses on train and test, including exact
bid/ask latency variants, so it is not a final active claim.

The regime-shift diagnostics explain why that failure is not simply a cost
artifact.  The XLK/top-holdings linkage is only modestly weaker out of sample:
one-minute correlation moves from about `0.655` to `0.634`, while beta is almost
unchanged.  The larger issue is directional instability.  In April, XLK rallies
about `1263` bps, the basket rallies about `1321` bps, the premium remains
persistently positive, and the contrarian timing rule is short XLK for most of
the month.  The April short-side gross loss is about `-851` bps before costs,
so the next refinement should be a regime/trend gate rather than another
symmetric z-score tweak.

The regime-gate repair experiment confirms the diagnosis but does not yet create
an honest active strategy.  A premium-persistence gate selected on Jan-Feb earns
`+373.61` bps in train and turns April positive at `+64.02` bps, but March loses
`-195.38` bps and the full Mar-Apr holdout remains `-131.36` bps.  Side-only
diagnostics make the regime flip explicit: short-only earns `+195.74` bps in
Jan-Feb but loses `-956.95` bps in Mar-Apr, while long-only is positive in
Mar-Apr but negative in train.  The correct policy is still no-trade until a
regime classifier survives a later holdout.

The supervised regime classifier replaces fixed gates with three states:
mean-reversion, trend-continuation, and no-trade.  It is trained on pre-holdout
data and selected on February validation, with an extra requirement that it beat
active always-long/always-short controls on validation.  The selected classifier
is validation-positive, but it loses `-982.51` bps on the Mar-Apr holdout and
gets worse under 2x costs and 1-minute latency.  This confirms that the regime
problem is real, but a classifier trained on the current sample is not yet a
tradable solution.

Reference PDFs are intentionally kept local and are not pushed to GitHub.
