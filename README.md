# Market Making and Statistical Arbitrage: XLK Microstructure Study

This repository contains a minute-level empirical study of ETF statistical arbitrage and market-making frictions using XLK and an eight-name technology constituent universe:

`AAPL, MSFT, NVDA, AVGO, ORCL, CRM, AMD, CSCO`

The project started as a market-neutral ETF-versus-basket arbitrage study and was later upgraded into a stricter research workflow with explicit parameter selection, transaction-cost diagnostics, z-score heatmaps, pair trading, max-holding exits, and audit tables that separate validation selection from true out-of-sample testing.

## Main Conclusion

The original eight-name XLK universe does not produce a robust market-neutral high-frequency arbitrage after bid/ask costs. Lower z-score thresholds create more trades, and February validation can select positive-looking pair rules, but March out-of-sample performance is mostly negative once bid/ask-aware execution is applied.

That negative result is useful: it shows that the weakness is not just an overly conservative entry threshold. The combination of a small proxy universe, noisy minute-level spreads, and transaction costs is enough to erase most apparent midpoint profits.

The separate XLK-only timing extension remains in the repository as an alternative strategy class: use the sparse basket premium as a fair-value signal, but execute only XLK.

## Current Experiment Structure

### Experiment A: Sparse Basket Replication

Legacy sparse mean-reversion tests estimate a basket hedge for XLK and evaluate whether residual deviations can be traded after costs.

Relevant files:

- `scripts/run_final_analysis.py`
- `scripts/run_experiment_suite.py`
- `output/tables/enhanced_sparse_candidates.csv`
- `output/tables/enhanced_backtest_summary.csv`
- `output/figures/enhanced_sparse_cumulative_net.png`

### Experiment B: Pair Trading on the Old Eight Names

The new pair module tests:

- `XLK-AAPL`
- `XLK-MSFT`
- `XLK-NVDA`
- `XLK-AVGO`
- `XLK-ORCL`
- `XLK-CRM`
- `XLK-AMD`
- `XLK-CSCO`

For each pair, the script estimates the training-period hedge ratio:

```text
r_XLK,t = beta * r_stock,t + error_t
residual_ret_t = r_XLK,t - beta * r_stock,t
spread_t = cumulative residual_ret_t
```

It then trades the rolling z-score of the spread:

```text
z > entry_z   -> short residual: short XLK, long beta * stock
z < -entry_z  -> long residual: long XLK, short beta * stock
```

Relevant files:

- `scripts/run_old_data_method_upgrade.py`
- `output/tables/old_pair_leaderboard.csv`
- `output/tables/old_pair_zscore_grid.csv`
- `output/tables/old_pair_trade_log.csv`
- `output/figures/pair_leaderboard_test_net_bps.png`
- `output/figures/pair_best_cumulative_pnl.png`
- `output/figures/pair_best_zscore_with_trades.png`

### Experiment C: Z-Score Heatmap and Risk Controls

The upgraded z-score grid tests:

```text
entry_z = 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5
exit_z  = 0.0, 0.25, 0.5, 0.75, 1.0, 1.25
constraint: exit_z < entry_z
```

The max-holding grid is:

```text
max_holding_minutes = None, 30, 60, 120, 240
```

The strategy engine also supports a `stop_z` argument, although the current full output focuses on max-holding controls first to keep the selection grid interpretable.

Each grid cell records:

- gross bps
- cost bps
- net bps
- number of trades
- win rate
- average holding minutes
- max drawdown bps
- t-stat style score
- turnover

Relevant files:

- `output/figures/heatmap_validation_net_bps.png`
- `output/figures/heatmap_test_net_bps.png`
- `output/figures/heatmap_trade_count.png`
- `output/tables/old_pair_zscore_grid.csv`

### Experiment D: XLK-Only Timing Extension

The timing extension uses sparse-basket fair-value information to trade only XLK. This avoids paying multi-leg hedge costs on every entry and exit.

Relevant files:

- `scripts/run_timing_extension.py`
- `scripts/run_timing_robustness.py`
- `output/tables/timing_extension_summary.csv`
- `output/tables/timing_robustness_decision.csv`
- `output/tables/timing_robustness_grid.csv`
- `output/figures/timing_extension_cumulative_net.png`

## Data Split

The current old-data methodology uses a clean three-way split:

```text
Train:      January 2026
Validation: February 2026
Test:       March 2026
```

The split is designed to avoid choosing parameters on March test data. Hedge ratios and diagnostics are estimated on January, z-score parameters are selected on February validation performance, and final performance is reported on March.

## Transaction Cost and Execution Model

The old quote parquet files include minute-level `bid`, `ask`, `bidsiz`, and `asksiz`, so the new module uses a bid/ask-aware approximation instead of only reporting midpoint returns.

For one unit of residual exposure, one-way cost is approximated as:

```text
0.5 * XLK spread + abs(beta) * 0.5 * stock spread
```

Gross P&L is marked using midpoint residual returns. Entry and exit turnover pay the estimated half-spread cost. This is not a full order-book simulator, but it is much closer to executable economics than midpoint-only backtesting.

The repository includes a direct midpoint-vs-bid/ask comparison:

- `output/tables/midpoint_vs_bidask_execution_comparison.csv`
- `output/figures/midpoint_vs_bidask_execution_comparison.png`

In the latest run, the best validation-selected pair still loses money in March after bid/ask costs even though the midpoint version is positive. This is the central transaction-cost diagnostic.

## Latest Method Upgrade: What Changed

This update added a reusable old-data method-upgrade script:

```bash
python3 scripts/run_old_data_method_upgrade.py
```

The update includes:

- pair trading for XLK against each of the original eight constituents;
- smaller z-score entry thresholds instead of the old extreme `entry_z = 3.5`;
- validation/test heatmaps for entry/exit z-score combinations;
- max-holding risk controls;
- trade-level logging with entry time, exit time, direction, holding minutes, P&L, cost, and exit reason;
- bid/ask-aware cost accounting from old quote parquet files;
- pair leaderboard ranked by validation-selected March test results;
- data diagnostics for spreads, volume, quote updates, trade counts, and missing rates;
- strategy diagnostics for gross/cost/net bps, trades, holding time, drawdown, and turnover;
- selection audit tables that mark which results are valid final claims and which are diagnostic only.

Old standalone threshold-heatmap artifacts were removed because they are superseded by the new validation/test pair z-score framework.

## Latest Results Snapshot

The full grid contains:

```text
6,840 parameter/sample rows
219,137 trade-log rows
```

Validation-selected March test results from `output/tables/old_pair_leaderboard.csv`:

| Pair | Validation Net bps | March Test Net bps | March Trades | Main Interpretation |
|---|---:|---:|---:|---|
| XLK-ORCL | 265.40 | -227.31 | 17 | Best validation rule still fails after March costs |
| XLK-MSFT | 234.74 | -235.84 | 17 | Similar validation/test decay |
| XLK-AAPL | 279.57 | -310.70 | 14 | Positive validation, negative test |
| XLK-CRM | 236.05 | -317.74 | 14 | Positive validation, negative test |
| XLK-AVGO | 102.97 | -402.04 | 19 | Cost and noise dominate |
| XLK-NVDA | 338.35 | -482.48 | 32 | More trades, still cost-sensitive |
| XLK-AMD | 266.40 | -543.71 | 31 | Negative March after costs |
| XLK-CSCO | 218.93 | -635.49 | 38 | Highest drawdown among selected rules |

For the selected XLK-ORCL rule, the execution comparison is:

| Execution Model | Sample | Gross bps | Cost bps | Net bps |
|---|---|---:|---:|---:|
| Midpoint no cost | Validation | 470.50 | 0.00 | 470.50 |
| Bid/ask aware | Validation | 470.50 | 205.10 | 265.40 |
| Midpoint no cost | Test | 509.66 | 0.00 | 509.66 |
| Bid/ask aware | Test | 509.66 | 736.97 | -227.31 |

This is the key result of the update: apparent midpoint profitability does not survive execution costs out of sample.

## Important Output Files

| Path | Description |
|---|---|
| `output/tables/old_pair_leaderboard.csv` | Validation-selected pair leaderboard with March test performance |
| `output/tables/old_pair_zscore_grid.csv` | Full pair z-score grid |
| `output/tables/old_pair_trade_log.csv` | Trade-level log for all pair/grid runs |
| `output/tables/old_strategy_diagnostics.csv` | Strategy-level diagnostics |
| `output/tables/old_data_diagnostics.csv` | Data-quality and spread diagnostics |
| `output/tables/old_selection_audit.csv` | Data-snooping and claim-validity audit |
| `output/tables/midpoint_vs_bidask_execution_comparison.csv` | Midpoint vs bid/ask-aware execution comparison |
| `output/figures/heatmap_validation_net_bps.png` | Validation z-score heatmap |
| `output/figures/heatmap_test_net_bps.png` | Test z-score heatmap |
| `output/figures/heatmap_trade_count.png` | Trade-count heatmap |
| `output/figures/pair_leaderboard_test_net_bps.png` | Pair leaderboard chart |
| `output/figures/midpoint_vs_bidask_execution_comparison.png` | Execution-cost comparison chart |
| `output/research_report.pdf` | Earlier report artifact |
| `output/research_report.md` | Earlier report source |

## How to Run

Run the new method-upgrade experiment:

```bash
python3 scripts/run_old_data_method_upgrade.py
```

For a faster smoke test:

```bash
python3 scripts/run_old_data_method_upgrade.py --quick
```

Run the older full project pipeline:

```bash
python3 run_pipeline.py
```

Run only the new method-upgrade pipeline step:

```bash
python3 run_pipeline.py --only 6
```

## Data Notes

Tracked processed data:

- `data/processed/minute_quotes_2026_01.parquet`
- `data/processed/minute_quotes_2026_02.parquet`
- `data/processed/minute_quotes_2026_03.parquet`
- `data/processed/minute_trades_2026_01.parquet`
- `data/processed/minute_trades_2026_02.parquet`
- `data/processed/minute_trades_2026_03.parquet`

Raw TAQ extracts are intentionally not tracked because they are very large WRDS files.

The new method-upgrade script reads the quote/trade parquet files directly. This makes it reusable even when a derived `research_panel.parquet` needs to be rebuilt.

## Next Step When New Data Arrives

The new WRDS top-20/six-month data should reuse the same framework. Only three inputs should change:

```text
1. minute quote/trade panel path
2. universe list
3. train/validation/test date split
```

The methodology should remain:

```text
pair leaderboard
z-score heatmap
max-holding and stop-loss controls
bid/ask-aware execution
selection audit
```
