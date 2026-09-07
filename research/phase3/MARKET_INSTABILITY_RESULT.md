# Phase 3 — Confirmatory Market Instability Result

## Status

**ROBUST DIRECTIONAL SUPPORT OBSERVED**

This classification follows the Phase 3 preregistered descriptive support rule.
It does not establish prediction, alpha, arbitrage, causality, or a realizable
trading strategy.

## Research Question

When simultaneous Kuru proposed and finalized state views exhibit greater
midpoint disagreement, is that descriptively associated with greater subsequent
absolute Coinbase MON-USD midpoint movement?

## Frozen Research Sequence

Methodology preregistration commit:

`a834e149e309fcae0e90ce3b213d5318aabf5e7c`

Confirmatory collection implementation commit:

`5f0c7c0e45f59d4f9aad1347e1d23065a49c526d`

Confirmatory dataset provenance commit:

`d8393672825722e544dc66e6256e2f4d844bc1d8`

Analysis implementation commit:

`9c9eaec151b094c8cbecae5e88ff0d4f3cd20621`

The confirmatory economic result was first generated only after the analysis
implementation had been committed and pushed.

## Dataset Binding

Frozen confirmatory dataset fingerprint:

`ff29993a22743674edf13363957e7e5386b338d4e599027b4006089991f382e2`

Qualifying captures:

`10`

The analysis used the first ten chronological technical-PASS captures defined
by the frozen collection protocol. The REVIEW attempt remained excluded from
the confirmatory dataset under the preregistered technical rule.

## Deterministic Report

Generated report schema:

`phase3.market_instability_report.v1`

Deterministic report SHA256:

`d97f3cbf4de3ba2b71a98a2bc06b76d81fa8efb9a185fb4e3f875fb50973d378`

Two independent executions of the frozen analysis code against the same frozen
ten-capture input sequence produced byte-identical report hashes.

## Primary Result

The primary population uses the preregistered 250 ms baseline freshness
threshold.

| Future horizon | Evaluable pairs | Pooled Spearman rho | Defined capture correlations | Median capture rho | Non-overlap rows | Non-overlap Spearman rho | Supportive |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 250 ms | 27,940 | 0.2047319146 | 10 / 10 | 0.1760937618 | 2,660 | 0.1238017693 | Yes |
| 1000 ms | 27,821 | 0.1472375089 | 10 / 10 | 0.1463359276 | 906 | 0.1114146501 | Yes |
| 5000 ms | 26,920 | 0.1129767629 | 10 / 10 | 0.0059554587 | 219 | 0.1142676897 | Yes |

All three preregistered primary horizons satisfied the individual descriptive
support rule:

1. pooled Spearman correlation was defined and positive;
2. the median defined capture-level Spearman correlation was positive, with all
   ten qualifying captures contributing defined correlations; and
3. deterministic non-overlapping-sensitivity Spearman correlation was defined
   and positive.

The preregistered cross-horizon requirement was support at at least two of the
three primary horizons. All three satisfied the rule.

Therefore:

**Primary Phase 3 relationship: ROBUST DIRECTIONAL SUPPORT OBSERVED.**

## Extended Horizon

At the 10000 ms extended horizon under the primary 250 ms freshness population:

- pooled Spearman rho: `0.1191122924`;
- median capture-level rho: `0.0365613084`;
- non-overlapping Spearman rho: `0.1243892757`;
- directionally supportive: `Yes`.

The 10000 ms horizon is an extended sensitivity only and did not contribute to
the primary classification.

## Freshness Sensitivity

The 500 ms freshness sensitivity remained directionally supportive at all four
reported horizons.

The 1000 ms freshness sensitivity was supportive at 250 ms, 1000 ms, and
10000 ms. At the 5000 ms horizon, its deterministic non-overlapping Spearman
rho was negative:

`-0.0207678706`

Therefore that sensitivity cell did not satisfy the individual support rule.

This mixed sensitivity detail is retained and must not be omitted when
describing the result.

## Interpretation

The confirmatory dataset provides preregistered descriptive evidence that
greater simultaneous Kuru proposed-versus-finalized midpoint disagreement was
associated with greater subsequent absolute Coinbase MON-USD midpoint movement
over the primary short horizons.

The observed associations are positive but modest in magnitude. In particular,
the median capture-level correlation at the 5000 ms primary horizon was only
approximately `0.006`, despite the pooled and non-overlapping correlations being
positive.

A substantial number of evaluable observations had zero Kuru disagreement, and
the median absolute Coinbase movement at the 250 ms primary horizon was zero.
These observations remained eligible as required by the preregistration.

## Claim Boundaries

This result does **not** establish:

- causality;
- that Kuru leads Coinbase;
- prediction or forecast skill;
- alpha or arbitrage;
- profitable execution;
- realized PnL;
- market impact;
- adverse selection suffered by a trader;
- a finality premium;
- protocol finality latency;
- statistical independence of overlapping observations.

Simultaneous Kuru state views must not be interpreted as temporal protocol-state
transitions.

The deterministic non-overlapping sensitivity reduces mechanical horizon
overlap but does not make observations statistically independent.

No p-values, confidence intervals, regressions, or post-hoc exposure thresholds
were introduced for the initial confirmatory result.

## Conclusion

Under the methodology frozen before confirmatory data collection, the Phase 3
primary descriptive association criterion was satisfied at all three primary
horizons.

The correct scoped conclusion is:

**ROBUST DIRECTIONAL SUPPORT OBSERVED for the preregistered descriptive
association between simultaneous Kuru proposed-versus-finalized disagreement
magnitude and subsequent Coinbase absolute midpoint movement magnitude in this
frozen confirmatory dataset.**

No stronger causal, predictive, trading, or protocol-level claim is supported.
