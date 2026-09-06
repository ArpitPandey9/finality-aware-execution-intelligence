# Phase 2 Temporal Outcome Result Note

## Status

**Primary hypothesis support: NOT ESTABLISHED — no robust directional association observed; the pre-specified 10000 ms extended sensitivity was mixed.**

This note reports the pre-registered Phase 2 state-conditioned temporal
market-response analysis. The methodology was committed before inspection of
the real economic outcomes.

Pre-result methodology commit:

`9c94b55a535006d7d5d79d6fcd277c17ca7aaaa6`

Frozen methodology contract SHA256:

`a5b6c1c61b69c2b565ebb1e97a05abe235df0c3cb42dbbe54b82b87644acee38`

Real deterministic report SHA256:

`e84937515281be0ecc3e35843a41b3a768ce026d7cb728d4b63fefb3e9bcd90d`

Frozen dataset fingerprint:

`0c709499d9d16b48080b2fea82ccee85ef4747284e51493324856c954bc13baa`

The report was independently generated twice and was byte-identical across
both runs.

## Research Question

Phase 2 asked whether the simultaneous Kuru proposed-versus-finalized midpoint
contrast observed at a Kuru four-state panel was descriptively associated with
subsequent Coinbase MON-USD midpoint movement.

The primary baseline freshness definition was 250 ms.

The pre-specified primary future horizons were:

- 250 ms;
- 1000 ms;
- 5000 ms.

The 10000 ms horizon was retained only as an extended sensitivity.

## Primary Result

The pre-registered primary analysis did not identify a robust directional
association.

For the 250 ms baseline-freshness population:

| Horizon | Evaluable panels | Forward-return median | Directional-concordance median |
| --- | ---: | ---: | ---: |
| 250 ms | 6,375 | 0.00 bps | 0.00 bps |
| 1000 ms | 6,342 | 0.00 bps | 0.00 bps |
| 5000 ms | 6,082 | 0.00 bps | 0.00 bps |

At 250 ms and 1000 ms, all five capture-level forward-return medians and all
five capture-level directional-concordance medians were zero.

At 5000 ms, four of five capture-level forward-return medians remained zero.
One capture had a positive forward-return median of approximately 0.99 bps.
Four of five directional-concordance medians were zero; one capture had a
negative median of approximately -0.40 bps.

These capture-level results do not establish a stable direction across
the five separate capture windows.

## Non-Overlapping Sensitivity

The deterministic within-capture non-overlapping sensitivity also produced
zero median forward returns and zero median directional concordance at each of
the three primary horizons:

- 250 ms;
- 1000 ms;
- 5000 ms.

This sensitivity reduces mechanical horizon overlap but is not treated as a
statistically independent sample.

It did not recover a directional relationship absent from the primary pooled
analysis.

## Directional Sign Evidence

Directional-concordance sign counts were not stable across horizons.

Within the primary 250 ms baseline population:

- at 250 ms, positive concordance observations exceeded negative observations;
- at 1000 ms, positive and negative observations were approximately balanced;
- at 5000 ms, negative observations exceeded positive observations.

These counts are descriptive only. They are not a win rate, hit rate,
prediction accuracy measure, execution probability, or trading-performance
statistic.

A substantial fraction of evaluable panels also had an exactly zero
proposed-versus-finalized midpoint contrast, for which directional concordance
was correctly treated as not applicable.

## Extended 10000 ms Sensitivity

The pre-specified 10000 ms extended horizon showed a small positive pooled
median:

- forward Coinbase midpoint return: approximately +0.59 bps;
- directional concordance: approximately +0.20 bps.

This was not robust to the deterministic non-overlapping sensitivity.

For the primary 250 ms freshness population, the non-overlapping 10000 ms
sample contained 25 selected observations. Its forward-return median was
effectively zero and its directional-concordance median was approximately
-0.89 bps.

The same qualitative disagreement persisted in the 500 ms and 1000 ms
baseline-freshness sensitivities: pooled 10000 ms concordance medians were
positive while non-overlapping concordance medians were negative.

The 10000 ms result is therefore treated as mixed sensitivity evidence and not
as a primary finding.

## Freshness Sensitivity

The 500 ms and 1000 ms baseline-freshness populations did not change the
primary conclusion.

Across 250 ms, 1000 ms, and 5000 ms future horizons, pooled forward-return and
directional-concordance medians remained predominantly zero.

The broader freshness populations therefore did not reveal a robust
relationship hidden by the primary 250 ms eligibility definition.

## Integrity and Eligibility

All twelve pre-specified freshness-threshold × horizon cells reconciled exactly
to the previously audited temporal coverage counts.

There were no observed:

- invalid Kuru panels;
- Coinbase reconstruction failures;
- insufficient-source-evidence outcomes beyond the pre-existing alignment
  eligibility statuses.

Capture-end observations were explicitly right-censored and no cross-capture
future-state stitching was used.

## Interpretation

Within this frozen five-capture dataset, the simultaneous Kuru
proposed-versus-finalized midpoint contrast did not exhibit a robust
descriptive association with subsequent Coinbase MON-USD midpoint direction
over the pre-registered primary horizons.

This result does not establish that:

- Kuru state information has no economic content;
- Coinbase never responds after Kuru observations;
- one venue leads or lags the other;
- protocol finality has no market effect;
- the absence of this specific relationship generalizes to other periods,
  markets, assets, or market regimes.

It establishes only that the specific pre-registered state-conditioned
directional relationship tested here was not robustly supported in the frozen
dataset.

## Claim Boundaries

The analysis does not claim:

- prediction;
- alpha;
- arbitrage;
- profitability;
- causal finality effects;
- a price of finality;
- realized execution advantage;
- a win rate or hit rate;
- protocol-finality latency.

Simultaneous Kuru state views remain simultaneous captured market-state views,
not observed temporal transitions through consensus states.

## Research Decision

**Primary hypothesis support: NOT ESTABLISHED.**

No post-hoc horizon, minimum state-gap threshold, subgroup, or alternative
directional rule is promoted from this dataset.

Any subsequent hypothesis must be defined as a new research question and
pre-registered before inspecting its corresponding outcomes.
