# Finality-Aware Cross-Venue Execution Intelligence Engine

Research system for studying how observable on-chain order-book liquidity and simulated execution conditions differ across blockchain consensus/finality-state views and an external centralized-market reference.

## Status

**Phase 0 — Data & Research Feasibility: COMPLETE**

**Phase 1 — Point-in-Time Cross-Venue Execution Intelligence: COMPLETE**

**Current full repository test suite: 217 passing tests**

The project has established a provenance-bound, anti-lookahead research pipeline spanning Kuru / Monad state-specific order books and reconstructed Coinbase MON-USD Level2 books.

No trading-performance, arbitrage, alpha, profitability, execution-probability, venue-superiority, or causal-finality claim is made.

**Next research gate:** pre-specify temporal market-response and adverse-selection methodology before inspecting future outcomes.

## Research Question

Kuru exposes order-book views for Monad proposed, voted, finalized, and committed states.

The project studies whether observable execution conditions differ across those simultaneous state views, how those conditions compare with an external Coinbase market reference, and—subject to a future pre-specified design—how market conditions evolve after those observations.

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

## Core Implementation

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
