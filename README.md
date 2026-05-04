# Market Making and Statistical Arbitrage: XLK Microstructure Study

This repository contains a minute-level empirical study of ETF statistical arbitrage and market-making frictions using XLK and an eight-name technology constituent universe:

`AAPL, MSFT, NVDA, AVGO, ORCL, CRM, AMD, CSCO`

The project started as a market-neutral ETF-versus-basket arbitrage study and was later upgraded into a stricter research workflow with explicit parameter selection, transaction-cost diagnostics, z-score heatmaps, pair trading, max-holding exits, and audit tables that separate validation selection from true out-of-sample testing.

## Main Conclusion

The original eight-name XLK universe does not yet support a broad production-ready market-neutral high-frequency arbitrage claim. Lower z-score thresholds create more trades, and February validation can select positive-looking pair rules, but March out-of-sample pair results are negative after consistent execution accounting. A prior XLK-ORCL explicit-fill diagnostic looked strongly positive, but the re-audit shows it was an execution-accounting mismatch: March midpoint gross P&L is `+509.66` bps, bid/ask boundary cost is `734.76` bps, and net P&L is `-225.10` bps.

That negative result is useful: it shows that the weakness is not just an overly conservative entry threshold, and it also shows how sensitive the conclusion is to the fill model. The combination of a small proxy universe, noisy minute-level spreads, and transaction costs is enough to erase many apparent midpoint profits.

The separate XLK-only timing extension remains in the repository as an alternative strategy class: use the sparse basket premium as a fair-value signal, but execute only XLK. Under the bid/ask boundary-cost audit, the March timing extension remains positive at `+638.42` bps net.

## Current Experiment Structure

### Experiment A: Sparse Basket Replication

Legacy sparse mean-reversion tests estimate a basket hedge for XLK and evaluate whether residual deviations can be traded after costs.

Relevant files:

- `scripts/run_final_analysis.py`
- `scripts/run_sparse_bidask_execution.py`
- `scripts/run_experiment_suite.py`
- `output/tables/enhanced_sparse_candidates.csv`
- `output/tables/enhanced_backtest_summary.csv`
- `output/tables/enhanced_sparse_bidask_comparison.csv`
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
- `scripts/run_old_data_execution_audit_fixed.py`
- `output/tables/old_pair_leaderboard.csv`
- `output/tables/old_pair_validation_selected_execution_fixed.csv`
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

The output also includes a z-score stop-loss diagnostic grid for the validation-selected pair rules:

```text
stop_z = None, 3.5, 4.0, 4.5, 5.0
constraint: stop_z > entry_z
```

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
- `scripts/run_timing_bidask_execution.py`
- `scripts/run_timing_robustness.py`
- `output/tables/timing_extension_summary.csv`
- `output/tables/timing_extension_bidask_comparison.csv`
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

The old quote parquet files include minute-level `bid`, `ask`, `bidsiz`, and `asksiz`, so the execution audit can charge top-of-book bid/ask boundary costs at position-change timestamps.

The current accounting convention is:

- gross P&L is midpoint residual return over the same holding window;
- cost is explicit bid/ask boundary cost at entries, exits, and position changes;
- net P&L is midpoint gross P&L minus boundary execution cost.

For a long residual trade, the script buys XLK at the prevailing ask and shorts the stock leg at the prevailing bid. At exit, it sells XLK at the prevailing bid and covers the stock leg at the prevailing ask. For a short residual trade, the script shorts XLK at the bid and buys the stock leg at the ask. At exit, it covers XLK at the ask and sells the stock leg at the bid.

This is still a minute-level top-of-book audit. It does not solve quote depth, queue position, latency, partial fills, borrow, or market impact.

The repository includes direct execution comparisons:

- `output/tables/midpoint_vs_bidask_execution_comparison.csv`
- `output/tables/old_pair_validation_selected_execution_fixed.csv`
- `output/tables/enhanced_sparse_bidask_comparison.csv`
- `output/tables/timing_extension_bidask_comparison.csv`

The comparison tables keep the older half-spread approximation where available, so the report can distinguish midpoint-only, half-spread-cost, and explicit bid/ask boundary-cost economics.

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
- z-score stop-loss diagnostics;
- trade-level logging with entry time, exit time, direction, holding minutes, P&L, cost, and exit reason;
- consistent midpoint-gross-minus-bid/ask-boundary-cost execution auditing from old quote parquet files;
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

Validation-selected March test results after the fixed execution-accounting audit from `output/tables/old_pair_validation_selected_execution_fixed.csv`:

| Pair | Validation Net bps | March Gross bps | March Cost bps | March Net bps | March Trades |
|---|---:|---:|---:|---:|---:|
| XLK-ORCL | 264.18 | 509.66 | 734.76 | -225.10 | 17 |
| XLK-MSFT | 234.67 | 415.20 | 648.19 | -232.99 | 17 |
| XLK-AAPL | 279.65 | 358.66 | 667.12 | -308.45 | 14 |
| XLK-CRM | 235.94 | 318.01 | 633.14 | -315.13 | 14 |
| XLK-AVGO | 104.12 | 753.64 | 1153.16 | -399.52 | 19 |
| XLK-NVDA | 337.88 | 1303.73 | 1787.47 | -483.73 | 32 |
| XLK-AMD | 266.84 | 908.59 | 1453.11 | -544.52 | 31 |
| XLK-CSCO | 220.43 | 844.95 | 1485.58 | -640.63 | 38 |

Sparse market-neutral audit:

| Sample | Old Net bps | Fixed Bid/Ask Cost bps | Fixed Net bps |
|---|---:|---:|---:|
| Train | 86.93 | 158.46 | -40.74 |
| Test | -89.03 | 33.16 | -115.24 |

XLK-only timing audit:

| Sample | Old Net bps | Fixed Bid/Ask Cost bps | Fixed Net bps |
|---|---:|---:|---:|
| January | 144.93 | 142.29 | 144.89 |
| February | 264.61 | 137.45 | 264.60 |
| March | 638.35 | 232.32 | 638.42 |

The key result of the execution update is that ORCL and sparse market-neutral positives should not be presented as alpha, while the XLK-only timing extension survives the stricter top-of-book boundary-cost audit.

## Important Output Files

| Path | Description |
|---|---|
| `output/tables/old_pair_leaderboard.csv` | Validation-selected pair leaderboard with March test performance |
| `output/tables/pair_trading_leaderboard.csv` | Alias table for the dedicated pair-trading module |
| `output/tables/old_pair_zscore_grid.csv` | Full pair z-score grid |
| `output/tables/old_pair_trade_log.csv` | Trade-level log for all pair/grid runs |
| `output/tables/old_pair_trade_log_execution_fixed.csv` | Trade-level pair log under consistent execution accounting |
| `output/tables/old_pair_validation_selected_execution_fixed.csv` | Validation-selected pair leaderboard under fixed execution accounting |
| `output/tables/old_pair_stoploss_grid.csv` | Z-score stop-loss diagnostic grid |
| `output/tables/old_strategy_diagnostics.csv` | Strategy-level diagnostics |
| `output/tables/old_data_diagnostics.csv` | Data-quality and spread diagnostics |
| `output/tables/old_selection_audit.csv` | Data-snooping and claim-validity audit |
| `output/tables/midpoint_vs_bidask_execution_comparison.csv` | Midpoint vs bid/ask-aware execution comparison |
| `output/tables/enhanced_sparse_bidask_comparison.csv` | Sparse old cost approximation vs fixed bid/ask boundary audit |
| `output/tables/timing_extension_bidask_comparison.csv` | Timing old cost approximation vs fixed bid/ask boundary audit |
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
python3 scripts/run_old_data_execution_audit_fixed.py
python3 scripts/run_final_analysis.py
python3 scripts/run_sparse_bidask_execution.py
python3 scripts/run_timing_extension.py
python3 scripts/run_timing_bidask_execution.py
python3 scripts/run_timing_robustness.py
python3 scripts/make_report.py
```

For a faster smoke test:

```bash
python3 scripts/run_old_data_method_upgrade.py --quick
```

Named module entrypoints are also provided:

```bash
python3 scripts/run_pair_trading.py
python3 scripts/run_zscore_heatmap.py
python3 scripts/run_bidask_execution.py
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
