# Phase 0 — Data & Research Feasibility Closure

## Status

**COMPLETE — technical feasibility: PASS**

Phase 0 established whether the project can obtain, normalize, preserve,
and audit the evidence required for a finality-aware cross-venue
research design.

This does **not** validate the economic hypothesis. No trading edge,
arbitrage opportunity, finality premium, causal relationship, or
profitability result has been established.

Phase 0 closed against repository commit `0a89745`.

## Research Scope

The system studies whether observable Kuru order-book conditions differ
across Monad's proposed, voted, finalized, and committed state views,
and how those observations compare with an external Coinbase reference.

Markets:

- Kuru / Monad: `MON_USDC`
- Coinbase: `MON-USD`

Coinbase is an independent market reference. It is not used to infer
Kuru numeric units. USD and USDC are not assumed to be identical.

## Technical Feasibility Evidence

### Endpoint and normalization

Kuru state-specific books and Coinbase Level-2 data were successfully
accessed during live feasibility probes.

For Kuru MON-USDC, independent on-chain and same-block verification
established:

- `pricePrecision = 1e8`
- `sizePrecision = 1e10`
- human price = REST price / `1e18`
- human base size = REST quantity / `sizePrecision`

This establishes numeric representation, not liquidity provenance.

### REST limitation

Near-simultaneous REST requests can return different state block
identifiers and top-book representations.

Because REST freshness and update cadence can affect those observations,
REST differences are not interpreted as finality latency, protocol
latency, or economic edge.

### Kuru WebSocket evidence

The Kuru `mon_usdc@monadDepth` stream was captured with raw messages,
client receive timestamps, state-specific payloads, and SHA256
integrity evidence.

Observed behavior established that repeated `U` values are not
sufficient to identify duplicate messages. `U` is therefore retained
only as an observed stream grouping field; no undocumented block-number
or event-ID semantics are assigned to it.

### Episode-aware quote lineage

Five 60-second Kuru WebSocket windows contained **6,159 messages**.

Exact price + quantity identity:

- evaluable episodes: **491**
- ordered proposed → voted → finalized → committed observations: **305**
- pooled ordered proportion: **62.12%**, descriptive only

Price-only identity:

- evaluable episodes: **425**
- ordered observations: **289**
- pooled ordered proportion: **68.00%**, descriptive only

The capture-level variation is material. These pooled values are not
treated as population survival probabilities, and the windows are not
assumed to be statistically independent.

### Coinbase Level-2 reconstruction

Live Coinbase `MON-USD` WebSocket validation established that:

- the first target Level-2 message can provide the snapshot baseline;
- subsequent updates can reconstruct the local book;
- observed side labels are `bid` and `offer`;
- zero quantity removes a price level;
- wrapper sequence integrity can be checked independently from L2-only
  sequence deltas.

The dual-capture gate rejects a capture if target updates precede the
required snapshot baseline.

## Final Dual-WebSocket Validation

Final Phase 0 capture:

`dual_ws_20260906T001804423491Z.json`

SHA256:

`871ca2894fa845ae26832ea2954dd1d7b621241140780cee2e6ad1ae4d2deddc`

Observed validation:

- Kuru target messages: **279**
- Kuru unique observed `U`: **28**
- Coinbase target L2 messages: **49**
- Coinbase snapshots: **1**
- Coinbase updates: **48**
- Coinbase wrapper sequence gaps: **0**
- crossed/locked reconstructed messages: **0**
- final reconstructed bid levels: **543**
- final reconstructed offer levels: **628**
- target-message-envelope overlap:
  **9.249280718 seconds**
- overall gate: **PASS**

The overlap value describes only the overlap between intervals bracketed
by the first and last locally received target messages for each source.
It is not exchange-clock synchronization, network latency, venue
latency, Monad consensus latency, or protocol-finality latency.

The raw dual capture and its hash sidecar remain in the ignored
`data/raw/` evidence area and are not embedded in the public repository.

## What Phase 0 Establishes

Phase 0 establishes that:

- Kuru state-specific market data is accessible;
- Kuru numeric normalization is evidence-backed;
- repeated raw WebSocket observations can be preserved and hashed;
- quote-lineage analysis can be performed conservatively;
- Coinbase Level-2 can be reconstructed from a valid snapshot baseline;
- Kuru and Coinbase can be captured concurrently using a shared
  same-process monotonic receive clock;
- capture integrity failures can be surfaced explicitly.

## What Phase 0 Does Not Establish

Phase 0 does **not** establish:

- a predictable finality premium;
- profitable proposed-state arbitrage;
- a trading signal or trading edge;
- causal effects from consensus state to Coinbase prices;
- that finalized liquidity is always better or safer;
- that a quote absent from a later state was rejected by consensus;
- that quote identity establishes individual order identity or intent;
- that client-observed first-sighting differences measure protocol
  finality;
- that USD/USDC basis can be ignored;
- that displayed Kuru liquidity consists only of resting limit orders.

## Evidence Boundary

The committed quote-lineage evidence bundle is provenance-bound.

Its source filenames and SHA256 hashes are recorded, but the underlying
raw WebSocket captures are not embedded in the repository. Reproduction
therefore requires those source captures to be available and to verify
against their recorded hashes.

## Phase 0 Conclusion

**Technical feasibility: PASS.**

The acquisition and evidence layer is sufficient to move into
point-in-time cross-venue research.

Further venue expansion is not required for the next gate.

## Phase 1 Research Gate

The next question is:

> Can Kuru state-conditioned order-book observations be aligned to a
> Coinbase reference on a defensible point-in-time basis, with explicit
> staleness and USD/USDC-basis controls, so that spread, depth, slippage,
> and cross-venue price conditions can be measured without look-ahead?

Phase 1 should prioritize:

1. deterministic as-of alignment using client-observed receive time;
2. explicit staleness and maximum-age rules;
3. state-conditioned spread and midpoint comparisons;
4. depth and executable-size / slippage methodology;
5. explicit USD/USDC basis treatment;
6. sensitivity analysis and preservation of negative results.

No trading-performance or alpha claim is made by this Phase 0 closure.
