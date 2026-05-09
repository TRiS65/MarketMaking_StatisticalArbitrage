# Microstructure Signal Refinement

Lecture-driven features: basket premium, quote imbalance, signed order-flow proxy, spread state, realized volatility, and Kyle-style liquidity proxy. The model is trained on train only; threshold is selected on validation.

## Selection

| decision   | reason                                |   horizon_min |   top_n | basket_symbols         |   threshold_pred_bps |   edge_mult |   train_net_bps |   validation_net_bps |   test_net_bps |   test_trades |
|:-----------|:--------------------------------------|--------------:|--------:|:-----------------------|---------------------:|------------:|----------------:|---------------------:|---------------:|--------------:|
| no_trade   | validation-positive but test-negative |            15 |       5 | NVDA AAPL MSFT AVGO MU |                  0.5 |         2.5 |        -346.383 |              9.18517 |       -133.287 |            26 |

## Controls

| control             |   train_gross_bps |   train_cost_bps |   train_net_bps |   train_trades |   train_avg_abs_position |   validation_gross_bps |   validation_cost_bps |   validation_net_bps |   validation_trades |   validation_avg_abs_position |   test_gross_bps |   test_cost_bps |   test_net_bps |   test_trades |   test_avg_abs_position |
|:--------------------|------------------:|-----------------:|----------------:|---------------:|-------------------------:|-----------------------:|----------------------:|---------------------:|--------------------:|------------------------------:|-----------------:|----------------:|---------------:|--------------:|------------------------:|
| selected            |          -28.7396 |          317.644 |        -346.383 |            332 |                0.0024276 |                27.0541 |               17.8689 |              9.18517 |                  36 |                    0.00254453 |         -62.7833 |         70.5041 |     -133.287   |            26 |              0.00081184 |
| sign_flip           |           28.7396 |          317.644 |        -288.904 |            332 |                0.0024276 |               -27.0541 |               17.8689 |            -44.9229  |                  36 |                    0.00254453 |          62.7833 |         70.5041 |       -7.72086 |            26 |              0.00081184 |
| active_always_long  |         -130.317  |          317.644 |        -447.961 |            332 |                0.0024276 |                40.6136 |               17.8689 |             22.7447  |                  36 |                    0.00254453 |          49.8867 |         70.5041 |      -20.6175  |            26 |              0.00081184 |
| active_always_short |          130.317  |          317.644 |        -187.327 |            332 |                0.0024276 |               -40.6136 |               17.8689 |            -58.4825  |                  36 |                    0.00254453 |         -49.8867 |         70.5041 |     -120.391   |            26 |              0.00081184 |

## Top Coefficients

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