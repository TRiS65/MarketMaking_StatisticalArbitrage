# Professor Feedback Robustness Memo

This run answers the main TAQ methodology questions raised in feedback:

- `r_XLK,t` is one-minute log return, not price.
- The old residual spread is compared against direct log-price spread and log-price regression residual.
- Gross/no-cost P&L is separated from 0.25-spread, 0.50-spread, and clipped last-trade execution proxies.
- OU/Avellaneda-Lee style diagnostics are reported as ADF p-value, half-life, equilibrium sigma, and s-score scale.

Best validation-selected test rows under the 0.25-spread scenario:

| pair     | stock   | spread_type               |   entry_z |   exit_z |   clipped_last_trade_proxy |   half_spread_taker_cost |   no_cost_midpoint |   quarter_spread_cost |
|:---------|:--------|:--------------------------|----------:|---------:|---------------------------:|-------------------------:|-------------------:|----------------------:|
| XLK-AMD  | AMD     | direct_log_price          |       1   |     0.5  |                   383.05   |                14.5467   |          453.352   |              233.949  |
| XLK-NVDA | NVDA    | direct_log_price          |       1   |     0.5  |                   280.183  |              -113.089    |          409.075   |              147.993  |
| XLK-PLTR | PLTR    | price_regression_residual |       1   |     0.5  |                   244.598  |                -2.27305  |          254.288   |              126.008  |
| XLK-AAPL | AAPL    | cum_residual_return       |       2   |     0    |                   182.427  |                26.1289   |          200.099   |              113.114  |
| XLK-INTC | INTC    | direct_log_price          |       2.5 |     0.5  |                    67.6228 |                -0.609835 |           52.2287  |               25.8094 |
| XLK-MSFT | MSFT    | direct_log_price          |       1   |     0.5  |                    97.1197 |              -124.174    |          102.432   |              -10.8707 |
| XLK-ORCL | ORCL    | price_regression_residual |       2.5 |     0    |                   -48.5873 |              -124.848    |            1.61472 |              -61.6165 |
| XLK-ANET | ANET    | direct_log_price          |       1   |     0.5  |                   116.258  |              -296.449    |           88.0084  |             -104.22   |
| XLK-CSCO | CSCO    | cum_residual_return       |       2.5 |     0    |                   -43.9858 |              -154.156    |          -67.9473  |             -111.052  |
| XLK-KLAC | KLAC    | price_regression_residual |       1   |     0.25 |                   517.015  |              -803.084    |          562.052   |             -120.516  |
| XLK-ORCL | ORCL    | cum_residual_return       |       2   |     0.25 |                   -45.0959 |              -193.833    |          -53.2113  |             -123.522  |
| XLK-LRCX | LRCX    | price_regression_residual |       1   |     0    |                   165.687  |              -444.848    |          174.007   |             -135.421  |
