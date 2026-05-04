# Method Update: Pair Trading, Z-Score Heatmaps, and Execution Costs

This note documents the latest update to the XLK statistical-arbitrage project.

## Motivation

The previous project version had two weaknesses:

1. The z-score rule used an overly conservative threshold, especially `entry_z = 3.5`, which created too few trades.
2. Some results were too close to midpoint backtests and did not sufficiently demonstrate how bid/ask execution costs affect the strategy.

The professor feedback was to try high-frequency pair trading, show z-score heatmaps, test smaller thresholds, add stop/risk controls, and make transaction-cost diagnostics more explicit.

## New Script

The main new script is:

```bash
python3 scripts/run_old_data_method_upgrade.py
```

It reads:

```text
data/processed/minute_quotes_2026_01.parquet
data/processed/minute_quotes_2026_02.parquet
data/processed/minute_quotes_2026_03.parquet
data/processed/minute_trades_2026_01.parquet
data/processed/minute_trades_2026_02.parquet
data/processed/minute_trades_2026_03.parquet
```

The script does not depend on `research_panel.parquet`.

## Experimental Design

The updated split is:

```text
Train:      January 2026
Validation: February 2026
Test:       March 2026
```

The train period estimates pair betas and diagnostics. The validation period selects z-score and max-holding parameters. The test period evaluates the selected strategy out of sample.

## Pair Trading Method

For each stock in the old eight-name universe:

```text
r_XLK,t = beta * r_stock,t + residual_t
spread_t = cumulative residual_t
z_t = rolling z-score(spread_t)
```

Trading rule:

```text
z_t > entry_z   -> short XLK, long beta * stock
z_t < -entry_z  -> long XLK, short beta * stock
```

Exit rule:

```text
normal exit: z-score crosses the exit band
max holding: position age exceeds the selected max_holding_minutes
end of day: position is flattened
```

The update also writes a z-score stop-loss diagnostic grid for the validation-selected rules:

```text
stop_z = None, 3.5, 4.0, 4.5, 5.0
constraint: stop_z > entry_z
```

## Parameter Grid

```text
entry_z = 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5
exit_z  = 0.0, 0.25, 0.5, 0.75, 1.0, 1.25
max_holding_minutes = None, 30, 60, 120, 240
```

Only combinations with `exit_z < entry_z` are evaluated.

## Execution-Cost Upgrade

Because the old quote parquet files include `bid` and `ask`, the update now computes actual entry and exit fills from the contemporaneous NBBO.

Long residual execution:

```text
entry: buy XLK at ask, short stock at bid
exit:  sell XLK at bid, cover stock at ask
```

Short residual execution:

```text
entry: short XLK at bid, buy stock at ask
exit:  cover XLK at ask, sell stock at bid
```

The older half-spread cost approximation is still shown in the comparison table as a benchmark.

## New Outputs

Tables:

```text
output/tables/old_data_diagnostics.csv
output/tables/old_pair_zscore_grid.csv
output/tables/old_pair_trade_log.csv
output/tables/old_pair_leaderboard.csv
output/tables/pair_trading_leaderboard.csv
output/tables/old_strategy_diagnostics.csv
output/tables/old_selection_audit.csv
output/tables/old_pair_stoploss_grid.csv
output/tables/midpoint_vs_bidask_execution_comparison.csv
```

Figures:

```text
output/figures/heatmap_validation_net_bps.png
output/figures/heatmap_test_net_bps.png
output/figures/heatmap_trade_count.png
output/figures/pair_leaderboard_test_net_bps.png
output/figures/pair_best_cumulative_pnl.png
output/figures/pair_best_zscore_with_trades.png
output/figures/midpoint_vs_bidask_execution_comparison.png
output/figures/drawdown_curve_best_strategy.png
```

## Result Summary

The full run generated:

```text
6,840 grid rows
219,137 trade-log rows
```

The validation period can select rules with positive net bps. Most selected pairs still fail in March, while XLK-ORCL is strongly positive under the explicit bid/ask-fill model and should be treated as an execution diagnostic pending deeper tradeability checks.

Top validation-selected March test results:

| Pair | Validation Net bps | March Test Net bps | March Trades |
|---|---:|---:|---:|
| XLK-ORCL | 3665.35 | 10248.72 | 112 |
| XLK-MSFT | 234.67 | -232.96 | 17 |
| XLK-AAPL | 279.65 | -308.56 | 14 |
| XLK-CRM | 233.63 | -312.75 | 14 |
| XLK-AVGO | 104.12 | -401.04 | 19 |
| XLK-NVDA | 337.88 | -483.73 | 32 |
| XLK-AMD | 266.84 | -544.06 | 31 |
| XLK-CSCO | 215.25 | -640.63 | 38 |

The most important diagnostic is the midpoint-vs-bid/ask comparison for the selected XLK-ORCL rule:

| Execution Model | Sample | Gross bps | Cost bps | Net bps |
|---|---|---:|---:|---:|
| Midpoint no cost | Validation | 918.89 | 0.00 | 918.89 |
| Half-spread cost approximation | Validation | 918.89 | 1209.27 | -290.38 |
| Actual bid/ask fills | Validation | 4870.06 | 1204.71 | 3665.35 |
| Midpoint no cost | Test | 3227.84 | 0.00 | 3227.84 |
| Half-spread cost approximation | Test | 3227.84 | 3337.79 | -109.95 |
| Actual bid/ask fills | Test | 13583.04 | 3334.33 | 10248.72 |

## Interpretation

The update supports a more defensible conclusion:

> In the original eight-name universe, market-neutral high-frequency pair and basket strategies are highly sensitive to transaction costs, quote quality, and parameter choices. The explicit bid/ask-fill model is now implemented, but the strongest ORCL result should be treated as an execution diagnostic rather than a production trading claim until quote depth, size, latency, and tradeability are stress-tested.

## Removed Old Artifacts

The older standalone threshold heatmap script and outputs were removed:

```text
scripts/run_threshold_heatmap.py
output/tables/heatmap_grid_*.csv
output/figures/heatmap_net_bps_*.png
```

They were replaced by the new validation/test pair z-score heatmap framework.
