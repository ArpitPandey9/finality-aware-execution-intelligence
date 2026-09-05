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

Kuru price and quantity values must be normalized only using the verified representation rules documented below.

Coinbase prices must not be used to infer Kuru units or decimal placement.

### Verified REST normalization

A same-block comparison between the Kuru committed REST depth endpoint and the MON-USDC OrderBook contract established the deterministic representation used for the observed L2 snapshot.

For MON-USDC:

- REST price strings match the contract's externally scaled price representation.
- Human price = REST price / `1e18`.
- Equivalently, human price = internal L2 price / `pricePrecision`.
- REST quantity strings match the raw size returned by `getL2Book`.
- Human base-asset size = REST quantity / `sizePrecision`.

For the verified market configuration:

- `pricePrecision = 1e8`
- `sizePrecision = 1e10`

These rules were verified against both the bid and ask at the same committed block.

They establish numeric normalization, not the provenance of displayed liquidity. Kuru's L2 book may include liquidity originating from the integrated backstop AMM as well as resting limit orders.

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

## Verified Kuru Snapshot Semantics

According to the Kuru Exchange API documentation:

- `lastUpdateId` is the block number of the order-book snapshot.
- `E` is the Monad block-header timestamp in milliseconds (`T × 1000`).
- `T` is the Monad block-header timestamp in Unix seconds.
- `proposed` represents block started.
- `voted` represents QC received.
- `finalized` represents reorg-proof state.
- `committed` represents state verified.

These snapshot semantics were verified independently of numeric normalization. The REST-to-on-chain numeric mapping is documented in the verified normalization section above.

## Verified Kuru MON-USDC Market Parameters

A read-only Monad mainnet call to the Kuru Router `verifiedMarket` mapping for the official MON-USDC market returned:

- price precision: `100000000` (`1e8`)
- size precision: `10000000000` (`1e10`)
- base asset: native MON (`0x0000000000000000000000000000000000000000`)
- base asset decimals: `18`
- quote asset: USDC (`0x754704Bc059F8C67012fEd69BC8A327a5aafb603`)
- quote asset decimals: `6`
- tick size: `100`
- minimum size: `2000000000000`
- maximum size: `2000000000000000000`
- taker fee parameter: `0`
- maker fee parameter: `0`

These values establish the market's on-chain configuration. The REST numeric representation was verified separately through the same-block comparison documented above.
