# Professor Feedback Robustness Memo

This run answers the main TAQ methodology questions raised in feedback:

- `r_XLK,t` is one-minute log return, not price.
- The old residual spread is compared against direct log-price spread and log-price regression residual.
- Gross/no-cost P&L is separated from 0.25-spread, 0.50-spread, and clipped last-trade execution proxies.
- OU/Avellaneda-Lee style diagnostics are reported as ADF p-value, half-life, equilibrium sigma, and s-score scale.

Best validation-selected test rows under the 0.25-spread scenario:

| pair     | stock   | spread_type               |   entry_z |   exit_z |   clipped_last_trade_proxy |   half_spread_taker_cost |   no_cost_midpoint |   quarter_spread_cost |
|:---------|:--------|:--------------------------|----------:|---------:|---------------------------:|-------------------------:|-------------------:|----------------------:|
| XLK-AAPL | AAPL    | price_regression_residual |      1    |      0.5 |                  1315.4    |               -207.309   |         5859.32    |            2826       |
| XLK-PLTR | PLTR    | price_regression_residual |      1    |      0.5 |                  1486.05   |                914.8     |         1573.04    |            1243.92    |
| XLK-ORCL | ORCL    | price_regression_residual |      1    |      0   |                  1313.93   |                238.995   |         1479.5     |             859.249   |
| XLK-AMD  | AMD     | direct_log_price          |      1.25 |      0.5 |                   493.447  |                204.427   |          491.958   |             348.192   |
| XLK-NVDA | NVDA    | direct_log_price          |      1    |      0.5 |                   323.044  |                -46.385   |          378.028   |             165.821   |
| XLK-INTC | INTC    | direct_log_price          |      2.5  |      0.5 |                   193.276  |                124.19    |          190.189   |             157.19    |
| XLK-AAPL | AAPL    | cum_residual_return       |      2    |      0   |                   145.249  |                  7.06338 |          188.046   |              97.5548  |
| XLK-AVGO | AVGO    | cum_residual_return       |      2    |      0   |                   136.907  |                -74.638   |          139.822   |              32.5919  |
| XLK-IBM  | IBM     | price_regression_residual |      1.25 |      0.5 |                   454.779  |              -1043.17    |         1088.77    |              22.8018  |
| XLK-MSFT | MSFT    | direct_log_price          |      1    |      0.5 |                   137.459  |               -165.737   |          172.7     |               3.48151 |
| XLK-PLTR | PLTR    | cum_residual_return       |      2    |      0.5 |                   -66.2818 |               -170.165   |           -9.75177 |             -89.9582  |
| XLK-ANET | ANET    | direct_log_price          |      1.25 |      0.5 |                    53.2793 |               -295.331   |           23.5716  |            -135.88    |
