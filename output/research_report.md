# XLK Microstructure Statistical Arbitrage: Final-Data Progress Report

## Dataset

- Raw data: `/Users/yezi/Desktop/Statistical_Arbitrage/final_proj/data/finaldata`
- Sample: `2025-05-01` to `2026-05-01`
- Universe: `XLK` + 20 constituents
- Requested-but-dropped symbols after quote/trade cleaning: `none`
- Split: train before `2026-02-01`, validation before `2026-03-01`, test before `2026-05-01`

## Main Research Position

The project now separates two claims:

1. **Market-neutral XLK-vs-basket arbitrage.** This remains the hard claim.  It must survive alternative spread definitions, explicit transaction-cost scenarios, and out-of-sample testing.
2. **Sparse-basket fair-value timing.** This is a different claim: the constituent basket is used as a signal, while only XLK is traded.

This language directly addresses the professor's concern that price definition, spread construction, and execution assumptions can dominate high-frequency results.

## Top Holdings Used

| symbol   | name                        |   official_weight_pct |   basket_weight | used_in_clean_panel   |
|:---------|:----------------------------|----------------------:|----------------:|:----------------------|
| NVDA     | NVIDIA CORP                 |              14.492   |       0.186069  | True                  |
| AAPL     | APPLE INC                   |              12.3596  |       0.158691  | True                  |
| MSFT     | MICROSOFT CORP              |               9.24841 |       0.118745  | True                  |
| AVGO     | BROADCOM INC                |               6.00254 |       0.0770694 | True                  |
| MU       | MICRON TECHNOLOGY INC       |               4.46675 |       0.0573507 | True                  |
| AMD      | ADVANCED MICRO DEVICES      |               4.30259 |       0.055243  | True                  |
| INTC     | INTEL CORP                  |               3.42365 |       0.0439579 | True                  |
| CSCO     | CISCO SYSTEMS INC           |               2.6563  |       0.0341054 | True                  |
| PLTR     | PALANTIR TECHNOLOGIES INC A |               2.40886 |       0.0309285 | True                  |
| LRCX     | LAM RESEARCH CORP           |               2.34648 |       0.0301275 | True                  |
| AMAT     | APPLIED MATERIALS INC       |               2.26041 |       0.0290225 | True                  |
| ORCL     | ORACLE CORP                 |               2.13269 |       0.0273826 | True                  |
| TXN      | TEXAS INSTRUMENTS INC       |               1.86674 |       0.023968  | True                  |
| KLAC     | KLA CORP                    |               1.6563  |       0.021266  | True                  |
| IBM      | INTL BUSINESS MACHINES CORP |               1.58865 |       0.0203974 | True                  |
| ADI      | ANALOG DEVICES INC          |               1.42237 |       0.0182625 | True                  |
| QCOM     | QUALCOMM INC                |               1.38244 |       0.0177498 | True                  |
| ANET     | ARISTA NETWORKS INC         |               1.30529 |       0.0167592 | True                  |
| SNDK     | SANDISK CORP                |               1.28246 |       0.0164661 | True                  |
| APH      | AMPHENOL CORP CL A          |               1.28031 |       0.0164385 | True                  |

## Data Diagnostics

| symbol   | start               | end                 |   minutes |   median_spread_bps |   avg_volume |   trade_count |
|:---------|:--------------------|:--------------------|----------:|--------------------:|-------------:|--------------:|
| AAPL     | 2025-05-01 09:31:00 | 2026-04-30 15:59:00 |     89036 |             2.54677 |     94615.3  |     139411801 |
| ADI      | 2025-05-01 09:32:00 | 2026-04-30 15:59:00 |     69042 |            23.0443  |      6743.31 |      11433530 |
| AMAT     | 2025-05-01 09:32:00 | 2026-04-30 15:59:00 |     73824 |            18.5646  |     13910.3  |      21025743 |
| AMD      | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     86676 |             6.83177 |    106564    |     115425809 |
| ANET     | 2025-05-01 09:33:00 | 2026-04-30 15:59:00 |     76955 |            14.7529  |     18157.2  |      22352603 |
| APH      | 2025-05-01 09:34:00 | 2026-04-30 15:59:00 |     83767 |             8.2512  |     17290.4  |      21496428 |
| AVGO     | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     81264 |            10.1609  |     46741.5  |      81720848 |
| CSCO     | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     94285 |             2.31642 |     37419.6  |      37859860 |
| IBM      | 2025-05-01 09:32:00 | 2026-04-30 15:59:00 |     74934 |            11.1128  |     10153.5  |      20050703 |
| INTC     | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     95223 |             4.31499 |    221496    |      97876707 |
| KLAC     | 2025-05-01 09:33:00 | 2026-04-30 15:59:00 |     70671 |            44.1827  |      1919.67 |       7614350 |
| LRCX     | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     79947 |             9.44617 |     20801.7  |      29280656 |
| MSFT     | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     84612 |             5.86216 |     49522.5  |     115802312 |
| MU       | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     83149 |             8.96386 |     60985    |      79375851 |
| NVDA     | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     95743 |             1.4857  |    394305    |     495268838 |
| ORCL     | 2025-05-01 09:31:00 | 2026-04-30 15:59:00 |     78274 |             9.39249 |     50012.1  |      68226541 |
| PLTR     | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     90375 |             4.27282 |    135419    |     155666878 |
| QCOM     | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     78211 |            10.1143  |     18734.1  |      28969759 |
| SNDK     | 2025-05-01 09:43:00 | 2026-04-30 15:59:00 |     73310 |            34.2066  |     21661.8  |      29732564 |
| TXN      | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     75598 |            15.0657  |     13448.4  |      19836036 |
| XLK      | 2025-05-01 09:30:00 | 2026-04-30 15:59:00 |     97400 |             1.06969 |     26936.9  |      49165476 |

## Professor Feedback Checks

The new `run_professor_robustness.py` module answers the main methodology questions:

- `r_XLK,t` is explicitly one-minute log return, not price.
- Cumulative residual-return spreads are compared against direct log-price spreads and log-price regression residuals.
- Gross/no-cost P&L is separated from 0.25-spread, 0.50-spread, and clipped last-trade execution proxies.
- OU / Avellaneda-Lee style diagnostics are reported for each spread.

Best validation-selected test rows:

| pair     | stock   | spread_type               |   entry_z |   exit_z |   clipped_last_trade_proxy |   half_spread_taker_cost |   no_cost_midpoint |   quarter_spread_cost |
|:---------|:--------|:--------------------------|----------:|---------:|---------------------------:|-------------------------:|-------------------:|----------------------:|
| XLK-AMD  | AMD     | direct_log_price          |       1   |     0.5  |                  383.05    |                14.5467   |         453.352    |              233.949  |
| XLK-NVDA | NVDA    | direct_log_price          |       1   |     0.5  |                  280.183   |              -113.089    |         409.075    |              147.993  |
| XLK-PLTR | PLTR    | price_regression_residual |       1   |     0.5  |                  244.598   |                -2.27305  |         254.288    |              126.008  |
| XLK-AAPL | AAPL    | cum_residual_return       |       2   |     0    |                  182.427   |                26.1289   |         200.099    |              113.114  |
| XLK-INTC | INTC    | direct_log_price          |       2.5 |     0.5  |                   67.6228  |                -0.609835 |          52.2287   |               25.8094 |
| XLK-MSFT | MSFT    | direct_log_price          |       1   |     0.5  |                   97.1197  |              -124.174    |         102.432    |              -10.8707 |
| XLK-ORCL | ORCL    | price_regression_residual |       2.5 |     0    |                  -48.5873  |              -124.848    |           1.61472  |              -61.6165 |
| XLK-ANET | ANET    | direct_log_price          |       1   |     0.5  |                  116.258   |              -296.449    |          88.0084   |             -104.22   |
| XLK-CSCO | CSCO    | cum_residual_return       |       2.5 |     0    |                  -43.9858  |              -154.156    |         -67.9473   |             -111.052  |
| XLK-KLAC | KLAC    | price_regression_residual |       1   |     0.25 |                  517.015   |              -803.084    |         562.052    |             -120.516  |
| XLK-ORCL | ORCL    | cum_residual_return       |       2   |     0.25 |                  -45.0959  |              -193.833    |         -53.2113   |             -123.522  |
| XLK-LRCX | LRCX    | price_regression_residual |       1   |     0    |                  165.687   |              -444.848    |         174.007    |             -135.421  |
| XLK-IBM  | IBM     | price_regression_residual |       1   |     0.25 |                  270.605   |              -638.361    |         325.572    |             -156.395  |
| XLK-ANET | ANET    | price_regression_residual |       1   |     0.5  |                    9.71263 |              -329.961    |         -14.7901   |             -172.376  |
| XLK-TXN  | TXN     | direct_log_price          |       1   |     0.5  |                  -30.9914  |              -401.86     |          -0.885628 |             -201.373  |

OU and stationarity diagnostics:

| pair     | spread_type               |   train_adf_p |   train_half_life_minutes |   ou_half_life_minutes |   train_spread_std_bps |
|:---------|:--------------------------|--------------:|--------------------------:|-----------------------:|-----------------------:|
| XLK-ANET | cum_residual_return       |     0.015942  |                   1444.12 |                1444.12 |                164.336 |
| XLK-ADI  | price_regression_residual |     0.0410928 |                   3323.81 |                3323.81 |               1851.2   |
| XLK-ORCL | cum_residual_return       |     0.0579981 |                   2171.06 |                2171.06 |                205.481 |
| XLK-AVGO | cum_residual_return       |     0.0768712 |                   1855.46 |                1855.46 |                179.624 |
| XLK-AMD  | cum_residual_return       |     0.139174  |                   2648.77 |                2648.77 |                216.294 |
| XLK-AAPL | cum_residual_return       |     0.189768  |                   3446.39 |                3446.39 |                258.034 |
| XLK-KLAC | cum_residual_return       |     0.204152  |                   2822.04 |                2822.04 |                225.541 |
| XLK-MSFT | price_regression_residual |     0.213026  |                   3347.22 |                3347.22 |               2067.26  |
| XLK-AMAT | price_regression_residual |     0.259887  |                   6009.01 |                6009.01 |               2050.68  |
| XLK-TXN  | cum_residual_return       |     0.269308  |                   3332.43 |                3332.43 |                240.167 |
| XLK-QCOM | cum_residual_return       |     0.297715  |                   3813.46 |                3813.46 |                262.07  |
| XLK-MSFT | cum_residual_return       |     0.297782  |                   3754.76 |                3754.76 |                258.577 |
| XLK-PLTR | cum_residual_return       |     0.328348  |                   3715.32 |                3715.32 |                246.907 |
| XLK-MU   | price_regression_residual |     0.35965   |                   7607.93 |                7607.93 |               2153.37  |
| XLK-CSCO | price_regression_residual |     0.371777  |                   7391.23 |                7391.23 |               2258.36  |

## Top-20 Method Diagnostics

The new top-20 method diagnostic layer absorbs the methodology addendum critically rather than copying it wholesale.  It is real-data only, has no synthetic fallback, uses lagged Kalman beta, charges passive-entry adverse selection, writes every tried rule to a trial registry, and applies a no-trade selection gate.

| method         |   selected_pairs |   gate_pass_pairs |   raw_validation_net_bps |   raw_test_net_bps |   raw_positive_test_pairs |   gate_test_net_bps |   gate_positive_test_pairs |   test_trades |
|:---------------|-----------------:|------------------:|-------------------------:|-------------------:|--------------------------:|--------------------:|---------------------------:|--------------:|
| baseline       |               20 |                 0 |                -1359.79  |         -14635.7   |                         0 |                   0 |                          0 |          2848 |
| coint_filter   |                3 |                 0 |                 -250.228 |           -837.028 |                         0 |                   0 |                          0 |           322 |
| combined       |                3 |                 0 |                 -185.587 |           -979.436 |                         0 |                   0 |                          0 |           218 |
| kalman_lagged  |               20 |                 0 |                -3643.45  |         -12823.4   |                         0 |                   0 |                          0 |          2609 |
| passive_stress |               20 |                 0 |                  420.997 |          -9767.92  |                         0 |                   0 |                          0 |          2943 |
| sscore_ou_gate |               20 |                 0 |                -2270.74  |         -12309.9   |                         0 |                   0 |                          0 |          2513 |

No-trade gate examples:

| pair_or_basket   | method         |   validation_net_bps |   test_net_bps |   test_2x_cost_net_bps |   test_latency1_net_bps | gate_selected_flag   | gate_reason       |
|:-----------------|:---------------|---------------------:|---------------:|-----------------------:|------------------------:|:---------------------|:------------------|
| XLK-AAPL         | baseline       |            144.266   |      -288.969  |               -579.396 |                -321.873 | False                | 2x_cost_net<0     |
| XLK-AAPL         | kalman_lagged  |            -23.3802  |       -38.0463 |               -367.053 |                 -58.141 | False                | validation_net<=0 |
| XLK-AAPL         | passive_stress |            143.859   |      -233.621  |               -358.607 |                -289.494 | False                | 2x_cost_net<0     |
| XLK-AAPL         | sscore_ou_gate |           -391.958   |      -341.255  |               -702.16  |                -620.173 | False                | validation_net<=0 |
| XLK-ADI          | baseline       |           -300.528   |      -785.398  |              -1218.92  |                -745.862 | False                | validation_net<=0 |
| XLK-ADI          | kalman_lagged  |           -310.8     |      -888.983  |              -1366.88  |                -947.496 | False                | validation_net<=0 |
| XLK-ADI          | passive_stress |           -208.776   |      -615.981  |               -833.178 |                -749.955 | False                | validation_net<=0 |
| XLK-ADI          | sscore_ou_gate |           -337.251   |     -1051.03   |              -2072.02  |               -1252.93  | False                | validation_net<=0 |
| XLK-AMAT         | baseline       |            -13.3909  |     -2463.93   |              -3568.38  |               -2890.78  | False                | validation_net<=0 |
| XLK-AMAT         | kalman_lagged  |           -146.005   |     -1588.53   |              -2498.38  |               -1727.84  | False                | validation_net<=0 |
| XLK-AMAT         | passive_stress |            110.973   |     -2011.72   |              -2588.95  |               -2625.16  | False                | 2x_cost_net<0     |
| XLK-AMAT         | sscore_ou_gate |            -36.3349  |      -538.612  |               -881.463 |                -574.938 | False                | validation_net<=0 |
| XLK-AMD          | baseline       |             -6.90899 |      -577.62   |              -1213.99  |                -653.415 | False                | validation_net<=0 |
| XLK-AMD          | kalman_lagged  |            112.648   |      -375.52   |               -814.225 |                -437.905 | False                | 2x_cost_net<0     |
| XLK-AMD          | passive_stress |             96.6958  |      -544.957  |               -905.895 |                -729.882 | False                | 2x_cost_net<0     |

Exit-reason audit:

| method   | sample     | exit_reason   |   trades |   gross_bps |   cost_bps |   net_bps |
|:---------|:-----------|:--------------|---------:|------------:|-----------:|----------:|
| baseline | train      | eod           |      115 |    183.689  |   477.976  | -294.287  |
| baseline | train      | max_hold      |      243 |     31.9421 |   647.802  | -615.86   |
| baseline | train      | reversion     |      241 |   2083.7    |  1204.66   |  879.033  |
| baseline | train      | stop_loss     |       75 |   -183.82   |   270.741  | -454.561  |
| baseline | validation | eod           |       10 |     24.4055 |    45.4564 |  -21.0509 |
| baseline | validation | max_hold      |       28 |     19.9112 |    51.3769 |  -31.4657 |
| baseline | validation | reversion     |       11 |    125.016  |    38.3064 |   86.71   |
| baseline | test       | eod           |       30 |    -29.9239 |   118.866  | -148.79   |
| baseline | test       | max_hold      |       71 |     13.7496 |   151.596  | -137.847  |
| baseline | test       | reversion     |       39 |    410.888  |   148.942  |  261.947  |
| baseline | test       | stop_loss     |       38 |   -142.617  |   124.865  | -267.482  |
| baseline | train      | eod           |      115 |    183.689  |   477.976  | -294.287  |
| baseline | train      | max_hold      |      247 |     13.5581 |   668.606  | -655.048  |
| baseline | train      | reversion     |      241 |   2083.7    |  1204.66   |  879.033  |
| baseline | validation | eod           |       10 |     24.4055 |    45.4564 |  -21.0509 |

XLK-only signal bucket test:

| sample   |   horizon_min |   signal_decile |   mean_future_return_bps |   count |
|:---------|--------------:|----------------:|-------------------------:|--------:|
| train    |             1 |               0 |               0.0325644  |    6996 |
| train    |             1 |               1 |               0.122036   |    6996 |
| train    |             1 |               2 |               0.0138372  |    6996 |
| train    |             1 |               3 |              -0.0977336  |    6995 |
| train    |             1 |               4 |               0.0158634  |    6996 |
| train    |             1 |               5 |              -0.0222973  |    6996 |
| train    |             1 |               6 |               0.00603886 |    6995 |
| train    |             1 |               7 |              -0.0734087  |    6996 |
| train    |             1 |               8 |              -0.0209741  |    6996 |
| train    |             1 |               9 |               0.0175283  |    6996 |
| train    |             5 |               0 |               0.0192616  |    6996 |
| train    |             5 |               1 |               0.677232   |    6996 |
| train    |             5 |               2 |               0.00713214 |    6996 |
| train    |             5 |               3 |              -0.698782   |    6995 |
| train    |             5 |               4 |              -0.0229462  |    6996 |
| train    |             5 |               5 |               0.100749   |    6996 |
| train    |             5 |               6 |              -0.0925557  |    6995 |
| train    |             5 |               7 |              -0.341025   |    6996 |
| train    |             5 |               8 |               0.0539106  |    6996 |
| train    |             5 |               9 |               0.271059   |    6996 |

## Empirical Execution Model

The execution upgrade replaces fixed 0.25/0.50-spread haircuts with quantities estimated from the cleaned TAQ panel.  It is still a minute-level proxy, not a queue-level production fill model.

Symbol-level cost summary:

| symbol   |   median_spread_bps |   p90_spread_bps |   median_halfspread_bps |   median_volume |   median_trade_count |
|:---------|--------------------:|-----------------:|------------------------:|----------------:|---------------------:|
| XLK      |             1.06969 |          9.5117  |                0.534845 |        16103    |                  342 |
| NVDA     |             1.4857  |          7.67566 |                0.74285  |       289740    |                 3457 |
| CSCO     |             2.31642 |          6.74876 |                1.15821  |        22915.8  |                  301 |
| AAPL     |             2.54677 |         21.819   |                1.27338  |        62436.5  |                 1194 |
| PLTR     |             4.27282 |         21.9548  |                2.13641  |        93897.6  |                 1245 |
| INTC     |             4.31499 |          8.9823  |                2.1575   |       142208    |                  683 |
| MSFT     |             5.86216 |         34.4858  |                2.93108  |        31149    |                  992 |
| AMD      |             6.83177 |         33.1557  |                3.41588  |        69868    |                  931 |
| APH      |             8.2512  |         36.1404  |                4.1256   |        10533    |                  192 |
| MU       |             8.96386 |         32.8736  |                4.48193  |        39431    |                  636 |
| ORCL     |             9.39249 |         35.4702  |                4.69625  |        29401    |                  607 |
| LRCX     |             9.44617 |         37.5     |                4.72308  |        13180.4  |                  272 |
| QCOM     |            10.1143  |         32.2141  |                5.05715  |        10909    |                  262 |
| AVGO     |            10.1609  |         38.7141  |                5.08043  |        30074.3  |                  740 |
| IBM      |            11.1128  |         35.2376  |                5.5564   |         5576    |                  190 |
| ANET     |            14.7529  |         47.2968  |                7.37644  |        11351    |                  220 |
| TXN      |            15.0657  |         41.2677  |                7.53283  |         7682.24 |                  187 |
| AMAT     |            18.5646  |         50.1423  |                9.28229  |         8285.27 |                  209 |
| ADI      |            23.0443  |         52.5025  |               11.5222   |         3930    |                  121 |
| SNDK     |            34.2066  |         76.2458  |               17.1033   |        11535    |                  206 |

Latency taker-cost summary:

| symbol   |   latency_min |   buy_taker_cost_bps_median |   sell_taker_cost_bps_median |   roundtrip_two_leg_cost_bps_median |
|:---------|--------------:|----------------------------:|-----------------------------:|------------------------------------:|
| AAPL     |             0 |                     1.27338 |                      1.27338 |                             2.54677 |
| AAPL     |             1 |                     2.18938 |                      2.22825 |                             2.54673 |
| AAPL     |             2 |                     2.39331 |                      2.42743 |                             2.54576 |
| AAPL     |             5 |                     2.71549 |                      2.73095 |                             2.54582 |
| ADI      |             0 |                    11.5222  |                     11.5222  |                            23.0443  |
| ADI      |             1 |                    11.3185  |                     11.2899  |                            23.0419  |
| ADI      |             2 |                    11.4196  |                     11.3927  |                            23.0408  |
| ADI      |             5 |                    11.6484  |                     11.3242  |                            23.0445  |
| AMAT     |             0 |                     9.28229 |                      9.28229 |                            18.5646  |
| AMAT     |             1 |                     9.33763 |                      9.17431 |                            18.5646  |
| AMAT     |             2 |                     9.5643  |                      9.21251 |                            18.5634  |
| AMAT     |             5 |                    10.0587  |                      9.23201 |                            18.5659  |
| AMD      |             0 |                     3.41588 |                      3.41588 |                             6.83177 |
| AMD      |             1 |                     4.50944 |                      4.40233 |                             6.8306  |
| AMD      |             2 |                     4.78036 |                      4.56396 |                             6.82912 |
| AMD      |             5 |                     5.22967 |                      4.81982 |                             6.83145 |
| ANET     |             0 |                     7.37644 |                      7.37644 |                            14.7529  |
| ANET     |             1 |                     7.70469 |                      7.60597 |                            14.7529  |
| ANET     |             2 |                     8.08656 |                      7.78684 |                            14.7521  |
| ANET     |             5 |                     8.64238 |                      7.89788 |                            14.7517  |

Passive touch-fill / markout proxy:

| symbol   | time_bucket   | spread_bucket   | imb_bucket   |   buy_bid_fill_prob |   sell_ask_fill_prob |   buy_passive_markout_cost_bps_median_if_filled |   sell_passive_markout_cost_bps_median_if_filled |
|:---------|:--------------|:----------------|:-------------|--------------------:|---------------------:|------------------------------------------------:|-------------------------------------------------:|
| AAPL     | open30        | s_q1            | ask_heavy    |            0.736111 |             0.75     |                                        1.97051  |                                          8.92767 |
| AAPL     | open30        | s_q1            | balanced     |            0.739884 |             0.768786 |                                       -1.2364   |                                         12.1177  |
| AAPL     | open30        | s_q1            | bid_heavy    |            0.75     |             0.684783 |                                       -0.18422  |                                         14.7345  |
| AAPL     | open30        | s_q2            | ask_heavy    |            0.70339  |             0.759887 |                                        5.42983  |                                         11.4327  |
| AAPL     | open30        | s_q2            | balanced     |            0.715969 |             0.71466  |                                        5.14993  |                                         10.6813  |
| AAPL     | open30        | s_q2            | bid_heavy    |            0.70405  |             0.766355 |                                        0.567335 |                                          5.65305 |
| AAPL     | open30        | s_q3            | ask_heavy    |            0.678571 |             0.67381  |                                        9.06959  |                                          7.88993 |
| AAPL     | open30        | s_q3            | balanced     |            0.689818 |             0.704815 |                                        5.8915   |                                          8.17168 |
| AAPL     | open30        | s_q3            | bid_heavy    |            0.66     |             0.702    |                                        5.91695  |                                         13.0439  |
| AAPL     | open30        | s_q4            | ask_heavy    |            0.559735 |             0.466814 |                                        6.8711   |                                          6.12916 |
| AAPL     | open30        | s_q4            | balanced     |            0.473931 |             0.49795  |                                        5.20459  |                                          7.46832 |
| AAPL     | open30        | s_q4            | bid_heavy    |            0.440605 |             0.574514 |                                        9.3721   |                                          4.6395  |
| AAPL     | mid_morning   | s_q1            | ask_heavy    |            0.725153 |             0.739877 |                                        4.52177  |                                          1.60979 |
| AAPL     | mid_morning   | s_q1            | balanced     |            0.753697 |             0.722981 |                                        3.91734  |                                          2.94621 |
| AAPL     | mid_morning   | s_q1            | bid_heavy    |            0.718681 |             0.723077 |                                        3.39549  |                                          3.11975 |
| AAPL     | mid_morning   | s_q2            | ask_heavy    |            0.707562 |             0.73071  |                                        4.5904   |                                          2.7441  |
| AAPL     | mid_morning   | s_q2            | balanced     |            0.708169 |             0.736495 |                                        3.72842  |                                          3.56103 |
| AAPL     | mid_morning   | s_q2            | bid_heavy    |            0.683453 |             0.738129 |                                        3.74642  |                                          3.8501  |
| AAPL     | mid_morning   | s_q3            | ask_heavy    |            0.665971 |             0.647182 |                                        4.64159  |                                          4.26287 |
| AAPL     | mid_morning   | s_q3            | balanced     |            0.638815 |             0.664709 |                                        4.24023  |                                          2.78182 |

## Execution-Optimized Pair Backtest

The maker/taker execution backtest is intentionally treated as a candidate screen.  It uses observed bid/ask fills and last-trade crossing proxies.  Positive validation results are not considered tradable unless the out-of-sample audit survives.

| stock   | spread_type      | policy   |   val_trades |   val_net_bps |   test_trades |   test_net_bps | decision             | oos_decision           | final_policy   |
|:--------|:-----------------|:---------|-------------:|--------------:|--------------:|---------------:|:---------------------|:-----------------------|:---------------|
| INTC    | direct_log_price | taker    |           19 |       2883.13 |            27 |       -3253.43 | validation_candidate | reject_after_oos_audit | no_trade       |

## Loss Streamline Decision

| research_path                       | decision                    | reason                                                                                                                                             |   train_or_validation_net_bps |   test_net_bps |   raw_test_net_bps_before_gate |
|:------------------------------------|:----------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------:|---------------:|-------------------------------:|
| market_neutral_pair_or_basket       | no_trade                    | validation-selected active pair/basket rules fail no-trade gate or lose after costs                                                                |                      nan      |          0     |                     -51353.3   |
| robust_alpha_suite_selected         | no_trade                    | selected robust-alpha rule loses OOS or does not beat no-trade                                                                                     |                      335.688  |       -202.214 |                       -202.214 |
| fixed_bps_xlk_only_timing_candidate | legacy_candidate_shape_only | legacy profit-search output is Jan-Feb positive, but it predates expanded top-20 controls and is not final evidence                                |                      456.479  |        613.353 |                        613.353 |
| expanded_fixed_bps_xlk_only_timing  | no_trade                    | train_or_validation_net<=0;test_net<=0;2x_cost_test<=0;latency1_test<=0;does_not_beat_directional_control;sign_flip_not_worse;circular_pvalue>0.10 |                    -2572.04   |       -977.239 |                       -977.239 |
| timing_robustness_current_selection | no_trade                    | No XLK-only timing rule passed train/validation filters.                                                                                           |                        0      |          0     |                          0     |
| named_timing_candidate_micro075_e60 | no_trade                    | named candidate audited on current top-5 basket with metadata test                                                                                 |                    -2695.47   |       -894.791 |                       -894.791 |
| regime_gated_timing_repair          | no_trade                    | Selected on train/validation only; test is holdout audit. Script label: diagnostic_only.                                                           |                       79.6331 |       -131.358 |                       -131.358 |
| regime_classifier_timing            | no_trade                    | selected on metadata validation only; test is holdout. Script label: diagnostic_only.                                                              |                      104.318  |       -271.672 |                       -271.672 |

## Fixed-BPS Timing Controls on Expanded Data

This section regenerates the old fixed-bps sparse timing candidate shape on the expanded top-20 panel.  The old `profit_search_*` tables are legacy candidate screens; this is the current-data control result.

| decision   | reason                                                                                                                                             | basket_symbols         |   train_net_bps |   validation_net_bps |   test_net_bps |   test_2x_cost_net_bps |   test_latency1_net_bps |   circular_pvalue |
|:-----------|:---------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------|----------------:|---------------------:|---------------:|-----------------------:|------------------------:|------------------:|
| no_trade   | train_or_validation_net<=0;test_net<=0;2x_cost_test<=0;latency1_test<=0;does_not_beat_directional_control;sign_flip_not_worse;circular_pvalue>0.10 | NVDA AAPL MSFT AVGO MU |        -2572.04 |             -45.1272 |       -977.239 |               -1211.91 |                -1034.28 |              0.66 |

Controls:

| control                     |   train_net_bps |   validation_net_bps |   test_net_bps |   test_trades |
|:----------------------------|----------------:|---------------------:|---------------:|--------------:|
| selected                    |       -2572.04  |             -45.1272 |       -977.239 |            83 |
| sign_flip                   |        -647.428 |            -238.614  |        507.89  |            83 |
| active_always_long          |       -1318.51  |            -344.133  |        807.851 |            83 |
| active_always_short         |       -1900.96  |              60.3926 |      -1277.2   |            83 |
| circular_shift_mean         |         nan     |             nan      |       -541.324 |           nan |
| circular_shift_p95          |         nan     |             nan      |        668.007 |           nan |
| selected_vs_circular_pvalue |         nan     |             nan      |          0.66  |           nan |

Monthly PnL:

| month   |   gross_bps |   cost_bps |     net_bps |   trades |
|:--------|------------:|-----------:|------------:|---------:|
| 2025-05 |   -392.696  |    171.524 |  -564.22    |       36 |
| 2025-06 |     10.9421 |    168.37  |  -157.428   |       40 |
| 2025-07 |    144.518  |    197.439 |   -52.9208  |       44 |
| 2025-08 |     65.7687 |    134.564 |   -68.7952  |       42 |
| 2025-09 |    156.226  |    154.457 |     1.76855 |       42 |
| 2025-10 |    374.169  |    236.28  |   137.889   |       48 |
| 2025-11 |   -172.799  |    241.575 |  -414.373   |       46 |
| 2025-12 |   -916.798  |    169.95  | -1086.75    |       46 |
| 2026-01 |   -231.636  |    135.574 |  -367.21    |       44 |
| 2026-02 |     96.7432 |    141.87  |   -45.1272  |       40 |

## Lecture-Driven Microstructure Refinement

The Baruch notes suggest a useful next layer: do not add a fancier spread model, but condition trading on order-flow, spread, volatility, and impact states.  I implemented a small ridge timing screen using basket premium, quote imbalance, Lee-Ready style signed flow, realized volatility, and a Kyle-style liquidity proxy.  It is trained on the train split only and threshold-selected on validation.

Horizon sweep:

|   horizon_min | decision   | reason                                              |   threshold_pred_bps |   train_net_bps |   validation_net_bps |   test_net_bps |   test_trades |
|--------------:|:-----------|:----------------------------------------------------|---------------------:|----------------:|---------------------:|---------------:|--------------:|
|             5 | no_trade   | no validation-positive threshold with enough trades |                    8 |          0      |               0      |       0        |             0 |
|            15 | no_trade   | no validation-positive threshold with enough trades |                   12 |          0      |             -44.368  |       0        |             0 |
|            30 | no_trade   | no validation-positive threshold with enough trades |                   12 |        -39.9371 |             -40.8502 |       0.389492 |            14 |
|            60 | no_trade   | no validation-positive threshold with enough trades |                   12 |        -14.9009 |            -213.331  |     -47.3      |            40 |

Controls for the last run:

| control             |   train_net_bps |   validation_net_bps |   test_net_bps |   test_trades |
|:--------------------|----------------:|---------------------:|---------------:|--------------:|
| selected            |        -346.383 |              9.18517 |     -133.287   |            26 |
| sign_flip           |        -288.904 |            -44.9229  |       -7.72086 |            26 |
| active_always_long  |        -447.961 |             22.7447  |      -20.6175  |            26 |
| active_always_short |        -187.327 |            -58.4825  |     -120.391   |            26 |

Largest ridge coefficients:

| feature           |       coef |
|:------------------|-----------:|
| premium_micro_bps |  2.98058   |
| premium_mid_bps   | -2.78508   |
| xlk_micro_gap_bps |  1.14864   |
| xlk_spread_bps    |  0.248486  |
| signed_flow_5     | -0.224414  |
| kyle_lambda_proxy |  0.217047  |
| realized_vol_bps  |  0.212252  |
| basket_imbalance  |  0.16744   |
| xlk_ret_lag5_bps  |  0.165715  |
| xlk_ret_lag1_bps  |  0.113172  |
| imbalance_diff    | -0.0790024 |
| roll_premium_bps  |  0.0783528 |

## Current Timing Robustness Re-Audit

The previously highlighted `micro_shrink_0.75_cw10d_e60_x0_mh240` result came from an older sparse basket convention.  The script now regenerates timing robustness on the current final-data clean top-5 holdings basket and evaluates the metadata test holdout.

Current train/validation-selected decision:

| decision   | reason                                                   |   train_net_bps |   validation_net_bps |   test_net_bps |
|:-----------|:---------------------------------------------------------|----------------:|---------------------:|---------------:|
| no_trade   | No XLK-only timing rule passed train/validation filters. |               0 |                    0 |              0 |

Named candidate audit:

| strategy                             | basket_symbols         |   train_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   train_trades |   test_trades |
|:-------------------------------------|:-----------------------|----------------:|--------------:|--------------:|---------------:|---------------:|--------------:|
| micro_shrink_0.75_cw10d_e60_x0_mh240 | NVDA AAPL MSFT AVGO MU |        -2695.47 |      -32.4451 |      -862.346 |       -894.791 |            642 |           151 |

Named candidate execution audit:

| execution_model   |   latency_min |   train_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   test_trades |
|:------------------|--------------:|----------------:|--------------:|--------------:|---------------:|--------------:|
| halfspread        |             0 |        -2695.47 |      -32.4451 |      -862.346 |       -894.791 |           151 |
| exact_bidask      |             0 |        -2695.46 |      -32.4045 |      -862.355 |       -894.759 |           151 |
| exact_bidask      |             1 |        -3283.71 |     -176.543  |      -913.675 |      -1090.22  |           152 |
| exact_bidask      |             2 |        -3422.98 |       88.6059 |      -841.822 |       -753.217 |           152 |
| exact_bidask      |             5 |        -2822.45 |      -20.3491 |      -866.279 |       -886.628 |           152 |

## Regime Shift Diagnostics

The regime-shift check asks whether poor timing performance comes from a broken XLK/basket linkage, wider execution costs, or a directional signal failure.  The expanded-sample evidence points mainly to signal-direction instability: XLK/basket correlation and beta do not collapse, but April is a strong XLK rally in which the positive premium stays persistent and the contrarian rule remains short XLK for too long.

Train/validation/test regime summary:

| metric                     |     train_avg |   validation_avg |    test_avg |   test_minus_train |
|:---------------------------|--------------:|-----------------:|------------:|-------------------:|
| xlk_basket_corr_1m         |   0.612807    |      0.708435    |   0.634166  |          0.021359  |
| xlk_on_basket_beta_1m      |   0.530802    |      0.711376    |   0.616637  |          0.085835  |
| residual_vol_bps_1m        |   4.21603     |      5.56141     |   5.12345   |          0.907418  |
| median_xlk_spread_bps      |   1.135       |      0.724244    |   1.02276   |         -0.112234  |
| signal_std_bps             | 351.906       |    135.297       | 150.386     |       -201.519     |
| alpha_ic_5m                |   0.000669893 |      0.0086332   |   0.0286324 |          0.0279625 |
| contrarian_decile_edge_5m  |   0.332085    |     -1.95747     |   2.3787    |          2.04662   |
| alpha_ic_15m               |  -0.0051507   |      0.000707948 |   0.0413642 |          0.0465149 |
| contrarian_decile_edge_15m |   0.199329    |     -6.89037     |   5.88396   |          5.68464   |
| alpha_ic_30m               |  -0.00701484  |     -0.0060882   |   0.053977  |          0.0609918 |
| contrarian_decile_edge_30m |   0.241743    |    -12.3078      |  10.2419    |         10.0001    |
| alpha_ic_60m               |  -0.00796296  |      0.00353157  |   0.0789449 |          0.0869079 |
| contrarian_decile_edge_60m |   0.305847    |    -16.9471      |  21.9551    |         21.6492    |

Monthly market state:

| month   |   xlk_return_bps |   basket_return_bps |   xlk_basket_corr_1m |   xlk_on_basket_beta_1m |   residual_vol_bps_1m |   median_xlk_spread_bps |   signal_std_bps |   abs_signal_gt_60_frac |
|:--------|-----------------:|--------------------:|---------------------:|------------------------:|----------------------:|------------------------:|-----------------:|------------------------:|
| 2025-05 |         381.592  |             495.993 |             0.675339 |                0.607413 |               4.44391 |                2.14615  |         180.083  |                0.730157 |
| 2025-06 |         368.558  |             481.647 |             0.442592 |                0.402667 |               4.86499 |                1.68318  |          91.9016 |                0.842978 |
| 2025-07 |         -64.6494 |            -277.347 |             0.559192 |                0.464762 |               3.49944 |                0.796147 |          51.1817 |                0.859801 |
| 2025-08 |         -24.4091 |             232.71  |             0.637035 |                0.532958 |               3.84886 |                0.764351 |          95.0331 |                0.578146 |
| 2025-09 |         322.199  |             376.881 |             0.588552 |                0.462169 |               3.52602 |                0.733299 |         168.296  |                0.776918 |
| 2025-10 |        -317.989  |            -445.089 |             0.640557 |                0.565861 |               4.27377 |                0.996264 |         108.79   |                0.903958 |
| 2025-11 |        -248.124  |            -246.401 |             0.776102 |                0.726364 |               4.87309 |                1.02988  |         210.489  |                0.658556 |
| 2025-12 |        -133.084  |            -179.869 |             0.594055 |                0.498026 |               4.20812 |                1.37146  |        2167.73   |                0.918706 |
| 2026-01 |        -295.7    |            -244.169 |             0.601841 |                0.516993 |               4.40605 |                0.694227 |          93.6499 |                0.628137 |
| 2026-02 |        -309.429  |            -409.318 |             0.708435 |                0.711376 |               5.56141 |                0.724244 |         135.297  |                0.775649 |

Named timing candidate monthly PnL anatomy:

| month   |   gross_bps |   cost_bps |    net_bps |   trades |   long_gross_bps |   short_gross_bps |   long_minutes |   short_minutes |
|:--------|------------:|-----------:|-----------:|---------:|-----------------:|------------------:|---------------:|----------------:|
| 2025-05 |   -454.105  |    215.033 |  -669.138  |       66 |         126.306  |         -580.411  |           3094 |            3408 |
| 2025-06 |     26.4973 |    237.257 |  -210.76   |       76 |         153.875  |         -127.378  |            384 |            6935 |
| 2025-07 |     37.4573 |    246.499 |  -209.041  |       82 |           0      |           37.4573 |              0 |            7741 |
| 2025-08 |    100.105  |    168.664 |   -68.5588 |       60 |          46.3834 |           53.7217 |           3386 |            2428 |
| 2025-09 |    195.417  |    161.283 |    34.1338 |       68 |         281.73   |          -86.3125 |           1922 |            4603 |
| 2025-10 |    456.819  |    273.974 |   182.845  |       86 |          61.6905 |          395.129  |            317 |            7978 |
| 2025-11 |     12.4635 |    353.523 |  -341.059  |       62 |         -90.1337 |          102.597  |           3062 |            2772 |
| 2025-12 |   -961.783  |    285.366 | -1247.15   |       84 |        -567.937  |         -393.845  |           4643 |            3426 |
| 2026-01 |    -22.7232 |    144.013 |  -166.736  |       58 |        -171.264  |          148.54   |            627 |            4973 |
| 2026-02 |    167.889  |    143.347 |    24.5423 |       70 |         -29.7541 |          197.643  |           3852 |            2861 |

## Regime-Gate Repair Experiments

The April diagnosis suggests a specific repair: prevent the contrarian rule from shorting XLK when the premium is persistent and/or both XLK and the sparse basket are trending upward.  The gate experiment keeps the target signal fixed and only changes the trade/no-trade overlay.  Gate selection uses metadata train/validation only; the metadata test window remains holdout.

Selection:

| decision        | selected_strategy                              | gate_mode   | state_kind          |   lookback_min |   trend_threshold_bps |   train_net_bps |   validation_net_bps |   test_net_bps |   test_2x_cost_net_bps |
|:----------------|:-----------------------------------------------|:------------|:--------------------|---------------:|----------------------:|----------------:|---------------------:|---------------:|-----------------------:|
| diagnostic_only | two_sided_premium_persistence_lb780_thr75_flat | two_sided   | premium_persistence |            780 |                    75 |         79.6331 |              280.215 |       -131.358 |               -210.735 |

Monthly side anatomy:

| strategy              | month   |   gross_bps |   cost_bps |    net_bps |   long_gross_bps |   short_gross_bps |   long_minutes |   short_minutes |
|:----------------------|:--------|------------:|-----------:|-----------:|-----------------:|------------------:|---------------:|----------------:|
| baseline_no_gate      | 2025-05 |   -454.105  |  215.033   |  -669.138  |         126.306  |         -580.411  |           3094 |            3408 |
| baseline_no_gate      | 2025-06 |     26.4973 |  237.257   |  -210.76   |         153.875  |         -127.378  |            384 |            6935 |
| baseline_no_gate      | 2025-07 |     37.4573 |  246.499   |  -209.041  |           0      |           37.4573 |              0 |            7741 |
| baseline_no_gate      | 2025-08 |    100.105  |  168.664   |   -68.5588 |          46.3834 |           53.7217 |           3386 |            2428 |
| baseline_no_gate      | 2025-09 |    195.417  |  161.283   |    34.1338 |         281.73   |          -86.3125 |           1922 |            4603 |
| baseline_no_gate      | 2025-10 |    456.819  |  273.974   |   182.845  |          61.6905 |          395.129  |            317 |            7978 |
| baseline_no_gate      | 2025-11 |     12.4635 |  353.523   |  -341.059  |         -90.1337 |          102.597  |           3062 |            2772 |
| baseline_no_gate      | 2025-12 |   -961.783  |  285.366   | -1247.15   |        -567.937  |         -393.845  |           4643 |            3426 |
| baseline_no_gate      | 2026-01 |    -22.7232 |  144.013   |  -166.736  |        -171.264  |          148.54   |            627 |            4973 |
| baseline_no_gate      | 2026-02 |    167.889  |  143.347   |    24.5423 |         -29.7541 |          197.643  |           3852 |            2861 |
| baseline_no_gate      | 2026-03 |    156.568  |  188.972   |   -32.4045 |         101.566  |           55.0019 |           4216 |            3046 |
| baseline_no_gate      | 2026-04 |   -724.159  |  138.195   |  -862.355  |         126.882  |         -851.041  |           1010 |            6420 |
| long_only_diagnostic  | 2025-05 |    126.306  |   83.4641  |    42.8417 |         126.306  |            0      |           3094 |               0 |
| long_only_diagnostic  | 2025-06 |    153.875  |   16.5832  |   137.292  |         153.875  |            0      |            384 |               0 |
| long_only_diagnostic  | 2025-07 |      0      |    0       |     0      |           0      |            0      |              0 |               0 |
| long_only_diagnostic  | 2025-08 |     46.3834 |   83.2557  |   -36.8723 |          46.3834 |            0      |           3386 |               0 |
| long_only_diagnostic  | 2025-09 |    281.73   |   56.0938  |   225.636  |         281.73   |            0      |           1922 |               0 |
| long_only_diagnostic  | 2025-10 |     61.6905 |    2.46582 |    59.2246 |          61.6905 |            0      |            317 |               0 |
| long_only_diagnostic  | 2025-11 |    -90.1337 |  199.036   |  -289.169  |         -90.1337 |            0      |           3062 |               0 |
| long_only_diagnostic  | 2025-12 |   -567.937  |  170.015   |  -737.952  |        -567.937  |            0      |           4643 |               0 |
| long_only_diagnostic  | 2026-01 |   -171.264  |   30.3749  |  -201.638  |        -171.264  |            0      |            627 |               0 |
| long_only_diagnostic  | 2026-02 |    -29.7541 |  106.543   |  -136.297  |         -29.7541 |            0      |           3852 |               0 |
| long_only_diagnostic  | 2026-03 |    101.566  |  141.998   |   -40.4315 |         101.566  |            0      |           4216 |               0 |
| long_only_diagnostic  | 2026-04 |    126.882  |   24.2637  |   102.618  |         126.882  |            0      |           1010 |               0 |
| short_only_diagnostic | 2025-05 |   -580.411  |  131.569   |  -711.98   |           0      |         -580.411  |              0 |            3408 |
| short_only_diagnostic | 2025-06 |   -127.378  |  220.674   |  -348.052  |           0      |         -127.378  |              0 |            6935 |
| short_only_diagnostic | 2025-07 |     37.4573 |  246.499   |  -209.041  |           0      |           37.4573 |              0 |            7741 |
| short_only_diagnostic | 2025-08 |     53.7217 |   85.4082  |   -31.6865 |           0      |           53.7217 |              0 |            2428 |
| short_only_diagnostic | 2025-09 |    -86.3125 |  105.19    |  -191.502  |           0      |          -86.3125 |              0 |            4603 |
| short_only_diagnostic | 2025-10 |    395.129  |  271.508   |   123.621  |           0      |          395.129  |              0 |            7978 |

## Regime Classifier

The classifier version replaces fixed gates with a three-state supervised model: mean-reversion, trend-continuation, or no-trade.  The metadata train split fits the classifier, validation selects model/confidence settings, and test is the holdout.  Selection also requires the classifier to beat active always-long/always-short controls on validation, preventing a disguised directional rule from passing as regime intelligence.

Selection:

| decision        | selected_strategy                  | train_scheme   | model_name   |   horizon_min |   label_edge_bps |   confidence |   validation_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   test_2x_cost_net_bps |   latency1_test_net_bps |
|:----------------|:-----------------------------------|:---------------|:-------------|--------------:|-----------------:|-------------:|---------------------:|--------------:|--------------:|---------------:|-----------------------:|------------------------:|
| diagnostic_only | train_all_rf_depth4_h60_edge5_p0.4 | train_all      | rf_depth4    |            60 |                5 |          0.4 |              104.318 |      -18.5335 |      -253.139 |       -271.672 |               -931.308 |                -162.026 |

Controls:

| control                        |   validation_net_bps |   test_net_bps |   test_trades |
|:-------------------------------|---------------------:|---------------:|--------------:|
| selected_classifier            |             104.318  |       -271.672 |           480 |
| sign_flip                      |            -375.314  |      -1047.55  |           480 |
| classifier_active_always_long  |             -39.6307 |       -574.756 |           480 |
| classifier_active_always_short |            -231.365  |       -744.464 |           480 |

Monthly anatomy:

| strategy                           | month   |   gross_bps |   cost_bps |   net_bps |   long_gross_bps |   short_gross_bps |   long_minutes |   short_minutes |
|:-----------------------------------|:--------|------------:|-----------:|----------:|-----------------:|------------------:|---------------:|----------------:|
| train_all_rf_depth4_h60_edge5_p0.4 | 2025-05 |     587.97  |   228.022  | 359.948   |          300.474 |          287.497  |           1189 |             713 |
| train_all_rf_depth4_h60_edge5_p0.4 | 2025-06 |     346.885 |   340.881  |   6.00483 |          117.123 |          229.763  |            388 |            1650 |
| train_all_rf_depth4_h60_edge5_p0.4 | 2025-07 |     302.795 |   260.564  |  42.2311  |          164.616 |          138.179  |           1119 |             429 |
| train_all_rf_depth4_h60_edge5_p0.4 | 2025-08 |     218.871 |    84.6969 | 134.174   |          128.496 |           90.3745 |            264 |             926 |
| train_all_rf_depth4_h60_edge5_p0.4 | 2025-09 |     379.508 |   234.308  | 145.2     |          308.914 |           70.5939 |           1491 |             262 |
| train_all_rf_depth4_h60_edge5_p0.4 | 2025-10 |     643.449 |   567.226  |  76.2223  |          329.379 |          314.07   |           2519 |            1398 |
| train_all_rf_depth4_h60_edge5_p0.4 | 2025-11 |     938.676 |   336.814  | 601.862   |          342.251 |          596.425  |            856 |             939 |
| train_all_rf_depth4_h60_edge5_p0.4 | 2025-12 |     576.309 |   368.5    | 207.809   |          543.348 |           32.961  |           2121 |            1535 |
| train_all_rf_depth4_h60_edge5_p0.4 | 2026-01 |     301.008 |   245.407  |  55.6006  |          141.95  |          159.057  |            682 |             883 |
| train_all_rf_depth4_h60_edge5_p0.4 | 2026-02 |     239.802 |   135.484  | 104.318   |          167.824 |           71.9777 |            278 |             842 |

## Sparse Market-Neutral Basket

| subset                  |   k | betas                                                      |   train_adf_p |   train_half_life_minutes |   train_avg_oneway_cost_bps |    score |
|:------------------------|----:|:-----------------------------------------------------------|--------------:|--------------------------:|----------------------------:|---------:|
| NVDA AVGO AMD ORCL      |   4 | NVDA:0.2351 AVGO:0.0723 AMD:0.0766 ORCL:0.0626             |     0.0879696 |                   1251.24 |                     3.82809 | 0.790154 |
| NVDA MSFT AVGO AMD ORCL |   5 | NVDA:0.2301 MSFT:0.0563 AVGO:0.0702 AMD:0.0746 ORCL:0.0604 |     0.107313  |                   1285.82 |                     4.1364  | 0.832952 |
| NVDA AVGO AMD PLTR ORCL |   5 | NVDA:0.2063 AVGO:0.0636 AMD:0.0672 PLTR:0.0789 ORCL:0.0545 |     0.125016  |                   1341.98 |                     3.92611 | 0.874528 |
| NVDA AAPL AVGO AMD ORCL |   5 | NVDA:0.2275 AAPL:0.0781 AVGO:0.0699 AMD:0.0736 ORCL:0.0609 |     0.139244  |                   1314.24 |                     4.07428 | 0.87785  |
| AVGO AMD PLTR ORCL      |   4 | AVGO:0.0899 AMD:0.0967 PLTR:0.1079 ORCL:0.0697             |     0.154328  |                   1583.36 |                     4.14411 | 1.02889  |
| NVDA AMD ORCL           |   3 | NVDA:0.2561 AMD:0.0833 ORCL:0.0686                         |     0.143237  |                   1725.73 |                     3.35679 | 1.07324  |
| NVDA AVGO PLTR ORCL     |   4 | NVDA:0.2312 AVGO:0.0707 PLTR:0.0869 ORCL:0.0594            |     0.225366  |                   1594.5  |                     3.67334 | 1.09608  |
| AAPL AVGO AMD PLTR ORCL |   5 | AAPL:0.0853 AVGO:0.0866 AMD:0.0928 PLTR:0.1037 ORCL:0.0677 |     0.232836  |                   1656.88 |                     4.40154 | 1.14931  |
| NVDA MSFT AMD ORCL      |   4 | NVDA:0.2502 MSFT:0.0599 AMD:0.0810 ORCL:0.0661             |     0.170136  |                   1820.59 |                     3.69993 | 1.15443  |
| MSFT AVGO AMD PLTR ORCL |   5 | MSFT:0.0606 AVGO:0.0873 AMD:0.0942 PLTR:0.1047 ORCL:0.0673 |     0.237416  |                   1673.96 |                     4.46827 | 1.16376  |

| strategy             | sample   |   trades |   gross_bps |   cost_bps |    net_bps |   max_drawdown_bps |
|:---------------------|:---------|---------:|------------:|-----------:|-----------:|-------------------:|
| sparse_e3.5_x1_plain | test     |        3 |     11.6926 |    9.43719 |    2.25537 |           -80.9062 |
| sparse_e3.5_x1_plain | train    |       36 |     76.4976 |  255.31    | -178.812   |          -288.356  |
| literature_no_trade  | test     |        0 |      0      |    0       |    0       |             0      |
| literature_no_trade  | train    |        0 |      0      |    0       |    0       |             0      |

Bid/ask boundary audit:

| sample   |   old_gross_bps |   old_cost_bps |   old_net_bps |   new_gross_bps |   new_bidask_cost_bps |   new_bidask_net_bps |   turnover |
|:---------|----------------:|---------------:|--------------:|----------------:|----------------------:|---------------------:|-----------:|
| test     |         11.6926 |        9.43719 |       2.25537 |         11.6926 |                29.014 |             -17.3215 |          3 |
| train    |         76.4976 |      255.31    |    -178.812   |         76.4976 |               669.917 |            -593.42   |         36 |

## Robust Alpha Suite

The robust alpha suite jointly tests XLK-only timing and partial/full hedge rules.  If the selected rule has `hedge_fraction = 0`, it is a timing strategy, not market-neutral arbitrage.

| decision    | selected_strategy                                                                             | reason                               |   train_net_bps |   test_net_bps |   benchmark_no_trade_train_bps |   benchmark_no_trade_test_bps | economic_label   |
|:------------|:----------------------------------------------------------------------------------------------|:-------------------------------------|----------------:|---------------:|-------------------------------:|------------------------------:|:-----------------|
| active_rule | xlk_only_timing_micro_conf_0.5_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180 | passed train-only robustness filters |         335.688 |       -202.214 |                              0 |                             0 | XLK-only timing  |

Controls:

| control                     |   train_net_bps |   test_net_bps |   test_trades |   test_avg_abs_position |
|:----------------------------|----------------:|---------------:|--------------:|------------------------:|
| selected                    |         335.688 |    -202.214    |            16 |                0.072844 |
| sign_flip                   |        -595.833 |     170.694    |            16 |                0.072844 |
| active_always_long          |         160.076 |      81.0797   |            16 |                0.072844 |
| active_always_short         |        -420.221 |    -112.6      |            16 |                0.072844 |
| circular_shift_mean         |         nan     |    -251.46     |           nan |              nan        |
| circular_shift_p95          |         nan     |    -125.148    |           nan |              nan        |
| selected_vs_circular_pvalue |         nan     |       0.336634 |           nan |              nan        |

Cost sensitivity:

|   cost_multiplier | sample   |   gross_bps |   cost_bps |   net_bps |
|------------------:|:---------|------------:|-----------:|----------:|
|               1   | train    |     465.76  |   130.073  |  335.688  |
|               1   | test     |    -186.454 |    15.76   | -202.214  |
|               1.5 | train    |     465.76  |   195.109  |  270.651  |
|               1.5 | test     |    -186.454 |    23.6401 | -210.094  |
|               2   | train    |     465.76  |   260.145  |  205.615  |
|               2   | test     |    -186.454 |    31.5201 | -217.974  |
|               3   | train    |     465.76  |   390.218  |   75.5427 |
|               3   | test     |    -186.454 |    47.2801 | -233.734  |
|               4   | train    |     465.76  |   520.29   |  -54.5299 |
|               4   | test     |    -186.454 |    63.0402 | -249.494  |

## XLK-Only Timing Extension

| period     |   gross_bps |   cost_bps |   net_bps |   trades |   avg_abs_position |   xlk_buyhold_bps |
|:-----------|------------:|-----------:|----------:|---------:|-------------------:|------------------:|
| train      |     760.402 |   1795.16  | -1034.76  |      386 |           0.752219 |          -11.6058 |
| validation |     407.969 |    202.23  |   205.739 |       46 |           0.902025 |         -309.429  |
| test       |    -550.251 |    302.178 |  -852.429 |       99 |           0.806039 |          969.964  |
| all        |     618.12  |   2299.57  | -1681.45  |      531 |           0.772773 |          648.929  |

Bid/ask boundary audit:

| sample     |   old_gross_bps |   old_cost_bps |   old_net_bps |   new_gross_bps |   new_bidask_cost_bps |   new_bidask_net_bps |   turnover |
|:-----------|----------------:|---------------:|--------------:|----------------:|----------------------:|---------------------:|-----------:|
| test       |        -550.251 |        302.178 |      -852.429 |        -550.251 |               302.087 |            -852.338  |         99 |
| train      |         760.402 |       1795.16  |     -1034.76  |         760.402 |               673.384 |              87.0174 |        386 |
| validation |         407.969 |        202.23  |       205.739 |         407.969 |               202.205 |             205.763  |         46 |

## Interpretation

The next report should avoid saying "ETF arbitrage is profitable" unless a market-neutral rule survives the new spread-construction and execution-cost checks.  The defensible framing is:

> Market-neutral XLK-vs-basket arbitrage is fragile under realistic TAQ execution assumptions.  The sparse/top-holdings basket contains fair-value information, but the final-data run does not yet prove a stable positive active strategy.  Report gross/no-cost, 0.25-spread, 0.50-spread, and last-trade proxy economics separately.

## Next Steps

1. Run the full grid overnight; the committed top-20 diagnostic grid is intentionally laptop-safe.
2. Improve passive execution with queue-depth and partial-fill modeling; the current passive mode is only a stress case.
3. Extend signal bucket tests into formal timing selection only if the decile relation is stable across train/validation/test.
4. Add portfolio-level drawdown / VaR constraints for correlated constituent losses.
5. Add a formal DSR / multiple-testing section using the trial registry as the denominator.
6. Regenerate the fixed-bps sparse5 timing candidate on the expanded top-20 sample before using it as final evidence; legacy profit-search outputs are candidate shapes only.
7. If pursuing a positive extension, move from linear microstructure timing to conditional gates: avoid high spread / high volatility states, trade only where order-flow and basket-premium signs agree, and validate on event-level fills.
8. Add a trend/regime gate before any contrarian XLK-only timing claim.  The April audit shows that persistent positive premium during an aligned XLK/basket rally can make the strategy short the ETF into a strong uptrend; this should trigger no-trade or one-sided trading restrictions.

## Reproducibility

```bash
python3 scripts/build_dataset.py --force
python3 scripts/run_newdata_pipeline.py --quick
```
