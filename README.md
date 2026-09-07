# Finality-Aware Cross-Venue Execution Intelligence Engine

Research system for studying how observable on-chain order-book liquidity and simulated execution conditions differ across blockchain consensus/finality-state views and an external centralized-market reference.

## Status

**Phase 0 — Data & Research Feasibility: COMPLETE**

**Phase 1 — Point-in-Time Cross-Venue Execution Intelligence: COMPLETE**

**Phase 2 — Pre-Registered Temporal Market Response: COMPLETE**

**Phase 3 — Pre-Registered State-Conditioned Market Instability: COMPLETE**

**Current full repository test suite: 297 passing tests**

The project has established a provenance-bound, anti-lookahead research pipeline spanning Kuru / Monad state-specific order books and reconstructed Coinbase MON-USD Level2 books.

No trading-performance, arbitrage, alpha, profitability, execution-probability, venue-superiority, predictive, or causal-finality claim is made.

**Latest research result:** Phase 3 observed **ROBUST DIRECTIONAL SUPPORT** under its pre-registered descriptive association rule: greater simultaneous Kuru proposed-versus-finalized midpoint disagreement magnitude was associated with greater subsequent absolute Coinbase MON-USD midpoint movement magnitude in the frozen confirmatory dataset. This is a descriptive association result, not evidence of causality, prediction, alpha, or a realizable trading edge.

## Research Question

Kuru exposes order-book views for Monad proposed, voted, finalized, and committed states.

The project studies whether observable execution conditions differ across those simultaneous state views, how those conditions compare with an external Coinbase market reference, and how pre-specified state-conditioned observations are descriptively associated with subsequent external-market behavior.

Phase 2 studied a signed directional relationship. Phase 3 separately studies whether the magnitude of simultaneous proposed-versus-finalized disagreement is associated with the magnitude of subsequent Coinbase price movement.

Current markets:

- Kuru / Monad: `MON_USDC`
- Coinbase: `MON-USD`

The common base asset is MON.

USD and USDC are not assumed to be economically identical.

## Phase 0 — Feasibility

Phase 0 established that the evidence pipeline required for the research question is technically feasible.

The system supports:

- Kuru state-specific order-book acquisition;
- independently verified MON-USDC price and size normalization;
- raw evidence preservation with SHA256 integrity checks;
- Kuru multi-state WebSocket capture;
- episode-aware quote-lineage analysis;
- Coinbase Level2 evidence capture;
- concurrent Kuru and Coinbase WebSocket acquisition;
- same-process monotonic receive timestamps.

Five 60-second Kuru WebSocket windows used in the Phase 0 quote-lineage study contained **6,159 messages**.

The complete conclusion is documented in [`research/phase0/PHASE0_RESULT.md`](research/phase0/PHASE0_RESULT.md).

## Phase 1 — Point-in-Time Execution Intelligence

Phase 1 converts the acquisition foundation into a deterministic point-in-time market-microstructure research pipeline.

Completed gates include:

- backward-as-of Coinbase reference selection with no future reference or interpolation;
- frozen 250 ms, 500 ms, and 1000 ms reference-age sensitivity bands;
- state-conditioned Kuru top-of-book analysis;
- state-conditioned Kuru executable-depth and simulated-slippage analysis;
- Coinbase MON-USD full-Level2 historical reconstruction;
- Coinbase MON base-quantity representation binding;
- PIT-aligned Kuru-versus-Coinbase displayed-depth comparison;
- PIT-aligned deterministic simulated execution at frozen MON target quantities;
- capture-level and pooled descriptive aggregation;
- deterministic provenance-bound report generation.

The primary five-capture Phase 1 dataset contains **8,255 Kuru observations**.

Ordered dataset fingerprint:

`0c709499d9d16b48080b2fea82ccee85ef4747284e51493324856c954bc13baa`

Economically eligible panels:

| Coinbase reference-age band | Eligible panels |
| --- | ---: |
| 250 ms | 6,376 |
| 500 ms | 7,274 |
| 1000 ms | 7,896 |

The three bands are nested sensitivity analyses and are not independent samples.

### Cross-Venue Result

The frozen displayed-depth bands are 5, 10, 25, and 50 bps from each venue's own contemporaneous best price.

Across states, sides, and all three freshness bands:

- median Kuru-minus-Coinbase displayed depth was positive at 5 bps;
- median depth gaps were negative at 10, 25, and 50 bps;
- five-capture 25 bps capture-level medians were also negative.

This describes captured book shape, not a general liquidity ranking.

For deterministic static book sweeps:

- 20,000 MON pooled slippage-gap medians were negative across states, sides, and sensitivity bands;
- 200,000 MON pooled medians were also negative but close to zero relative to their observed tails;
- 200,000 MON capture-level medians included both positive and negative values.

The result therefore does not support a simple claim that either venue systematically provides superior execution.

Finalized and committed execution/depth summaries were exactly equal throughout this dataset. That is a dataset-specific observation, not a protocol invariant or causal finality result.

See [`research/phase1/PHASE1_RESULT.md`](research/phase1/PHASE1_RESULT.md) for the Phase 1 conclusion.

## Phase 2 — Pre-Registered Temporal Market Response

Phase 2 moves from static point-in-time comparison to a pre-registered
post-observation outcome study.

The research question is whether the simultaneous Kuru
proposed-versus-finalized midpoint contrast observed at a four-state panel is
descriptively associated with subsequent Coinbase MON-USD midpoint movement.

The methodology was frozen before inspection of the real economic outcomes.

Pre-result methodology commit:

`9c94b55a535006d7d5d79d6fcd277c17ca7aaaa6`

Frozen five-capture dataset fingerprint:

`0c709499d9d16b48080b2fea82ccee85ef4747284e51493324856c954bc13baa`

Deterministic real-report SHA256:

`e84937515281be0ecc3e35843a41b3a768ce026d7cb728d4b63fefb3e9bcd90d`

The independently generated real reports were byte-identical.

The primary baseline-freshness definition is **250 ms**. The pre-specified
primary future horizons are:

- 250 ms;
- 1000 ms;
- 5000 ms.

A 10000 ms horizon is retained only as an extended sensitivity.

### Temporal Result

**Primary hypothesis support: NOT ESTABLISHED.**

For the primary 250 ms baseline-freshness population, pooled Coinbase forward
midpoint-return medians and pooled directional-concordance medians were
**0.00 bps** at each of the 250 ms, 1000 ms, and 5000 ms primary horizons.

At the 250 ms and 1000 ms horizons, all five separate capture windows also had
zero median forward return and zero median directional concordance.

The deterministic within-capture non-overlapping sensitivity likewise had
zero median forward return and zero median directional concordance at all
three primary horizons.

The pre-specified 10000 ms extended horizon showed a small positive pooled
median, but that result did not survive the non-overlapping sensitivity. It is
therefore retained as mixed sensitivity evidence rather than promoted as a
primary finding.

This result does not establish that Kuru state information has no economic
content or that one venue never responds after the other. It establishes only
that the specific pre-registered state-conditioned directional relationship
was not robustly supported in this frozen five-capture dataset.

No post-hoc horizon, state-gap threshold, subgroup, predictive rule, alpha
claim, arbitrage claim, win-rate claim, or causal-finality interpretation is
promoted from the Phase 2 result.

See
[`research/phase2/TEMPORAL_OUTCOME_RESULT_NOTE.md`](research/phase2/TEMPORAL_OUTCOME_RESULT_NOTE.md)
for the canonical Phase 2 empirical result.

## Phase 3 — Pre-Registered State-Conditioned Market Instability

Phase 3 asks a new confirmatory question after the Phase 2 directional
relationship was not established:

> When simultaneous Kuru proposed and finalized state views exhibit greater
> midpoint disagreement, is that descriptively associated with greater
> subsequent absolute Coinbase MON-USD midpoint movement?

Phase 3 is not a post-hoc rescue of Phase 2. Its methodology and collection
protocol were frozen before fresh confirmatory economic outcomes were inspected.

Methodology preregistration commit:

`a834e149e309fcae0e90ce3b213d5318aabf5e7c`

Confirmatory collection implementation commit:

`5f0c7c0e45f59d4f9aad1347e1d23065a49c526d`

Confirmatory dataset provenance commit:

`d8393672825722e544dc66e6256e2f4d844bc1d8`

Analysis implementation commit:

`9c9eaec151b094c8cbecae5e88ff0d4f3cd20621`

Result commit:

`bfcdae7a2ec94ad80ec4c4faf0987462d52563d0`

The frozen confirmatory dataset contains **10 qualifying captures**, selected
under the pre-registered first-ten chronological technical-PASS rule. The
preserved REVIEW attempt was not promoted into the confirmatory dataset.

Ordered confirmatory dataset fingerprint:

`ff29993a22743674edf13363957e7e5386b338d4e599027b4006089991f382e2`

Deterministic real-report SHA256:

`d97f3cbf4de3ba2b71a98a2bc06b76d81fa8efb9a185fb4e3f875fb50973d378`

Two separate executions of the frozen analysis implementation against the same
frozen ten-capture input sequence produced byte-identical report hashes.

### Market-Instability Result

**Primary relationship status: ROBUST DIRECTIONAL SUPPORT OBSERVED.**

The primary population uses the pre-registered **250 ms** baseline-freshness
threshold.

| Future horizon | Evaluable pairs | Pooled Spearman rho | Defined capture correlations | Median capture rho | Non-overlap Spearman rho | Supportive |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 250 ms | 27,940 | 0.2047319146 | 10 / 10 | 0.1760937618 | 0.1238017693 | Yes |
| 1000 ms | 27,821 | 0.1472375089 | 10 / 10 | 0.1463359276 | 0.1114146501 | Yes |
| 5000 ms | 26,920 | 0.1129767629 | 10 / 10 | 0.0059554587 | 0.1142676897 | Yes |

All three primary horizons satisfied the frozen descriptive support rule. The
pre-registered cross-horizon requirement required support at at least two of the
three primary horizons.

The 10000 ms extended horizon was also directionally supportive under the
primary 250 ms freshness population, but it is an extended sensitivity and does
not contribute to the primary classification.

Sensitivity evidence is not uniformly supportive across every specification.
At the **1000 ms freshness / 5000 ms horizon** cell, the deterministic
non-overlapping Spearman correlation was:

`-0.0207678706`

That sensitivity cell therefore did not satisfy the individual support rule.

The observed Phase 3 associations are positive but modest. In particular, the
median capture-level Spearman correlation at the 5000 ms primary horizon was
approximately `0.006`.

The Phase 3 result does **not** establish:

- causality;
- that Kuru leads Coinbase;
- forecast skill or prediction;
- alpha or arbitrage;
- profitable execution or realized PnL;
- a finality premium;
- protocol-finality latency;
- statistical independence of overlapping observations.

No p-values, confidence intervals, regressions, or post-hoc exposure thresholds
were introduced for the initial confirmatory result.

See
[`research/phase3/MARKET_INSTABILITY_CONTRACT.md`](research/phase3/MARKET_INSTABILITY_CONTRACT.md)
for the pre-registered methodology,
[`research/phase3/CONFIRMATORY_DATASET_PROVENANCE.md`](research/phase3/CONFIRMATORY_DATASET_PROVENANCE.md)
for the frozen dataset provenance, and
[`research/phase3/MARKET_INSTABILITY_RESULT.md`](research/phase3/MARKET_INSTABILITY_RESULT.md)
for the canonical empirical result.

## Evidence Discipline

The system separates observation from inference.

It does not:

- assign undocumented semantics to Kuru `U`;
- treat quote identity as order identity;
- classify missing later-state quotes as consensus rejection;
- interpret client receive-time differences as protocol-finality latency;
- treat pooled observation counts as probabilities;
- classify a cross-venue difference as executable arbitrage;
- treat static captured-book fillability as realized execution;
- assume MON_USDC and MON-USD are economically identical;
- infer causal finality effects from simultaneous state views.

Raw observations are preserved before transformation. Missing or insufficient evidence is surfaced rather than silently filled.

## Evidence Map

### Phase 0

- [`PHASE0_RESULT.md`](research/phase0/PHASE0_RESULT.md) — Phase 0 conclusion and Phase 1 gate.
- [`DATA_CONTRACT.md`](research/phase0/DATA_CONTRACT.md) — field semantics and evidence boundaries.
- [`NORMALIZATION_EVIDENCE.md`](research/phase0/NORMALIZATION_EVIDENCE.md) — Kuru normalization verification.
- [`QUOTE_LINEAGE_EMPIRICAL_RESULT.md`](research/phase0/quote_lineage_evidence/QUOTE_LINEAGE_EMPIRICAL_RESULT.md) — multi-window quote-lineage evidence.

### Phase 1

- [`PHASE1_RESULT.md`](research/phase1/PHASE1_RESULT.md) — canonical Phase 1 conclusion.
- [`ALIGNMENT_CONTRACT.md`](research/phase1/ALIGNMENT_CONTRACT.md) — backward-as-of PIT reference policy.
- [`STALENESS_POLICY.md`](research/phase1/STALENESS_POLICY.md) — frozen reference-age sensitivity methodology.
- [`TOP_OF_BOOK_CONTRACT.md`](research/phase1/TOP_OF_BOOK_CONTRACT.md) — state-conditioned top-of-book methodology.
- [`EXECUTABLE_DEPTH_CONTRACT.md`](research/phase1/EXECUTABLE_DEPTH_CONTRACT.md) — Kuru depth/slippage methodology.
- [`DEPTH_EXECUTION_RESULT_NOTE.md`](research/phase1/DEPTH_EXECUTION_RESULT_NOTE.md) — Kuru executable-depth result.
- [`COINBASE_L2_RECONSTRUCTION_CONTRACT.md`](research/phase1/COINBASE_L2_RECONSTRUCTION_CONTRACT.md) — historical full-Level2 reconstruction.
- [`COINBASE_QUANTITY_UNIT_EVIDENCE.md`](research/phase1/COINBASE_QUANTITY_UNIT_EVIDENCE.md) — Coinbase MON quantity binding.
- [`CROSS_VENUE_EXECUTION_CONTRACT.md`](research/phase1/CROSS_VENUE_EXECUTION_CONTRACT.md) — final PIT cross-venue methodology.
- [`CROSS_VENUE_EXECUTION_RESULT_NOTE.md`](research/phase1/CROSS_VENUE_EXECUTION_RESULT_NOTE.md) — final cross-venue empirical result.

### Phase 2

- [`TEMPORAL_OUTCOME_CONTRACT.md`](research/phase2/TEMPORAL_OUTCOME_CONTRACT.md) — pre-registered temporal-outcome methodology.
- [`TEMPORAL_OUTCOME_RESULT_NOTE.md`](research/phase2/TEMPORAL_OUTCOME_RESULT_NOTE.md) — canonical Phase 2 empirical result and research decision.

### Phase 3

- [`MARKET_INSTABILITY_CONTRACT.md`](research/phase3/MARKET_INSTABILITY_CONTRACT.md) — pre-registered Phase 3 market-instability methodology and confirmatory collection protocol.
- [`CONFIRMATORY_DATASET_PROVENANCE.md`](research/phase3/CONFIRMATORY_DATASET_PROVENANCE.md) — frozen ten-capture confirmatory dataset provenance and integrity binding.
- [`MARKET_INSTABILITY_RESULT.md`](research/phase3/MARKET_INSTABILITY_RESULT.md) — canonical Phase 3 confirmatory empirical result and claim boundaries.

## Core Implementation

Phase 2 temporal components:

- `temporal_outcome.py` — frozen-horizon, point-in-time future-outcome construction and explicit right-censoring;
- `temporal_aggregation.py` — pooled, capture-level, sign, and deterministic non-overlapping temporal summaries;
- `scripts/analyze_temporal_outcomes.py` — provenance-bound deterministic Phase 2 report orchestration.


Phase 3 market-instability components:

- `market_instability.py` — transforms canonical temporal rows into the frozen absolute proposed-finalized disagreement exposure and absolute Coinbase forward-movement outcome;
- `market_instability_aggregation.py` — deterministic average-rank Spearman association, explicit undefined-correlation handling, capture-level robustness, and non-overlapping sensitivity;
- `scripts/analyze_market_instability.py` — frozen-dataset-bound deterministic Phase 3 confirmatory report orchestration.

Key modules include:

- `normalization.py` — Kuru price and size normalization;
- `kuru_ws.py` — multi-state Kuru WebSocket evidence;
- `quote_lineage.py` — episode-aware quote lineage;
- `dual_ws.py` — concurrent Kuru/Coinbase capture controls;
- `alignment.py` — point-in-time backward-as-of reference selection;
- `top_of_book.py` — state-conditioned top-of-book analysis;
- `depth_execution.py` — deterministic depth and sweep primitives;
- `depth_panel.py` — Kuru four-state executable-depth panels;
- `coinbase_l2_reconstruction.py` — historical Coinbase Level2 reconstruction;
- `cross_venue_execution.py` — PIT-aligned cross-venue execution/depth rows;
- `cross_venue_aggregation.py` — capture-level and pooled cross-venue summaries.

The repository remains a research system, not a trading bot.
