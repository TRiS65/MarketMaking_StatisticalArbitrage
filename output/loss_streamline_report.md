# Loss Streamline Report

## Executive decision

| research_path                       | evidence_tier                | policy_role                  | decision                     | selected_trading_policy   | reason                                                                                                                                             |   train_or_validation_net_bps |   test_net_bps |   raw_test_net_bps_before_gate |
|:------------------------------------|:-----------------------------|:-----------------------------|:-----------------------------|:--------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------:|---------------:|-------------------------------:|
| market_neutral_pair_or_basket       | final_12m_evidence           | selected_no_trade_policy     | no_trade                     | no_trade                  | validation-selected active pair/basket rules fail no-trade gate or lose after costs                                                                |                        nan    |           0    |                      -51353.3  |
| robust_alpha_suite_selected         | final_12m_evidence           | selected_no_trade_policy     | no_trade                     | no_trade                  | selected robust-alpha rule loses OOS or does not beat no-trade                                                                                     |                        335.69 |        -202.21 |                        -202.21 |
| fixed_bps_xlk_only_timing_candidate | legacy_candidate_screen      | not_policy_eligible          | legacy_candidate_shape_only  | not_selected_for_trading  | legacy profit-search output is Jan-Feb positive, but it predates finaldata top-20 controls and is not final evidence                               |                        456.48 |         613.35 |                         613.35 |
| finaldata_fixed_bps_xlk_only_timing | final_12m_evidence           | selected_no_trade_policy     | no_trade                     | no_trade                  | train_or_validation_net<=0;test_net<=0;2x_cost_test<=0;latency1_test<=0;does_not_beat_directional_control;sign_flip_not_worse;circular_pvalue>0.10 |                      -2572.04 |        -977.24 |                        -977.24 |
| timing_robustness_current_selection | final_12m_evidence           | selected_no_trade_policy     | no_trade                     | no_trade                  | No XLK-only timing rule passed train/validation filters.                                                                                           |                          0    |           0    |                           0    |
| named_timing_candidate_micro075_e60 | final_12m_evidence           | selected_no_trade_policy     | no_trade                     | no_trade                  | named candidate audited on current top-5 basket with metadata test                                                                                 |                      -2695.47 |        -894.79 |                        -894.79 |
| regime_gated_timing_repair          | diagnostic_only_overlay      | diagnostic_not_tradeable     | no_trade                     | not_selected_for_trading  | Selected on train/validation only; test is holdout audit. Script label: diagnostic_only.                                                           |                         79.63 |        -131.36 |                        -131.36 |
| regime_classifier_timing            | diagnostic_only_overlay      | diagnostic_not_tradeable     | no_trade                     | not_selected_for_trading  | selected on metadata validation only; test is holdout. Script label: diagnostic_only.                                                              |                        104.32 |        -271.67 |                        -271.67 |
| markowitz_ac_monetization           | final_12m_evidence           | selected_no_trade_policy     | no_trade                     | no_trade                  | train/validation-selected monetization portfolio loses test or fails drawdown/execution stress. Script label: no_trade.                            |                        526.14 |        -712.26 |                        -712.26 |
| narrow_pair_rescue_audit            | future_event_audit_candidate | future_work_not_final_policy | future_event_audit_candidate | not_selected_for_trading  | minimal pair rescue gate checks only whether a gross-positive pair deserves raw-event validation; not policy-eligible final evidence               |                        nan    |          26.12 |                         182.43 |
| no_short_uptrend_rescue_audit       | diagnostic_only_overlay      | diagnostic_not_tradeable     | no_trade                     | not_selected_for_trading  | No no-short-into-uptrend rule passed train/validation filters.                                                                                     |                        nan    |         nan    |                         nan    |

**Actual selected trading policy:** `no_trade`. Legacy positive screens and diagnostic overlays are not policy-eligible final evidence.

## 1. Market-neutral / pair-trading PnL attribution

| method         |   selected_pairs |   gate_pass_pairs |   raw_validation_net_bps |   raw_test_net_bps |   raw_test_net_per_trade_bps |   raw_positive_test_pairs |   gate_test_net_bps |   test_trades |
|:---------------|-----------------:|------------------:|-------------------------:|-------------------:|-----------------------------:|--------------------------:|--------------------:|--------------:|
| baseline       |               20 |                 0 |                 -1359.79 |          -14635.7  |                        -5.14 |                         0 |                   0 |          2848 |
| coint_filter   |                3 |                 0 |                  -250.23 |            -837.03 |                        -2.6  |                         0 |                   0 |           322 |
| combined       |                3 |                 0 |                  -185.59 |            -979.44 |                        -4.49 |                         0 |                   0 |           218 |
| kalman_lagged  |               20 |                 0 |                 -3643.45 |          -12823.4  |                        -4.92 |                         0 |                   0 |          2609 |
| passive_stress |               20 |                 0 |                   421    |           -9767.92 |                        -3.32 |                         0 |                   0 |          2943 |
| sscore_ou_gate |               20 |                 0 |                 -2270.74 |          -12309.9  |                        -4.9  |                         0 |                   0 |          2513 |

Interpretation: if gate_test_net_bps is zero, the economically selected policy is no-trade. Negative raw_test_net_bps indicates that model filters reduce losses but do not create tradable alpha.

## 2. Exit-reason attribution

| sample     | exit_reason   |   trades |   gross_bps |   cost_bps |    net_bps |   net_per_trade_bps |
|:-----------|:--------------|---------:|------------:|-----------:|-----------:|--------------------:|
| test       | reversion     |     7301 |    85032    |   27127    |   57905    |                7.93 |
| test       | stop_loss     |     1872 |    -8500.41 |    5944.13 |  -14444.5  |               -7.72 |
| test       | eod           |    10788 |    -9659.69 |   37778.5  |  -47438.2  |               -4.4  |
| test       | max_hold      |    29542 |     2685.67 |   84236.9  |  -81551.2  |               -2.76 |
| train      | reversion     |    35924 |   334140    |  164990    |  169150    |                4.71 |
| train      | eod           |    33474 |    66647.6  |  126953    |  -60305.3  |               -1.8  |
| train      | stop_loss     |    32436 |  -105663    |  126096    | -231759    |               -7.15 |
| train      | max_hold      |    86963 |    -6561.76 |  248357    | -254919    |               -2.93 |
| validation | reversion     |     2729 |    33648.3  |    9341.57 |   24306.7  |                8.91 |
| validation | eod           |     2948 |     5033.94 |   14015.5  |   -8981.57 |               -3.05 |
| validation | stop_loss     |     5536 |    -8100.11 |   16982.5  |  -25082.6  |               -4.53 |
| validation | max_hold      |    10575 |     2334.24 |   27489.2  |  -25154.9  |               -2.38 |

Interpretation: profitable reversion exits combined with negative max-hold / stop-loss / EOD exits usually means entry thresholds are too loose and residuals do not revert quickly enough.

## 3. Robust-alpha selected rule

Selected strategy: `xlk_only_timing_micro_conf_0.5_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180`
Train net: 335.69 bps; test net: -202.21 bps.
Test gross/cost: -186.45 / 15.76 bps; break-even cost multiplier: -11.831x.
Always-long control test net: 81.08 bps. If this is close to or better than selected, timing alpha is not established.
Circular-shift p-value proxy: 0.337.

## 4. Fixed-bps XLK-only timing candidate audit

Expanded top-20 regeneration:

| decision   | reason                                                                                                                                             | basket_symbols         |   train_net_bps |   validation_net_bps |   test_net_bps |   test_2x_cost_net_bps |   test_latency1_net_bps |   circular_pvalue |
|:-----------|:---------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------|----------------:|---------------------:|---------------:|-----------------------:|------------------------:|------------------:|
| no_trade   | train_or_validation_net<=0;test_net<=0;2x_cost_test<=0;latency1_test<=0;does_not_beat_directional_control;sign_flip_not_worse;circular_pvalue>0.10 | NVDA AAPL MSFT AVGO MU |        -2572.04 |               -45.13 |        -977.24 |               -1211.91 |                -1034.28 |              0.66 |

Legacy profit-search screen:

| protocol       | hedge   | signal_price   | signal_kind   |   hedge_frac |   threshold_bps |   exit_bps |   max_hold |   jan_net_bps |   feb_net_bps |   train_net_bps |   test_net_bps |   test_gross_per_trade_bps |   test_cost_per_trade_bps |   test_net_per_trade_bps |   test_cost_capacity_x |   candidate_train_gate |
|:---------------|:--------|:---------------|:--------------|-------------:|----------------:|-----------:|-----------:|--------------:|--------------:|----------------:|---------------:|---------------------------:|--------------------------:|-------------------------:|-----------------------:|-----------------------:|
| jan_best       | sparse5 | micro          | roll_center   |            0 |              50 |         25 |        390 |        289.64 |        166.84 |          456.48 |         613.35 |                      14.03 |                       3.8 |                    10.22 |                   3.69 |                      1 |
| train_best     | sparse5 | micro          | roll_center   |            0 |              50 |         25 |        390 |        289.64 |        166.84 |          456.48 |         613.35 |                      14.03 |                       3.8 |                    10.22 |                   3.69 |                      1 |
| robust_jan_feb | sparse5 | micro          | roll_center   |            0 |              50 |         25 |        390 |        289.64 |        166.84 |          456.48 |         613.35 |                      14.03 |                       3.8 |                    10.22 |                   3.69 |                      1 |
| march_oracle   | sparse5 | micro          | raw           |            0 |              50 |          0 |        390 |         82.99 |        158.68 |          241.67 |         652.23 |                      18.47 |                       3.3 |                    15.17 |                   5.6  |                      0 |

Interpretation: a positive fixed-bps timing candidate is not the same as market-neutral arbitrage. The existing profit-search file is treated as a legacy candidate screen unless it is regenerated on the finaldata top-20 sample. It should be promoted only if it passes sign-flip, always-long/short, circular-shift, latency, and cost-multiplier stress tests on the current data.

## 5. Signal-bucket regime check

| sample     |   horizon_min |   linear_slope_bps_per_decile |   decile0_future_bps |   decile9_future_bps |   best_decile |   best_decile_future_bps |
|:-----------|--------------:|------------------------------:|---------------------:|---------------------:|--------------:|-------------------------:|
| test       |             1 |                         -0.02 |                 0.4  |                -0.23 |             0 |                     0.4  |
| test       |             5 |                         -0.06 |                 1.86 |                -0.93 |             0 |                     1.86 |
| test       |            15 |                         -0.06 |                 4.79 |                -2.43 |             0 |                     4.79 |
| test       |            30 |                          0.03 |                 8.65 |                -4.7  |             7 |                     9.46 |
| test       |            60 |                          0.21 |                15.21 |                -7.6  |             7 |                    17.52 |
| train      |             1 |                         -0.01 |                 0.03 |                 0.02 |             1 |                     0.12 |
| train      |             5 |                         -0.01 |                 0.02 |                 0.27 |             1 |                     0.68 |
| train      |            15 |                         -0.02 |                 0.18 |                 0.77 |             1 |                     1.8  |
| train      |            30 |                         -0.03 |                 0.22 |                 1.39 |             1 |                     3.33 |
| train      |            60 |                         -0.05 |                 0.56 |                 2.98 |             1 |                     5.47 |
| validation |             1 |                         -0    |                -0.42 |                -0.67 |             6 |                     0.28 |
| validation |             5 |                          0.01 |                -1.56 |                -2.81 |             6 |                     2.21 |
| validation |            15 |                          0.02 |                -3.76 |                -7.32 |             6 |                     6.7  |
| validation |            30 |                         -0    |                -6.09 |               -12.82 |             6 |                    13.25 |
| validation |            60 |                         -0.09 |               -11.99 |               -20.55 |             6 |                    14.41 |

Interpretation: a non-monotone or sign-flipping decile curve means the signal should not be traded as a symmetric z-score. Prefer fixed-bps thresholds, asymmetric tails, or a no-trade gate.

## 6. Current timing robustness / named candidate audit

Current train/validation-selected timing decision:

| decision   | reason                                                   |   train_net_bps |   validation_net_bps |   test_net_bps |
|:-----------|:---------------------------------------------------------|----------------:|---------------------:|---------------:|
| no_trade   | No XLK-only timing rule passed train/validation filters. |               0 |                    0 |              0 |

Named candidate `micro_shrink_0.75_cw10d_e60_x0_mh240` on the current top-5 basket:

| strategy                             | basket_symbols         |   train_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   train_trades |   test_trades |
|:-------------------------------------|:-----------------------|----------------:|--------------:|--------------:|---------------:|---------------:|--------------:|
| micro_shrink_0.75_cw10d_e60_x0_mh240 | NVDA AAPL MSFT AVGO MU |        -2695.47 |        -32.45 |       -862.35 |        -894.79 |            642 |           151 |

Named candidate execution audit:

| execution_model   |   latency_min |   train_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   test_trades |
|:------------------|--------------:|----------------:|--------------:|--------------:|---------------:|--------------:|
| halfspread        |             0 |        -2695.47 |        -32.45 |       -862.35 |        -894.79 |           151 |
| exact_bidask      |             0 |        -2695.46 |        -32.4  |       -862.35 |        -894.76 |           151 |
| exact_bidask      |             1 |        -3283.71 |       -176.54 |       -913.67 |       -1090.22 |           152 |
| exact_bidask      |             2 |        -3422.98 |         88.61 |       -841.82 |        -753.22 |           152 |
| exact_bidask      |             5 |        -2822.45 |        -20.35 |       -866.28 |        -886.63 |           152 |

Interpretation: this resolves the earlier contradiction. The old positive timing result does not survive regeneration on the current final-data top-5 basket plus metadata test holdout.

## 7. Regime-gate repair experiment

Selection table:

| decision        | selected_strategy                              | gate_mode   | state_kind          |   lookback_min |   trend_threshold_bps |   train_net_bps |   validation_net_bps |   test_net_bps |   test_2x_cost_net_bps |
|:----------------|:-----------------------------------------------|:------------|:--------------------|---------------:|----------------------:|----------------:|---------------------:|---------------:|-----------------------:|
| diagnostic_only | two_sided_premium_persistence_lb780_thr75_flat | two_sided   | premium_persistence |            780 |                    75 |           79.63 |               280.21 |        -131.36 |                -210.74 |

Monthly side anatomy for baseline, side-only diagnostics, and selected/best gates:

| strategy              | month   |   gross_bps |   cost_bps |   net_bps |   long_gross_bps |   short_gross_bps |   long_minutes |   short_minutes |
|:----------------------|:--------|------------:|-----------:|----------:|-----------------:|------------------:|---------------:|----------------:|
| baseline_no_gate      | 2025-05 |     -454.11 |     215.03 |   -669.14 |           126.31 |           -580.41 |           3094 |            3408 |
| baseline_no_gate      | 2025-06 |       26.5  |     237.26 |   -210.76 |           153.88 |           -127.38 |            384 |            6935 |
| baseline_no_gate      | 2025-07 |       37.46 |     246.5  |   -209.04 |             0    |             37.46 |              0 |            7741 |
| baseline_no_gate      | 2025-08 |      100.11 |     168.66 |    -68.56 |            46.38 |             53.72 |           3386 |            2428 |
| baseline_no_gate      | 2025-09 |      195.42 |     161.28 |     34.13 |           281.73 |            -86.31 |           1922 |            4603 |
| baseline_no_gate      | 2025-10 |      456.82 |     273.97 |    182.85 |            61.69 |            395.13 |            317 |            7978 |
| baseline_no_gate      | 2025-11 |       12.46 |     353.52 |   -341.06 |           -90.13 |            102.6  |           3062 |            2772 |
| baseline_no_gate      | 2025-12 |     -961.78 |     285.37 |  -1247.15 |          -567.94 |           -393.85 |           4643 |            3426 |
| baseline_no_gate      | 2026-01 |      -22.72 |     144.01 |   -166.74 |          -171.26 |            148.54 |            627 |            4973 |
| baseline_no_gate      | 2026-02 |      167.89 |     143.35 |     24.54 |           -29.75 |            197.64 |           3852 |            2861 |
| baseline_no_gate      | 2026-03 |      156.57 |     188.97 |    -32.4  |           101.57 |             55    |           4216 |            3046 |
| baseline_no_gate      | 2026-04 |     -724.16 |     138.2  |   -862.35 |           126.88 |           -851.04 |           1010 |            6420 |
| long_only_diagnostic  | 2025-05 |      126.31 |      83.46 |     42.84 |           126.31 |              0    |           3094 |               0 |
| long_only_diagnostic  | 2025-06 |      153.88 |      16.58 |    137.29 |           153.88 |              0    |            384 |               0 |
| long_only_diagnostic  | 2025-07 |        0    |       0    |      0    |             0    |              0    |              0 |               0 |
| long_only_diagnostic  | 2025-08 |       46.38 |      83.26 |    -36.87 |            46.38 |              0    |           3386 |               0 |
| long_only_diagnostic  | 2025-09 |      281.73 |      56.09 |    225.64 |           281.73 |              0    |           1922 |               0 |
| long_only_diagnostic  | 2025-10 |       61.69 |       2.47 |     59.22 |            61.69 |              0    |            317 |               0 |
| long_only_diagnostic  | 2025-11 |      -90.13 |     199.04 |   -289.17 |           -90.13 |              0    |           3062 |               0 |
| long_only_diagnostic  | 2025-12 |     -567.94 |     170.01 |   -737.95 |          -567.94 |              0    |           4643 |               0 |
| long_only_diagnostic  | 2026-01 |     -171.26 |      30.37 |   -201.64 |          -171.26 |              0    |            627 |               0 |
| long_only_diagnostic  | 2026-02 |      -29.75 |     106.54 |   -136.3  |           -29.75 |              0    |           3852 |               0 |
| long_only_diagnostic  | 2026-03 |      101.57 |     142    |    -40.43 |           101.57 |              0    |           4216 |               0 |
| long_only_diagnostic  | 2026-04 |      126.88 |      24.26 |    102.62 |           126.88 |              0    |           1010 |               0 |
| short_only_diagnostic | 2025-05 |     -580.41 |     131.57 |   -711.98 |             0    |           -580.41 |              0 |            3408 |
| short_only_diagnostic | 2025-06 |     -127.38 |     220.67 |   -348.05 |             0    |           -127.38 |              0 |            6935 |
| short_only_diagnostic | 2025-07 |       37.46 |     246.5  |   -209.04 |             0    |             37.46 |              0 |            7741 |
| short_only_diagnostic | 2025-08 |       53.72 |      85.41 |    -31.69 |             0    |             53.72 |              0 |            2428 |
| short_only_diagnostic | 2025-09 |      -86.31 |     105.19 |   -191.5  |             0    |            -86.31 |              0 |            4603 |
| short_only_diagnostic | 2025-10 |      395.13 |     271.51 |    123.62 |             0    |            395.13 |              0 |            7978 |

Interpretation: premium-persistence gates can reduce the April short-side blow-up, but the train/validation-selected gate still does not produce positive test net after a 2x cost buffer. Side-only diagnostics show the regime flip directly: short exposure helps in some earlier months but fails badly in April, while long-only helps April but fails in train. This supports a no-trade policy until a regime classifier is validated on a later holdout.

## 8. Supervised regime classifier

Selection table:

| decision        | selected_strategy                  | train_scheme   | model_name   |   horizon_min |   confidence |   validation_net_bps |   mar_net_bps |   apr_net_bps |   test_net_bps |   test_2x_cost_net_bps |   latency1_test_net_bps |
|:----------------|:-----------------------------------|:---------------|:-------------|--------------:|-------------:|---------------------:|--------------:|--------------:|---------------:|-----------------------:|------------------------:|
| diagnostic_only | train_all_rf_depth4_h60_edge5_p0.4 | train_all      | rf_depth4    |            60 |          0.4 |               104.32 |        -18.53 |       -253.14 |        -271.67 |                -931.31 |                 -162.03 |

Controls:

| control                        |   validation_net_bps |   test_net_bps |   test_trades |
|:-------------------------------|---------------------:|---------------:|--------------:|
| selected_classifier            |               104.32 |        -271.67 |           480 |
| sign_flip                      |              -375.31 |       -1047.55 |           480 |
| classifier_active_always_long  |               -39.63 |        -574.76 |           480 |
| classifier_active_always_short |              -231.37 |        -744.46 |           480 |

Interpretation: the classifier is allowed to choose mean-reversion, trend-continuation, or no-trade, but it still fails the metadata test holdout. The selected classifier is validation-positive, yet test net is negative and cost/latency stress is worse. Therefore the regime idea remains a research direction, not a tradable rule.

## 9. Markowitz / Almgren-Chriss monetization optimizer

Selection table:

| decision   | reason                                                                                         | candidate_set     |   spread_fraction |   participation_rate |   execution_horizon_min |   active_signals |   gross_leverage |   train_net_bps |   validation_net_bps |   test_net_bps |   test_max_drawdown_bps |   test_last_trade_proxy_bps |
|:-----------|:-----------------------------------------------------------------------------------------------|:------------------|------------------:|---------------------:|------------------------:|-----------------:|-----------------:|----------------:|---------------------:|---------------:|------------------------:|----------------------------:|
| no_trade   | train/validation-selected monetization portfolio loses test or fails drawdown/execution stress | liquid_validation |              0.25 |                    0 |                       1 |                3 |                1 |          743.62 |               526.14 |        -712.26 |                -1393.79 |                     -625.26 |

Selected strategy weights:

| signal_id                                 | stock   | spread_type               |   median_stock_spread_bps |   train_half_life_minutes |   weight |
|:------------------------------------------|:--------|:--------------------------|--------------------------:|--------------------------:|---------:|
| MSFT_price_regression_residual_e1.5_x0.5  | MSFT    | price_regression_residual |                    5.8622 |                   3347.22 |     0.35 |
| AVGO_price_regression_residual_e1.0_x0.5  | AVGO    | price_regression_residual |                   10.1609 |                  19803.3  |     0.35 |
| APH_price_regression_residual_e1.0_x0.0   | APH     | price_regression_residual |                    8.2512 |                  12304.1  |     0.3  |
| QCOM_direct_log_price_e1.25_x0.0          | QCOM    | direct_log_price          |                   10.1143 |                  21644    |     0    |
| CSCO_price_regression_residual_e1.0_x0.0  | CSCO    | price_regression_residual |                    2.3164 |                   7391.23 |     0    |
| INTC_price_regression_residual_e1.0_x0.0  | INTC    | price_regression_residual |                    4.315  |                  10856.2  |     0    |
| MU_price_regression_residual_e1.25_x0.5   | MU      | price_regression_residual |                    8.9639 |                   7607.93 |     0    |
| LRCX_price_regression_residual_e1.0_x0.0  | LRCX    | price_regression_residual |                    9.4462 |                   7924.15 |     0    |
| AAPL_price_regression_residual_e1.25_x0.5 | AAPL    | price_regression_residual |                    2.5468 |                  15909.5  |     0    |
| AAPL_direct_log_price_e1.0_x0.25          | AAPL    | direct_log_price          |                    2.5468 |                  23563.9  |     0    |
| QCOM_price_regression_residual_e1.0_x0.5  | QCOM    | price_regression_residual |                   10.1143 |                  18868.4  |     0    |
| AVGO_direct_log_price_e1.0_x0.5           | AVGO    | direct_log_price          |                   10.1609 |                  23638.3  |     0    |

Top validation frontier rows:

| candidate_set     |   spread_fraction |   participation_rate |   execution_horizon_min |   markowitz_gamma |   active_signals |   gross_leverage |   train_net_bps |   validation_net_bps |   test_net_bps |   test_max_drawdown_bps |
|:------------------|------------------:|---------------------:|------------------------:|------------------:|-----------------:|-----------------:|----------------:|---------------------:|---------------:|------------------------:|
| liquid_validation |              0.25 |                 0    |                       1 |                 0 |                3 |             1    |          743.62 |               526.14 |        -712.26 |                -1393.79 |
| liquid_validation |              0.25 |                 0    |                       5 |                 0 |                3 |             1    |          216.41 |               520.99 |        -752.34 |                -1311.98 |
| ou_filtered       |              0.25 |                 0    |                       1 |                 0 |                1 |             0.35 |          580.42 |               253.03 |        -340.86 |                 -583.08 |
| ou_filtered       |              0.25 |                 0.01 |                       1 |                 0 |                1 |             0.35 |          438.82 |               245.51 |        -366.51 |                 -602.91 |
| liquid_validation |              0.25 |                 0.01 |                       1 |                 0 |                1 |             0.35 |          438.82 |               245.51 |        -366.51 |                 -602.91 |
| liquid_validation |              0.25 |                 0    |                       1 |                 0 |                3 |             0.38 |          355.93 |               231.43 |        -289.6  |                 -530.1  |
| liquid_validation |              0.25 |                 0.01 |                       1 |                 0 |                1 |             0.35 |          332.72 |               239.87 |        -385.73 |                 -617.78 |
| ou_filtered       |              0.25 |                 0.01 |                       1 |                 0 |                1 |             0.35 |          332.72 |               239.87 |        -385.73 |                 -617.78 |
| ou_filtered       |              0.25 |                 0    |                       5 |                 0 |                1 |             0.35 |          210.26 |               233.36 |        -407.92 |                 -636.17 |
| liquid_validation |              0.25 |                 0.01 |                       5 |                 0 |                1 |             0.35 |           68.66 |               225.84 |        -433.57 |                 -661.47 |
| ou_filtered       |              0.25 |                 0.01 |                       5 |                 0 |                1 |             0.35 |           68.66 |               225.84 |        -433.57 |                 -661.47 |
| ou_filtered       |              0.25 |                 0    |                       1 |                 0 |                1 |             0.17 |          282.05 |               122.96 |        -165.64 |                 -283.34 |

Interpretation: the optimizer confirms the bottleneck is monetization rather than a total absence of prediction. Liquid validation-positive strategy streams can be combined into strongly positive train/validation portfolios, but the selected portfolio loses on the holdout after quoted-spread and AC-style execution buffers. The final policy remains no-trade.

## Recommended next implementation

1. Keep market-neutral pair/basket trading behind a hard no-trade gate. Do not report it as profitable unless gate_pass_pairs > 0 and the gated test result is positive.

2. Promote the fixed-bps XLK-only timing candidate, if present, to the robust-alpha suite and run controls: sign flip, always-long/short, circular shifts, 1-minute latency, and 1x/2x/3x/4x cost stress.

3. Replace symmetric z-score timing with fixed-bps roll-centered thresholds when the signal bucket curve is non-monotone. This follows the same robustness logic as simple basket-trading systems: prefer stable parameter islands to single best points.

4. Treat passive entry only as a stress case unless adverse selection and fill probability are calibrated from quote/trade data.

5. If no active rule passes these screens, the final strategy is no-trade. That is a valid non-losing policy and a defensible research conclusion.
