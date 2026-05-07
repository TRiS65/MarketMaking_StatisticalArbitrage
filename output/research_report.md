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

## Reproducibility

```bash
python3 scripts/build_dataset.py --force
python3 scripts/run_newdata_pipeline.py --quick
```
