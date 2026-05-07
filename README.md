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

The professor robustness table does find pair/spread definitions where no-cost and 0.25-spread results are strongly positive, while 0.50-spread taker costs often erase the edge. That is the main empirical evidence that execution quality is now the central research question.

The top-20 method diagnostics absorb the methodology addendum conservatively:
there is no synthetic fallback, Kalman beta is lagged, passive entries include
adverse selection, and each trial is registered.  The combined filters reduce
some losses, but they do not create a tradable pair alpha in the expanded sample.
The no-trade gate rejects all selected pair rules.

Reference PDFs are intentionally kept local and are not pushed to GitHub.
