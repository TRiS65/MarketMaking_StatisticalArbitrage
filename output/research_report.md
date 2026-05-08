# XLK Microstructure Statistical Arbitrage: New-Data Progress Report

## Dataset

- Raw data: `/Users/yezi/Desktop/Statistical_Arbitrage/final_proj/data/newdata`
- Sample: `2025-11-01` to `2026-05-01`
- Universe: `XLK` + 19 constituents
- Requested-but-dropped symbols after quote/trade cleaning: `SNDK`
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
| SNDK     | SANDISK CORP                |               1.28246 |       0.0164661 | False                 |
| APH      | AMPHENOL CORP CL A          |               1.28031 |       0.0164385 | True                  |

## Data Diagnostics

| symbol   | start               | end                 |   minutes |   median_spread_bps |   avg_volume |   trade_count |
|:---------|:--------------------|:--------------------|----------:|--------------------:|-------------:|--------------:|
| AAPL     | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     42582 |             2.56631 |     82352.7  |      68484338 |
| ADI      | 2025-11-03 09:33:00 | 2026-04-30 15:59:00 |     31149 |            25.7225  |      6993.84 |       5539665 |
| AMAT     | 2025-11-03 09:31:00 | 2026-04-30 15:59:00 |     33850 |            24.0668  |     13095.5  |       9720939 |
| AMD      | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     40758 |             9.17053 |     85838    |      51260690 |
| ANET     | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     36432 |            19.4284  |     16276.7  |      10029069 |
| APH      | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     38859 |            13.9352  |     18489.2  |      10984681 |
| AVGO     | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     39660 |             8.99922 |     51537.5  |      48065160 |
| CSCO     | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     45546 |             2.55135 |     39349.6  |      21108602 |
| IBM      | 2025-11-03 09:31:00 | 2026-04-30 15:59:00 |     36215 |             9.59331 |     10579.8  |      11042119 |
| INTC     | 2025-11-03 09:31:00 | 2026-04-30 15:59:00 |     46062 |             2.85063 |    217147    |      57888289 |
| KLAC     | 2025-11-03 09:34:00 | 2026-04-30 15:59:00 |     34736 |            40.8643  |      1845.05 |       4064568 |
| LRCX     | 2025-11-03 09:31:00 | 2026-04-30 15:59:00 |     34908 |            16.0727  |     20680.7  |      13743943 |
| MSFT     | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     41853 |             5.21241 |     60859.5  |      74046055 |
| MU       | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     38585 |            12.0517  |     76920.8  |      50893368 |
| NVDA     | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     46210 |             1.57068 |    383179    |     281818587 |
| ORCL     | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     37694 |             7.29189 |     62148.4  |      40996967 |
| PLTR     | 2025-11-03 09:32:00 | 2026-04-30 15:59:00 |     43589 |             4.7727  |    107564    |      71844161 |
| QCOM     | 2025-11-03 09:31:00 | 2026-04-30 15:59:00 |     37070 |            11.409   |     20822.2  |      15491983 |
| TXN      | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     35122 |            17.491   |     13639.8  |       9173623 |
| XLK      | 2025-11-03 09:30:00 | 2026-04-30 15:59:00 |     47695 |             1.06733 |     36557.1  |      27915985 |

## Professor Feedback Checks

The new `run_professor_robustness.py` module answers the main methodology questions:

- `r_XLK,t` is explicitly one-minute log return, not price.
- Cumulative residual-return spreads are compared against direct log-price spreads and log-price regression residuals.
- Gross/no-cost P&L is separated from 0.25-spread, 0.50-spread, and clipped last-trade execution proxies.
- OU / Avellaneda-Lee style diagnostics are reported for each spread.

Best validation-selected test rows:

| pair     | stock   | spread_type               |   entry_z |   exit_z |   clipped_last_trade_proxy |   half_spread_taker_cost |   no_cost_midpoint |   quarter_spread_cost |
|:---------|:--------|:--------------------------|----------:|---------:|---------------------------:|-------------------------:|-------------------:|----------------------:|
| XLK-AAPL | AAPL    | price_regression_residual |      1    |     0.5  |                  1315.4    |               -207.309   |         5859.32    |            2826       |
| XLK-PLTR | PLTR    | price_regression_residual |      1    |     0.5  |                  1486.05   |                914.8     |         1573.04    |            1243.92    |
| XLK-ORCL | ORCL    | price_regression_residual |      1    |     0    |                  1313.93   |                238.995   |         1479.5     |             859.249   |
| XLK-AMD  | AMD     | direct_log_price          |      1.25 |     0.5  |                   493.447  |                204.427   |          491.958   |             348.192   |
| XLK-NVDA | NVDA    | direct_log_price          |      1    |     0.5  |                   323.044  |                -46.385   |          378.028   |             165.821   |
| XLK-INTC | INTC    | direct_log_price          |      2.5  |     0.5  |                   193.276  |                124.19    |          190.189   |             157.19    |
| XLK-AAPL | AAPL    | cum_residual_return       |      2    |     0    |                   145.249  |                  7.06338 |          188.046   |              97.5548  |
| XLK-AVGO | AVGO    | cum_residual_return       |      2    |     0    |                   136.907  |                -74.638   |          139.822   |              32.5919  |
| XLK-IBM  | IBM     | price_regression_residual |      1.25 |     0.5  |                   454.779  |              -1043.17    |         1088.77    |              22.8018  |
| XLK-MSFT | MSFT    | direct_log_price          |      1    |     0.5  |                   137.459  |               -165.737   |          172.7     |               3.48151 |
| XLK-PLTR | PLTR    | cum_residual_return       |      2    |     0.5  |                   -66.2818 |               -170.165   |           -9.75177 |             -89.9582  |
| XLK-ANET | ANET    | direct_log_price          |      1.25 |     0.5  |                    53.2793 |               -295.331   |           23.5716  |            -135.88    |
| XLK-QCOM | QCOM    | cum_residual_return       |      2.5  |     0    |                  -151.142  |               -219.539   |         -105.304   |            -162.421   |
| XLK-MU   | MU      | direct_log_price          |      2    |     0    |                   -89.5637 |               -253.107   |          -92.6669  |            -172.887   |
| XLK-ANET | ANET    | price_regression_residual |      1    |     0.25 |                   -42.9458 |               -315.689   |          -65.2297  |            -190.459   |

OU and stationarity diagnostics:

| pair     | spread_type               |   train_adf_p |   train_half_life_minutes |   ou_half_life_minutes |   train_spread_std_bps |
|:---------|:--------------------------|--------------:|--------------------------:|-----------------------:|-----------------------:|
| XLK-PLTR | cum_residual_return       |     0.0727941 |                   743.715 |                743.715 |                125.889 |
| XLK-ADI  | price_regression_residual |     0.183559  |                  1411.77  |               1411.77  |               1786.19  |
| XLK-AMAT | price_regression_residual |     0.280575  |                  1966.99  |               1966.99  |               2280.61  |
| XLK-KLAC | price_regression_residual |     0.295024  |                  2271.6   |               2271.6   |               2553.16  |
| XLK-ORCL | price_regression_residual |     0.299342  |                  1701.79  |               1701.79  |               2342.49  |
| XLK-QCOM | cum_residual_return       |     0.30401   |                  1107.76  |               1107.76  |                154.367 |
| XLK-LRCX | price_regression_residual |     0.337211  |                  2534.63  |               2534.63  |               2466.68  |
| XLK-INTC | price_regression_residual |     0.365442  |                  3068.26  |               3068.26  |               2952.96  |
| XLK-AMD  | cum_residual_return       |     0.388407  |                  1045.44  |               1045.44  |                141.731 |
| XLK-TXN  | price_regression_residual |     0.391854  |                  1802.21  |               1802.21  |               2077.66  |
| XLK-AAPL | price_regression_residual |     0.3945    |                  2669.06  |               2669.06  |               2983.16  |
| XLK-MU   | price_regression_residual |     0.401959  |                  2742.15  |               2742.15  |               2490.78  |
| XLK-MSFT | price_regression_residual |     0.425732  |                  1532.98  |               1532.98  |               2690.71  |
| XLK-APH  | price_regression_residual |     0.469717  |                  3924.34  |               3924.34  |               3227.03  |
| XLK-INTC | cum_residual_return       |     0.484839  |                  1744.2   |               1744.2   |                170.465 |

## Top-20 Method Diagnostics

The new top-20 method diagnostic layer absorbs the methodology addendum critically rather than copying it wholesale.  It is real-data only, has no synthetic fallback, uses lagged Kalman beta, charges passive-entry adverse selection, writes every tried rule to a trial registry, and applies a no-trade selection gate.

| method         |   selected_pairs |   gate_pass_pairs |   raw_validation_net_bps |   raw_test_net_bps |   raw_positive_test_pairs |   gate_test_net_bps |   gate_positive_test_pairs |   test_trades |
|:---------------|-----------------:|------------------:|-------------------------:|-------------------:|--------------------------:|--------------------:|---------------------------:|--------------:|
| baseline       |               19 |                 0 |               -1494.03   |         -14985.1   |                         0 |                   0 |                          0 |          2578 |
| coint_filter   |                1 |                 0 |                 211.669  |           -188.991 |                         0 |                   0 |                          0 |            94 |
| combined       |                1 |                 0 |                 -47.3034 |           -428.482 |                         0 |                   0 |                          0 |            74 |
| kalman_lagged  |               19 |                 0 |               -3911.12   |         -15984.3   |                         1 |                   0 |                          0 |          3097 |
| passive_stress |               19 |                 0 |                 190.568  |         -12166.2   |                         0 |                   0 |                          0 |          2794 |
| sscore_ou_gate |               19 |                 0 |                -417.602  |          -9747.57  |                         1 |                   0 |                          0 |          1394 |

No-trade gate examples:

| pair_or_basket   | method         |   validation_net_bps |   test_net_bps |   test_2x_cost_net_bps |   test_latency1_net_bps | gate_selected_flag   | gate_reason       |
|:-----------------|:---------------|---------------------:|---------------:|-----------------------:|------------------------:|:---------------------|:------------------|
| XLK-AAPL         | baseline       |             105.403  |       -383.41  |               -707.839 |                -336.901 | False                | 2x_cost_net<0     |
| XLK-AAPL         | kalman_lagged  |             -17.6244 |       -219.106 |               -545.841 |                -168.892 | False                | validation_net<=0 |
| XLK-AAPL         | passive_stress |              27.3768 |       -134.35  |               -252.814 |                -225.334 | False                | 2x_cost_net<0     |
| XLK-AAPL         | sscore_ou_gate |              13.2468 |       -272.16  |               -349.561 |                -257.436 | False                | cost_share>=0.75  |
| XLK-ADI          | baseline       |            -207.517  |       -700.336 |              -1132.04  |                -719.518 | False                | validation_net<=0 |
| XLK-ADI          | kalman_lagged  |            -367.706  |      -1318.1   |              -2131.54  |               -1483.56  | False                | validation_net<=0 |
| XLK-ADI          | passive_stress |            -100.894  |       -622.953 |               -880.086 |                -746.962 | False                | validation_net<=0 |
| XLK-ADI          | sscore_ou_gate |             -15.8548 |       -454.272 |               -673.804 |                -457.058 | False                | validation_net<=0 |
| XLK-AMAT         | baseline       |            -126.116  |      -2745.56  |              -3938.8   |               -3039.6   | False                | validation_net<=0 |
| XLK-AMAT         | kalman_lagged  |             -97.532  |      -2438.48  |              -3614.42  |               -2683.7   | False                | validation_net<=0 |
| XLK-AMAT         | passive_stress |             154.552  |      -2122.05  |              -2712.06  |               -2751.63  | False                | 2x_cost_net<0     |
| XLK-AMAT         | sscore_ou_gate |             -95.766  |       -524.69  |              -1018.16  |                -595.809 | False                | validation_net<=0 |
| XLK-AMD          | baseline       |              18.2845 |       -715.543 |              -1409.96  |                -708.834 | False                | cost_share>=0.75  |
| XLK-AMD          | kalman_lagged  |             118.643  |       -381.47  |               -814.053 |                -384.993 | False                | 2x_cost_net<0     |
| XLK-AMD          | passive_stress |             157.773  |       -457.97  |               -788.469 |                -858.389 | False                | 2x_cost_net<0     |

Exit-reason audit:

| method   | sample     | exit_reason   |   trades |   gross_bps |   cost_bps |   net_bps |
|:---------|:-----------|:--------------|---------:|------------:|-----------:|----------:|
| baseline | train      | eod           |       44 |     60.4524 |   181.074  | -120.622  |
| baseline | train      | max_hold      |       99 |    -60.6224 |   283.244  | -343.866  |
| baseline | train      | reversion     |       49 |    397.297  |   260.131  |  137.167  |
| baseline | train      | stop_loss     |       79 |   -186.499  |   277.851  | -464.35   |
| baseline | validation | eod           |       10 |     22.8702 |    67.0539 |  -44.1837 |
| baseline | validation | max_hold      |       28 |     15.7636 |    55.798  |  -40.0344 |
| baseline | validation | reversion     |       12 |    164.494  |    43.7627 |  120.731  |
| baseline | test       | eod           |       28 |    -29.5534 |   114.659  | -144.212  |
| baseline | test       | max_hold      |       74 |    -33.0371 |   161.383  | -194.42   |
| baseline | test       | reversion     |       42 |    461.501  |   215.217  |  246.284  |
| baseline | test       | stop_loss     |       36 |   -129.222  |   107.962  | -237.184  |
| baseline | train      | eod           |       44 |     60.4524 |   181.074  | -120.622  |
| baseline | train      | max_hold      |      102 |    -71.2094 |   296.558  | -367.768  |
| baseline | train      | reversion     |       49 |    397.297  |   260.131  |  137.167  |
| baseline | validation | eod           |       10 |     22.8702 |    67.0539 |  -44.1837 |

XLK-only signal bucket test:

| sample   |   horizon_min |   signal_decile |   mean_future_return_bps |   count |
|:---------|--------------:|----------------:|-------------------------:|--------:|
| train    |             1 |               0 |               0.0322569  |    2243 |
| train    |             1 |               1 |               0.120788   |    2242 |
| train    |             1 |               2 |              -0.185557   |    2242 |
| train    |             1 |               3 |              -0.157853   |    2242 |
| train    |             1 |               4 |              -0.00427357 |    2243 |
| train    |             1 |               5 |              -0.105299   |    2242 |
| train    |             1 |               6 |              -0.0206658  |    2242 |
| train    |             1 |               7 |              -0.150865   |    2242 |
| train    |             1 |               8 |               0.0109971  |    2242 |
| train    |             1 |               9 |               0.0977812  |    2243 |
| train    |             5 |               0 |               0.39215    |    2243 |
| train    |             5 |               1 |              -0.214831   |    2242 |
| train    |             5 |               2 |              -0.462747   |    2242 |
| train    |             5 |               3 |              -0.492115   |    2242 |
| train    |             5 |               4 |              -0.465029   |    2243 |
| train    |             5 |               5 |              -0.656002   |    2242 |
| train    |             5 |               6 |              -0.271281   |    2242 |
| train    |             5 |               7 |              -0.27493    |    2242 |
| train    |             5 |               8 |              -0.0365918  |    2242 |
| train    |             5 |               9 |               0.711996   |    2243 |

## Empirical Execution Model

The execution upgrade replaces fixed 0.25/0.50-spread haircuts with quantities estimated from the cleaned TAQ panel.  It is still a minute-level proxy, not a queue-level production fill model.

Symbol-level cost summary:

| symbol   |   median_spread_bps |   p90_spread_bps |   median_halfspread_bps |   median_volume |   median_trade_count |
|:---------|--------------------:|-----------------:|------------------------:|----------------:|---------------------:|
| XLK      |             1.06733 |          8.13196 |                0.533665 |        23427    |                  418 |
| NVDA     |             1.57068 |         12.4714  |                0.78534  |       288421    |                 4373 |
| CSCO     |             2.55135 |          7.59205 |                1.27567  |        24405.3  |                  351 |
| AAPL     |             2.56631 |         22.8745  |                1.28316  |        55090.1  |                 1283 |
| INTC     |             2.85063 |          9.11162 |                1.42531  |       145094    |                  876 |
| PLTR     |             4.7727  |         24.4579  |                2.38635  |        77774    |                 1230 |
| MSFT     |             5.21241 |         35.6472  |                2.6062   |        40339    |                 1371 |
| ORCL     |             7.29189 |         30.0959  |                3.64594  |        40025.2  |                  804 |
| AVGO     |             8.99922 |         35.7187  |                4.49961  |        33688.4  |                  901 |
| AMD      |             9.17053 |         36.8594  |                4.58526  |        59688.5  |                  923 |
| IBM      |             9.59331 |         27.9943  |                4.79666  |         5982    |                  217 |
| QCOM     |            11.409   |         31.6557  |                5.70451  |        12446    |                  308 |
| MU       |            12.0517  |         38.2396  |                6.02586  |        52313    |                  921 |
| APH      |            13.9352  |         45.4155  |                6.96762  |        11321    |                  209 |
| LRCX     |            16.0727  |         45.1448  |                8.03635  |        13039    |                  292 |
| TXN      |            17.491   |         44.6679  |                8.74548  |         7933    |                  188 |
| ANET     |            19.4284  |         51.0081  |                9.71419  |        10214.5  |                  208 |
| AMAT     |            24.0668  |         55.0472  |               12.0334   |         7912.77 |                  212 |
| ADI      |            25.7225  |         55.5283  |               12.8612   |         4123.83 |                  131 |
| KLAC     |            40.8643  |         75.662   |               20.4322   |         1004    |                   84 |

Latency taker-cost summary:

| symbol   |   latency_min |   buy_taker_cost_bps_median |   sell_taker_cost_bps_median |   roundtrip_two_leg_cost_bps_median |
|:---------|--------------:|----------------------------:|-----------------------------:|------------------------------------:|
| AAPL     |             0 |                     1.28316 |                      1.28316 |                             2.56631 |
| AAPL     |             1 |                     2.21844 |                      2.38826 |                             2.56664 |
| AAPL     |             2 |                     2.49544 |                      2.67339 |                             2.56551 |
| AAPL     |             5 |                     2.74069 |                      3.07432 |                             2.5657  |
| ADI      |             0 |                    12.8612  |                     12.8612  |                            25.7225  |
| ADI      |             1 |                    12.4951  |                     12.4692  |                            25.7245  |
| ADI      |             2 |                    12.5822  |                     12.4684  |                            25.7249  |
| ADI      |             5 |                    12.9168  |                     12.2458  |                            25.7361  |
| AMAT     |             0 |                    12.0334  |                     12.0334  |                            24.0668  |
| AMAT     |             1 |                    11.8097  |                     11.7248  |                            24.0623  |
| AMAT     |             2 |                    11.9653  |                     11.8223  |                            24.0582  |
| AMAT     |             5 |                    12.3191  |                     11.6376  |                            24.067   |
| AMD      |             0 |                     4.58526 |                      4.58526 |                             9.17053 |
| AMD      |             1 |                     5.68927 |                      5.69671 |                             9.17276 |
| AMD      |             2 |                     5.98086 |                      5.74971 |                             9.17097 |
| AMD      |             5 |                     6.11235 |                      6.10513 |                             9.16323 |
| ANET     |             0 |                     9.71419 |                      9.71419 |                            19.4284  |
| ANET     |             1 |                     9.8695  |                      9.92745 |                            19.4322  |
| ANET     |             2 |                    10.1099  |                     10.0839  |                            19.4259  |
| ANET     |             5 |                    10.3746  |                     10.2609  |                            19.4395  |

Passive touch-fill / markout proxy:

| symbol   | time_bucket   | spread_bucket   | imb_bucket   |   buy_bid_fill_prob |   sell_ask_fill_prob |   buy_passive_markout_cost_bps_median_if_filled |   sell_passive_markout_cost_bps_median_if_filled |
|:---------|:--------------|:----------------|:-------------|--------------------:|---------------------:|------------------------------------------------:|-------------------------------------------------:|
| AAPL     | open30        | s_q1            | balanced     |            0.810345 |             0.724138 |                                        -5.95626 |                                        14.5141   |
| AAPL     | open30        | s_q2            | ask_heavy    |            0.707483 |             0.77551  |                                         3.82539 |                                         7.53579  |
| AAPL     | open30        | s_q2            | balanced     |            0.713889 |             0.741667 |                                         5.84078 |                                         9.81162  |
| AAPL     | open30        | s_q2            | bid_heavy    |            0.717742 |             0.709677 |                                         4.47604 |                                         5.91913  |
| AAPL     | open30        | s_q3            | ask_heavy    |            0.683333 |             0.6625   |                                         6.39857 |                                         8.73948  |
| AAPL     | open30        | s_q3            | balanced     |            0.674157 |             0.700843 |                                         6.12004 |                                         7.35778  |
| AAPL     | open30        | s_q3            | bid_heavy    |            0.675105 |             0.687764 |                                         5.73794 |                                        15.2521   |
| AAPL     | open30        | s_q4            | ask_heavy    |            0.551282 |             0.470085 |                                         8.16951 |                                         6.33904  |
| AAPL     | open30        | s_q4            | balanced     |            0.45     |             0.462162 |                                         6.12769 |                                         7.88713  |
| AAPL     | open30        | s_q4            | bid_heavy    |            0.448148 |             0.585185 |                                         7.22514 |                                         6.54906  |
| AAPL     | mid_morning   | s_q1            | ask_heavy    |            0.730061 |             0.742331 |                                         5.06743 |                                         1.09345  |
| AAPL     | mid_morning   | s_q1            | balanced     |            0.737805 |             0.72439  |                                         4.06827 |                                         2.9168   |
| AAPL     | mid_morning   | s_q1            | bid_heavy    |            0.716146 |             0.723958 |                                         4.60498 |                                         0.860931 |
| AAPL     | mid_morning   | s_q2            | ask_heavy    |            0.688312 |             0.737013 |                                         5.5052  |                                         1.59559  |
| AAPL     | mid_morning   | s_q2            | balanced     |            0.704127 |             0.740317 |                                         3.67053 |                                         3.72736  |
| AAPL     | mid_morning   | s_q2            | bid_heavy    |            0.69012  |             0.730539 |                                         3.65497 |                                         4.34678  |
| AAPL     | mid_morning   | s_q3            | ask_heavy    |            0.639659 |             0.648188 |                                         4.90907 |                                         2.19208  |
| AAPL     | mid_morning   | s_q3            | balanced     |            0.639934 |             0.665376 |                                         4.60694 |                                         2.01887  |
| AAPL     | mid_morning   | s_q3            | bid_heavy    |            0.678899 |             0.644037 |                                         4.65464 |                                         2.73618  |
| AAPL     | mid_morning   | s_q4            | ask_heavy    |            0.4375   |             0.269737 |                                         3.42156 |                                         4.36247  |

## Execution-Optimized Pair Backtest

The maker/taker execution backtest is intentionally treated as a candidate screen.  It uses observed bid/ask fills and last-trade crossing proxies.  Positive validation results are not considered tradable unless the out-of-sample audit survives.

| stock   | spread_type               | policy   |   val_trades |   val_net_bps |   test_trades |   test_net_bps | decision             | oos_decision           | final_policy   |
|:--------|:--------------------------|:---------|-------------:|--------------:|--------------:|---------------:|:---------------------|:-----------------------|:---------------|
| INTC    | price_regression_residual | taker    |           20 |       3083.69 |            43 |       -3416.85 | validation_candidate | reject_after_oos_audit | no_trade       |

## Loss Streamline Decision

| research_path                       | decision                    | reason                                                                                                                                             |   train_or_validation_net_bps |   test_net_bps |   raw_test_net_bps_before_gate |
|:------------------------------------|:----------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------:|---------------:|-------------------------------:|
| market_neutral_pair_or_basket       | no_trade                    | validation-selected active pair/basket rules fail no-trade gate or lose after costs                                                                |                       nan     |         0      |                    -53500.6    |
| robust_alpha_suite_selected         | no_trade                    | selected robust-alpha rule loses OOS or does not beat no-trade                                                                                     |                       472.546 |       -17.7254 |                       -17.7254 |
| fixed_bps_xlk_only_timing_candidate | legacy_candidate_shape_only | legacy profit-search output is Jan-Feb positive, but it predates expanded top-20 controls and is not final evidence                                |                       456.479 |       613.353  |                       613.353  |
| expanded_fixed_bps_xlk_only_timing  | no_trade                    | train_or_validation_net<=0;test_net<=0;2x_cost_test<=0;latency1_test<=0;does_not_beat_directional_control;sign_flip_not_worse;circular_pvalue>0.10 |                     -2115.46  |      -977.239  |                      -977.239  |
| timing_robustness_current_selection | no_trade                    | No XLK-only timing rule passed Jan-Feb train filters.                                                                                              |                         0     |         0      |                         0      |
| named_timing_candidate_micro075_e60 | no_trade                    | named candidate audited on current top-5 basket with Mar-Apr test                                                                                  |                      -142.16  |      -894.791  |                      -894.791  |
| regime_gated_timing_repair          | no_trade                    | Selected on Jan-Feb only; Mar-Apr is holdout audit. Script label: diagnostic_only.                                                                 |                       373.614 |      -131.358  |                      -131.358  |

## Fixed-BPS Timing Controls on Expanded Data

This section regenerates the old fixed-bps sparse timing candidate shape on the expanded top-20 panel.  The old `profit_search_*` tables are legacy candidate screens; this is the current-data control result.

| decision   | reason                                                                                                                                             | basket_symbols         |   train_net_bps |   validation_net_bps |   test_net_bps |   test_2x_cost_net_bps |   test_latency1_net_bps |   circular_pvalue |
|:-----------|:---------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------|----------------:|---------------------:|---------------:|-----------------------:|------------------------:|------------------:|
| no_trade   | train_or_validation_net<=0;test_net<=0;2x_cost_test<=0;latency1_test<=0;does_not_beat_directional_control;sign_flip_not_worse;circular_pvalue>0.10 | NVDA AAPL MSFT AVGO MU |        -2115.46 |             -45.1272 |       -977.239 |               -1211.91 |                -1034.28 |               0.8 |

Controls:

| control                     |   train_net_bps |   validation_net_bps |   test_net_bps |   test_trades |
|:----------------------------|----------------:|---------------------:|---------------:|--------------:|
| selected                    |      -2115.46   |             -45.1272 |       -977.239 |            83 |
| sign_flip                   |       1091.32   |            -238.614  |        507.89  |            83 |
| active_always_long          |      -1032.71   |            -344.133  |        807.851 |            83 |
| active_always_short         |          8.5748 |              60.3926 |      -1277.2   |            83 |
| circular_shift_mean         |        nan      |             nan      |       -335.576 |           nan |
| circular_shift_p95          |        nan      |             nan      |        736.585 |           nan |
| selected_vs_circular_pvalue |        nan      |             nan      |          0.8   |           nan |

Monthly PnL:

| month   |   gross_bps |   cost_bps |    net_bps |   trades |
|:--------|------------:|-----------:|-----------:|---------:|
| 2025-11 |   -454.955  |    206.546 |  -661.5    |       38 |
| 2025-12 |   -916.798  |    169.95  | -1086.75   |       46 |
| 2026-01 |   -231.636  |    135.574 |  -367.21   |       44 |
| 2026-02 |     96.7432 |    141.87  |   -45.1272 |       40 |
| 2026-03 |    197.418  |    126.355 |    71.0634 |       42 |
| 2026-04 |   -939.983  |    108.32  | -1048.3    |       41 |

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
| selected            |        -14.9009 |             -213.331 |       -47.3    |            40 |
| sign_flip           |       -193.159  |             -181.897 |       -78.9887 |            40 |
| active_always_long  |       -193.159  |             -181.897 |       -78.9887 |            40 |
| active_always_short |        -14.9009 |             -213.331 |       -47.3    |            40 |

Largest ridge coefficients:

| feature           |       coef |
|:------------------|-----------:|
| premium_mid_bps   |  2.83863   |
| realized_vol_bps  | -2.10577   |
| kyle_lambda_proxy |  1.37726   |
| premium_micro_bps | -1.2952    |
| intercept         | -0.997884  |
| xlk_micro_gap_bps |  0.74131   |
| xlk_ret_lag5_bps  |  0.721895  |
| xlk_ret_lag1_bps  |  0.605648  |
| xlk_ret_lag15_bps |  0.500674  |
| signed_flow_5     | -0.308216  |
| xlk_spread_bps    |  0.149119  |
| roll_premium_bps  | -0.0451124 |

## Current Timing Robustness Re-Audit

The previously highlighted `micro_shrink_0.75_cw10d_e60_x0_mh240` result was March-only and came from an older sparse basket convention.  The script now regenerates timing robustness on the current expanded clean top-5 holdings basket and evaluates the full March-April holdout.

Current Jan-Feb-selected decision:

| decision   | reason                                                |   train_net_bps |   test_net_bps |
|:-----------|:------------------------------------------------------|----------------:|---------------:|
| no_trade   | No XLK-only timing rule passed Jan-Feb train filters. |               0 |              0 |

Named candidate audit:

| strategy                             | basket_symbols         |   train_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   train_trades |   test_trades |
|:-------------------------------------|:-----------------------|----------------:|--------------:|--------------:|---------------:|---------------:|--------------:|
| micro_shrink_0.75_cw10d_e60_x0_mh240 | NVDA AAPL MSFT AVGO MU |         -142.16 |      -32.4451 |      -862.346 |       -894.791 |            128 |           151 |

Named candidate execution audit:

| execution_model   |   latency_min |   train_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   test_trades |
|:------------------|--------------:|----------------:|--------------:|--------------:|---------------:|--------------:|
| halfspread        |             0 |        -142.16  |      -32.4451 |      -862.346 |       -894.791 |           151 |
| exact_bidask      |             0 |        -142.194 |      -32.4045 |      -862.355 |       -894.759 |           151 |
| exact_bidask      |             1 |        -120.777 |     -176.543  |      -913.675 |      -1090.22  |           152 |
| exact_bidask      |             2 |        -319.421 |       88.6059 |      -841.822 |       -753.217 |           152 |
| exact_bidask      |             5 |        -267.18  |      -20.3491 |      -866.279 |       -886.628 |           152 |

## Regime Shift Diagnostics

The regime-shift check asks whether poor timing performance comes from a broken XLK/basket linkage, wider execution costs, or a directional signal failure.  The expanded-sample evidence points mainly to signal-direction instability: XLK/basket correlation and beta do not collapse, but April is a strong XLK rally in which the positive premium stays persistent and the contrarian rule remains short XLK for too long.

Train-vs-test regime summary:

| metric                     |   train_avg |    test_avg |   test_minus_train |
|:---------------------------|------------:|------------:|-------------------:|
| xlk_basket_corr_1m         |   0.655138  |   0.634166  |        -0.020972   |
| xlk_on_basket_beta_1m      |   0.614184  |   0.616637  |         0.00245218 |
| residual_vol_bps_1m        |   4.98373   |   5.12345   |         0.139715   |
| median_xlk_spread_bps      |   0.709236  |   1.02276   |         0.313526   |
| signal_std_bps             | 114.473     | 150.386     |        35.9131     |
| alpha_ic_5m                |  -0.0113578 |   0.0286324 |         0.0399902  |
| contrarian_decile_edge_5m  |  -1.9271    |   2.3787    |         4.3058     |
| alpha_ic_15m               |  -0.0322288 |   0.0413642 |         0.073593   |
| contrarian_decile_edge_15m |  -6.90304   |   5.88396   |        12.787      |
| alpha_ic_30m               |  -0.0590983 |   0.053977  |         0.113075   |
| contrarian_decile_edge_30m | -13.0812    |  10.2419    |        23.3231     |
| alpha_ic_60m               |  -0.0777925 |   0.0789449 |         0.156737   |
| contrarian_decile_edge_60m | -21.0606    |  21.9551    |        43.0156     |

Monthly market state:

| month   |   xlk_return_bps |   basket_return_bps |   xlk_basket_corr_1m |   xlk_on_basket_beta_1m |   residual_vol_bps_1m |   median_xlk_spread_bps |   signal_std_bps |   abs_signal_gt_60_frac |
|:--------|-----------------:|--------------------:|---------------------:|------------------------:|----------------------:|------------------------:|-----------------:|------------------------:|
| 2025-11 |         -248.124 |            -246.401 |             0.776102 |                0.726364 |               4.87309 |                1.02988  |         173.251  |                0.654751 |
| 2025-12 |         -133.084 |            -179.869 |             0.594055 |                0.498026 |               4.20812 |                1.37146  |        2167.73   |                0.918706 |
| 2026-01 |         -295.7   |            -244.169 |             0.601841 |                0.516993 |               4.40605 |                0.694227 |          93.6499 |                0.628137 |
| 2026-02 |         -309.429 |            -409.318 |             0.708435 |                0.711376 |               5.56141 |                0.724244 |         135.297  |                0.775649 |
| 2026-03 |         -292.892 |            -346.281 |             0.665573 |                0.679319 |               5.52103 |                0.773664 |         183.382  |                0.820896 |
| 2026-04 |         1262.86  |            1321.4   |             0.602759 |                0.553954 |               4.72586 |                1.27186  |         117.391  |                0.846362 |

Named timing candidate monthly PnL anatomy:

| month   |   gross_bps |   cost_bps |    net_bps |   trades |   long_gross_bps |   short_gross_bps |   long_minutes |   short_minutes |
|:--------|------------:|-----------:|-----------:|---------:|-----------------:|------------------:|---------------:|----------------:|
| 2025-11 |   -578.952  |    326.161 |  -905.113  |       62 |        -463.509  |         -115.444  |           4584 |            1342 |
| 2025-12 |   -961.783  |    285.366 | -1247.15   |       84 |        -567.937  |         -393.845  |           4643 |            3426 |
| 2026-01 |    -22.7232 |    144.013 |  -166.736  |       58 |        -171.264  |          148.54   |            627 |            4973 |
| 2026-02 |    167.889  |    143.347 |    24.5423 |       70 |         -29.7541 |          197.643  |           3852 |            2861 |
| 2026-03 |    156.568  |    188.972 |   -32.4045 |       76 |         101.566  |           55.0019 |           4216 |            3046 |
| 2026-04 |   -724.159  |    138.195 |  -862.355  |       75 |         126.882  |         -851.041  |           1010 |            6420 |

## Regime-Gate Repair Experiments

The April diagnosis suggests a specific repair: prevent the contrarian rule from shorting XLK when the premium is persistent and/or both XLK and the sparse basket are trending upward.  The gate experiment keeps the target signal fixed and only changes the trade/no-trade overlay.  Gate selection uses January-February only; March-April remains holdout.

Selection:

| decision        | selected_strategy                              | gate_mode   | state_kind          |   lookback_min |   trend_threshold_bps |   train_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   test_2x_cost_net_bps |
|:----------------|:-----------------------------------------------|:------------|:--------------------|---------------:|----------------------:|----------------:|--------------:|--------------:|---------------:|-----------------------:|
| diagnostic_only | two_sided_premium_persistence_lb780_thr75_flat | two_sided   | premium_persistence |            780 |                    75 |         373.614 |      -195.377 |       64.0195 |       -131.358 |               -210.735 |

Monthly side anatomy:

| strategy                                                      | month   |   gross_bps |   cost_bps |     net_bps |   long_gross_bps |   short_gross_bps |   long_minutes |   short_minutes |
|:--------------------------------------------------------------|:--------|------------:|-----------:|------------:|-----------------:|------------------:|---------------:|----------------:|
| baseline_no_gate                                              | 2025-11 |   -578.952  |   326.161  |  -905.113   |        -463.509  |         -115.444  |           4584 |            1342 |
| baseline_no_gate                                              | 2025-12 |   -961.783  |   285.366  | -1247.15    |        -567.937  |         -393.845  |           4643 |            3426 |
| baseline_no_gate                                              | 2026-01 |    -22.7232 |   144.013  |  -166.736   |        -171.264  |          148.54   |            627 |            4973 |
| baseline_no_gate                                              | 2026-02 |    167.889  |   143.347  |    24.5423  |         -29.7541 |          197.643  |           3852 |            2861 |
| baseline_no_gate                                              | 2026-03 |    156.568  |   188.972  |   -32.4045  |         101.566  |           55.0019 |           4216 |            3046 |
| baseline_no_gate                                              | 2026-04 |   -724.159  |   138.195  |  -862.355   |         126.882  |         -851.041  |           1010 |            6420 |
| long_only_diagnostic                                          | 2025-11 |   -463.509  |   202.699  |  -666.208   |        -463.509  |            0      |           4584 |               0 |
| long_only_diagnostic                                          | 2025-12 |   -567.937  |   170.015  |  -737.952   |        -567.937  |            0      |           4643 |               0 |
| long_only_diagnostic                                          | 2026-01 |   -171.264  |    30.3749 |  -201.638   |        -171.264  |            0      |            627 |               0 |
| long_only_diagnostic                                          | 2026-02 |    -29.7541 |   106.543  |  -136.297   |         -29.7541 |            0      |           3852 |               0 |
| long_only_diagnostic                                          | 2026-03 |    101.566  |   141.998  |   -40.4315  |         101.566  |            0      |           4216 |               0 |
| long_only_diagnostic                                          | 2026-04 |    126.882  |    24.2637 |   102.618   |         126.882  |            0      |           1010 |               0 |
| short_only_diagnostic                                         | 2025-11 |   -115.444  |   123.462  |  -238.906   |           0      |         -115.444  |              0 |            1342 |
| short_only_diagnostic                                         | 2025-12 |   -393.845  |   115.351  |  -509.196   |           0      |         -393.845  |              0 |            3426 |
| short_only_diagnostic                                         | 2026-01 |    148.54   |   113.638  |    34.9025  |           0      |          148.54   |              0 |            4973 |
| short_only_diagnostic                                         | 2026-02 |    197.643  |    36.8037 |   160.839   |           0      |          197.643  |              0 |            2861 |
| short_only_diagnostic                                         | 2026-03 |     55.0019 |    46.9749 |     8.02699 |           0      |           55.0019 |              0 |            3046 |
| short_only_diagnostic                                         | 2026-04 |   -851.041  |   113.932  |  -964.973   |           0      |         -851.041  |              0 |            6420 |
| two_sided_premium_persistence_lb780_thr75_flat                | 2025-11 |    162.081  |   186.567  |   -24.4863  |         273.508  |         -111.427  |           1081 |            1261 |
| two_sided_premium_persistence_lb780_thr75_flat                | 2025-12 |   -195.482  |    73.814  |  -269.296   |        -164.026  |          -31.4561 |            802 |             476 |
| two_sided_premium_persistence_lb780_thr75_flat                | 2026-01 |    171.838  |    78.4391 |    93.3988  |        -171.264  |          343.101  |            627 |            2186 |
| two_sided_premium_persistence_lb780_thr75_flat                | 2026-02 |    362.733  |    82.5183 |   280.215   |         122.76   |          239.973  |           1040 |            1025 |
| two_sided_premium_persistence_lb780_thr75_flat                | 2026-03 |   -142.559  |    52.8178 |  -195.377   |          26.8515 |         -169.411  |            575 |            1232 |
| two_sided_premium_persistence_lb780_thr75_flat                | 2026-04 |     90.5791 |    26.5596 |    64.0195  |          87.5356 |            3.0435 |            539 |             439 |
| flip_short_uptrend_multi_day_trend_premium_lb1950_thr100_flip | 2025-11 |   -578.952  |   326.161  |  -905.113   |        -463.509  |         -115.444  |           4584 |            1342 |
| flip_short_uptrend_multi_day_trend_premium_lb1950_thr100_flip | 2025-12 |   -893.673  |   285.352  | -1179.03    |        -533.883  |         -359.791  |           5029 |            3040 |
| flip_short_uptrend_multi_day_trend_premium_lb1950_thr100_flip | 2026-01 |   -234.698  |   144.021  |  -378.719   |        -277.251  |           42.5529 |            772 |            4828 |
| flip_short_uptrend_multi_day_trend_premium_lb1950_thr100_flip | 2026-02 |    167.889  |   143.347  |    24.5423  |         -29.7541 |          197.643  |           3852 |            2861 |
| flip_short_uptrend_multi_day_trend_premium_lb1950_thr100_flip | 2026-03 |    156.568  |   188.972  |   -32.4045  |         101.566  |           55.0019 |           4216 |            3046 |
| flip_short_uptrend_multi_day_trend_premium_lb1950_thr100_flip | 2026-04 |    777.474  |   138.157  |   639.317   |         877.698  |         -100.225  |           6179 |            1251 |

## Sparse Market-Neutral Basket

| subset                  |   k | betas                                                      |   train_adf_p |   train_half_life_minutes |   train_avg_oneway_cost_bps |    score |
|:------------------------|----:|:-----------------------------------------------------------|--------------:|--------------------------:|----------------------------:|---------:|
| NVDA AMD PLTR LRCX AMAT |   5 | NVDA:0.1930 AMD:0.0807 PLTR:0.1040 LRCX:0.0792 AMAT:0.0560 |     0.0265127 |                   343.717 |                     4.90411 | 0.296453 |
| NVDA MSFT AMD PLTR AMAT |   5 | NVDA:0.2003 MSFT:0.0636 AMD:0.0864 PLTR:0.1069 AMAT:0.0709 |     0.0274649 |                   355.18  |                     4.80604 | 0.301176 |
| NVDA AMD PLTR AMAT      |   4 | NVDA:0.2057 AMD:0.0888 PLTR:0.1112 AMAT:0.0724             |     0.0282008 |                   378.25  |                     4.48796 | 0.307085 |
| NVDA AMD PLTR AMAT ORCL |   5 | NVDA:0.1941 AMD:0.0833 PLTR:0.1037 AMAT:0.0689 ORCL:0.0624 |     0.0399209 |                   379.603 |                     4.73226 | 0.324367 |
| NVDA MSFT AMD PLTR LRCX |   5 | NVDA:0.1953 MSFT:0.0628 AMD:0.0823 PLTR:0.1028 LRCX:0.0894 |     0.0477607 |                   370.045 |                     4.63664 | 0.325516 |
| NVDA AVGO AMD PLTR AMAT |   5 | NVDA:0.1881 AVGO:0.0770 AMD:0.0806 PLTR:0.1032 AMAT:0.0641 |     0.0502912 |                   365.295 |                     4.8078  | 0.329095 |
| NVDA AAPL AMD PLTR AMAT |   5 | NVDA:0.2005 AAPL:0.0788 AMD:0.0864 PLTR:0.1075 AMAT:0.0701 |     0.0449295 |                   384.721 |                     4.73145 | 0.331919 |
| NVDA AAPL AMD PLTR LRCX |   5 | NVDA:0.1955 AAPL:0.0782 AMD:0.0823 PLTR:0.1033 LRCX:0.0887 |     0.0562212 |                   379.894 |                     4.56845 | 0.337537 |
| NVDA AMD PLTR LRCX      |   4 | NVDA:0.2006 AMD:0.0846 PLTR:0.1069 LRCX:0.0910             |     0.0478761 |                   407.108 |                     4.31669 | 0.337764 |
| AAPL AMD PLTR AMAT ORCL |   5 | AAPL:0.0884 AMD:0.1095 PLTR:0.1302 AMAT:0.0865 ORCL:0.0772 |     0.0340087 |                   401.914 |                     5.2289  | 0.339543 |

| strategy             | sample   |   trades |   gross_bps |   cost_bps |   net_bps |   max_drawdown_bps |
|:---------------------|:---------|---------:|------------:|-----------:|----------:|-------------------:|
| sparse_e3.5_x0_plain | test     |        4 |    -24.3074 |    15.2564 |  -39.5638 |           -70.5221 |
| sparse_e3.5_x0_plain | train    |        6 |    102.006  |    31.0504 |   70.9561 |           -94.6965 |
| literature_no_trade  | test     |        0 |      0      |     0      |    0      |             0      |
| literature_no_trade  | train    |        0 |      0      |     0      |    0      |             0      |

Bid/ask boundary audit:

| sample   |   old_gross_bps |   old_cost_bps |   old_net_bps |   new_gross_bps |   new_bidask_cost_bps |   new_bidask_net_bps |   turnover |
|:---------|----------------:|---------------:|--------------:|----------------:|----------------------:|---------------------:|-----------:|
| test     |        -24.3074 |        15.2564 |      -39.5638 |        -24.3074 |               101.139 |            -125.446  |          4 |
| train    |        102.006  |        31.0504 |       70.9561 |        102.006  |               128.142 |             -26.1359 |          6 |

## Robust Alpha Suite

The robust alpha suite jointly tests XLK-only timing and partial/full hedge rules.  If the selected rule has `hedge_fraction = 0`, it is a timing strategy, not market-neutral arbitrage.

| decision    | selected_strategy                                                                  | reason                               |   train_net_bps |   test_net_bps |   benchmark_no_trade_train_bps |   benchmark_no_trade_test_bps | economic_label   |
|:------------|:-----------------------------------------------------------------------------------|:-------------------------------------|----------------:|---------------:|-------------------------------:|------------------------------:|:-----------------|
| active_rule | xlk_only_timing_mid_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180 | passed train-only robustness filters |         472.546 |       -17.7254 |                              0 |                             0 | XLK-only timing  |

Controls:

| control                     |   train_net_bps |   test_net_bps |   test_trades |   test_avg_abs_position |
|:----------------------------|----------------:|---------------:|--------------:|------------------------:|
| selected                    |         472.546 |     -17.7254   |            10 |               0.0336719 |
| sign_flip                   |        -484.459 |     -23.4718   |            10 |               0.0336719 |
| active_always_long          |         312.151 |     -11.4609   |            10 |               0.0336719 |
| active_always_short         |        -324.064 |     -29.7363   |            10 |               0.0336719 |
| circular_shift_mean         |         nan     |     -61.6979   |           nan |             nan         |
| circular_shift_p95          |         nan     |      42.7593   |           nan |             nan         |
| selected_vs_circular_pvalue |         nan     |       0.243902 |           nan |             nan         |

Cost sensitivity:

|   cost_multiplier | sample   |   gross_bps |   cost_bps |   net_bps |
|------------------:|:---------|------------:|-----------:|----------:|
|               1   | train    |   478.502   |    5.95631 |  472.546  |
|               1   | test     |     2.87321 |   20.5986  |  -17.7254 |
|               1.5 | train    |   478.502   |    8.93446 |  469.568  |
|               1.5 | test     |     2.87321 |   30.8979  |  -28.0247 |
|               2   | train    |   478.502   |   11.9126  |  466.59   |
|               2   | test     |     2.87321 |   41.1972  |  -38.324  |
|               3   | train    |   478.502   |   17.8689  |  460.633  |
|               3   | test     |     2.87321 |   61.7958  |  -58.9226 |
|               4   | train    |   478.502   |   23.8252  |  454.677  |
|               4   | test     |     2.87321 |   82.3944  |  -79.5212 |

## XLK-Only Timing Extension

| period     |   gross_bps |   cost_bps |   net_bps |   trades |   avg_abs_position |   xlk_buyhold_bps |
|:-----------|------------:|-----------:|----------:|---------:|-------------------:|------------------:|
| train      |    -125.87  |    557.201 |  -683.072 |      120 |           0.742022 |         -676.907  |
| validation |     407.969 |    202.23  |   205.739 |       46 |           0.902025 |         -309.429  |
| test       |    -550.251 |    302.178 |  -852.429 |       99 |           0.806039 |          969.964  |
| all        |    -268.152 |   1061.61  | -1329.76  |      265 |           0.789119 |          -16.3728 |

Bid/ask boundary audit:

| sample     |   old_gross_bps |   old_cost_bps |   old_net_bps |   new_gross_bps |   new_bidask_cost_bps |   new_bidask_net_bps |   turnover |
|:-----------|----------------:|---------------:|--------------:|----------------:|----------------------:|---------------------:|-----------:|
| test       |        -550.251 |        302.178 |      -852.429 |        -550.251 |               302.087 |             -852.338 |         99 |
| train      |        -125.87  |        557.201 |      -683.072 |        -125.87  |               607.417 |             -733.287 |        120 |
| validation |         407.969 |        202.23  |       205.739 |         407.969 |               202.205 |              205.763 |         46 |

## Interpretation

The next report should avoid saying "ETF arbitrage is profitable" unless a market-neutral rule survives the new spread-construction and execution-cost checks.  The defensible framing is:

> Market-neutral XLK-vs-basket arbitrage is fragile under realistic TAQ execution assumptions.  The more promising direction is to use the sparse/top-holdings basket as a fair-value signal and trade XLK only, but the first new-data quick run does not yet prove a stable positive active strategy.  Report gross/no-cost, 0.25-spread, 0.50-spread, and last-trade proxy economics separately.

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
