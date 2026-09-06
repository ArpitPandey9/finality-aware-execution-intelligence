# Phase 1 — PIT-Aligned Cross-Venue Execution Result Note

## Status

**Result status: COMPLETE — descriptive cross-venue evidence established.**

This result note evaluates the frozen five dual-WebSocket captures using the predefined point-in-time Coinbase reference-age sensitivity bands of 250 ms, 500 ms, and 1000 ms.

The analysis compares each Kuru `MON_USDC` state-specific captured order book with the latest eligible reconstructed Coinbase `MON-USD` Level2 book under the frozen backward-as-of alignment policy.

This is a descriptive market-microstructure result. It is not a trading strategy, arbitrage test, profitability study, execution-probability estimate, or causal finality claim.

## Reproducibility

Ordered five-capture dataset fingerprint:

`0c709499d9d16b48080b2fea82ccee85ef4747284e51493324856c954bc13baa`

Deterministic generated-report SHA256:

`80e2d7018c25e0cd4676d9b112f816d6c8d867edc0a6f261e72d57ba6059f331`

Two independent report builds were byte-identical.

The frozen source population contains 8,255 Kuru observations.

Point-in-time economically eligible panels were:

| Coinbase reference-age band | Economically eligible panels | No prior reference | Stale reference |
| --- | ---: | ---: | ---: |
| 250 ms | 6,376 | 122 | 1,757 |
| 500 ms | 7,274 | 122 | 859 |
| 1000 ms | 7,896 | 122 | 237 |

Across all three sensitivity bands:

- invalid Kuru execution panels: `0`;
- invalid Coinbase reconstructions: `0`;
- every economically eligible observation retained one common Coinbase reference across all four Kuru state views;
- every frozen Kuru/Coinbase target comparison was fully fillable inside both captured displayed books.

The final point is a deterministic captured-book outcome. These fillability counts are not execution probabilities.

## Frozen comparison

The common base asset is MON.

The compared quote markets differ:

- Kuru: `MON_USDC`;
- Coinbase: `MON-USD`.

USD/USDC parity is not assumed or normalized away.

Frozen simulated base-quantity targets were:

- 200 MON;
- 2,000 MON;
- 20,000 MON;
- 200,000 MON.

Frozen own-venue displayed-depth bands were:

- 5 bps;
- 10 bps;
- 25 bps;
- 50 bps.

For depth:

`depth_gap_MON = Kuru_depth_MON - Coinbase_depth_MON`

For simulated book-walk slippage:

`slippage_gap_bps = Kuru_slippage_bps - Coinbase_slippage_bps`

Negative slippage gap therefore means lower simulated book-walk slippage on the captured Kuru book for that observation. It does not imply executable trading edge or economic superiority.

## Primary result 1 — displayed depth changes materially with distance from the best quote

The sign of the median displayed-depth gap was stable across all three freshness bands and all four Kuru state views.

At **5 bps**, median `depth_gap_MON` was positive for both BUY and SELL sides.

At **10 bps, 25 bps, and 50 bps**, median `depth_gap_MON` was negative for both BUY and SELL sides.

Therefore, in these captures, Kuru showed greater median displayed MON depth very close to its own best quote, while Coinbase showed greater median displayed MON depth across the wider frozen own-best bands.

This is a book-shape result, not a general venue-liquidity ranking.

The 25 bps result was especially consistent. Across the three reference-age bands, median gaps were approximately:

- BUY: `-1.54m` to `-1.58m MON`;
- SELL: approximately `-1.75m MON`.

The five capture-level 25 bps medians were also negative for every state, side, and threshold examined. The wider-depth result therefore was not created solely by pooling the five capture windows.

At 50 bps, median gaps were substantially more negative, approximately `-12.2m` to `-13.1m MON` depending on side, state, and threshold.

## Primary result 2 — simulated slippage does not support a simple venue-ranking conclusion

At the smallest frozen targets, many captured books produced zero slippage-gap medians.

At 20,000 MON, pooled slippage-gap medians were consistently negative across Kuru states, sides, and freshness thresholds. Typical pooled medians were approximately:

- BUY: about `-3.45 bps`;
- SELL: about `-3.88` to `-3.90 bps`.

At 200,000 MON, pooled medians also remained negative across all states, sides, and freshness thresholds, but were much closer to zero. Depending on state, side, and threshold, medians were approximately `-0.09` to `-0.67 bps`.

However, the five capture-level 200,000 MON medians were heterogeneous and included both positive and negative values.

Accordingly, the pooled negative median is descriptive evidence about the centre of the observed distribution. It is not evidence that Kuru systematically provides superior execution, and it is not an executable edge.

The distribution also contains material tails. For 200,000 MON SELL simulations, maximum positive slippage gaps reached approximately `2,232 bps`.

Those extreme observations remain in the primary distribution. No capping or winsorisation was applied.

Any subsequent threshold introduced specifically to investigate those tails must be labelled post-hoc.

## Secondary result — cross-quote VWAP differences

The secondary cross-quote VWAP comparison remained directionally different between BUY and SELL simulations in the primary 200,000 MON view.

For finalized and committed states, pooled median cross-quote VWAP differences across the 250/500/1000 ms bands were approximately:

- BUY: `-0.68`, `-0.64`, and `-0.54 bps`;
- SELL: `+2.81`, `+2.87`, and `+2.90 bps`.

These values must not be interpreted as arbitrage spreads or executable cross-venue returns.

They combine:

- Kuru USDC-denominated prices;
- Coinbase USD-denominated prices;
- venue-specific book shape;
- point-in-time reference age.

USD/USDC basis remains an explicit limitation.

## State-conditioned result

No monotonic finality-related improvement can be established from this analysis.

The four Kuru state views are simultaneous state-conditioned observations compared with the same selected Coinbase reference. They are not temporal execution transitions.

Finalized and committed aggregate execution and displayed-depth summaries were exactly equal for every frozen threshold, side, target, and depth band in this five-capture dataset.

This is consistent with the previously observed finalized/committed raw full-book equality in these captures.

It is dataset-specific evidence only.

It does not establish that finalized and committed books are semantically equivalent or always identical at the protocol level.

## Interpretation

The strongest cross-venue evidence from this sample is structural rather than directional:

1. displayed MON depth close to the best quote and displayed MON depth farther into the book tell different stories;
2. wider 10/25/50 bps bands show substantially greater captured Coinbase depth on a median basis;
3. simulated slippage-gap pooled medians are often negative at larger targets, but capture-level heterogeneity prevents a robust venue-superiority interpretation;
4. tail behaviour is material and cannot be represented adequately by the median alone;
5. finalized and committed results remain indistinguishable in this dataset, without supporting a causal finality claim.

The evidence therefore supports a point-in-time cross-venue market-microstructure measurement layer, but it does not support claims of arbitrage, alpha, realized execution advantage, execution probability, or a price of finality.

## Excluded costs and mechanisms

The static simulations do not include:

- trading fees;
- gas;
- MEV;
- queue priority;
- cancellation risk;
- order-submission latency;
- inclusion risk;
- adverse market reaction;
- market impact beyond the captured displayed book;
- realized fills.

The output describes deterministic arithmetic over captured displayed liquidity only.
