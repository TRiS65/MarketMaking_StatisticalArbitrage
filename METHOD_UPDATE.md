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

The strategy engine also has a `stop_z` parameter for z-score stop-loss exits, although the current full grid focuses on max-holding exits.

## Parameter Grid

```text
entry_z = 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5
exit_z  = 0.0, 0.25, 0.5, 0.75, 1.0, 1.25
max_holding_minutes = None, 30, 60, 120, 240
```

Only combinations with `exit_z < entry_z` are evaluated.

## Execution-Cost Upgrade

Because the old quote parquet files include `bid` and `ask`, the update adds a bid/ask-aware execution approximation.

One-way residual cost:

```text
0.5 * XLK spread + abs(beta) * 0.5 * stock spread
```

Gross P&L is still marked with midpoint returns, but every position change pays the estimated half-spread cost. This makes the strategy much less optimistic than a midpoint-only backtest.

## New Outputs

Tables:

```text
output/tables/old_data_diagnostics.csv
output/tables/old_pair_zscore_grid.csv
output/tables/old_pair_trade_log.csv
output/tables/old_pair_leaderboard.csv
output/tables/old_strategy_diagnostics.csv
output/tables/old_selection_audit.csv
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

The validation period can select rules with positive net bps, but the selected rules generally fail in March after bid/ask costs.

Top validation-selected March test results:

| Pair | Validation Net bps | March Test Net bps | March Trades |
|---|---:|---:|---:|
| XLK-ORCL | 265.40 | -227.31 | 17 |
| XLK-MSFT | 234.74 | -235.84 | 17 |
| XLK-AAPL | 279.57 | -310.70 | 14 |
| XLK-CRM | 236.05 | -317.74 | 14 |
| XLK-AVGO | 102.97 | -402.04 | 19 |
| XLK-NVDA | 338.35 | -482.48 | 32 |
| XLK-AMD | 266.40 | -543.71 | 31 |
| XLK-CSCO | 218.93 | -635.49 | 38 |

The most important diagnostic is the midpoint-vs-bid/ask comparison for the selected XLK-ORCL rule:

| Execution Model | Sample | Gross bps | Cost bps | Net bps |
|---|---|---:|---:|---:|
| Midpoint no cost | Validation | 470.50 | 0.00 | 470.50 |
| Bid/ask aware | Validation | 470.50 | 205.10 | 265.40 |
| Midpoint no cost | Test | 509.66 | 0.00 | 509.66 |
| Bid/ask aware | Test | 509.66 | 736.97 | -227.31 |

## Interpretation

The update supports a more defensible conclusion:

> In the original eight-name universe, market-neutral high-frequency pair and basket strategies are highly sensitive to transaction costs and parameter choices. Lower z-score thresholds increase trade frequency, but the apparent midpoint profits do not survive bid/ask-aware execution out of sample. The old-universe result should therefore be framed as a diagnostic negative result rather than a production-ready arbitrage strategy.

## Removed Old Artifacts

The older standalone threshold heatmap script and outputs were removed:

```text
scripts/run_threshold_heatmap.py
output/tables/heatmap_grid_*.csv
output/figures/heatmap_net_bps_*.png
```

They were replaced by the new validation/test pair z-score heatmap framework.
