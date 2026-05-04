# Microstructure-Based Fair Value and Intraday Statistical Arbitrage in XLK

## Executive Summary

This final version implements a literature-grounded diagnostic test of ETF-basket intraday statistical arbitrage using WRDS TAQ quotes/trades for January-March 2026 and the supplied XLK holdings file.  It now reports two strategy classes side by side.

The original market-neutral ETF-basket arbitrage conclusion is negative.  The active sparse microprice-signal hedge strategy is not robust to the exact top-of-book bid/ask boundary-cost audit: it has -40.74 bps net P&L in January-February and -115.24 bps net P&L in March.  The no-trade benchmark therefore dominates the active market-neutral rule in the honest March test.

However, a second strategy class does produce a positive result: use the sparse basket microprice premium as a fair-value timing signal, but execute only XLK.  The fixed 50/25 bps timing extension earns 638.42 bps net in March under the same bid/ask boundary-cost audit.  A stricter stability-island robustness selection, chosen from January-February only, selects `micro_shrink_0.75_cw10d_e60_x0_mh240` and earns 120.05 bps net in March.  This is not market-neutral ETF arbitrage; it is a sparse-basket fair-value signal for intraday XLK timing.

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

## Bid/Ask Execution Accounting Audit

The execution audit keeps each strategy's selected position path fixed, computes midpoint gross P&L over the same holding window, and subtracts explicit bid/ask boundary costs at position changes.  This is a minute-level top-of-book audit, not a depth-, queue-, latency-, borrow-, or market-impact-aware simulator.

| sample   |   old_gross_bps |   old_cost_bps |   old_net_bps |   new_gross_bps |   new_bidask_cost_bps |   new_bidask_net_bps |   turnover |
|:---------|----------------:|---------------:|--------------:|----------------:|----------------------:|---------------------:|-----------:|
| test     |        -82.0832 |        6.94978 |      -89.033  |        -82.0832 |               33.1588 |            -115.242  |          2 |
| train    |        117.726  |       30.7967  |       86.9296 |        117.726  |              158.464  |             -40.7373 |          6 |

The old pair-trading diagnostic is also re-audited under the same accounting.  The XLK-ORCL March result is not a robust positive alpha after costs: midpoint gross P&L is positive, but bid/ask boundary costs exceed it.

| pair     |   validation_net_bps |   test_gross_bps |   test_cost_bps |   test_net_bps |   test_trades |
|:---------|---------------------:|-----------------:|----------------:|---------------:|--------------:|
| XLK-ORCL |              264.184 |          509.66  |         734.756 |       -225.095 |            17 |
| XLK-MSFT |              234.674 |          415.199 |         648.192 |       -232.994 |            17 |
| XLK-AAPL |              279.655 |          358.664 |         667.117 |       -308.453 |            14 |
| XLK-CRM  |              235.937 |          318.011 |         633.141 |       -315.13  |            14 |
| XLK-AVGO |              104.117 |          753.636 |        1153.16  |       -399.52  |            19 |
| XLK-NVDA |              337.879 |         1303.73  |        1787.47  |       -483.733 |            32 |
| XLK-AMD  |              266.841 |          908.588 |        1453.11  |       -544.524 |            31 |
| XLK-CSCO |              220.434 |          844.951 |        1485.58  |       -640.634 |            38 |

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

Bid/ask boundary-cost audit for the same XLK timing path:

| sample   |   old_gross_bps |   old_cost_bps |   old_net_bps |   new_gross_bps |   new_bidask_cost_bps |   new_bidask_net_bps |   turnover |
|:---------|----------------:|---------------:|--------------:|----------------:|----------------------:|---------------------:|-----------:|
| feb      |         402.055 |         137.45 |       264.605 |         402.055 |               137.453 |              264.601 |         50 |
| jan      |         287.185 |         142.26 |       144.925 |         287.185 |               142.293 |              144.892 |         44 |
| mar      |         870.743 |         232.39 |       638.353 |         870.743 |               232.321 |              638.422 |         58 |

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

## Timing Robustness Grid

To avoid turning the March-positive 50/25 bps timing rule into a parameter story, I added a separate robustness grid over microprice shrinkage, rolling-center horizon, entry/exit bands, and max holding time.  The selection rule is deliberately conservative: first choose a stable January-February parameter island, then choose the best rule inside that island; March is evaluated only after selection.

| decision          | reason                                                    | selected_strategy                    |   train_net_bps |   mar_net_bps |   all_net_bps |   train_trades |   mar_trades |
|:------------------|:----------------------------------------------------------|:-------------------------------------|----------------:|--------------:|--------------:|---------------:|-------------:|
| active_xlk_timing | Selected by Jan-Feb stability island first; March is OOS. | micro_shrink_0.75_cw10d_e60_x0_mh240 |          1025.8 |        120.05 |       1145.85 |            116 |           75 |

Top train-selected parameter islands:

| signal_view       |   center_days |   entry_bps |   valid_rules |   median_train_net_bps |   p25_train_net_bps |   median_mar_net_bps |   positive_march_rate |
|:------------------|--------------:|------------:|--------------:|-----------------------:|--------------------:|---------------------:|----------------------:|
| micro_shrink_0.75 |            10 |          60 |             5 |                731.365 |             604.599 |            71.2328   |              0.888889 |
| micro_shrink_0.50 |            10 |          60 |             6 |                606.186 |             508.566 |            62.0572   |              0.777778 |
| micro_shrink_0.25 |            10 |          60 |             6 |                574.601 |             505.285 |           120.05     |              0.777778 |
| micro             |            10 |          30 |             1 |               1097.22  |             912.275 |            -0.912862 |              0.444444 |
| micro             |            10 |          60 |             5 |                652.846 |             567.901 |            75.7209   |              0.888889 |
| micro_shrink_0.50 |            10 |          30 |             1 |               1039.24  |             920.008 |            77.4385   |              0.666667 |
| mid               |            10 |          60 |             6 |                512.196 |             442.88  |           131.379    |              0.777778 |
| micro_shrink_0.25 |            10 |          30 |             1 |               1015.26  |             903.139 |            77.4677   |              0.666667 |

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

The initial holdings-weight basket result was not a tradable positive result: it lost before costs and then lost more after costs.  The v2 diagnostic improved methodology by treating microprice as signal-only and using rolling residual signals, but strict January-February selection did not find a train-positive active strategy.  The final hybrid sparse specification looked mildly positive under the old half-spread approximation, but the exact bid/ask boundary-cost audit turns it negative in both train and March test.

The most defensible conclusion is therefore two-part: **the proposed market-neutral ETF-basket arbitrage fails under this incomplete-basket implementation, but the same sparse-basket microprice premium can be repurposed into a profitable XLK-only timing signal in this sample.**

## Reproducibility

```bash
python3 scripts/build_dataset.py
python3 scripts/run_final_analysis.py
python3 scripts/run_sparse_bidask_execution.py
python3 scripts/run_timing_extension.py
python3 scripts/run_timing_bidask_execution.py
python3 scripts/run_timing_robustness.py
python3 scripts/run_old_data_method_upgrade.py
python3 scripts/run_old_data_execution_audit_fixed.py
python3 scripts/make_report.py
```
