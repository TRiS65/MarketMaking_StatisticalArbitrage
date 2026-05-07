# Microstructure Signal Refinement

Lecture-driven features: basket premium, quote imbalance, signed order-flow proxy, spread state, realized volatility, and Kyle-style liquidity proxy. The model is trained on train only; threshold is selected on validation.

## Selection

| decision   | reason                                              |   horizon_min |   top_n | basket_symbols         |   threshold_pred_bps |   edge_mult |   train_net_bps |   validation_net_bps |   test_net_bps |   test_trades |
|:-----------|:----------------------------------------------------|--------------:|--------:|:-----------------------|---------------------:|------------:|----------------:|---------------------:|---------------:|--------------:|
| no_trade   | no validation-positive threshold with enough trades |            60 |       5 | NVDA AAPL MSFT AVGO MU |                   12 |         2.5 |        -14.9009 |             -213.331 |          -47.3 |            40 |

## Controls

| control             |   train_gross_bps |   train_cost_bps |   train_net_bps |   train_trades |   train_avg_abs_position |   validation_gross_bps |   validation_cost_bps |   validation_net_bps |   validation_trades |   validation_avg_abs_position |   test_gross_bps |   test_cost_bps |   test_net_bps |   test_trades |   test_avg_abs_position |
|:--------------------|------------------:|-----------------:|----------------:|---------------:|-------------------------:|-----------------------:|----------------------:|---------------------:|--------------------:|------------------------------:|-----------------:|----------------:|---------------:|--------------:|------------------------:|
| selected            |           89.1289 |           104.03 |        -14.9009 |             42 |               0.00112039 |               -15.7169 |               197.614 |             -213.331 |                 138 |                     0.0189741 |          15.8443 |         63.1443 |       -47.3    |            40 |              0.00220202 |
| sign_flip           |          -89.1289 |           104.03 |       -193.159  |             42 |               0.00112039 |                15.7169 |               197.614 |             -181.897 |                 138 |                     0.0189741 |         -15.8443 |         63.1443 |       -78.9887 |            40 |              0.00220202 |
| active_always_long  |          -89.1289 |           104.03 |       -193.159  |             42 |               0.00112039 |                15.7169 |               197.614 |             -181.897 |                 138 |                     0.0189741 |         -15.8443 |         63.1443 |       -78.9887 |            40 |              0.00220202 |
| active_always_short |           89.1289 |           104.03 |        -14.9009 |             42 |               0.00112039 |               -15.7169 |               197.614 |             -213.331 |                 138 |                     0.0189741 |          15.8443 |         63.1443 |       -47.3    |            40 |              0.00220202 |

## Top Coefficients

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