# Phase 2 — State-Conditioned Temporal Market Response Contract

## Status

**PRE-REGISTERED METHODOLOGY — economic future-outcome values not yet inspected.**

This contract freezes the initial Phase 2 temporal-outcome methodology before Coinbase future-price returns or state-conditioned forward-response results are calculated.

The design extends the completed Phase 1 point-in-time measurement layer into within-capture future market-state measurement.

It does not define a trading strategy and does not claim prediction, alpha, arbitrage, profitability, realized execution advantage, causal finality effects, or a price of finality.

## Research Question

Given an economically eligible Kuru four-state observation at captured receive time `t0`:

1. how does the reconstructed Coinbase `MON-USD` midpoint evolve over fixed future horizons; and
2. is the direction of that future Coinbase movement descriptively associated with the simultaneous Kuru proposed-versus-finalized midpoint contrast observed at `t0`?

The analysis is descriptive.

A directional association must not be described as:

- prediction;
- lead-lag causality;
- information transmission;
- alpha;
- an executable signal;
- arbitrage;
- finality premium;
- protocol causality.

## Markets

Kuru / Monad:

`MON_USDC`

Coinbase:

`MON-USD`

The common base asset is MON.

The primary future-price outcome is calculated entirely inside Coinbase `MON-USD`.

USD/USDC parity is therefore not required for the primary forward-return calculation.

Kuru-versus-Coinbase absolute price differences are not the primary temporal outcome.

## Unit of Observation

The unit of observation is one valid Kuru four-state panel at one Kuru captured receive timestamp.

One panel contains simultaneous views for:

- proposed;
- voted;
- finalized;
- committed.

The same future Coinbase outcome must not be counted four times merely because four Kuru state views exist.

A panel contributes at most one future Coinbase return per:

- baseline freshness threshold;
- future horizon.

## Source Dataset

The initial Phase 2 dataset is restricted to the same five provenance-bound dual-WebSocket captures used in Phase 1.

Ordered dataset fingerprint:

`0c709499d9d16b48080b2fea82ccee85ef4747284e51493324856c954bc13baa`

No additional capture may be silently added to the primary Phase 2 result.

Any later dataset extension must be reported separately.

## Time Basis

All temporal matching within a capture uses same-process:

`received_monotonic_ns`

Wall-clock timestamps are not used to order the primary within-capture temporal analysis.

No temporal relationship is inferred across separate capture files.

No future outcome may cross a capture boundary.

## Baseline Event Time

For Kuru observation `i`:

`t0_i = kuru_record.received_monotonic_ns`

The Phase 2 horizon is measured from `t0_i`.

Kuru protocol timestamps such as `E`, `T`, or undocumented grouping field `U` are not substituted for this captured receive-time anchor.

## Baseline Coinbase Reference

The baseline Coinbase reference uses the existing Phase 1 backward-as-of rule.

For Kuru observation time `t0`, select the eligible Coinbase target Level2 record with the greatest captured receive time satisfying:

`t_cb0 <= t0`

No future reference is allowed.

No interpolation is allowed.

When receive times tie, the existing deterministic Phase 1 record-index ordering remains authoritative.

The selected Coinbase book is reconstructed from the beginning of the capture using the existing verified Level2 reconstruction semantics.

## Baseline Freshness

The initial Phase 2 analysis preserves the existing Phase 1 reference-age bands:

- 250 ms;
- 500 ms;
- 1000 ms.

### Primary baseline eligibility

The **250 ms** band is the primary Phase 2 eligibility definition.

It is selected before future price outcomes are inspected because it is the strictest existing Phase 1 reference-age band and still retains substantial temporal coverage.

### Sensitivity bands

The 500 ms and 1000 ms bands are secondary baseline-freshness sensitivities.

The three bands are nested and overlapping.

They must not be pooled together or treated as independent samples.

A result that appears only under a looser baseline band must not be promoted as a robust primary finding.

## Frozen Future Horizons

### Primary horizons

The primary future horizons are:

- 250 ms;
- 1000 ms;
- 5000 ms.

These horizons were frozen after a timestamp-only feasibility audit and before inspecting future midpoint values or returns.

### Extended sensitivity horizon

A 10000 ms horizon is retained as a pre-specified extended-horizon sensitivity.

Because capture-end censoring is materially higher at 10 seconds than at the primary horizons, the 10-second result must not override contradictory primary-horizon evidence.

### Excluded initial horizon

A 30000 ms horizon is excluded from the initial Phase 2 economic analysis.

The timestamp-only feasibility audit showed approximately 50% coverage at 30 seconds across the three baseline freshness populations.

Any later 30-second result must therefore be explicitly labelled as a later extension rather than part of the frozen initial primary analysis.

## Timestamp-Only Feasibility Basis

Before future prices were inspected, the five-capture audit showed:

- approximately 99% or greater coverage at 250 ms;
- approximately 99% coverage at 1 second;
- approximately 94–95% coverage at 5 seconds;
- approximately 85–86% coverage at 10 seconds;
- approximately 50% coverage at 30 seconds.

These coverage observations were used only to freeze the horizon design.

They are not economic results.

## Future Coinbase State

For horizon `h`:

`t_h = t0 + h`

The future Coinbase state is the reconstructed target `MON-USD` Level2 book **as of `t_h`**.

Use the Coinbase target record with the greatest captured receive time satisfying:

`t_cbh <= t_h`

The implementation must not use the first Coinbase record after `t_h` as the future price observation.

Using a post-horizon price would introduce forward information relative to the defined horizon.

## Continuous-Capture Requirement

A future outcome is eligible only when capture continuity can be demonstrated through `t_h`.

At minimum:

1. the Coinbase replay begins from the valid capture snapshot baseline;
2. all stored Coinbase wrappers are replayed in original capture order;
3. existing wrapper sequence-integrity rules remain satisfied;
4. reconstruction remains valid through the horizon;
5. at least one stored Coinbase wrapper exists at or after `t_h`.

If condition 5 is not satisfied:

`RIGHT_CENSORED_CAPTURE_END`

The observation must not be repaired by:

- carrying data across capture files;
- extrapolating beyond the capture;
- using wall-clock interpolation;
- using a later independent capture.

## Persistent Book State

The Level2 book is a state.

If no target book mutation occurs between the baseline state and a future horizon, the previously reconstructed book remains the as-of book at that horizon provided capture continuity through the horizon is demonstrated.

Therefore:

`future_coinbase_record_index == baseline_coinbase_record_index`

is a valid possible outcome.

It is not automatically missing evidence.

A zero forward midpoint return in such a case is valid if the reconstructed midpoint is unchanged.

## Future As-Of Age

For diagnostic purposes:

`future_asof_age_ms = (t_h - t_cbh) / 1_000_000`

This field measures how long before the exact horizon the latest reconstructed target-book record was observed.

No additional future-state freshness threshold is imposed in the initial analysis.

Reason:

the reconstructed Level2 book persists until changed, and verified stream continuity through the horizon is the relevant evidence requirement.

`future_asof_age_ms` remains an auditable diagnostic and must be summarized.

It must not be interpreted as exchange latency, network latency, market inactivity probability, or protocol finality latency.

## Coinbase Midpoint

For a valid reconstructed Coinbase book:

`mid = (best_bid + best_offer) / 2`

Requirements:

- best bid > 0;
- best offer > 0;
- best bid <= best offer;
- exact Decimal arithmetic;
- no binary floating-point arithmetic in research calculations.

## Primary Future Outcome

For each eligible panel and future horizon:

`coinbase_forward_mid_return_bps = (mid_h / mid_0 - 1) * 10000`

where:

- `mid_0` is the reconstructed Coinbase midpoint selected as of `t0`;
- `mid_h` is the reconstructed Coinbase midpoint selected as of `t0 + h`.

Interpretation:

- positive: Coinbase midpoint is higher at the future horizon;
- zero: unchanged;
- negative: lower.

This is a captured-market forward midpoint change.

It is not a realized trading return.

## Primary Kuru State Contrast

The pre-specified primary state contrast is proposed versus finalized.

For the same Kuru four-state panel:

`kuru_proposed_finalized_mid_gap_bps = (proposed_mid / finalized_mid - 1) * 10000`

Both midpoint values come from the same Kuru `MON_USDC` panel.

Interpretation:

- positive: proposed midpoint > finalized midpoint;
- zero: equal;
- negative: proposed midpoint < finalized midpoint.

The proposed-versus-finalized pair is selected before temporal outcome inspection.

It spans an early and stronger state view while avoiding promotion of the finalized-versus-committed pair, which Phase 1 found to be exactly equal throughout the frozen dataset.

That prior static observation does not establish a protocol invariant.

## No Temporal Transition Claim

The proposed and finalized Kuru books in one panel are simultaneous captured state views.

They are not treated as sequential time observations.

The primary state contrast therefore does not measure:

- price movement from proposed to finalized;
- finality delay;
- state-transition latency;
- causal movement caused by consensus progression.

## Contrast Sign

Define:

- `POSITIVE` when proposed-finalized midpoint gap > 0;
- `ZERO` when gap = 0;
- `NEGATIVE` when gap < 0.

Zero-contrast observations remain in the primary eligible population.

They must not be silently discarded.

## Directional Concordance Outcome

For non-zero Kuru proposed-finalized contrasts only:

`directional_concordance_bps = sign(kuru_proposed_finalized_mid_gap_bps) * coinbase_forward_mid_return_bps`

Interpretation:

- positive: future Coinbase midpoint movement has the same sign as the Kuru proposed-versus-finalized contrast;
- zero: future Coinbase midpoint does not move;
- negative: future Coinbase movement has the opposite sign.

This metric is descriptive directional concordance only.

It must not be described as:

- predictive accuracy;
- hit rate;
- win rate;
- alpha;
- trade PnL;
- information lead;
- adverse-selection profit;
- causal finality effect.

## Zero-Contrast Handling

When:

`kuru_proposed_finalized_mid_gap_bps == 0`

the directional-concordance metric is:

`NOT_APPLICABLE_ZERO_CONTRAST`

The observation remains eligible for the unconditional Coinbase forward-return distribution.

It is excluded only from the signed directional-concordance distribution, with exact numerator and denominator counts preserved.

## Outcome Status

Each baseline-threshold / horizon observation must receive one explicit status.

At minimum:

- `EVALUABLE`
- `NO_PRIOR_REFERENCE`
- `STALE_REFERENCE`
- `RIGHT_CENSORED_CAPTURE_END`
- `INSUFFICIENT_SOURCE_EVIDENCE`
- `INVALID_KURU_PANEL`
- `COINBASE_RECONSTRUCTION_FAILURE`

The existing Phase 1 alignment statuses are preserved rather than remapped.

`COINBASE_RECONSTRUCTION_FAILURE` is a capture-integrity outcome. The analysis must not invent a baseline-versus-future failure location when the canonical historical replay cannot establish one.

No failed or censored observation may be silently removed.

## Capture Integrity

If Coinbase historical reconstruction fails for a capture under the existing reconstruction contract, the implementation must not repair isolated future outcomes using stored top-of-book fields.

Reconstruction failure invalidates the affected capture for Phase 2 temporal outcomes.

The raw stored record may be used for parity verification, not as an unverified replacement for failed replay.

## State-Panel Integrity

The Kuru observation must satisfy the existing complete four-state top-of-book validity rules before entering state-conditioned temporal analysis.

A missing or invalid state invalidates the Kuru panel.

No missing state may be filled using:

- a prior Kuru message;
- a later Kuru message;
- another state;
- Coinbase;
- interpolation.

## Event Overlap

High-frequency Kuru observations produce overlapping future windows.

The primary pooled analysis retains all eligible panels.

Those panels must not be described as independent observations.

Pooled observation counts must not be converted into statistical confidence merely because the row count is large.

## Capture-Level Primary Aggregation

For each:

- baseline freshness threshold;
- future horizon;
- capture;

report at minimum:

- baseline-aligned panel count;
- evaluable outcome count;
- right-censored count;
- invalid/insufficient-evidence counts;
- proposed-finalized contrast sign counts;
- Coinbase forward-return descriptive distribution;
- non-zero-contrast directional-concordance descriptive distribution;
- future-as-of-age descriptive distribution.

The capture is the primary aggregation unit for robustness interpretation.

## Pooled Descriptive Aggregation

For each baseline freshness threshold and horizon, pooled rows may be summarized descriptively with:

- count;
- minimum;
- p05;
- p25;
- p50;
- p75;
- p95;
- maximum;
- positive / zero / negative sign counts.

Percentiles use the repository's existing deterministic linear-interpolation methodology.

Pooled distributions are descriptive only.

They are not inferential samples of independent observations.

## Capture-Median Robustness

For each threshold and horizon, report the five capture-level medians when evaluable.

The primary interpretation must distinguish:

- a pooled median;
- the signs and magnitudes of individual capture medians.

A pooled sign that is contradicted across capture medians must not be presented as a robust directional effect.

No capture-median sign count is a win rate.

## Horizon-Overlap Sensitivity

A deterministic non-overlapping sensitivity sample is pre-specified.

For each capture, baseline freshness threshold, and horizon:

1. sort evaluable panels by `(t0_ns, kuru_record_index)`;
2. retain the earliest panel;
3. after retaining a panel at time `t_keep`, retain the next panel only when:

`t_next >= t_keep + horizon`

4. continue greedily through the capture.

This sample is a robustness diagnostic for overlapping future windows.

It must not be called statistically independent.

The full eligible-panel analysis remains the primary descriptive dataset.

## Threshold Separation

Results for 250 ms, 500 ms, and 1000 ms baseline freshness populations are reported separately.

They must not be concatenated into one dataset.

The 250 ms result is primary.

The 500 ms and 1000 ms results are freshness sensitivities.

## Horizon Separation

Results for each future horizon are reported separately.

The primary horizons are:

- 250 ms;
- 1000 ms;
- 5000 ms.

The 10000 ms horizon is an extended sensitivity.

Horizons must not be pooled into one observation population.

## No Post-Hoc Magnitude Threshold

The initial primary analysis does not impose a minimum absolute proposed-finalized midpoint-gap threshold.

No state-gap threshold may be selected after viewing future returns merely to strengthen directional concordance.

If a magnitude threshold is introduced later, it must be labelled post-hoc unless frozen in a separate preregistered extension before its outcomes are inspected.

## No Outcome-Driven Horizon Selection

No horizon may be removed, added, or relabelled because its forward-return direction appears weak or strong.

All frozen primary horizons must be reported.

The 10-second sensitivity must also be reported when source evidence permits.

## No Significance Fishing

The initial Phase 2 analysis is descriptive.

It does not require:

- p-values;
- t-tests;
- regression significance;
- confidence intervals;
- multiple-testing-adjusted significance claims.

Any later inferential design requires a separate methodology contract that addresses serial dependence, event overlap, capture clustering, and sample construction before inferential results are inspected.

## Costs and Execution Excluded

The temporal midpoint analysis does not include:

- trading fees;
- gas;
- MEV;
- queue priority;
- spread-crossing cost;
- order placement;
- cancellation risk;
- inclusion risk;
- market impact;
- realized fills;
- inventory;
- funding;
- hedging costs.

A forward midpoint move is not a realizable strategy return.

## Claim Boundaries

Allowed descriptive claims include:

- a future Coinbase midpoint was higher, unchanged, or lower at a frozen horizon;
- a proposed-finalized Kuru midpoint contrast had a positive, zero, or negative sign;
- a future Coinbase move had the same or opposite sign as a non-zero Kuru state contrast;
- a pattern was or was not stable across captures, horizons, or freshness sensitivities;
- censoring and future-as-of-age differed across horizons.

Not allowed without additional evidence:

- Kuru predicts Coinbase;
- proposed state leads Coinbase;
- finality causes the future move;
- a positive directional-concordance value is alpha;
- directional-concordance sign counts are trading win rates;
- the observed relationship is arbitrage;
- a future midpoint change is realized PnL;
- simultaneous state differences measure protocol finality latency;
- overlapping panel rows are independent observations.

## Reproducibility Requirements

Before an empirical Phase 2 result may be accepted:

1. verify all five source SHA256 sidecars;
2. reproduce the Phase 1 dataset fingerprint;
3. reproduce the existing Phase 1 baseline alignment counts;
4. bind source identities to Kuru `MON_USDC` and Coinbase `MON-USD`;
5. reconstruct Coinbase Level2 books from the beginning of each capture;
6. preserve original wrapper order and sequence-integrity checks;
7. verify stored reconstruction parity;
8. enforce the frozen baseline freshness bands;
9. enforce the frozen future horizons;
10. preserve exact Decimal arithmetic;
11. preserve explicit censoring and invalidity statuses;
12. produce capture-level and pooled deterministic summaries;
13. produce the non-overlapping horizon sensitivity;
14. generate deterministic report serialization;
15. reproduce the report byte-for-byte on a second run;
16. pass targeted Phase 2 tests;
17. pass the full repository test suite.

## Initial Phase 2 Gate

Phase 2 temporal-outcome implementation may begin only after this contract is reviewed for:

- no future-information leakage;
- deterministic as-of semantics;
- explicit capture-end censoring;
- explicit baseline freshness;
- fixed future horizons;
- one-panel observation accounting;
- exact state-contrast sign convention;
- exact Coinbase forward-return formula;
- overlap treatment;
- claim boundaries.

Future economic outcome values must not be inspected before this methodology is frozen.
