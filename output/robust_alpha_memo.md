# Robust XLK Optimization Memo

Test start: `2026-03-01`.

## Selected decision

   decision                                                                  selected_strategy                               reason  train_net_bps  test_net_bps  benchmark_no_trade_train_bps  benchmark_no_trade_test_bps  economic_label
active_rule xlk_only_timing_mid_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180 passed train-only robustness filters     472.545957    -17.725389                           0.0                          0.0 XLK-only timing

## Top train-selected rules

```
                                                                                             strategy                family      signal_view                  subset threshold_mode center_mode  entry  exit_band  hedge_fraction  orientation  train_trades  train_net_bps  train_month_positive_rate  fold_positive_rate  test_trades  test_net_bps  final_train_selection_score
                   xlk_only_timing_mid_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing              mid           NVDA AMD PLTR         zscore        mean    3.0        0.5             0.0            1          14.0     472.545957                       0.50                0.50         10.0    -17.725389                   545.097509
        xlk_only_timing_micro_conf_0.5_ridge_pos_k3_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing   micro_conf_0.5           NVDA AMD PLTR         zscore        mean    3.0        0.5             0.0            1          14.0     457.584644                       0.50                0.50         10.0    -21.624286                   518.711673
      xlk_only_timing_micro_shrink_0.5_ridge_pos_k5_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing micro_shrink_0.5 NVDA AMD PLTR LRCX AMAT         zscore        mean    3.0        0.5             0.0            1          10.0     330.031278                       0.50                0.50          0.0      0.000000                   424.696255
        xlk_only_timing_micro_conf_0.5_ridge_pos_k5_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing   micro_conf_0.5 NVDA AMD PLTR LRCX AMAT         zscore        mean    3.0        0.5             0.0            1           8.0     327.637726                       0.50                0.50          0.0      0.000000                   421.825122
                   xlk_only_timing_mid_ridge_pos_k5_zscore_mean_e3_x0.5_h0_contra_nogate_cw1950_mh180       xlk_only_timing              mid NVDA AMD PLTR LRCX AMAT         zscore        mean    3.0        0.5             0.0            1           8.0     327.637726                       0.50                0.50          0.0      0.000000                   421.825122
partial_or_full_hedge_micro_shrink_0.5_ridge_pos_k5_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge micro_shrink_0.5 NVDA AMD PLTR LRCX AMAT         zscore        mean    3.0        0.5             1.0            1          10.0     115.634371                       0.50                0.50          0.0      0.000000                   168.962805
             partial_or_full_hedge_mid_ridge_pos_k5_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge              mid NVDA AMD PLTR LRCX AMAT         zscore        mean    3.0        0.5             1.0            1           8.0     107.685408                       0.50                0.50          0.0      0.000000                   158.752285
  partial_or_full_hedge_micro_conf_0.5_ridge_pos_k5_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge   micro_conf_0.5 NVDA AMD PLTR LRCX AMAT         zscore        mean    3.0        0.5             1.0            1           8.0     107.487008                       0.50                0.50          0.0      0.000000                   158.486538
             partial_or_full_hedge_mid_ridge_pos_k3_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge              mid           NVDA AMD PLTR         zscore        mean    3.0        0.5             1.0            1          14.0      69.341980                       0.50                0.50         10.0    -44.079902                    99.972634
  partial_or_full_hedge_micro_conf_0.5_ridge_pos_k3_zscore_mean_e3_x0.5_h1_contra_nogate_cw1950_mh180 partial_or_full_hedge   micro_conf_0.5           NVDA AMD PLTR         zscore        mean    3.0        0.5             1.0            1          14.0      41.857721                       0.25                0.25         10.0    -36.276111                    43.466930
     xlk_only_timing_micro_conf_0.5_ridge_pos_k5_fixed_bps_mean_e50_x25_h0_contra_nogate_cw1950_mh180       xlk_only_timing   micro_conf_0.5 NVDA AMD PLTR LRCX AMAT      fixed_bps        mean   50.0       25.0             0.0            1         218.0     179.970474                       0.25                0.25        202.0  -1701.614100                  -406.000965
                xlk_only_timing_mid_ridge_pos_k5_fixed_bps_mean_e50_x25_h0_contra_nogate_cw1950_mh180       xlk_only_timing              mid NVDA AMD PLTR LRCX AMAT      fixed_bps        mean   50.0       25.0             0.0            1         216.0     157.769956                       0.25                0.25        204.0  -1641.074611                  -436.249417
```

## How to read this

The suite distinguishes **market-neutral ETF-basket arbitrage** from **XLK-only timing**.  If the selected rule has `hedge_fraction = 0`, it is a timing strategy that executes only XLK; it should not be marketed as a hedged ETF arbitrage.  If `hedge_fraction > 0`, it trades the residual and pays basket-side spread costs.

The optimizer selects only from train-period evidence.  March/test P&L is reported afterward.  Keep `no_trade` as the decision if no active rule passes train net, fold stability, monthly stability, trade-count, and parameter-family filters.

## Sanity controls

```
                    control  train_net_bps  test_net_bps  test_trades  test_avg_abs_position
                   selected     472.545957    -17.725389         10.0               0.033672
                  sign_flip    -484.458567    -23.471807         10.0               0.033672
         active_always_long     312.151480    -11.460902         10.0               0.033672
        active_always_short    -324.064091    -29.736293         10.0               0.033672
        circular_shift_mean            NaN    -61.697920          NaN                    NaN
         circular_shift_p95            NaN     42.759341          NaN                    NaN
selected_vs_circular_pvalue            NaN      0.243902          NaN                    NaN
```

## Cost sensitivity

```
 cost_multiplier sample  gross_bps  cost_bps    net_bps
             1.0  train 478.502262  5.956305 472.545957
             1.0   test   2.873209 20.598598 -17.725389
             1.5  train 478.502262  8.934458 469.567804
             1.5   test   2.873209 30.897897 -28.024688
             2.0  train 478.502262 11.912610 466.589652
             2.0   test   2.873209 41.197195 -38.323986
             3.0  train 478.502262 17.868916 460.633347
             3.0   test   2.873209 61.795793 -58.922584
             4.0  train 478.502262 23.825221 454.677041
             4.0   test   2.873209 82.394391 -79.521182
```
