# Robust XLK Optimization Memo

Test start: `2026-03-01`.

## Selected decision

   decision                                                                             selected_strategy                               reason  train_net_bps  test_net_bps  benchmark_no_trade_train_bps  benchmark_no_trade_test_bps  economic_label
active_rule xlk_only_timing_micro_conf_0.5_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180 passed train-only robustness filters     335.687696    -202.21372                           0.0                          0.0 XLK-only timing

## Top train-selected rules

```
                                                                                             strategy                family      signal_view              subset threshold_mode center_mode  entry  exit_band  hedge_fraction  orientation  train_trades  train_net_bps  train_month_positive_rate  fold_positive_rate  test_trades  test_net_bps  final_train_selection_score
        xlk_only_timing_micro_conf_0.5_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing   micro_conf_0.5      NVDA AAPL MSFT         zscore        mean    3.0        0.5             0.0            1          54.0     335.687696                        0.5                0.75         16.0   -202.213720                   358.642331
                   xlk_only_timing_mid_ridge_pos_k4_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing              mid NVDA AAPL MSFT AVGO         zscore        mean    3.0        0.5             0.0            1          48.0     290.225636                        0.5                0.75         10.0   -352.651210                   322.757072
        xlk_only_timing_micro_conf_0.5_ridge_pos_k4_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing   micro_conf_0.5 NVDA AAPL MSFT AVGO         zscore        mean    3.0        0.5             0.0            1          48.0     292.008035                        0.5                0.75          8.0   -260.326394                   320.401320
                   xlk_only_timing_mid_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing              mid      NVDA AAPL MSFT         zscore        mean    3.0        0.5             0.0            1          54.0     244.583109                        0.4                0.75         18.0   -224.160164                   237.055245
  partial_or_full_hedge_micro_conf_0.5_ridge_pos_k3_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge   micro_conf_0.5      NVDA AAPL MSFT         zscore        mean    3.0        0.5             1.0            1          54.0     108.594090                        0.5                0.75         16.0   -173.446712                   142.958471
      xlk_only_timing_micro_shrink_0.5_ridge_pos_k4_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing micro_shrink_0.5 NVDA AAPL MSFT AVGO         zscore        mean    3.0        0.5             0.0            1          40.0     143.405377                        0.4                0.50         14.0   -304.881635                    98.360608
             partial_or_full_hedge_mid_ridge_pos_k3_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge              mid      NVDA AAPL MSFT         zscore        mean    3.0        0.5             1.0            1          54.0      61.066464                        0.3                0.75         18.0   -189.462372                    70.850160
  partial_or_full_hedge_micro_conf_0.5_ridge_pos_k4_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge   micro_conf_0.5 NVDA AAPL MSFT AVGO         zscore        mean    3.0        0.5             1.0            1          48.0      39.360053                        0.4                0.75          8.0   -211.354584                    57.198896
             partial_or_full_hedge_mid_ridge_pos_k4_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge              mid NVDA AAPL MSFT AVGO         zscore        mean    3.0        0.5             1.0            1          48.0      40.703710                        0.4                0.50         10.0   -246.835636                    48.237401
partial_or_full_hedge_micro_shrink_0.5_ridge_pos_k4_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge micro_shrink_0.5 NVDA AAPL MSFT AVGO         zscore        mean    3.0        0.5             1.0            1          40.0      11.645760                        0.2                0.50         14.0   -202.087428                    10.568073
      xlk_only_timing_micro_shrink_0.5_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing micro_shrink_0.5      NVDA AAPL MSFT         zscore        mean    3.0        0.5             0.0            1          58.0      28.845966                        0.4                0.50         16.0   -143.946193                   -47.346045
partial_or_full_hedge_micro_shrink_0.5_ridge_pos_k3_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge micro_shrink_0.5      NVDA AAPL MSFT         zscore        mean    3.0        0.5             1.0            1          58.0     -35.429422                        0.4                0.75         16.0   -150.543658                   -85.757818
```

## How to read this

The suite distinguishes **market-neutral ETF-basket arbitrage** from **XLK-only timing**.  If the selected rule has `hedge_fraction = 0`, it is a timing strategy that executes only XLK; it should not be marketed as a hedged ETF arbitrage.  If `hedge_fraction > 0`, it trades the residual and pays basket-side spread costs.

The optimizer selects only from train-period evidence.  March/test P&L is reported afterward.  Keep `no_trade` as the decision if no active rule passes train net, fold stability, monthly stability, trade-count, and parameter-family filters.

## Sanity controls

```
                    control  train_net_bps  test_net_bps  test_trades  test_avg_abs_position
                   selected     335.687696   -202.213720         16.0               0.072844
                  sign_flip    -595.832732    170.693635         16.0               0.072844
         active_always_long     160.076149     81.079679         16.0               0.072844
        active_always_short    -420.221184   -112.599763         16.0               0.072844
        circular_shift_mean            NaN   -251.459990          NaN                    NaN
         circular_shift_p95            NaN   -125.148201          NaN                    NaN
selected_vs_circular_pvalue            NaN      0.336634          NaN                    NaN
```

## Cost sensitivity

```
 cost_multiplier sample   gross_bps   cost_bps     net_bps
             1.0  train  465.760214 130.072518  335.687696
             1.0   test -186.453678  15.760042 -202.213720
             1.5  train  465.760214 195.108777  270.651438
             1.5   test -186.453678  23.640063 -210.093741
             2.0  train  465.760214 260.145036  205.615179
             2.0   test -186.453678  31.520085 -217.973762
             3.0  train  465.760214 390.217553   75.542661
             3.0   test -186.453678  47.280127 -233.733805
             4.0  train  465.760214 520.290071  -54.529857
             4.0   test -186.453678  63.040169 -249.493847
```
