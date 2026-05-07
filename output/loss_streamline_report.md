# Loss Streamline Report

## Executive decision

| research_path                       | decision                    | reason                                                                                                                                             |   train_or_validation_net_bps |   test_net_bps |   raw_test_net_bps_before_gate |
|:------------------------------------|:----------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------:|---------------:|-------------------------------:|
| market_neutral_pair_or_basket       | no_trade                    | validation-selected active pair/basket rules fail no-trade gate or lose after costs                                                                |                        nan    |           0    |                      -53500.6  |
| robust_alpha_suite_selected         | no_trade                    | selected robust-alpha rule loses OOS or does not beat no-trade                                                                                     |                        472.55 |         -17.73 |                         -17.73 |
| fixed_bps_xlk_only_timing_candidate | legacy_candidate_shape_only | legacy profit-search output is Jan-Feb positive, but it predates expanded top-20 controls and is not final evidence                                |                        456.48 |         613.35 |                         613.35 |
| expanded_fixed_bps_xlk_only_timing  | no_trade                    | train_or_validation_net<=0;test_net<=0;2x_cost_test<=0;latency1_test<=0;does_not_beat_directional_control;sign_flip_not_worse;circular_pvalue>0.10 |                      -2115.46 |        -977.24 |                        -977.24 |
| timing_robustness_current_selection | no_trade                    | No XLK-only timing rule passed Jan-Feb train filters.                                                                                              |                          0    |           0    |                           0    |
| named_timing_candidate_micro075_e60 | no_trade                    | named candidate audited on current top-5 basket with Mar-Apr test                                                                                  |                       -142.16 |        -894.79 |                        -894.79 |

## 1. Market-neutral / pair-trading PnL attribution

| method         |   selected_pairs |   gate_pass_pairs |   raw_validation_net_bps |   raw_test_net_bps |   raw_test_net_per_trade_bps |   raw_positive_test_pairs |   gate_test_net_bps |   test_trades |
|:---------------|-----------------:|------------------:|-------------------------:|-------------------:|-----------------------------:|--------------------------:|--------------------:|--------------:|
| baseline       |               19 |                 0 |                 -1494.03 |          -14985    |                        -5.81 |                         0 |                   0 |          2578 |
| coint_filter   |                1 |                 0 |                   211.67 |            -188.99 |                        -2.01 |                         0 |                   0 |            94 |
| combined       |                1 |                 0 |                   -47.3  |            -428.48 |                        -5.79 |                         0 |                   0 |            74 |
| kalman_lagged  |               19 |                 0 |                 -3911.12 |          -15984.3  |                        -5.16 |                         1 |                   0 |          3097 |
| passive_stress |               19 |                 0 |                   190.57 |          -12166.2  |                        -4.35 |                         0 |                   0 |          2794 |
| sscore_ou_gate |               19 |                 0 |                  -417.6  |           -9747.57 |                        -6.99 |                         1 |                   0 |          1394 |

Interpretation: if gate_test_net_bps is zero, the economically selected policy is no-trade. Negative raw_test_net_bps indicates that model filters reduce losses but do not create tradable alpha.

## 2. Exit-reason attribution

| sample     | exit_reason   |   trades |   gross_bps |   cost_bps |   net_bps |   net_per_trade_bps |
|:-----------|:--------------|---------:|------------:|-----------:|----------:|--------------------:|
| test       | reversion     |     5917 |    67711.8  |   23283.3  |  44428.4  |                7.51 |
| test       | stop_loss     |      721 |    -3930.87 |    2181.59 |  -6112.46 |               -8.48 |
| test       | eod           |     9164 |    -7864.84 |   32902.1  | -40767    |               -4.45 |
| test       | max_hold      |    25910 |     2223.73 |   77601.4  | -75377.7  |               -2.91 |
| train      | reversion     |     7685 |    77824    |   33425.9  |  44398    |                5.78 |
| train      | eod           |    10049 |    10408.3  |   33840.9  | -23432.6  |               -2.33 |
| train      | max_hold      |    28423 |   -11718.9  |   85040.4  | -96759.3  |               -3.4  |
| train      | stop_loss     |    12699 |   -49722.9  |   49762.8  | -99485.8  |               -7.83 |
| validation | reversion     |     2168 |    25831.5  |    8168.59 |  17662.9  |                8.15 |
| validation | stop_loss     |      689 |    -4023.38 |    2883.27 |  -6906.65 |              -10.02 |
| validation | eod           |     2530 |     4102.9  |   11848.1  |  -7745.2  |               -3.06 |
| validation | max_hold      |     9266 |     -465.74 |   24523.8  | -24989.6  |               -2.7  |

Interpretation: profitable reversion exits combined with negative max-hold / stop-loss / EOD exits usually means entry thresholds are too loose and residuals do not revert quickly enough.

## 3. Robust-alpha selected rule

Selected strategy: `xlk_only_timing_mid_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180`
Train net: 472.55 bps; test net: -17.73 bps.
Test gross/cost: 2.87 / 20.60 bps; break-even cost multiplier: 0.139x.
Always-long control test net: -11.46 bps. If this is close to or better than selected, timing alpha is not established.
Circular-shift p-value proxy: 0.244.

## 4. Fixed-bps XLK-only timing candidate audit

Expanded top-20 regeneration:

| decision   | reason                                                                                                                                             | basket_symbols         |   train_net_bps |   validation_net_bps |   test_net_bps |   test_2x_cost_net_bps |   test_latency1_net_bps |   circular_pvalue |
|:-----------|:---------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------|----------------:|---------------------:|---------------:|-----------------------:|------------------------:|------------------:|
| no_trade   | train_or_validation_net<=0;test_net<=0;2x_cost_test<=0;latency1_test<=0;does_not_beat_directional_control;sign_flip_not_worse;circular_pvalue>0.10 | NVDA AAPL MSFT AVGO MU |        -2115.46 |               -45.13 |        -977.24 |               -1211.91 |                -1034.28 |               0.8 |

Legacy profit-search screen:

| protocol       | hedge   | signal_price   | signal_kind   |   hedge_frac |   threshold_bps |   exit_bps |   max_hold |   jan_net_bps |   feb_net_bps |   train_net_bps |   test_net_bps |   test_gross_per_trade_bps |   test_cost_per_trade_bps |   test_net_per_trade_bps |   test_cost_capacity_x |   candidate_train_gate |
|:---------------|:--------|:---------------|:--------------|-------------:|----------------:|-----------:|-----------:|--------------:|--------------:|----------------:|---------------:|---------------------------:|--------------------------:|-------------------------:|-----------------------:|-----------------------:|
| jan_best       | sparse5 | micro          | roll_center   |            0 |              50 |         25 |        390 |        289.64 |        166.84 |          456.48 |         613.35 |                      14.03 |                       3.8 |                    10.22 |                   3.69 |                      1 |
| train_best     | sparse5 | micro          | roll_center   |            0 |              50 |         25 |        390 |        289.64 |        166.84 |          456.48 |         613.35 |                      14.03 |                       3.8 |                    10.22 |                   3.69 |                      1 |
| robust_jan_feb | sparse5 | micro          | roll_center   |            0 |              50 |         25 |        390 |        289.64 |        166.84 |          456.48 |         613.35 |                      14.03 |                       3.8 |                    10.22 |                   3.69 |                      1 |
| march_oracle   | sparse5 | micro          | raw           |            0 |              50 |          0 |        390 |         82.99 |        158.68 |          241.67 |         652.23 |                      18.47 |                       3.3 |                    15.17 |                   5.6  |                      0 |

Interpretation: a positive fixed-bps timing candidate is not the same as market-neutral arbitrage. The existing profit-search file is treated as a legacy candidate screen unless it is regenerated on the expanded top-20 sample. It should be promoted only if it passes sign-flip, always-long/short, circular-shift, latency, and cost-multiplier stress tests on the current data.

## 5. Signal-bucket regime check

| sample     |   horizon_min |   linear_slope_bps_per_decile |   decile0_future_bps |   decile9_future_bps |   best_decile |   best_decile_future_bps |
|:-----------|--------------:|------------------------------:|---------------------:|---------------------:|--------------:|-------------------------:|
| test       |             1 |                         -0.02 |                 0.37 |                -0.2  |             0 |                     0.37 |
| test       |             5 |                         -0.09 |                 1.88 |                -1    |             6 |                     1.96 |
| test       |            15 |                         -0.13 |                 4.64 |                -2.73 |             6 |                     5.12 |
| test       |            30 |                         -0.09 |                 8.46 |                -4.52 |             6 |                     8.86 |
| test       |            60 |                          0.01 |                16.07 |                -6.74 |             7 |                    17.06 |
| train      |             1 |                          0    |                 0.03 |                 0.1  |             1 |                     0.12 |
| train      |             5 |                          0.03 |                 0.39 |                 0.71 |             9 |                     0.71 |
| train      |            15 |                          0.09 |                 0.79 |                 2.04 |             9 |                     2.04 |
| train      |            30 |                          0.19 |                 1.72 |                 4.03 |             9 |                     4.03 |
| train      |            60 |                          0.36 |                 4.93 |                 8.13 |             9 |                     8.13 |
| validation |             1 |                         -0    |                -0.45 |                -0.66 |             5 |                     0.3  |
| validation |             5 |                          0    |                -1.47 |                -2.79 |             6 |                     2.15 |
| validation |            15 |                          0.01 |                -4.17 |                -7.3  |             6 |                     7.04 |
| validation |            30 |                          0    |                -6.1  |               -12.79 |             6 |                    13.59 |
| validation |            60 |                         -0.01 |                -8.06 |               -20.5  |             6 |                    15.17 |

Interpretation: a non-monotone or sign-flipping decile curve means the signal should not be traded as a symmetric z-score. Prefer fixed-bps thresholds, asymmetric tails, or a no-trade gate.

## 6. Current timing robustness / named candidate audit

Current Jan-Feb-selected timing decision:

| decision   | reason                                                |   train_net_bps |   test_net_bps |
|:-----------|:------------------------------------------------------|----------------:|---------------:|
| no_trade   | No XLK-only timing rule passed Jan-Feb train filters. |               0 |              0 |

Named candidate `micro_shrink_0.75_cw10d_e60_x0_mh240` on the current top-5 basket:

| strategy                             | basket_symbols         |   train_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   train_trades |   test_trades |
|:-------------------------------------|:-----------------------|----------------:|--------------:|--------------:|---------------:|---------------:|--------------:|
| micro_shrink_0.75_cw10d_e60_x0_mh240 | NVDA AAPL MSFT AVGO MU |         -142.16 |        -32.45 |       -862.35 |        -894.79 |            128 |           151 |

Named candidate execution audit:

| execution_model   |   latency_min |   train_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   test_trades |
|:------------------|--------------:|----------------:|--------------:|--------------:|---------------:|--------------:|
| halfspread        |             0 |         -142.16 |        -32.45 |       -862.35 |        -894.79 |           151 |
| exact_bidask      |             0 |         -142.19 |        -32.4  |       -862.35 |        -894.76 |           151 |
| exact_bidask      |             1 |         -120.78 |       -176.54 |       -913.67 |       -1090.22 |           152 |
| exact_bidask      |             2 |         -319.42 |         88.61 |       -841.82 |        -753.22 |           152 |
| exact_bidask      |             5 |         -267.18 |        -20.35 |       -866.28 |        -886.63 |           152 |

Interpretation: this resolves the earlier contradiction. The old March-only positive timing result does not survive regeneration on the current expanded top-5 basket plus Mar-Apr holdout.

## Recommended next implementation

1. Keep market-neutral pair/basket trading behind a hard no-trade gate. Do not report it as profitable unless gate_pass_pairs > 0 and the gated test result is positive.

2. Promote the fixed-bps XLK-only timing candidate, if present, to the robust-alpha suite and run controls: sign flip, always-long/short, circular shifts, 1-minute latency, and 1x/2x/3x/4x cost stress.

3. Replace symmetric z-score timing with fixed-bps roll-centered thresholds when the signal bucket curve is non-monotone. This follows the same robustness logic as simple basket-trading systems: prefer stable parameter islands to single best points.

4. Treat passive entry only as a stress case unless adverse selection and fill probability are calibrated from quote/trade data.

5. If no active rule passes these screens, the final strategy is no-trade. That is a valid non-losing policy and a defensible research conclusion.
