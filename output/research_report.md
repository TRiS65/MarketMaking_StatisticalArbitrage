# Microstructure-Based Fair Value and Intraday Statistical Arbitrage in XLK

## Executive Summary

This final version implements a literature-grounded diagnostic test of ETF-basket intraday statistical arbitrage using WRDS TAQ quotes/trades for January-March 2026 and the supplied XLK holdings file.  It now reports two strategy classes side by side.

The original market-neutral ETF-basket arbitrage conclusion is negative.  The active sparse microprice-signal hedge strategy is positive in the January-February selection period, with 86.93 bps net P&L, but fails out of sample in March, with -89.03 bps net P&L.  The no-trade benchmark therefore dominates the active market-neutral rule in the honest March test.

However, a second strategy class does produce a positive result: use the sparse basket microprice premium as a fair-value timing signal, but execute only XLK.  This XLK-only timing extension earns 638.35 bps net in March and 1047.88 bps net over the sample.  This is not market-neutral ETF arbitrage; it is a sparse-basket fair-value signal for intraday XLK timing.

## Data Construction

Raw WRDS TAQ files were scanned with DuckDB and aggregated to one-minute parquet files.  Quotes were filtered to regular hours, valid positive bid/ask prices and sizes, non-cancelled quotes, quoted spreads below 100 bps, and prices within 500 bps of a centered rolling median to remove narrow-spread bad ticks.  Trades were filtered to regular hours, positive price/size, and `TR_CORR = 00`.

The eight-name selected basket covers 53.54% of the XLK holdings file and is therefore treated as an incomplete risk proxy rather than a literal NAV replication basket.

## Selected Holdings

| symbol   | name                   |   official_weight_pct |   basket_weight |
|:---------|:-----------------------|----------------------:|----------------:|
| NVDA     | NVIDIA CORP            |              15.4537  |       0.288617  |
| AAPL     | APPLE INC              |              12.6167  |       0.235634  |
| MSFT     | MICROSOFT CORP         |               9.77076 |       0.182481  |
| AVGO     | BROADCOM INC           |               5.96344 |       0.111375  |
| AMD      | ADVANCED MICRO DEVICES |               3.4364  |       0.0641792 |
| CSCO     | CISCO SYSTEMS INC      |               2.65657 |       0.0496148 |
| ORCL     | ORACLE CORP            |               2.30833 |       0.043111  |
| CRM      | SALESFORCE INC         |               1.33794 |       0.0249878 |

## Minute Data Diagnostics

| symbol   |   minutes |   median_spread_bps |   avg_volume |   trade_count |
|:---------|----------:|--------------------:|-------------:|--------------:|
| AAPL     |     20861 |            2.9721   |      87114.8 |      35436759 |
| AMD      |     19553 |            9.33358  |      83976.1 |      24537293 |
| AVGO     |     18860 |           10.1902   |      51282.1 |      22154477 |
| CRM      |     18530 |           12.4987   |      26884.2 |       8300230 |
| CSCO     |     22670 |            2.55722  |      43549.1 |      11425050 |
| MSFT     |     20797 |            5.15331  |      71026.9 |      41606645 |
| NVDA     |     22693 |            1.19439  |     390865   |     138130510 |
| ORCL     |     18190 |            7.6314   |      61075.4 |      18803754 |
| XLK      |     23748 |            0.733003 |      48286.9 |      15447039 |

## Final Method

The final experiment uses the literature in the project folder as design constraints:

- d'Aspremont: search sparse mean-reverting baskets rather than forcing a dense normalized holdings basket.
- Kanamura, Rachev, and Fabozzi: evaluate spread trading as a first-passage / mean-reversion problem.
- Leung and Li: use entry/exit bands instead of continuous trading around zero.
- Martin: include proportional-cost no-trade logic and compare against no-trade.
- Gueant, Lehalle, Fernandez-Tapia; Ghoshal and Roberts: account for inventory, turnover, spread costs, and adverse-selection-style execution friction.
- Almgren: use time-varying liquidity costs rather than a constant fee.
- Dare: use a train/test statistical-arbitrage workflow.

Microprice is used only as a fair-value signal.  Executable gross P&L is computed from midpoint residual returns, with bid-ask costs charged separately.  Candidate selection and threshold choice use January-February 2026; March 2026 is the out-of-sample test.

## Sparse Candidate Ranking

| subset                  | betas                                                      |   train_adf_p |   train_half_life_minutes |   train_avg_oneway_cost_bps |    score |
|:------------------------|:-----------------------------------------------------------|--------------:|--------------------------:|----------------------------:|---------:|
| MSFT NVDA ORCL CRM AMD  | MSFT:0.0797 NVDA:0.2257 ORCL:0.0745 CRM:0.0602 AMD:0.1074  |     0.0149172 |                   187.77  |                     4.45279 | 0.197858 |
| NVDA ORCL CRM AMD       | NVDA:0.2331 ORCL:0.0795 CRM:0.0657 AMD:0.1105              |     0.0220765 |                   225.312 |                     4.10373 | 0.216807 |
| NVDA AVGO ORCL CRM AMD  | NVDA:0.2092 AVGO:0.0954 ORCL:0.0703 CRM:0.0638 AMD:0.0975  |     0.0294932 |                   196.379 |                     4.63133 | 0.220309 |
| MSFT NVDA AVGO ORCL AMD | MSFT:0.0794 NVDA:0.2076 AVGO:0.0929 ORCL:0.0715 AMD:0.0974 |     0.0471017 |                   198.326 |                     4.5497  | 0.237259 |
| NVDA AVGO ORCL AMD      | NVDA:0.2145 AVGO:0.0966 ORCL:0.0766 AMD:0.1002             |     0.0565331 |                   233.876 |                     4.1845  | 0.257161 |
| AAPL NVDA ORCL CRM AMD  | AAPL:0.0878 NVDA:0.2260 ORCL:0.0778 CRM:0.0643 AMD:0.1066  |     0.0422305 |                   258.482 |                     4.4505  | 0.260482 |
| MSFT NVDA ORCL AMD      | MSFT:0.0852 NVDA:0.2305 ORCL:0.0803 AMD:0.1099             |     0.0675366 |                   257.805 |                     4.05107 | 0.27746  |
| NVDA ORCL AMD           | NVDA:0.2389 ORCL:0.0862 AMD:0.1134                         |     0.0655512 |                   286.128 |                     3.63619 | 0.281339 |

## Final Backtest

| strategy             | sample   |   trades |   avg_abs_position |   gross_bps |   cost_bps |   net_bps |   sharpe_minute_ann |   max_drawdown_bps |
|:---------------------|:---------|---------:|-------------------:|------------:|-----------:|----------:|--------------------:|-------------------:|
| sparse_e3.5_x1_plain | test     |        2 |          0.044489  |    -82.0832 |    6.94978 |  -89.033  |            -3.24726 |          -122.912  |
| sparse_e3.5_x1_plain | train    |        6 |          0.0489195 |    117.726  |   30.7967  |   86.9296 |             1.3562  |           -80.4235 |
| literature_no_trade  | test     |        0 |          0         |      0      |    0       |    0      |           nan       |             0      |
| literature_no_trade  | train    |        0 |          0         |      0      |    0       |    0      |           nan       |             0      |

## Positive Timing Extension

The positive extension follows a different economic claim.  The basket is no longer traded as a hedge.  Instead, the sparse basket supplies a microprice fair-value premium signal for trading XLK only:

- signal basket: `MSFT NVDA ORCL CRM AMD`;
- signal: microprice premium minus five-day rolling premium mean;
- traded instrument: XLK only;
- entry: premium above/below 50 bps;
- exit: premium reverts inside 25 bps;
- max hold: intraday.

| period   |   gross_bps |   cost_bps |   net_bps |   trades |   avg_abs_position |   long_gross_bps |   short_gross_bps |   xlk_buyhold_bps |
|:---------|------------:|-----------:|----------:|---------:|-------------------:|-----------------:|------------------:|------------------:|
| jan      |     287.185 |    142.26  |   144.925 |       44 |           0.687983 |         -127.266 |           414.451 |          -345.091 |
| feb      |     402.055 |    137.45  |   264.605 |       50 |           0.73375  |          139.978 |           262.076 |          -204.096 |
| mar      |     870.743 |    232.39  |   638.353 |       58 |           0.757126 |          550.871 |           319.872 |          -370.728 |
| all      |    1559.98  |    512.099 |  1047.88  |      152 |           0.727119 |          563.583 |           996.4   |          -919.915 |

Controls show that the result is not explained by simple long exposure or by flipping the signal:

| control                     |   train_net_bps |   mar_net_bps |   avg_pos_mar |
|:----------------------------|----------------:|--------------:|--------------:|
| selected                    |         409.531 |     638.353   |      0.28881  |
| sign_flip                   |        -968.949 |   -1103.13    |     -0.28881  |
| active_always_long          |        -943.525 |      -1.39127 |      0.757126 |
| active_always_short         |         384.107 |    -463.389   |     -0.757126 |
| circular_shift_mean         |         nan     |    -440.23    |    nan        |
| circular_shift_p95          |         nan     |     447.052   |    nan        |
| selected_vs_circular_pvalue |         nan     |       0.0175  |    nan        |

Cost sensitivity:

|   cost_multiplier |       all |      feb |        jan |     mar |
|------------------:|----------:|---------:|-----------:|--------:|
|               1   | 1047.88   |  264.605 |  144.925   | 638.353 |
|               1.5 |  791.834  |  195.88  |   73.7957  | 522.158 |
|               2   |  535.784  |  127.156 |    2.66595 | 405.962 |
|               3   |   23.6846 |  -10.294 | -139.594   | 173.572 |
|               4   | -488.415  | -147.744 | -281.853   | -58.818 |

## Model Comparison

| model                               | selection_rule                                    |   train_net_bps |   march_net_bps |   full_net_bps | verdict                                                                |
|:------------------------------------|:--------------------------------------------------|----------------:|----------------:|---------------:|:-----------------------------------------------------------------------|
| baseline_original_best              | best full-sample diagnostic only                  |        nan      |        nan      |     -579.651   | invalid as tradable positive result; diagnostic failure                |
| v2_best_by_train_overall            | max Jan-Feb net among v2 grid                     |        -48.1997 |        -47.6356 |      -95.8354  | methodologically better signals, but no train-positive active strategy |
| v2_best_march_diagnostic            | best March net, not allowed for ex-ante selection |       -118.168  |         54.0767 |      -64.0912  | useful diagnostic; not an honest selected strategy                     |
| hybrid_sparse_micro_signal_mid_exec | sparse portfolio + threshold selected on Jan-Feb  |         86.9296 |        -89.033  |       -2.10341 | train-positive, fails OOS; no-trade dominates in March                 |
| literature_no_trade                 | transaction-cost no-trade benchmark               |          0      |          0      |        0       | best honest March result among ex-ante choices                         |

## Selection Audit

The `v2_best_march_diagnostic` row is not selected because it sorts the grid by March P&L after observing March.  March is the test set, so choosing that row is selection-on-test / look-ahead bias.  It remains useful as a post-mortem diagnostic, but it cannot be reported as an honest tradable strategy.

| model                               | selection_protocol                                                               |   train_net_bps |   march_net_bps | bias_flag                          | final_use                                                                  |
|:------------------------------------|:---------------------------------------------------------------------------------|----------------:|----------------:|:-----------------------------------|:---------------------------------------------------------------------------|
| v2_best_by_train_overall            | Valid ex-ante selection: choose from grid using Jan-Feb only, then report March. |        -48.1997 |        -47.6356 | No test leakage.                   | No, active rule loses in train and March; useful as diagnostic benchmark.  |
| v2_best_march_diagnostic            | Invalid as final strategy: choose after sorting by March net P&L.                |       -118.168  |         54.0767 | Selection-on-test/look-ahead bias. | No, because March is the test set. Keep only as post-mortem diagnostic.    |
| hybrid_sparse_micro_signal_mid_exec | Valid ex-ante selection: sparse basket and threshold selected on Jan-Feb.        |         86.9296 |        -89.033  | No test leakage in selection.      | Yes as the final active experiment, but it fails OOS; compare to no-trade. |
| literature_no_trade                 | Benchmark implied by transaction-cost/no-trade literature.                       |          0      |          0      | None.                              | Yes as the final decision benchmark; dominates active rules in March.      |

## Interpretation

The initial holdings-weight basket result was not a tradable positive result: it lost before costs and then lost more after costs.  The v2 diagnostic improved methodology by treating microprice as signal-only and using rolling residual signals, but strict January-February selection did not find a train-positive active strategy.  The final hybrid sparse specification found a train-positive microprice signal, but midpoint-executable March P&L was negative.

The most defensible conclusion is therefore two-part: **the proposed market-neutral ETF-basket arbitrage fails under this incomplete-basket implementation, but the same sparse-basket microprice premium can be repurposed into a profitable XLK-only timing signal in this sample.**

## Reproducibility

```bash
python3 scripts/build_dataset.py
python3 scripts/run_final_analysis.py
python3 scripts/make_report.py
```
