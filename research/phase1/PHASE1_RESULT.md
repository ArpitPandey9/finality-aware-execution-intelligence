# Phase 1 — Point-in-Time Cross-Venue Execution Intelligence Result

## Status

**Phase 1: COMPLETE — descriptive market-microstructure evidence established.**

Phase 1 converted the Phase 0 acquisition and normalization foundation into a point-in-time research pipeline for comparing Kuru / Monad state-conditioned order books with a reconstructed Coinbase market reference.

The phase establishes a reproducible measurement framework. It does not establish arbitrage, alpha, profitability, realized execution advantage, execution probability, or a causal price of finality.

## Scope

Markets:

- Kuru / Monad: `MON_USDC`
- Coinbase: `MON-USD`

Kuru state views:

- proposed;
- voted;
- finalized;
- committed.

The common base asset is MON.

USD and USDC are not assumed to be economically identical.

## Dataset

The primary Phase 1 empirical dataset contains five dual-WebSocket capture windows and 8,255 Kuru observations.

Ordered five-capture dataset fingerprint:

`0c709499d9d16b48080b2fea82ccee85ef4747284e51493324856c954bc13baa`

The frozen Coinbase reference-age sensitivity bands are:

- 250 ms;
- 500 ms;
- 1000 ms.

These bands are nested sensitivity analyses, not independent samples.

Economically eligible point-in-time panels were:

| Reference-age band | Eligible panels | No prior reference | Stale reference |
| --- | ---: | ---: | ---: |
| 250 ms | 6,376 | 122 | 1,757 |
| 500 ms | 7,274 | 122 | 859 |
| 1000 ms | 7,896 | 122 | 237 |

## Completed Research Gates

### 1. Point-in-time alignment

A deterministic backward-as-of alignment policy selects the latest eligible Coinbase Level2 reference satisfying:

`coinbase_receive_time <= kuru_receive_time`

Future references and interpolation are prohibited.

Each economically eligible Kuru observation uses one selected Coinbase reference across all four Kuru state views.

### 2. State-conditioned top-of-book analysis

The project evaluates Kuru proposed, voted, finalized, and committed top-of-book states against the same point-in-time Coinbase reference.

The analysis preserves paired within-panel state comparisons and does not reinterpret simultaneous state views as temporal state transitions.

### 3. Kuru executable-depth and simulated-slippage analysis

Kuru full captured depth was bound to the independently verified MON-USDC normalization.

Frozen displayed-depth bands:

- 5 bps;
- 10 bps;
- 25 bps;
- 50 bps.

Frozen simulated MON targets:

- 200;
- 2,000;
- 20,000;
- 200,000.

The sweep is deterministic and static. It does not model realized fills, queue priority, cancellation, gas, MEV, inclusion risk, latency reaction, or market impact beyond captured displayed depth.

### 4. Coinbase full-Level2 historical reconstruction

Coinbase MON-USD books are reconstructed from captured Level2 snapshot and update messages.

The reconstruction gate validates:

- source identity;
- snapshot initialization;
- update semantics;
- zero-quantity deletion;
- wrapper sequence integrity;
- historical replay order;
- stored-book parity.

Observed Coinbase Level2 quantity was separately bound to MON base-asset quantity for the captured market representation.

### 5. PIT-aligned cross-venue executable comparison

The final Phase 1 layer compares Kuru and Coinbase displayed-book depth and deterministic simulated execution at identical MON target quantities.

Deterministic cross-venue report SHA256:

`80e2d7018c25e0cd4676d9b112f816d6c8d867edc0a6f261e72d57ba6059f331`

Independent report builds were byte-identical.

Across every economically eligible panel and frozen target, both captured books contained sufficient displayed depth to complete the static target sweep.

These fillability counts are not execution probabilities.

## Primary Cross-Venue Findings

### Displayed depth

For both BUY and SELL sides, across all four Kuru state views and all three reference-age sensitivity bands:

- median 5 bps `Kuru depth - Coinbase depth` was positive;
- median 10 bps depth gap was negative;
- median 25 bps depth gap was negative;
- median 50 bps depth gap was negative.

The five capture-level 25 bps medians were also negative.

The evidence therefore describes a difference in captured book shape: Kuru showed greater median displayed MON depth very close to its own best quote, while Coinbase showed substantially greater median displayed MON depth over the wider frozen own-best bands.

This is not a general venue-liquidity ranking.

### Simulated slippage

At 20,000 MON, pooled cross-venue slippage-gap medians were negative across states, sides, and freshness bands.

At 200,000 MON, pooled medians also remained negative but were closer to zero.

However, the five capture-level 200,000 MON medians contained both positive and negative values.

The pooled result therefore does not support a claim that either venue systematically provides superior execution.

Material tails were preserved rather than capped. Any threshold introduced later specifically to investigate those tails must be labelled post-hoc.

### Finalized and committed state views

Finalized and committed aggregate execution and displayed-depth summaries were exactly equal for every frozen threshold, side, target, and depth band in this dataset.

This is consistent with the dataset-specific raw full-book equality observed in the Kuru depth analysis.

It does not establish protocol-level semantic equivalence or a general invariant between finalized and committed books.

## Phase 1 Conclusion

Phase 1 establishes a reproducible point-in-time cross-venue execution-intelligence layer with:

- anti-lookahead reference selection;
- explicit staleness sensitivity;
- state-conditioned Kuru evidence;
- independently reconstructed Coinbase Level2 books;
- exact Decimal arithmetic;
- frozen execution targets and depth bands;
- capture-level and pooled descriptive summaries;
- provenance-bound deterministic outputs;
- explicit claim boundaries.

The evidence supports continued research into market-state evolution after state-conditioned observations.

It does not support claims of arbitrage, alpha, profitability, execution probability, realized execution advantage, venue superiority, or causal finality effects.

## Next Research Gate

A subsequent phase should move from static point-in-time comparison to pre-specified temporal outcome measurement.

Before inspecting those outcomes, the research design should freeze:

- observation/event eligibility;
- future measurement horizons;
- price/reference outcome definitions;
- adverse-selection metrics;
- censoring rules;
- overlapping-event treatment;
- anti-lookahead requirements;
- benchmark and cost boundaries.

No temporal result should be interpreted before those rules are frozen.

## Evidence Map

- [`ALIGNMENT_CONTRACT.md`](ALIGNMENT_CONTRACT.md)
- [`STALENESS_POLICY.md`](STALENESS_POLICY.md)
- [`TOP_OF_BOOK_CONTRACT.md`](TOP_OF_BOOK_CONTRACT.md)
- [`EXECUTABLE_DEPTH_CONTRACT.md`](EXECUTABLE_DEPTH_CONTRACT.md)
- [`DEPTH_EXECUTION_RESULT_NOTE.md`](DEPTH_EXECUTION_RESULT_NOTE.md)
- [`WS_DEPTH_NORMALIZATION_EVIDENCE.md`](WS_DEPTH_NORMALIZATION_EVIDENCE.md)
- [`COINBASE_L2_RECONSTRUCTION_CONTRACT.md`](COINBASE_L2_RECONSTRUCTION_CONTRACT.md)
- [`COINBASE_QUANTITY_UNIT_EVIDENCE.md`](COINBASE_QUANTITY_UNIT_EVIDENCE.md)
- [`CROSS_VENUE_EXECUTION_CONTRACT.md`](CROSS_VENUE_EXECUTION_CONTRACT.md)
- [`CROSS_VENUE_EXECUTION_RESULT_NOTE.md`](CROSS_VENUE_EXECUTION_RESULT_NOTE.md)
