# Market Making and Statistical Arbitrage: XLK Final-Data Study

This repository now targets the 12-month WRDS TAQ dataset:

- sample: `2025-05-01` to `2026-05-01`
- frequency: raw millisecond TAQ, aggregated to one-minute regular-hours bars
- universe: `XLK` plus the top 20 names from the `0501` XLK holdings file
- raw data path: `data/finaldata`
- default split: train before `2026-02-01`, validation before `2026-03-01`, test before `2026-05-01`

The project separates two claims:

1. **Market-neutral XLK-vs-basket arbitrage.** This is the strict arbitrage claim and must survive spread-construction checks and realistic execution costs.
2. **Sparse/top-holdings basket fair-value timing.** This uses the basket as a signal and trades only XLK. It is not market neutral.

The current research line follows the professor feedback: define variables precisely, compare spread constructions, separate gross/no-cost P&L from transaction costs, and test multiple execution assumptions.

## Main Workflow

Build the final minute panel from the raw gz files:

```bash
python3 scripts/build_dataset.py --force
```

Run the current research pipeline:

```bash
python3 scripts/run_newdata_pipeline.py --quick
```

The raw build scans about 169GB of gzipped TAQ data, so it is intentionally separate from the experiment pipeline.

## Key Scripts

| Path | Purpose |
|---|---|
| `scripts/build_dataset.py` | DuckDB aggregation from raw TAQ quotes/trades into minute parquet and `research_panel.parquet` |
| `scripts/project_config.py` | Shared dataset metadata, universe, and split dates |
| `scripts/research_utils.py` | Shared panel alignment, returns, OU, last-trade proxy, and spread helpers |
| `scripts/run_professor_robustness.py` | Spread-definition and transaction-cost robustness requested by professor |
| `scripts/run_monetization_optimizer.py` | Markowitz/QP-style allocation across liquid pair signals with Almgren-Chriss execution stress |
| `scripts/run_top20_method_diagnostics.py` | Real-only top-20 pair diagnostics with no-trade gate, lagged Kalman beta, passive stress, exit reasons, and signal buckets |
| `scripts/run_empirical_execution_model.py` | Empirical bid/ask, latency, passive-fill markout, and capacity cost calibration |
| `scripts/run_execution_optimized_backtest.py` | Minute-level maker/taker execution screen for pair candidates |
| `scripts/run_fixed_bps_timing_controls.py` | Finaldata controls for the fixed-bps XLK-only timing candidate shape |
| `scripts/run_timing_robustness.py` | Current top-5 XLK-only timing robustness with metadata test holdout and exact bid/ask latency audit |
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
| `output/tables/monetization_selection.csv` | Markowitz/Almgren-Chriss monetization decision |
| `output/tables/monetization_markowitz_frontier.csv` | Execution-stressed portfolio frontier across candidate sets |
| `output/tables/monetization_selected_weights.csv` | Selected strategy weights from the monetization optimizer |
| `output/tables/top20_trial_registry.csv` | Every top-20 pair-method trial and selection flag |
| `output/tables/top20_method_comparison_summary.csv` | Method ablation after validation selection and no-trade gate |
| `output/tables/top20_no_trade_gate.csv` | Why selected active pair rules are accepted or rejected |
| `output/tables/top20_exit_reason_audit.csv` | Reversion/max-hold/stop-loss/EOD exit reason P&L |
| `output/tables/top20_signal_bucket.csv` | Sparse-basket signal deciles vs future XLK returns |
| `output/tables/empirical_symbol_costs.csv` | Observed spread, volume, and trade-count execution-cost summary |
| `output/tables/empirical_taker_latency_costs.csv` | Quote-boundary taker cost using 0/1/2/5 minute latency quotes |
| `output/tables/empirical_passive_fill_model.csv` | Last-trade touch-fill and markout proxy by symbol/time/spread/imbalance bucket |
| `output/tables/execution_optimized_selection.csv` | Maker/taker execution-screen selection and OOS audit |
| `output/tables/fixed_bps_timing_selection.csv` | Finaldata fixed-bps timing decision and controls summary |
| `output/tables/timing_robustness_decision.csv` | Current train/validation-selected timing decision with metadata test holdout |
| `output/tables/timing_robustness_target_rule.csv` | Re-audit of `micro_shrink_0.75_cw10d_e60_x0_mh240` on the current top-5 basket |
| `output/tables/regime_shift_summary.csv` | Train/test regime diagnostics for XLK/basket linkage, spread, signal scale, and signal IC |
| `output/tables/regime_target_rule_monthly_pnl.csv` | Monthly gross/cost/net attribution for the named timing candidate |
| `output/tables/regime_gate_selection.csv` | Train/validation-selected regime gate and metadata test holdout audit |
| `output/tables/regime_gate_monthly.csv` | Monthly side anatomy for baseline, side-only diagnostics, and selected/best gates |
| `output/tables/regime_classifier_selection.csv` | Supervised classifier selection and metadata test holdout audit |
| `output/tables/regime_classifier_controls.csv` | Sign-flip and active directional controls for selected classifier |
| `output/tables/microstructure_refinement_horizon_summary.csv` | Order-flow/spread/volatility/impact timing horizon sweep |
| `output/tables/loss_streamline_decision.csv` | Final active/no-trade policy summary by research path |
| `output/tables/robust_alpha_selection.csv` | Train-only robust alpha selection decision |
| `output/tables/robust_alpha_controls.csv` | Sign-flip, always-long/short, circular-shift controls |
| `output/tables/robust_alpha_cost_sensitivity.csv` | Cost multiplier sensitivity |
| `output/research_report.md` | Current markdown report |
| `output/research_report.pdf` | Current PDF report |

## Evidence Hierarchy and Final Policy

The repository separates final evidence from diagnostic or legacy artifacts:

| Tier | Meaning | Policy role |
|---|---|---|
| Final 12-month evidence | Regenerated on `data/finaldata` using the metadata split | Policy-eligible |
| Legacy candidate screen | Older `profit_search_*` positive rows | Historical motivation only |
| Diagnostic-only overlay | Regime gate / classifier experiments | Explains failure modes, not a trading policy |
| Actual selected policy | Result after no-trade gates and execution stress | `no_trade` |

Use this wording unless a future finaldata run clearly overturns it:

> Final 12-month evidence shows pockets of gross and low-cost relative-value signal, but no active market-neutral, XLK-only timing, regime-classifier, or Markowitz/AC monetization rule survives the holdout and execution gates. The selected trading policy is no-trade. The research conclusion is not “no signal”; it is “signal exists in pockets, but monetization fails under realistic costs, slow reversion, and regime instability.”

This is not primarily a laptop-compute failure.  A MacBook limits how far the project can go toward event-level queue simulation, partial-fill modeling, and multi-leg synchronized execution, but the current no-trade result is driven by strategy evidence: several finaldata candidates lose on gross P&L before costs in the holdout.  For example, the re-audited `micro_shrink_0.75_cw10d_e60_x0_mh240` timing rule has test gross `-567.59` bps, cost `327.20` bps, and net `-894.79` bps; April alone has gross `-724.16` bps and net `-862.35` bps.  More detailed execution cannot rescue a rule whose out-of-sample direction is wrong before costs.

## Final-Data Quick Results Snapshot

The 12-month finaldata run gives a more conservative conclusion than the old shorter samples:

| Experiment | Train / Validation | Test | Interpretation |
|---|---:|---:|---|
| Sparse market-neutral basket, half-spread approximation | train `-178.81` bps | test `+2.26` bps | Tiny test gain does not matter because train fails; no-trade remains benchmark |
| Sparse market-neutral basket, bid/ask boundary audit | train `-593.42` bps | test `-17.32` bps | Fails under actual quote-boundary execution |
| Fixed top-holdings XLK-only timing | validation `+205.74` bps | test `-852.43` bps | Old fixed timing rule does not transfer |
| Robust alpha quick selected XLK-only timing | train `+335.69` bps | test `-202.21` bps | Train-positive but fails OOS |
| Top-20 pair method diagnostics after no-trade gate | varies | `0.00` bps | Every validation-selected pair method fails at least one gate |
| Execution-optimized pair screen | validation candidate `+3083.69` bps | test `-3416.85` bps | Validation false positive; final policy remains no-trade |
| Finaldata fixed-bps XLK-only timing controls | train `-2572.04` bps, validation `-45.13` bps | test `-977.24` bps | Old fixed-bps candidate shape does not transfer |
| Current top-5 timing robustness re-audit | no train/validation stability rule passes | `0.00` bps selected policy | No active timing rule selected |
| Named timing candidate `micro_shrink_0.75_cw10d_e60_x0_mh240` | train `-2695.47` bps | test `-894.79` bps | Earlier positive result does not survive finaldata/current basket |
| Regime-shift audit | corr `0.613` train vs `0.634` test; beta `0.531` vs `0.617` | April short gross about `-851` bps before costs | Linkage does not collapse; April is a directional/signal-regime failure |
| Regime-gate repair | selected train/validation gate train `+79.63` bps, validation `+280.21` bps | test `-131.36` bps, 2x cost `-210.74` bps | Premium-persistence gates reduce April damage but do not pass final active gate |
| Supervised regime classifier | validation `+104.32` bps | test `-271.67` bps, 2x cost `-931.31` bps | Learns some validation states but fails holdout and costs; no active claim |
| Markowitz / AC monetization optimizer | train `+743.62` bps, validation `+526.14` bps | test `-712.26` bps, last-trade proxy `-625.26` bps | Portfolio optimization finds validation signal but cannot monetize it out of sample |
| Microstructure feature timing refinement | no horizon passes validation gate | best reported test `+0.39` bps with validation `-40.85` bps | Order-flow/spread/volatility features do not rescue timing as a linear rule |

The professor robustness table does find pair/spread definitions where no-cost and 0.25-spread results are strongly positive, while 0.50-spread taker costs often erase the edge. That is the main empirical evidence that execution quality is now the central research question.

The monetization optimizer makes this sharper.  It takes the liquid validation-positive pair signals, allocates across them with a long-only Markowitz/QP-style portfolio, and adds Almgren-Chriss-inspired participation impact and timing-risk buffers.  The best train/validation-selected portfolio is strongly positive in-sample (`+743.62` train, `+526.14` validation), but loses `-712.26` bps in the untouched test window and `-625.26` bps under the clipped last-trade proxy.  That is direct evidence that the bottleneck is monetization: prediction exists in pockets, but the edge is too unstable and slow to convert into robust net P&L.

The practical implication is to stop broad parameter fishing.  Any further profitability rescue should be deliberately narrow: audit only gross-positive, low-cost candidates such as the AMD/AAPL-style pair rows that remain positive under conservative cost screens; separate signal baskets from tradable hedge baskets; and test any long-only or no-short-into-uptrend timing rule through the same metadata split before treating it as evidence.  The current final policy remains no-trade.

The top-20 method diagnostics absorb the methodology addendum conservatively:
there is no synthetic fallback, Kalman beta is lagged, passive entries include
adverse selection, and each trial is registered.  The combined filters reduce
some losses, but they do not create a tradable pair alpha in the finaldata sample.
The no-trade gate rejects all selected pair rules.

The execution upgrade replaces fixed cost multipliers with observed bid/ask,
latency quotes, last-trade passive touch-fill proxies, markout, and capacity
stress.  It does not claim queue-level fills.  The quick maker/taker screen finds
a validation candidate, but it loses out of sample, so the execution-layer policy
also remains no-trade for market-neutral pair trading.

Legacy `profit_search_*` outputs identify a useful fixed-bps sparse5 timing
candidate shape, but those files predate the finaldata top-20 pipeline.  They are
not final evidence until regenerated and passed through sign-flip,
always-long/short, circular-shift, latency, and cost-stress controls.

The regenerated finaldata fixed-bps timing controls reject that candidate
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
the metadata test holdout.  It loses on train and test, including exact
bid/ask latency variants, so it is not a final active claim.

The regime-shift diagnostics explain why that failure is not simply a cost
artifact.  The XLK/top-holdings linkage does not collapse out of sample:
one-minute correlation averages about `0.613` in train and `0.634` in test, while beta moves from about `0.531` to `0.617`.  The larger issue is directional instability.  In April, XLK rallies
about `1263` bps, the basket rallies about `1321` bps, the premium remains
persistently positive, and the contrarian timing rule is short XLK for most of
the month.  The April short-side gross loss is about `-851` bps before costs,
so the next refinement should be a regime/trend gate rather than another
symmetric z-score tweak.

The regime-gate repair experiment confirms the diagnosis but does not yet create
an honest active strategy.  A premium-persistence gate selected on the metadata
train/validation windows earns `+79.63` bps in train and `+280.21` bps in
validation, and it turns April positive at `+64.02` bps, but March loses
`-195.38` bps and the test holdout remains `-131.36` bps.  Side-only diagnostics
make the regime flip explicit: short exposure helps in some earlier periods but
fails badly in April, while long-only helps April but fails in train.  The
correct policy is still no-trade until a regime classifier survives a later
holdout.

The supervised regime classifier replaces fixed gates with three states:
mean-reversion, trend-continuation, and no-trade.  It is trained on pre-holdout
data and selected on metadata validation, with an extra requirement that it beat
active always-long/always-short controls on validation.  The selected classifier
is validation-positive, but it loses `-271.67` bps on the test holdout and
gets worse under 2x costs and remains fragile under 1-minute latency.  This confirms that the regime
problem is real, but a classifier trained on the current sample is not yet a
tradable solution.

Reference PDFs are intentionally kept local and are not pushed to GitHub.
