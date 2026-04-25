# XLK Microstructure Statistical Arbitrage Project

Final project implementation for **Microstructure-Based Fair Value and Intraday Statistical Arbitrage in ETFs and Synthetic Constituent Baskets**.

The final empirical conclusion is two-part.  With the available eight-name XLK proxy basket, the active market-neutral ETF-basket arbitrage specifications do not deliver a robust tradable positive out-of-sample result after bid-ask costs.  Microprice does become useful after changing the economic claim: use the sparse basket premium as a fair-value timing signal, but execute only XLK.

## Final Workflow

```bash
python3 scripts/build_dataset.py
python3 scripts/run_final_analysis.py
python3 scripts/run_timing_extension.py
python3 scripts/run_timing_robustness.py
python3 scripts/make_report.py
```

`build_dataset.py --force` rescans the original WRDS gz files.  The repository intentionally does **not** track those raw gz files because they are multi-GB WRDS extracts and exceed GitHub file-size limits.  The tracked processed parquet files are enough to rerun the final analysis and report.

## Data Included

| Path | Description |
|---|---|
| `data/0422_holdings-daily-us-en-xlk.xlsx` | XLK holdings workbook used for selected-basket weights |
| `data/processed/minute_quotes_2026_MM.parquet` | One-minute quote bars for XLK and selected constituents |
| `data/processed/minute_trades_2026_MM.parquet` | One-minute trade bars for XLK and selected constituents |
| `data/processed/research_panel.parquet` | Cleaned symbol-minute research panel |
| `data/processed/enhanced_sparse_backtest.parquet` | Final sparse-signal backtest path |
| `data/processed/timing_extension_backtest.parquet` | XLK-only timing extension backtest path |
| `data/processed/timing_robustness_selected_backtest.parquet` | Stability-island selected timing rule path |

## Final Outputs

| Path | Description |
|---|---|
| `output/research_report.pdf` | Final report |
| `output/research_report.md` | Markdown report source |
| `output/literature_notes.md` | Mapping from supplied literature to final methodology |
| `output/tables/model_comparison.csv` | Final comparison of baseline, v2 diagnostic, hybrid sparse, and no-trade benchmark |
| `output/tables/enhanced_backtest_summary.csv` | Final train/test active sparse strategy and no-trade benchmark |
| `output/tables/enhanced_sparse_candidates.csv` | Sparse mean-reverting candidate ranking |
| `output/tables/timing_extension_summary.csv` | Fixed 50/25 bps XLK-only timing extension summary |
| `output/tables/timing_robustness_decision.csv` | Train-only stability-island timing selection |
| `output/tables/timing_robustness_grid.csv` | Timing robustness grid over signal views and thresholds |
| `output/tables/timing_robustness_stability.csv` | Parameter-island stability diagnostics |
| `output/tables/minute_data_diagnostics.csv` | Minute-bar diagnostics |
| `output/tables/selected_xlk_holdings.csv` | Eight-name selected basket and normalized weights |
| `output/figures/enhanced_sparse_cumulative_net.png` | Final cumulative net P&L figure |
| `output/figures/timing_extension_cumulative_net.png` | XLK-only timing cumulative net P&L |

## Method Notes

Quotes are filtered to regular hours, valid positive bid/ask prices and sizes, non-cancelled quotes, quoted spreads below 100 bps, and prices within 500 bps of a centered rolling median to remove narrow-spread bad ticks.  Trades are filtered to regular hours, positive price/size, and `TR_CORR = 00`.

The final analysis uses:

- sparse mean-reverting portfolio selection motivated by d'Aspremont;
- OU-style ADF and half-life diagnostics;
- microprice as a fair-value **signal**, not an executable fill price;
- midpoint residual returns for gross P&L;
- explicit bid-ask costs, turnover, and end-of-day flattening;
- Jan-February 2026 selection and March 2026 out-of-sample evaluation;
- a no-trade benchmark motivated by transaction-cost no-trade-region literature.

The final result is best framed as a diagnostic negative finding for market-neutral ETF-basket arbitrage, plus a separate positive timing extension.  The robustness grid explicitly avoids choosing the best March row: it selects a January-February stability island first, then reports March out of sample.
