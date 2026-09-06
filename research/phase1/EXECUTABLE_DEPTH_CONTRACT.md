# Phase 1 — State-Conditioned Executable Depth and Slippage Contract

## Status

Methodology frozen before inspecting state-conditioned depth, fillability, VWAP, or slippage results.

## Objective

Measure how observed Kuru MON_USDC book depth and deterministic simulated sweep outcomes differ across the simultaneously observed:

- proposed;
- voted;
- finalized;
- committed

state views.

This stage extends the completed price-only top-of-book analysis into quantity-aware market-microstructure analysis.

## Initial Scope

The initial gate is Kuru state-conditioned execution-depth analysis.

It does not yet perform a full Kuru-versus-Coinbase executable-book comparison.

Coinbase full-book point-in-time reconstruction is a separate downstream gate.

Because this initial layer is Kuru-only, Coinbase reference-age thresholds of 250 ms, 500 ms, and 1000 ms are not applied here. Those thresholds remain part of the cross-venue point-in-time methodology and must not be imported into this Kuru-only depth analysis.

The purpose of separating these layers is to avoid mixing:

- Kuru quantity normalization;
- Kuru state-conditioned book mechanics;
- Coinbase book reconstruction;
- cross-venue basis and timing effects

inside one uncontrolled analysis step.

## Source Evidence Requirement

A source observation is eligible only when:

- the source capture passes its integrity gate;
- the Kuru market identity is `MON_USDC`;
- the source record contains the preserved raw multi-state WebSocket message;
- all four required state books are present;
- each state contains structurally valid bid and ask arrays;
- the full-depth numeric representation passes the verified WebSocket normalization contract.

No missing state book may be silently repaired from another message.

No future message may be substituted.

Kuru `U` remains an observed stream grouping field only.

## Numeric Representation

For every Kuru raw level:

`[price_raw, quantity_raw]`

use exact Decimal arithmetic.

For the observed MON_USDC representation:

`human_price = price_raw / 1e18`

`human_base_size = quantity_raw / 1e10`

Binary floating-point arithmetic must not be used for economic calculations.

## Book Validation

For every state:

- every economic level must contain exactly a usable price and quantity;
- raw price and quantity values must parse as non-negative integer representations;
- normalized economic prices must be strictly positive;
- normalized economic quantities used for execution must be strictly positive;
- bid prices must be non-increasing in source order;
- ask prices must be non-decreasing in source order;
- best ask must not be below best bid.

Source order is preserved.

The implementation must not silently sort, aggregate, interpolate, fabricate, or repair malformed book levels.

A structurally invalid state makes the complete four-state execution panel ineligible.

## Captured-Depth Boundary

All depth metrics refer only to liquidity present in the captured WebSocket book.

Failure to fill a target quantity means:

`INSUFFICIENT_CAPTURED_DEPTH`

It does not mean that the venue itself could not execute that quantity through liquidity not represented in the captured payload or through other execution mechanisms.

## Side Semantics

A simulated MON purchase consumes the ask side.

A simulated MON sale consumes the bid side.

The analysis is a deterministic walk through observed displayed levels.

It does not submit an order or model queue priority, cancellation during execution, transaction inclusion, gas, fees, MEV, latency, or market reaction.

## Frozen Depth Bands

State-conditioned displayed base-asset depth is measured within the following price-distance bands from the same state's best price:

- `5 bps`;
- `10 bps`;
- `25 bps`;
- `50 bps`.

For a buy-side depth band with best ask `A0`, include asks satisfying:

`ask_price <= A0 * (1 + band_bps / 10000)`

For a sell-side depth band with best bid `B0`, include bids satisfying:

`bid_price >= B0 * (1 - band_bps / 10000)`

Report base-asset quantity inside each band.

These bands are frozen before empirical state-conditioned results are inspected.

## Frozen Simulated Base-Quantity Targets

The primary target sizes are:

- `200 MON`;
- `2,000 MON`;
- `20,000 MON`;
- `200,000 MON`.

The ladder is derived mechanically from the verified MON_USDC minimum size of `200 MON`:

- `1x`;
- `10x`;
- `100x`;
- `1000x`.

The primary target set must not be changed after inspecting results merely to improve fillability or produce a stronger state contrast.

Any later additional size is a separately labeled sensitivity analysis.

## Deterministic Sweep Algorithm

For target base quantity `Q`:

1. initialize remaining quantity to `Q`;
2. walk source levels from best price outward;
3. at each level fill:

   `fill_i = min(remaining, level_quantity_i)`;

4. accumulate base quantity:

   `filled_base += fill_i`;

5. accumulate quote amount:

   `quote_amount += fill_i * level_price_i`;

6. stop when `filled_base == Q` or captured levels are exhausted.

No interpolation beyond displayed quantity is permitted.

A partial final level may be consumed.

## Fillability

A target is `FULLY_FILLED_IN_CAPTURED_BOOK` when:

`filled_base == target_base`

Otherwise it is:

`INSUFFICIENT_CAPTURED_DEPTH`

For insufficient captured depth:

- filled quantity remains reported;
- unfilled quantity remains reported;
- available captured depth remains reported;
- VWAP and slippage for the requested full target are not reported as though the target filled.

## VWAP

For a fully filled target:

`VWAP = total_quote_amount / target_base`

For a buy simulation, the benchmark is the same-state best ask.

For a sell simulation, the benchmark is the same-state best bid.

## Side-Normalized Slippage

For a buy:

`slippage_bps = (VWAP / best_ask - 1) * 10000`

For a sell:

`slippage_bps = (1 - VWAP / best_bid) * 10000`

Under a valid monotonic book these quantities are expected to be non-negative.

A negative result is treated as a validation failure rather than silently accepted.

## Required Per-Sweep Output

Each state-side-target result must preserve at minimum:

- source capture identifier;
- Kuru source record index;
- Kuru receive timestamps;
- observed `U`;
- state name;
- side;
- target base quantity;
- raw and normalized best price;
- captured side level count;
- total captured base depth;
- fillability status;
- filled base quantity;
- unfilled base quantity;
- levels touched;
- final level partially consumed flag;
- quote amount consumed;
- VWAP when fully filled;
- slippage bps when fully filled.

## Required Depth Output

For every complete state panel and side, report:

- total captured base depth;
- base depth within `5 bps`;
- base depth within `10 bps`;
- base depth within `25 bps`;
- base depth within `50 bps`.

## Within-Panel State Contrasts

State comparisons are only calculated inside the same complete Kuru observation.

Predefined pairs are:

- proposed versus voted;
- proposed versus finalized;
- proposed versus committed;
- voted versus finalized;
- finalized versus committed.

For each side and target quantity, report fillability transition counts:

- both fully filled;
- only first state fully filled;
- only second state fully filled;
- neither fully filled.

Slippage deltas are calculated only when both states fully fill the same target.

For pair `(state_a, state_b)`:

`slippage_delta_bps = state_b.slippage_bps - state_a.slippage_bps`

A negative value means only that the second simultaneously observed state view has lower simulated displayed-book slippage for that side and target.

It does not establish a temporal transition or causal effect of finality.

For the same side and depth band, define:

`depth_delta_base = state_b.depth_within_bps - state_a.depth_within_bps`

A positive depth delta means only that the second simultaneously observed state view contains more captured displayed base-asset quantity inside that band. A negative value means less captured displayed quantity.

Depth-band deltas are calculated from the same observation and same side only.

For paired slippage and depth deltas, report minimum, p05, p25, p50, p75, p95, maximum, and positive/zero/negative counts where the metric is defined.

## Aggregation

For each state, side, and frozen target size report:

- eligible panel count;
- fully filled count;
- insufficient-captured-depth count;
- full-fill proportion with numerator and denominator;
- VWAP/slippage descriptive distributions only among fully filled targets;
- capture-level fill counts;
- capture-level median slippage where available.

For each state, side, and frozen depth band report:

- observation count;
- minimum;
- p05;
- p25;
- p50;
- p75;
- p95;
- maximum;
- capture-level median depth.

VWAP and slippage distributions use the same descriptive statistics: minimum, p05, p25, p50, p75, p95, and maximum.

Percentiles use the repository's existing deterministic linear-interpolation percentile rule.

These descriptive quantiles are not confidence intervals.

Pooled statistics are descriptive.

Capture windows are not assumed independent observations.

## Claim Boundary

The analysis describes deterministic simulated sweeps through captured displayed book levels.

It does not model or prove:

- actual order submission;
- transaction inclusion;
- queue position;
- cancellation risk during execution;
- price impact caused by the simulated trade;
- gas or transaction costs;
- trading fees unless separately verified and explicitly modeled;
- MEV;
- execution latency;
- consensus latency;
- protocol-finality latency;
- arbitrage;
- alpha;
- expected profit;
- realized profit;
- a causal finality premium;
- universal superiority of finalized or committed liquidity.

A simultaneously observed state contrast is not automatically a temporal quote transition.

## Initial Gate

Implementation passes only when tests demonstrate:

- exact Decimal-based full-depth normalization;
- rejection of malformed or unordered books;
- complete four-state panel handling;
- deterministic depth-within-bps calculations;
- deterministic partial-level sweep handling;
- correct buy and sell VWAP calculations;
- correct side-normalized slippage;
- explicit insufficient-captured-depth behavior;
- frozen target-size enforcement;
- frozen depth-band enforcement;
- within-panel-only state pairing;
- preservation of raw provenance;
- preservation of claim boundaries;
- deterministic reproduction over the provenance-verified five-capture dataset.

Only after this gate passes should a full point-in-time Kuru-versus-Coinbase executable-book comparison be implemented.
