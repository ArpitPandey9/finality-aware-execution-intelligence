# Phase 1 — State-Conditioned Point-in-Time Top-of-Book Contract

## Status

Methodology contract before state-conditioned cross-venue price analysis.

This layer depends on the Phase 1 point-in-time alignment contract and frozen staleness sensitivity policy.

## Objective

For each economically eligible Kuru multi-state observation, derive comparable top-of-book price metrics for proposed, voted, finalized, and committed state views against the same backward-as-of Coinbase reference.

The purpose is to measure descriptive state-conditioned price and spread differences without introducing look-ahead, post-hoc freshness selection, or unsupported execution claims.

## Initial Scope

The initial top-of-book gate is intentionally limited to price-side metrics:

- normalized Kuru best bid and best ask;
- Kuru midpoint and spread;
- Kuru spread in basis points;
- Coinbase best bid and best offer;
- Coinbase midpoint and spread;
- Coinbase spread in basis points;
- Kuru midpoint minus Coinbase midpoint;
- Kuru-versus-Coinbase midpoint difference in basis points.

Displayed quantities may be preserved as provenance, but depth, executable size, VWAP, slippage, fill probability, and transaction-cost conclusions are outside this initial gate.

## Required Source Contract

Input must first pass the Phase 1 alignment source-validation rules.

Therefore the analysis inherits the following identity boundary:

- Kuru market: `MON_USDC`;
- Coinbase market: `MON-USD`;
- Coinbase source channel: `level2`;
- Coinbase target product: `MON-USD`.

Source-identity validation does not make `MON_USDC` and `MON-USD` economically identical markets.

## Freshness Sensitivity

Every economic result must be evaluated separately under the frozen reference-age bands:

- strict: `250 ms`;
- moderate: `500 ms`;
- lenient: `1000 ms`.

No one band is treated as the true threshold.

The three bands are sensitivity analyses over overlapping observations and must not be treated as independent samples.

For each band, only alignment rows classified as `ALIGNED` at that exact threshold are economically eligible.

`NO_PRIOR_REFERENCE`, `STALE_REFERENCE`, and `INSUFFICIENT_SOURCE_EVIDENCE` observations remain counted and auditable but do not feed economic metrics.

A directional or magnitude pattern that appears only under the lenient band must not be promoted as a robust headline result.

## State Panel Unit

One Kuru WebSocket observation contains four named state views at one local client receive time:

- proposed;
- voted;
- finalized;
- committed.

The same Coinbase backward-as-of reference must be used for all four state views from that Kuru observation.

The initial cross-state analysis uses a complete four-state panel. All four Kuru state views must contain valid best-bid and best-ask evidence before that Kuru observation enters state-conditioned economic comparison.

This prevents different state samples from being created merely because one state view is missing or malformed.

Kuru `U` remains an observed stream grouping field only and is not interpreted as a block number, event identifier, or protocol-finality timestamp.

## Numeric Rules

All calculations must use exact decimal arithmetic. Binary floating-point inputs are not permitted.

Kuru raw prices use the Phase 0 verified price normalization:

`kuru_price = raw_price / 1e18`

Coinbase reconstructed prices are parsed directly as exact decimal values.

No per-row rounding is permitted before metric calculation. Presentation rounding, if used later, must occur only after exact derived values are calculated.

## Top-of-Book Validity

For every state used in the initial economic panel:

- normalized bid and ask must be finite and non-negative;
- ask must not be below bid;
- midpoint must be greater than zero.

The Coinbase reference must likewise contain a valid reconstructed, non-crossed top of book as already required by the alignment contract.

## Economic Eligibility and Exclusion

Eligibility is evaluated once per Kuru observation for each freshness band before state rows are emitted.

The panel-level outcomes are:

- `ECONOMICALLY_ELIGIBLE`: the alignment status is `ALIGNED`, the Coinbase reference top is valid, and all four Kuru state views contain valid top-of-book price evidence;
- `INVALID_STATE_PANEL`: the alignment status is `ALIGNED`, but one or more required Kuru state views are missing or contain invalid bid/ask evidence;
- `INVALID_REFERENCE_TOP`: the alignment status is `ALIGNED`, but the attached Coinbase reference cannot produce a valid exact-decimal top of book.

Rows carrying `NO_PRIOR_REFERENCE`, `STALE_REFERENCE`, or `INSUFFICIENT_SOURCE_EVIDENCE` retain their alignment status and are not economically eligible.

Only an `ECONOMICALLY_ELIGIBLE` panel produces exactly four state-conditioned economic rows.

Invalid or ineligible observations must remain represented in capture-level and threshold-level counts. They must not be silently dropped, substituted, or repaired from future observations.

## Metric Definitions

For Kuru state bid `K_b` and ask `K_a`:

`K_mid = (K_b + K_a) / 2`

`K_spread = K_a - K_b`

`K_spread_bps = K_spread / K_mid * 10000`

For Coinbase bid `C_b` and offer `C_a`:

`C_mid = (C_b + C_a) / 2`

`C_spread = C_a - C_b`

`C_spread_bps = C_spread / C_mid * 10000`

Cross-venue midpoint difference:

`reference_mid_difference = K_mid - C_mid`

`reference_mid_difference_bps = (K_mid - C_mid) / C_mid * 10000`

A positive midpoint difference means only that the observed Kuru midpoint is numerically above the aligned Coinbase midpoint. A negative value means the reverse.

Neither sign establishes an executable trade.

## Required Derived Row Provenance

Each state-conditioned economic row must preserve at minimum:

- source capture identifier;
- freshness threshold;
- Kuru source record index;
- Kuru receive timestamps;
- observed Kuru `U`;
- state name;
- raw Kuru bid and ask;
- normalized Kuru bid and ask;
- Coinbase source record index;
- Coinbase sequence number;
- Coinbase receive timestamps;
- Coinbase best bid and offer;
- reference age in milliseconds;
- alignment status;
- all derived metric values.

One logical Kuru observation therefore produces four state rows under a given freshness band only when the complete four-state panel passes the economic validity gate.

## State-Conditioned Aggregation

For each freshness band, marginal state-conditioned summaries are calculated separately for proposed, voted, finalized, and committed.

For each Kuru state, report:

- economically eligible observation count;
- Kuru spread-bps minimum, p05, p25, p50, p75, p95, and maximum;
- cross-venue reference-midpoint-difference-bps minimum, p05, p25, p50, p75, p95, and maximum;
- cross-venue reference-midpoint-difference-bps positive, zero, and negative counts;
- capture-level median Kuru spread bps;
- capture-level median cross-venue reference-midpoint difference bps.

Quantiles are descriptive empirical summaries. They are not confidence intervals and do not imply independent observations.

Because all four state rows from one economically eligible panel share the same Coinbase reference, Coinbase reference-book summaries must be calculated once per panel rather than four times.

For each freshness band, the panel-level Coinbase reference summary reports:

- economically eligible panel count;
- Coinbase spread-bps minimum, p05, p25, p50, p75, p95, and maximum;
- capture-level median Coinbase spread bps.

The pooled summaries must not weight one Coinbase reference four times merely because the Kuru observation contains four state views.

## Paired State-View Contrasts

Because one economically eligible Kuru observation contains all four state views at the same local client receive time and all four rows share the same Coinbase reference, state-view metrics may also be compared within the same complete panel.

The predefined state-view pairs are:

- proposed versus voted;
- proposed versus finalized;
- proposed versus committed;
- voted versus finalized;
- finalized versus committed.

For a pair `(state_a, state_b)`, define:

`spread_delta_bps = state_b.kuru_spread_bps - state_a.kuru_spread_bps`

`reference_mid_difference_delta_bps = state_b.reference_mid_difference_bps - state_a.reference_mid_difference_bps`

For spread delta:

- a negative value means the second state view has a numerically narrower observed spread;
- a positive value means the second state view has a numerically wider observed spread;
- zero means no spread change between the two observed state views.

For cross-venue reference-difference delta, the sign indicates only the numerical change in the Kuru-minus-Coinbase midpoint difference between the two state views. It is not an execution, profitability, arbitrage, or finality-premium result.

`exact_top_equal` is true only when both raw Kuru best-bid and raw Kuru best-ask values are exactly equal across the two state views.

Paired contrasts are calculated only inside the same economically eligible four-state panel. Observations from different Kuru messages, capture files, or freshness bands must never be paired with one another.

Each state-view pair must report separately for each freshness band:

- paired observation count;
- exact-top-equality count;
- exact-top-equality rate, defined as `exact_top_equal_count / paired_observation_count`;
- spread-delta minimum, p05, p25, p50, p75, p95, and maximum;
- spread-delta positive, zero, and negative counts;
- cross-venue reference-difference-delta minimum, p05, p25, p50, p75, p95, and maximum;
- cross-venue reference-difference-delta positive, zero, and negative counts;
- capture-level paired medians and exact-top-equality counts.

Capture-level summaries must remain visible alongside pooled summaries.

These contrasts compare simultaneously observed state views. They do not establish that the same quote or order temporally progressed from one consensus state to another, and they do not establish a causal effect of finality.

Exact equality observed between any two state views is an empirical property of the analyzed capture dataset and must not be generalized into a protocol invariant without separate evidence.

## Aggregation Boundary

State-conditioned results must be reported separately for each freshness band.

Capture-level results must remain available so pooled summaries do not hide variation across acquisition windows.

Any pooled statistic is descriptive only. The five capture windows are not assumed to be statistically independent observations.

Counts must accompany percentage or distribution summaries so changes in eligible sample size remain visible.

## Cross-Venue Boundary

Kuru `MON_USDC` and Coinbase `MON-USD` remain distinct markets.

USD/USDC basis is not removed by point-in-time alignment or midpoint normalization.

Therefore `reference_mid_difference` and `reference_mid_difference_bps` are descriptive cross-venue reference metrics, not automatically:

- arbitrage;
- executable spread;
- alpha;
- finality premium;
- realized or expected profit;
- evidence of venue advantage.

No network latency, exchange latency, consensus latency, or protocol-finality latency may be inferred from local reference age.

## Phase 1 Top-of-Book Gate

Implementation passes only when tests demonstrate:

- exact Decimal-based calculations;
- complete four-state panel handling;
- identical Coinbase reference across the four state rows;
- exclusion of stale, no-prior, and insufficient-evidence rows;
- separate reporting under 250 ms, 500 ms, and 1000 ms sensitivity bands;
- preservation of provenance and claim boundaries;
- deterministic state-conditioned and panel-level reference aggregation;
- deterministic within-panel paired state-view contrasts;
- deterministic reproduction on the provenance-verified five-capture dataset.

Only after this gate passes should deeper-book depth, simulated execution, VWAP, slippage, or stronger finality-conditioned economic claims be considered.
