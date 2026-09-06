# Phase 1 — Reference Staleness Policy

## Status

Methodology decision derived from five 60-second dual-WebSocket capture windows.

No single `max_age_ms` value is treated as a true or protocol-defined threshold.

## Evidence Base

Five 60-second Kuru + Coinbase capture windows, separated by 30-second gaps, passed the dual-source integrity gate.

Across those windows:

- Kuru observations with an eligible prior Coinbase reference: **8,133**
- Coinbase target inter-arrival observations: **1,907**
- pooled reference-age p50: **76.389057 ms**
- pooled reference-age p90: **515.016233 ms**
- pooled reference-age p95: **798.474137 ms**
- pooled reference-age p99: **1580.286243 ms**
- maximum observed reference age: **4521.555171 ms**

Capture-level variation was material and the windows are not assumed to be statistically independent.

## Sensitivity Framework

Phase 1 will evaluate aligned observations under three reporting bands:

- **250 ms — strict**
- **500 ms — moderate**
- **1000 ms — lenient**

These bands are analysis sensitivities, not venue SLAs, execution guarantees, network-latency thresholds, Monad finality thresholds, or protocol constants.

Observed aligned shares across the five windows were:

- 250 ms: **58.09% to 86.21%**
- 500 ms: **75.77% to 94.96%**
- 1000 ms: **88.87% to 99.71%**

Pooled descriptive aligned shares were:

- 250 ms: **78.40%**
- 500 ms: **89.44%**
- 1000 ms: **97.09%**

The pooled values are descriptive only and must not be interpreted as population probabilities.

## Reporting Rule

Any Phase 1 cross-venue economic metric that depends on Coinbase reference freshness must be reported across the 250 ms, 500 ms, and 1000 ms sensitivity bands.

Results that exist only under the lenient band must not be presented as robust findings.

Observations exceeding the selected sensitivity band remain `STALE_REFERENCE` and must not be repaired using a future Coinbase observation.

The existing backward as-of rule remains unchanged:

`t_coinbase <= t_kuru`

## Additional Diagnostic Thresholds

50 ms, 100 ms, and 2000 ms may be used for diagnostics or robustness checks, but they are not the core Phase 1 reporting bands.

## Interpretation Boundary

Reference age is measured using same-process client-observed monotonic receive timestamps.

It is not exchange-clock latency, network latency, execution latency, consensus latency, or protocol-finality latency.

The five evidence windows were collected close together in time and therefore do not establish behavior across broader market regimes or times of day.

## Provenance

The five source capture identifiers used to define this policy are:

- `dual_ws_20260906T011119618860Z.json`
- `dual_ws_20260906T011253398169Z.json`
- `dual_ws_20260906T011426627600Z.json`
- `dual_ws_20260906T011600173225Z.json`
- `dual_ws_20260906T011733287613Z.json`

The provenance-verifying analysis produced dataset fingerprint:

`0c709499d9d16b48080b2fea82ccee85ef4747284e51493324856c954bc13baa`

The fingerprint is derived from the ordered source capture identifiers and their verified SHA256 hashes.

The raw capture files and SHA256 sidecars are intentionally not embedded in the repository. Reproducing the empirical calculations requires the listed source captures together with their matching SHA256 sidecars.

## Gate

The staleness methodology is considered defined when downstream analysis applies the same backward as-of rule and reports results under all three core sensitivity bands without changing thresholds in response to economic outcomes.
