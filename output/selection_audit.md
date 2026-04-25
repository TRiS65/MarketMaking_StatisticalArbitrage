# Selection Audit

The final version does not choose the v2 March-best row because that row is selected after observing the March test set.  That is exactly the kind of look-ahead selection that makes a backtest look tradable without being ex-ante tradable.

The rule for a valid experiment is: choose model class, basket, and thresholds using January-February; then evaluate March once.

| model                               | selection_protocol                                                               |   train_net_bps |   march_net_bps | train_to_test_pattern                    | bias_flag                          | final_use                                                                  |
|:------------------------------------|:---------------------------------------------------------------------------------|----------------:|----------------:|:-----------------------------------------|:-----------------------------------|:---------------------------------------------------------------------------|
| v2_best_by_train_overall            | Valid ex-ante selection: choose from grid using Jan-Feb only, then report March. |        -48.1997 |        -47.6356 | -48.19973454519217 -> -47.63563092491599 | No test leakage.                   | No, active rule loses in train and March; useful as diagnostic benchmark.  |
| v2_best_march_diagnostic            | Invalid as final strategy: choose after sorting by March net P&L.                |       -118.168  |         54.0767 | -118.16789351467456 -> 54.07665059355374 | Selection-on-test/look-ahead bias. | No, because March is the test set. Keep only as post-mortem diagnostic.    |
| hybrid_sparse_micro_signal_mid_exec | Valid ex-ante selection: sparse basket and threshold selected on Jan-Feb.        |         86.9296 |        -89.033  | 86.92956617591311 -> -89.03297730972562  | No test leakage in selection.      | Yes as the final active experiment, but it fails OOS; compare to no-trade. |
| literature_no_trade                 | Benchmark implied by transaction-cost/no-trade literature.                       |          0      |          0      | 0.0 -> 0.0                               | None.                              | Yes as the final decision benchmark; dominates active rules in March.      |

Key implication: the v2 March-best row has negative January-February net P&L and positive March net P&L.  It is informative as a post-mortem diagnostic that some raw-shrunk signals happened to work in March, but it cannot be the final selected strategy because the selection criterion directly used the test outcome.

The hybrid sparse strategy is retained as the final active experiment because it is train-selected and methodologically consistent: microprice forms the signal, midpoint residual returns form executable gross P&L, and bid-ask costs are explicit.  It still fails in March, so the final economic decision is no-trade.
