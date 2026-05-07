# Fixed-BPS XLK-Only Timing Controls

This regenerates the old fixed-bps sparse-basket timing candidate shape on the expanded top-20 panel. It is a directional XLK-only timing test, not market-neutral arbitrage.

## Selection

| decision   | reason                                                                                                                                             | basket_symbols         | basket_weights                                            | signal_price   |   center_days |   entry_bps |   exit_bps |   max_hold |   train_net_bps |   validation_net_bps |   test_net_bps |   test_trades |   circular_pvalue |   test_2x_cost_net_bps |   test_latency1_net_bps |
|:-----------|:---------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------|:----------------------------------------------------------|:---------------|--------------:|------------:|-----------:|-----------:|----------------:|---------------------:|---------------:|--------------:|------------------:|-----------------------:|------------------------:|
| no_trade   | train_or_validation_net<=0;test_net<=0;2x_cost_test<=0;latency1_test<=0;does_not_beat_directional_control;sign_flip_not_worse;circular_pvalue>0.10 | NVDA AAPL MSFT AVGO MU | NVDA:0.3112 AAPL:0.2654 MSFT:0.1986 AVGO:0.1289 MU:0.0959 | micro          |            10 |          50 |         25 |        390 |        -2115.46 |             -45.1272 |       -977.239 |            83 |               0.8 |               -1211.91 |                -1034.28 |

## Controls

| control                     |   train_gross_bps |   train_cost_bps |   train_net_bps |   train_trades |   train_avg_abs_position |   validation_gross_bps |   validation_cost_bps |   validation_net_bps |   validation_trades |   validation_avg_abs_position |   test_gross_bps |   test_cost_bps |   test_net_bps |   test_trades |   test_avg_abs_position |
|:----------------------------|------------------:|-----------------:|----------------:|---------------:|-------------------------:|-----------------------:|----------------------:|---------------------:|--------------------:|------------------------------:|-----------------:|----------------:|---------------:|--------------:|------------------------:|
| selected                    |         -1603.39  |           512.07 |      -2115.46   |            128 |                 0.822314 |                96.7432 |                141.87 |             -45.1272 |                  40 |                      0.882185 |         -742.565 |         234.675 |       -977.239 |            83 |                0.901489 |
| sign_flip                   |          1603.39  |           512.07 |       1091.32   |            128 |                 0.822314 |               -96.7432 |                141.87 |            -238.614  |                  40 |                      0.882185 |          742.565 |         234.675 |        507.89  |            83 |                0.901489 |
| active_always_long          |          -520.644 |           512.07 |      -1032.71   |            128 |                 0.822314 |              -202.263  |                141.87 |            -344.133  |                  40 |                      0.882185 |         1042.53  |         234.675 |        807.851 |            83 |                0.901489 |
| active_always_short         |           520.644 |           512.07 |          8.5748 |            128 |                 0.822314 |               202.263  |                141.87 |              60.3926 |                  40 |                      0.882185 |        -1042.53  |         234.675 |      -1277.2   |            83 |                0.901489 |
| circular_shift_mean         |           nan     |           nan    |        nan      |            nan |               nan        |               nan      |                nan    |             nan      |                 nan |                    nan        |          nan     |         nan     |       -335.576 |           nan |              nan        |
| circular_shift_p95          |           nan     |           nan    |        nan      |            nan |               nan        |               nan      |                nan    |             nan      |                 nan |                    nan        |          nan     |         nan     |        736.585 |           nan |              nan        |
| selected_vs_circular_pvalue |           nan     |           nan    |        nan      |            nan |               nan        |               nan      |                nan    |             nan      |                 nan |                    nan        |          nan     |         nan     |          0.8   |           nan |              nan        |

## Monthly PnL

| month   |   gross_bps |   cost_bps |    net_bps |   trades |   avg_abs_position |
|:--------|------------:|-----------:|-----------:|---------:|-------------------:|
| 2025-11 |   -454.955  |    206.546 |  -661.5    |       38 |           0.78986  |
| 2025-12 |   -916.798  |    169.95  | -1086.75   |       46 |           0.947059 |
| 2026-01 |   -231.636  |    135.574 |  -367.21   |       44 |           0.716566 |
| 2026-02 |     96.7432 |    141.87  |   -45.1272 |       40 |           0.882185 |
| 2026-03 |    197.418  |    126.355 |    71.0634 |       42 |           0.865554 |
| 2026-04 |   -939.983  |    108.32  | -1048.3    |       41 |           0.939011 |

## Trade Concentration

|   trades |   total_trade_net_bps |   top1_trade_net_bps |   top5_trade_net_bps |   top1_share_of_positive_total |   top5_share_of_positive_total |
|---------:|----------------------:|---------------------:|---------------------:|-------------------------------:|-------------------------------:|
|      126 |              -2978.89 |              299.777 |                 1262 |                            nan |                            nan |