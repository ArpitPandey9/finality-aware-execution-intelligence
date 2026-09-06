# Finality-Aware Cross-Venue Execution Intelligence Engine

Research system for studying how observable on-chain order-book liquidity and execution conditions change across blockchain consensus/finality-state views and an external centralized-market reference.

## Status

**Phase 0 — Data & Research Feasibility: COMPLETE**

**Technical feasibility: PASS**

**Next:** Phase 1 — point-in-time cross-venue alignment and state-conditioned execution-intelligence methodology.

The repository currently has **79 passing tests**.

No trading-performance, arbitrage, alpha, or profitability claim is made.

## Research Question

Kuru exposes order-book views for Monad proposed, voted, finalized, and committed states.

The project asks whether observable execution conditions differ across those state views and how they compare with an external Coinbase market reference.

Current markets:

- Kuru / Monad: `MON_USDC`
- Coinbase: `MON-USD`

USD and USDC are not assumed to be economically identical.

## Phase 0 Result

Phase 0 established that the evidence pipeline required for this research question is technically feasible.

The system now supports:

- Kuru state-specific order-book acquisition;
- independently verified MON-USDC price and size normalization;
- raw evidence preservation with SHA256 integrity checks;
- Kuru multi-state WebSocket capture;
- episode-aware quote-lineage analysis;
- Coinbase Level-2 reconstruction from a valid snapshot baseline;
- wrapper-level Coinbase sequence-integrity controls;
- concurrent Kuru and Coinbase WebSocket acquisition;
- same-process monotonic receive timestamps.

The complete Phase 0 conclusion is documented in [`research/phase0/PHASE0_RESULT.md`](research/phase0/PHASE0_RESULT.md).

## Empirical Quote-Lineage Evidence

Five 60-second Kuru WebSocket windows contained **6,159 messages**.

- exact price + quantity identity: **491 evaluable episodes / 305 ordered observations**
- price-only identity: **425 evaluable episodes / 289 ordered observations**

The pooled proportions are descriptive only and are not treated as stable population survival probabilities.

See [`QUOTE_LINEAGE_EMPIRICAL_RESULT.md`](research/phase0/quote_lineage_evidence/QUOTE_LINEAGE_EMPIRICAL_RESULT.md).

## Evidence Discipline

The system separates observation from inference. It does not assign undocumented semantics to Kuru `U`, treat quote identity as order identity, classify missing later-state quotes as consensus rejection, interpret client receive-time differences as protocol-finality latency, or classify a cross-venue price difference as executable arbitrage.

Raw observations are preserved before transformation. Missing or insufficient evidence is surfaced rather than silently filled.

## Evidence Map

- [`PHASE0_RESULT.md`](research/phase0/PHASE0_RESULT.md) — Phase 0 conclusion and Phase 1 gate.
- [`DATA_CONTRACT.md`](research/phase0/DATA_CONTRACT.md) — field semantics and evidence boundaries.
- [`NORMALIZATION_EVIDENCE.md`](research/phase0/NORMALIZATION_EVIDENCE.md) — Kuru normalization verification.
- [`QUOTE_LINEAGE_EMPIRICAL_RESULT.md`](research/phase0/quote_lineage_evidence/QUOTE_LINEAGE_EMPIRICAL_RESULT.md) — multi-window empirical evidence.

## Core Implementation

- `normalization.py` — Kuru price and size normalization.
- `kuru_ws.py` — multi-state WebSocket evidence.
- `quote_lineage.py` — episode-aware quote lineage.
- `lineage_aggregation.py` — multi-capture aggregation.
- `lineage_evidence.py` — provenance-bound evidence export.
- `dual_ws.py` — Coinbase reconstruction and dual-stream controls.
- `capture_dual_ws.py` — concurrent Kuru + Coinbase acquisition.

## Phase 1

Phase 1 focuses on **point-in-time alignment**, not additional venue sprawl.

The next gate is deterministic as-of matching, explicit staleness limits, state-conditioned spread/depth/slippage methodology, USD/USDC basis treatment, and sensitivity analysis without look-ahead.

Only after those controls are defined should cross-venue differences be interpreted economically.

The project remains a research system, not a trading bot.
