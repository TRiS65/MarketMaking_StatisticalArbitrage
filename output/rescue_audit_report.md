# Narrow Rescue Audit

This audit deliberately avoids broad parameter fishing.  It asks whether the remaining gross-positive pair candidates or a pre-defined no-short-into-uptrend timing rule deserve future event-level execution work.

## Pair Rescue Gate

| pair     | stock   | spread_type               |   clipped_last_trade_proxy |   exact_bidask_latency0 |   exact_bidask_latency1 |   exact_bidask_latency2 |   exact_bidask_latency5 | passes_rescue_gate   |
|:---------|:--------|:--------------------------|---------------------------:|------------------------:|------------------------:|------------------------:|------------------------:|:---------------------|
| XLK-AAPL | AAPL    | cum_residual_return       |                   182.428  |               26.1241   |                 1.47078 |                 17.9499 |                -33.3729 | True                 |
| XLK-AMD  | AMD     | direct_log_price          |                   383.041  |               14.5303   |              -266.992   |               -281.238  |               -308.303  | False                |
| XLK-INTC | INTC    | direct_log_price          |                    67.6262 |               -0.627441 |                17.8539  |                 10.5722 |                -10.6224 | False                |
| XLK-PLTR | PLTR    | price_regression_residual |                   244.593  |               -2.24894  |              -143.842   |               -280.088  |               -365.548  | False                |

A pair passes only if exact bid/ask latency-0, exact bid/ask latency-1, and clipped last-trade proxy are all positive in the metadata test window.

## Trade Concentration

| pair     | stock   | spread_type               |   entry_z |   exit_z | execution_scenario    |   test_trade_segments |   top5_abs_net_share |   largest_trade_net_bps |
|:---------|:--------|:--------------------------|----------:|---------:|:----------------------|----------------------:|---------------------:|------------------------:|
| XLK-AMD  | AMD     | direct_log_price          |       1   |      0.5 | exact_bidask_latency0 |                    41 |             0.492405 |                -470.416 |
| XLK-PLTR | PLTR    | price_regression_residual |       1   |      0.5 | exact_bidask_latency0 |                    34 |             0.493339 |                -751.532 |
| XLK-AAPL | AAPL    | cum_residual_return       |       2   |      0   | exact_bidask_latency0 |                    22 |             0.587233 |                -264.82  |
| XLK-INTC | INTC    | direct_log_price          |       2.5 |      0.5 | exact_bidask_latency0 |                     6 |             0.942187 |                -218.723 |

## No-Short-Into-Uptrend Audit

| selection_type             | decision        | reason                                                                   | strategy                                         | state_kind      |   lookback_min |   trend_threshold_bps |   train_net_bps |   validation_net_bps |   test_net_bps |   test_2x_cost_net_bps |   mar_net_bps |   apr_net_bps |
|:---------------------------|:----------------|:-------------------------------------------------------------------------|:-------------------------------------------------|:----------------|---------------:|----------------------:|----------------:|---------------------:|---------------:|-----------------------:|--------------:|--------------:|
| walk_forward_selected      | no_trade        | No no-short-into-uptrend rule passed train/validation filters.           | nan                                              | nan             |            nan |                   nan |          nan    |             nan      |       nan      |                nan     |      nan      |     nan       |
| test_oracle_not_selectable | diagnostic_only | best test row shown only to measure possible shape; not honest selection | short_uptrend_multi_day_trend_lb3900_thr200_flat | multi_day_trend |           3900 |                   200 |        -3268.65 |              24.5423 |       -37.7115 |               -277.449 |      -32.4045 |      -5.30695 |
| predefined_reference       | diagnostic_only | predefined no-short stress row                                           | short_uptrend_multi_day_trend_lb780_thr0_flat    | multi_day_trend |            780 |                     0 |        -3797.6  |             -18.5898 |      -302.4    |               -642.944 |     -108.819  |    -193.582   |
| predefined_reference       | diagnostic_only | predefined no-short stress row                                           | short_uptrend_multi_day_trend_lb780_thr50_flat   | multi_day_trend |            780 |                    50 |        -3834.25 |              16.7435 |      -534.291  |              -1018.5   |      -54.2383 |    -480.053   |
| predefined_reference       | diagnostic_only | predefined no-short stress row                                           | short_uptrend_multi_day_trend_lb390_thr50_flat   | multi_day_trend |            390 |                    50 |        -4401.37 |              51.2748 |      -940.532  |              -1463.16  |       61.561  |   -1002.09    |
| predefined_reference       | diagnostic_only | predefined no-short stress row                                           | short_uptrend_intraday_trend_lb120_thr25_flat    | intraday_trend  |            120 |                    25 |        -5110.47 |            -174.956  |     -1403.33   |              -2261.63  |     -117.027  |   -1286.31    |
| predefined_reference       | diagnostic_only | predefined no-short stress row                                           | short_uptrend_multi_day_trend_lb390_thr0_flat    | multi_day_trend |            390 |                     0 |        -5136.82 |            -230.824  |      -956.93   |              -1598.53  |     -145.042  |    -811.888   |
| predefined_reference       | diagnostic_only | predefined no-short stress row                                           | short_uptrend_intraday_trend_lb120_thr0_flat     | intraday_trend  |            120 |                     0 |        -6100.82 |             -22.1015 |     -1409.26   |              -2362.22  |     -295.843  |   -1113.42    |
| predefined_reference       | diagnostic_only | predefined no-short stress row                                           | short_uptrend_intraday_trend_lb60_thr25_flat     | intraday_trend  |             60 |                    25 |        -6132.1  |            -154.474  |     -1508.49   |              -2463.57  |     -333.46   |   -1175.03    |
| predefined_reference       | diagnostic_only | predefined no-short stress row                                           | short_uptrend_intraday_trend_lb60_thr0_flat      | intraday_trend  |             60 |                     0 |        -8997.7  |            -214.267  |     -1657.43   |              -2793.21  |     -604.955  |   -1052.47    |

## Interpretation

These are not final alpha claims.  If no row passes the rescue gate, the final policy remains no-trade.  If a row passes, the next step is raw-event validation around its actual signal timestamps, not another wider parameter grid.