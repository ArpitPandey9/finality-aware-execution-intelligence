# Phase 0 Data Contract

## Purpose

This document records the current interpretation boundary for the raw market-data fields used by the Phase 0 feasibility probe.

No unsupported normalization assumption should enter downstream analytics.

## Kuru

Market:

`MON_USDC`

Consensus-state views:

- proposed
- voted
- finalized
- committed

Fields currently captured:

- `lastUpdateId`
- `E` as event-time field returned by the endpoint
- `T` as block-time field returned by the endpoint
- bid level count
- ask level count
- raw best bid
- raw best ask

### Raw numeric values

Kuru price and quantity fields must remain raw until the relevant market precision and token-decimal metadata are explicitly verified.

Coinbase prices must not be used to infer Kuru units or decimal placement.

### Current unresolved items

Before normalized analytics are permitted, verify and record:

1. MON token decimals.
2. USDC token decimals for the relevant deployment.
3. Kuru market price precision.
4. Kuru market size/quantity precision.
5. Whether API depth values are already scaled or require deterministic decimal conversion.
6. Exact semantics of endpoint timestamp fields.
7. Exact semantics and ordering guarantees of `lastUpdateId`.

Until these are verified, raw Kuru numeric values are evidence only.

## Coinbase

Market:

`MON-USD`

Level:

Level-2 order book.

Fields currently captured:

- sequence
- bid level count
- ask level count
- best bid
- best ask

Coinbase serves as an independent centralized-market reference.

It is not a normalization source for Kuru.

## Cross-Venue Limitation

The initial comparison is:

`Kuru MON/USDC` versus `Coinbase MON/USD`

USDC and USD are not assumed to be perfectly interchangeable.

Any future cross-venue analysis must explicitly account for USD/USDC basis and timing differences where relevant.

## Evidence Rule

Raw observations must be preserved before transformation.

Missing, failed, delayed, or inconsistent observations must be recorded rather than silently filled or inferred.

No trading-performance or alpha claim is supported by this data contract.
