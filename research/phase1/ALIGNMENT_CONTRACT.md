# Phase 1 — Point-in-Time Alignment Contract

## Status

Methodology gate before state-conditioned cross-venue economic analysis.

Phase 1 begins only after Phase 0 technical feasibility passed.

## Objective

For each captured Kuru multi-state observation, select a Coinbase Level-2 reference that was already locally observable at the Kuru receive time.

The alignment must prevent look-ahead and expose stale or insufficient reference evidence instead of silently substituting another observation.

## Time Basis

Alignment uses `received_monotonic_ns` recorded by the same dual-WebSocket capture process.

Monotonic receive time is a client-observed local ordering clock.

It is not an exchange timestamp, synchronized venue clock, network-latency measurement, consensus-latency measurement, or protocol-finality clock.

Monotonic timestamps from different capture processes or different capture files must not be directly compared.

## As-Of Selection Rule

For a Kuru observation at monotonic time `t_kuru`, eligible Coinbase observations satisfy:

`t_coinbase <= t_kuru`

Among eligible observations, select the Coinbase observation with the greatest `t_coinbase`.

If multiple eligible Coinbase records have the same `t_coinbase`, select the later source-record index as the deterministic tie-break.

This is a backward-looking as-of join.

Future Coinbase observations are never eligible.

No interpolation between Coinbase observations is permitted in the initial Phase 1 methodology.

If no prior Coinbase observation exists, the Kuru observation is classified as `NO_PRIOR_REFERENCE`.

## Reference Age

For an aligned pair:

`reference_age_ms = (t_kuru - t_coinbase) / 1_000_000`

Reference age must be non-negative.

The alignment function must require an explicit `max_age_ms` parameter rather than silently choosing a default threshold.

If `reference_age_ms > max_age_ms`, the observation is classified as `STALE_REFERENCE`.

A stale reference must not be replaced with a future Coinbase observation.

## Kuru State Treatment

One Kuru `monadDepthUpdate` message contains proposed, voted, finalized, and committed state views observed at the same local client receive time.

The same as-of Coinbase reference is therefore attached to all four state views from that Kuru message.

State-specific Kuru prices and sizes remain separate downstream observations.

Kuru `U` is retained only as an observed stream grouping field; no undocumented block-number or event-ID meaning is assigned to it.

## Coinbase Eligibility

Only Coinbase target Level-2 records produced after a valid snapshot baseline and containing a valid reconstructed top of book are eligible as references.

Capture-level Coinbase sequence-integrity or reconstruction failures must cause the source evidence to be reviewed rather than silently accepted.

## Required Alignment Output

Each aligned observation should preserve at minimum:

- source capture identifier
- Kuru record index
- Kuru `received_at_utc`
- Kuru `received_monotonic_ns`
- observed Kuru `U`
- Kuru state-specific top-of-book values
- Coinbase record index
- Coinbase `sequence_num`
- Coinbase `received_at_utc`
- Coinbase `received_monotonic_ns`
- Coinbase reconstructed top of book
- `reference_age_ms`
- explicit alignment status

## Alignment Status

Initial statuses are:

- `ALIGNED`
- `NO_PRIOR_REFERENCE`
- `STALE_REFERENCE`
- `INSUFFICIENT_SOURCE_EVIDENCE`

## Cross-Venue Boundary

Kuru `MON_USDC` and Coinbase `MON-USD` remain distinct markets.

Alignment does not remove USD/USDC basis risk.

No aligned price difference is automatically an arbitrage, executable spread, trading signal, finality premium, or profitability result.

## Phase 1 Gate

Alignment methodology passes only when tests demonstrate deterministic backward as-of selection, no future-reference use, explicit staleness handling, capture-bound monotonic-clock use, and preservation of insufficient evidence.

Only after this gate passes should state-conditioned spread, depth, slippage, or cross-venue divergence metrics be added.
