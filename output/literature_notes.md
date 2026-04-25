# Literature Integration Notes

This enhanced layer uses every paper supplied in the project folder as a design constraint.

| Paper | How it enters the implementation |
|---|---|
| d'Aspremont, *Identifying Small Mean Reverting Portfolios* | Search over small constituent subsets instead of forcing a dense basket; rank candidates by stationarity, half-life, and cost. |
| Kanamura, Rachev, Fabozzi, *A Profit Model for Spread Trading* | Treat spread trading as a first-passage/mean-reversion problem; require estimated spread movement to be large relative to trading cost. |
| Leung and Li, *Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit* | Use entry/exit bands rather than continuous trading, and choose thresholds on the training sample only. |
| Martin, *Optimal Multifactor Trading under Proportional Transaction Costs* | Add a no-trade buffer/cost gate so small target-position changes are ignored. |
| Gueant, Lehalle, Fernandez-Tapia, *Dealing with the Inventory Risk* | Track position, turnover, and end-of-day flattening; avoid interpreting raw signal quality without inventory risk. |
| Ghoshal and Roberts, *Optimal FX Market Making under Inventory Risk and Adverse Selection Constraints* | Treat adverse selection through conservative execution assumptions: crossing half-spreads and avoiding trades where signal is small versus cost. |
| Almgren, *Optimal Trading with Stochastic Liquidity and Volatility* | Let spread costs vary minute by minute through contemporaneous bid-ask spreads instead of using a constant fee. |
| Dare, *Statistical Arbitrage in the U.S. Treasury Futures Market* | Use a train/test statistical-arbitrage workflow: construct spread, test mean reversion, then evaluate out-of-sample trading. |

Main methodological changes: the original holdings-weight basket is an economic benchmark, but not necessarily the tradable mean-reverting portfolio; microprice is a fair-value signal rather than an executable fill.  The enhanced model estimates a sparse hedge portfolio on January-February 2026, uses microprice residuals for entry/exit signals, computes gross P&L on midpoint residual returns, and evaluates the selected rule in March 2026.
