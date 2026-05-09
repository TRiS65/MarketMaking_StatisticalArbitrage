# Fixed-BPS XLK-Only Timing Controls

This regenerates the old fixed-bps sparse-basket timing candidate shape on the expanded top-20 panel. It is a directional XLK-only timing test, not market-neutral arbitrage.

## Selection

| decision   | reason                                                                                                                                             | basket_symbols         | basket_weights                                            | signal_price   |   center_days |   entry_bps |   exit_bps |   max_hold |   train_net_bps |   validation_net_bps |   test_net_bps |   test_trades |   circular_pvalue |   test_2x_cost_net_bps |   test_latency1_net_bps |
|:-----------|:---------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------|:----------------------------------------------------------|:---------------|--------------:|------------:|-----------:|-----------:|----------------:|---------------------:|---------------:|--------------:|------------------:|-----------------------:|------------------------:|
| no_trade   | train_or_validation_net<=0;test_net<=0;2x_cost_test<=0;latency1_test<=0;does_not_beat_directional_control;sign_flip_not_worse;circular_pvalue>0.10 | NVDA AAPL MSFT AVGO MU | NVDA:0.3112 AAPL:0.2654 MSFT:0.1986 AVGO:0.1289 MU:0.0959 | micro          |            10 |          50 |         25 |        390 |        -2572.04 |             -45.1272 |       -977.239 |            83 |              0.66 |               -1211.91 |                -1034.28 |

## Controls

| control                     |   train_gross_bps |   train_cost_bps |   train_net_bps |   train_trades |   train_avg_abs_position |   validation_gross_bps |   validation_cost_bps |   validation_net_bps |   validation_trades |   validation_avg_abs_position |   test_gross_bps |   test_cost_bps |   test_net_bps |   test_trades |   test_avg_abs_position |
|:----------------------------|------------------:|-----------------:|----------------:|---------------:|-------------------------:|-----------------------:|----------------------:|---------------------:|--------------------:|------------------------------:|-----------------:|----------------:|---------------:|--------------:|------------------------:|
| selected                    |          -962.305 |          1609.73 |       -2572.04  |            388 |                 0.836642 |                96.7432 |                141.87 |             -45.1272 |                  40 |                      0.882185 |         -742.565 |         234.675 |       -977.239 |            83 |                0.901489 |
| sign_flip                   |           962.305 |          1609.73 |        -647.428 |            388 |                 0.836642 |               -96.7432 |                141.87 |            -238.614  |                  40 |                      0.882185 |          742.565 |         234.675 |        507.89  |            83 |                0.901489 |
| active_always_long          |           291.222 |          1609.73 |       -1318.51  |            388 |                 0.836642 |              -202.263  |                141.87 |            -344.133  |                  40 |                      0.882185 |         1042.53  |         234.675 |        807.851 |            83 |                0.901489 |
| active_always_short         |          -291.222 |          1609.73 |       -1900.96  |            388 |                 0.836642 |               202.263  |                141.87 |              60.3926 |                  40 |                      0.882185 |        -1042.53  |         234.675 |      -1277.2   |            83 |                0.901489 |
| circular_shift_mean         |           nan     |           nan    |         nan     |            nan |               nan        |               nan      |                nan    |             nan      |                 nan |                    nan        |          nan     |         nan     |       -541.324 |           nan |              nan        |
| circular_shift_p95          |           nan     |           nan    |         nan     |            nan |               nan        |               nan      |                nan    |             nan      |                 nan |                    nan        |          nan     |         nan     |        668.007 |           nan |              nan        |
| selected_vs_circular_pvalue |           nan     |           nan    |         nan     |            nan |               nan        |               nan      |                nan    |             nan      |                 nan |                    nan        |          nan     |         nan     |          0.66  |           nan |              nan        |

## Monthly PnL

| month   |   gross_bps |   cost_bps |     net_bps |   trades |   avg_abs_position |
|:--------|------------:|-----------:|------------:|---------:|-------------------:|
| 2025-05 |   -392.696  |    171.524 |  -564.22    |       36 |           0.774743 |
| 2025-06 |     10.9421 |    168.37  |  -157.428   |       40 |           0.956919 |
| 2025-07 |    144.518  |    197.439 |   -52.9208  |       44 |           0.885518 |
| 2025-08 |     65.7687 |    134.564 |   -68.7952  |       42 |           0.69159  |
| 2025-09 |    156.226  |    154.457 |     1.76855 |       42 |           0.826151 |
| 2025-10 |    374.169  |    236.28  |   137.889   |       48 |           0.908766 |
| 2025-11 |   -172.799  |    241.575 |  -414.373   |       46 |           0.805899 |
| 2025-12 |   -916.798  |    169.95  | -1086.75    |       46 |           0.947059 |
| 2026-01 |   -231.636  |    135.574 |  -367.21    |       44 |           0.716566 |
| 2026-02 |     96.7432 |    141.87  |   -45.1272  |       40 |           0.882185 |
| 2026-03 |    197.418  |    126.355 |    71.0634  |       42 |           0.865554 |
| 2026-04 |   -939.983  |    108.32  | -1048.3     |       41 |           0.939011 |

## Trade Concentration

|   trades |   total_trade_net_bps |   top1_trade_net_bps |   top5_trade_net_bps |   top1_share_of_positive_total |   top5_share_of_positive_total |
|---------:|----------------------:|---------------------:|---------------------:|-------------------------------:|-------------------------------:|
|      256 |              -3012.59 |              436.452 |              1471.18 |                            nan |                            nan |