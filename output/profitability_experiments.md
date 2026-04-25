# Profitability Experiment Memo

## Motivation

The previous final version was honest but negative: market-neutral XLK-vs-basket arbitrage failed out of sample.  The question here was whether there is a defensible way to avoid losses without selecting on March after the fact.

I used two ideas from the IMC Prosperity write-up:

- normalize prices by a fair-value proxy and trade deviations from that normalized premium;
- do not force full hedging if the hedge leg adds cost and tracking noise; test partial hedge / ETF-only execution separately.

The Prosperity idea transfers only as an engineering heuristic.  The IMC environment is a simulated order-book game, while this project uses real TAQ data with explicit bid-ask costs.

## Experiment Design

The candidate universe was deliberately constrained:

- signal price: microprice only;
- signals: raw premium, rolling-centered premium, EWMA-centered premium;
- baskets: official eight-name basket and sparse five-name basket;
- execution: midpoint returns only;
- hedge fractions: 0, 0.5, 1.0;
- thresholds: fixed premium thresholds, not March-fitted z-scores;
- model selection protocols:
  - Jan best;
  - Jan-Feb train best;
  - robust Jan/Feb positive;
  - March oracle, shown only as an invalid diagnostic.

## Best Honest Positive Candidate

The best non-oracle candidate under Jan, Jan-Feb, and robust Jan/Feb protocols is:

- hedge universe: sparse5 basket, `MSFT NVDA ORCL CRM AMD`;
- signal: microprice rolling-centered premium;
- execution: ETF-only, no basket hedge;
- threshold: 50 bps;
- exit band: 25 bps;
- max hold: intraday, 390 minutes.

This is not market-neutral ETF arbitrage.  It is an ETF timing strategy that uses the sparse basket premium as a fair-value signal.

## Results

| Period | Net bps | Gross bps | Cost bps | Trades | Avg abs position | XLK buy-hold bps |
|---|---:|---:|---:|---:|---:|---:|
| Jan | 144.93 | 287.18 | 142.26 | 44 | 0.688 | -345.09 |
| Feb | 264.61 | 402.05 | 137.45 | 50 | 0.734 | -204.10 |
| Mar | 638.35 | 870.74 | 232.39 | 58 | 0.757 | -370.73 |
| All | 1047.88 | 1559.98 | 512.10 | 152 | 0.727 | -919.91 |

Controls:

| Control | March net bps |
|---|---:|
| Selected rule | 638.35 |
| Sign flip | -1103.13 |
| Active always long | -1.39 |
| Active always short | -463.39 |
| Circular-shift mean | -195.85 |
| Circular-shift 95th percentile | 699.52 |
| P(random circular shift >= selected) | 0.063 |

Cost sensitivity:

| Cost multiplier | Jan net | Feb net | March net | All net |
|---:|---:|---:|---:|---:|
| 1.0 | 144.93 | 264.61 | 638.35 | 1047.88 |
| 1.5 | 73.80 | 195.88 | 522.16 | 791.83 |
| 2.0 | 2.67 | 127.16 | 405.96 | 535.78 |
| 3.0 | -139.59 | -10.29 | 173.57 | 23.68 |
| 4.0 | -281.85 | -147.74 | -58.82 | -488.41 |

## Interpretation

There is a way to avoid losses, but it changes the economic claim.

The profitable candidate should not be presented as an ETF-basket arbitrage.  It is better described as:

> A sparse-basket microprice premium signal for intraday XLK timing.

The evidence is encouraging but not conclusive.  The signal is positive in Jan, Feb, and March; it beats XLK buy-and-hold in a down sample; the sign flip loses strongly; and simple always-long/always-short controls do not explain the result.  However, the circular-shift p-value is about 6.3%, so the evidence is suggestive rather than ironclad.

The strict market-neutral arbitrage conclusion remains negative.  The practical positive result comes from not trading the noisy basket hedge.
