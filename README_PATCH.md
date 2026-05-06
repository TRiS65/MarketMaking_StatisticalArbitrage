# XLK execution patch for review

This patch is designed to be reviewed locally before any GitHub push.

It addresses three things that can be done with the existing old Jan-Mar data:

1. Re-audit pair-trading bid/ask execution with a consistent timing convention.
   - `scripts/run_old_data_execution_audit_fixed.py`
   - It reads `output/tables/old_pair_trade_log.csv` and old minute quote parquet files.
   - It recomputes midpoint gross P&L over the same trade window and subtracts explicit bid/ask boundary costs.
   - It writes:
     - `output/tables/old_pair_trade_log_execution_fixed.csv`
     - `output/tables/old_pair_leaderboard_execution_fixed.csv`

2. Add bid/ask-aware execution to the sparse market-neutral basket result.
   - `scripts/run_sparse_bidask_execution.py`
   - It reads `output/tables/enhanced_backtest_summary.csv`,
     `data/processed/enhanced_sparse_backtest.parquet`, and old quote parquet files.
   - It keeps the same midpoint gross returns but replaces the old half-spread approximation with exact bid/ask boundary costs at every position change.
   - It writes:
     - `data/processed/enhanced_sparse_bidask_backtest.parquet`
     - `output/tables/enhanced_sparse_bidask_summary.csv`

3. Add bid/ask-aware execution to the XLK-only timing extension.
   - `scripts/run_timing_bidask_execution.py`
   - It reads `data/processed/timing_extension_backtest.parquet` and old quote parquet files.
   - It keeps the same XLK position path but charges ask/bid boundary execution costs for every position change.
   - It writes:
     - `data/processed/timing_extension_bidask_backtest.parquet`
     - `output/tables/timing_extension_bidask_summary.csv`

Suggested order:

```bash
python3 scripts/run_old_data_method_upgrade.py
python3 scripts/run_old_data_execution_audit_fixed.py

python3 scripts/run_final_analysis.py
python3 scripts/run_sparse_bidask_execution.py

python3 scripts/run_timing_extension.py
python3 scripts/run_timing_bidask_execution.py
```

Important interpretation:

- These scripts still assume minute-level top-of-book bid/ask availability.
- They do not solve depth, order size, latency, queue priority, partial fills, or borrow constraints.
- They are designed to make the execution accounting internally consistent and to flag whether a result depends on suspicious fill conventions.
