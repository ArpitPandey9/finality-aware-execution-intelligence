# Phase 1 — PIT-Aligned Cross-Venue Executable Comparison Contract

## Status

Methodology frozen before empirical cross-venue execution results.

## Research Question

For the frozen five dual-WebSocket captures, when each Kuru MON_USDC state view is compared with the latest point-in-time eligible Coinbase MON-USD reconstructed Level2 book, how do displayed depth and deterministic simulated execution conditions differ?

This is a descriptive market-microstructure comparison.

It is not a trading strategy, arbitrage test, causal finality test, or realized-execution study.

## Markets

Kuru:

`MON_USDC`

Coinbase:

`MON-USD`

Common base asset:

`MON`

Quote assets differ:

- Kuru: `USDC`;
- Coinbase: `USD`.

Therefore:

`Kuru MON_USDC != Coinbase MON-USD`

The common MON base asset supports common fixed-base-quantity sweeps.

The USD-versus-USDC quote basis remains and must not be silently removed or treated as zero.

## Dataset

The empirical study uses the same frozen five verified dual-WebSocket captures used by the preceding Phase 1 analyses.

Dataset identity and source hashes must remain unchanged.

No additional capture may be inserted into the primary result after results are observed.

## Point-in-Time Alignment

The existing Phase 1 alignment implementation is authoritative.

For each Kuru record with receive monotonic time:

`t_kuru`

the Coinbase reference is the target MON-USD Level2 record with the greatest captured receive monotonic time satisfying:

`t_coinbase <= t_kuru`

No future Coinbase record is eligible.

If multiple eligible Coinbase records have the same receive monotonic timestamp, the later original source record index is selected.

No interpolation is permitted.

No event-time reordering is permitted.

No future repair is permitted.

## Freshness Sensitivity

The existing frozen Coinbase reference-age thresholds remain:

- `250 ms` — strict;
- `500 ms` — moderate;
- `1000 ms` — lenient.

Equality with the threshold is eligible.

A reference older than the threshold is stale.

The three thresholds are nested sensitivity bands.

They are not independent datasets or independent experiments.

The primary comparison must preserve the existing alignment statuses:

- `ALIGNED`;
- `NO_PRIOR_REFERENCE`;
- `STALE_REFERENCE`;
- `INSUFFICIENT_SOURCE_EVIDENCE`.

Only `ALIGNED` observations may produce cross-venue economic comparison rows.

## Coinbase Full-Book Binding

The selected alignment `coinbase_reference.record_index` refers to the original index in:

`sources.coinbase.records`

Coinbase full-book reconstruction must process stored Coinbase wrapper records in original capture order from the beginning of the capture through that selected record index.

All wrappers are processed for sequence integrity, including non-target wrappers.

The full book attached to a Kuru observation must be exactly the reconstructed state after the selected original Coinbase record.

The reconstruction must use raw Coinbase WebSocket messages.

Stored derived top-of-book or level-count fields may be used for parity verification only.

The same selected Coinbase reconstructed book is attached to all four Kuru state views belonging to the same Kuru observation.

## Coinbase Reconstruction Integrity

Before economic metrics are emitted, the Coinbase reconstruction must preserve the established reconstruction gate:

- first target MON-USD Level2 event is a snapshot;
- wrapper sequences are contiguous;
- target updates occur only after initialization;
- zero quantity removes a price level;
- prices and quantities use exact Decimal arithmetic;
- reconstructed top matches stored top;
- reconstructed bid-level count matches stored count;
- reconstructed offer-level count matches stored count;
- reconstructed book is two-sided;
- reconstruction contains no crossed book.

Any reconstruction integrity failure makes the affected capture insufficient for economic comparison.

No partial repair is permitted.

## Quantity Units

Kuru MON_USDC captured raw levels use the verified market-specific normalization:

`human_price = raw_price / 1e18`

`human_quantity_MON = raw_quantity / 1e10`

Coinbase MON-USD Level2:

`price_level`

is used directly as the displayed USD price.

`new_quantity`

is used directly as MON base quantity.

No additional scaling is applied to Coinbase quantities.

This Coinbase quantity binding is scoped to the observed MON-USD interfaces and prior empirical WS-to-REST evidence.

## Frozen Execution Sides

The existing execution-side definitions remain authoritative.

### BUY

A simulated MON buy consumes offers / asks from lowest price upward.

### SELL

A simulated MON sell consumes bids from highest price downward.

## Frozen Base-Quantity Targets

The existing primary target ladder remains unchanged:

- `200 MON`;
- `2,000 MON`;
- `20,000 MON`;
- `200,000 MON`.

These quantities were frozen before the prior Kuru executable-depth results and remain frozen for the cross-venue primary comparison.

No larger or smaller target may be introduced into the primary analysis after empirical results are inspected.

Any later target-size extension must be explicitly labeled post-hoc sensitivity analysis.

## Frozen Depth Bands

Displayed depth is evaluated within the existing same-venue, same-side best-price bands:

- `5 bps`;
- `10 bps`;
- `25 bps`;
- `50 bps`.

For BUY, depth is measured from that venue's best offer.

For SELL, depth is measured from that venue's best bid.

Each venue therefore uses its own contemporaneous best price as the band anchor.

This avoids pretending that USD and USDC are the same quote asset.

## Static Sweep

For each eligible observation, state, side, and frozen target:

1. use only the captured/reconstructed displayed book available at that point in time;
2. walk price levels deterministically in execution order;
3. consume quantities until the target is filled or captured depth is exhausted;
4. allow partial consumption of the final level;
5. compute VWAP only from consumed displayed levels;
6. compute side-normalized slippage relative to that venue/state's own best executable price.

The sweep assumes no future order-book change.

It does not model queue position, cancellation, matching-engine priority, inclusion, latency, market reaction, or replenishment.

## Fill Status

Each venue-side-target sweep returns one of:

- `FULLY_FILLED_IN_CAPTURED_BOOK`;
- `INSUFFICIENT_CAPTURED_DEPTH`.

`FULLY_FILLED_IN_CAPTURED_BOOK` means only that the target can be consumed in the static captured/reconstructed displayed book.

It is not an execution probability and does not establish that a real order would fill.

`INSUFFICIENT_CAPTURED_DEPTH` means only that the preserved book representation does not contain enough displayed quantity for that synthetic sweep.

It does not establish that the venue itself lacked executable liquidity outside the captured representation.

## Venue-Internal Slippage

For BUY:

`slippage_bps = (VWAP / best_offer - 1) * 10000`

For SELL:

`slippage_bps = (1 - VWAP / best_bid) * 10000`

The metric is non-negative for a valid ordered static sweep.

Venue-internal slippage is the primary execution-shape metric because each venue is normalized relative to its own contemporaneous best price.

## Cross-Venue Slippage Gap

When both venues fully fill the same MON target:

`slippage_gap_bps = Kuru_slippage_bps - Coinbase_slippage_bps`

Interpretation:

- positive: greater simulated adverse book-walk slippage on Kuru;
- negative: greater simulated adverse book-walk slippage on Coinbase;
- zero: equal simulated adverse slippage.

This is a descriptive static-book difference.

It is not a trading edge, realized transaction-cost difference, profit estimate, or venue-ranking statistic.

## Cross-Venue Displayed-Depth Gap

For each frozen own-best depth band:

`depth_gap_MON = Kuru_depth_MON - Coinbase_depth_MON`

Interpretation:

- positive: more captured displayed MON depth on Kuru within the respective own-best band;
- negative: more reconstructed displayed MON depth on Coinbase within its respective own-best band;
- zero: equal displayed MON depth.

The two bands are anchored to different quote markets and therefore do not represent identical absolute price intervals.

## Fillability Transition

For each state, side, target, threshold, and aligned observation, classify:

- `BOTH_FULL`;
- `KURU_ONLY_FULL`;
- `COINBASE_ONLY_FULL`;
- `NEITHER_FULL`.

These are descriptive counts.

They must not be reported as execution probabilities.

## VWAP Cross-Venue Difference

When both venues fully fill, venue-specific VWAP values may be preserved.

A secondary descriptive cross-venue value may be computed:

`vwap_difference_bps = (Kuru_VWAP - Coinbase_VWAP) / Coinbase_VWAP * 10000`

This metric mixes:

- venue price differences;
- USD-versus-USDC quote basis;
- book shape;
- point-in-time reference age.

It must therefore be labeled a cross-quote descriptive VWAP difference.

It must not be called:

- arbitrage;
- executable edge;
- finality premium;
- profit;
- pure execution-cost difference.

## State Views

Kuru state views remain:

- `proposed`;
- `voted`;
- `finalized`;
- `committed`.

For one Kuru observation, all four state views use the same selected Coinbase reference book.

Therefore state-conditioned cross-venue differences are within-observation descriptive contrasts.

They are not temporal transitions between four independent Coinbase observations.

## Aggregation

For each freshness threshold, Kuru state, side, target, and where applicable depth band, report auditable descriptive summaries.

At minimum preserve:

- observation count;
- aligned count;
- stale count;
- no-prior count;
- insufficient-source count;
- fillability-transition counts;
- Kuru full-fill count;
- Coinbase full-fill count;
- paired both-full count;
- slippage-gap distribution where both fully fill;
- depth-gap distribution;
- secondary cross-quote VWAP-difference distribution where both fully fill.

Distribution summaries use:

- minimum;
- p05;
- p25;
- p50;
- p75;
- p95;
- maximum.

Quantiles use deterministic linear interpolation consistent with the existing Phase 1 aggregation methodology.

These are descriptive quantiles, not confidence intervals.

## Capture-Level Diagnostics

Pooled results must be accompanied by capture-level summaries.

At minimum, capture-level medians must be available for primary slippage-gap and displayed-depth-gap metrics.

This is used to determine whether a pooled result is dominated by one capture.

The five captures are observation windows, not five independent market experiments.

## Finalized-versus-Committed Boundary

The prior frozen five-capture dataset showed exact finalized-versus-committed raw Kuru full-book equality for all `8255` observed Kuru panels.

The cross-venue analysis may reproduce identical finalized and committed Kuru-side metrics as a consequence of that dataset-specific equality.

This must not be generalized into:

- protocol semantic equivalence;
- a Kuru invariant;
- a finality property.

## Tail Handling

No observation may be deleted, capped, winsorized, or silently repaired because its simulated slippage is large.

Any tail forensic threshold introduced after primary results are observed must be labeled post-hoc.

Extreme outcomes remain part of the primary descriptive distribution unless source integrity fails.

## Costs Excluded

The primary cross-venue executable comparison excludes:

- Coinbase fees;
- Kuru trading fees unless separately source-bound;
- gas;
- transaction inclusion cost;
- priority fees;
- MEV;
- bridge cost;
- transfer cost;
- stablecoin conversion cost.

No net-profit or net-execution-cost claim may be made without a separate point-in-time cost methodology.

## No Causal Finality Claim

The state-conditioned comparison does not establish that consensus/finality state caused any observed difference.

The four Kuru state views are descriptive state-conditioned representations from captured messages.

The Coinbase reference is an independently observed prior market state.

Any association remains observational.

## Claim Boundaries

The analysis may describe:

- PIT-aligned displayed liquidity;
- deterministic captured-book fillability;
- static simulated VWAP;
- venue-internal simulated slippage;
- descriptive Kuru-minus-Coinbase depth differences;
- descriptive Kuru-minus-Coinbase slippage differences;
- cross-quote VWAP differences with explicit USD/USDC basis limitation;
- state-conditioned distributions.

The analysis must not claim:

- arbitrage;
- alpha;
- expected profit;
- realized execution;
- fill probability;
- venue superiority;
- causal finality effect;
- finality premium;
- network latency;
- exchange latency;
- consensus latency;
- protocol-finality latency;
- USD/USDC parity;
- semantic equivalence of finalized and committed.

## Reproducibility Gate

Before empirical interpretation, the implementation must:

1. reproduce the same ordered five-capture dataset fingerprint;
2. preserve source SHA256 provenance;
3. use the existing alignment implementation;
4. reconstruct Coinbase books only from raw stored messages;
5. bind selected full books by original Coinbase record index;
6. reproduce stored Coinbase top and level-count parity;
7. use exact Decimal arithmetic;
8. use only the frozen thresholds, bands, sides, and targets;
9. produce deterministic output across repeated runs;
10. pass the full repository test suite.

Only after these gates pass may empirical cross-venue results be interpreted.
