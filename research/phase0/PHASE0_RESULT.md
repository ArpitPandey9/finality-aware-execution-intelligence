# Phase 0 — Data & Research Feasibility Result

## Status

**Endpoint feasibility: PASS**

Phase 0 tests whether the initial research question can be supported by accessible market-data endpoints before building analytics or making any market-performance claims.

## Research scope

The project examines whether observable on-chain order-book liquidity differs across blockchain consensus/finality states, and whether apparent cross-venue execution conditions survive as blockchain state confidence strengthens.

Initial venues:

- **Kuru / Monad:** `MON_USDC`
- **Coinbase:** `MON-USD`

Coinbase is used as an external centralized-venue reference. It is not used to infer or convert Kuru raw units.

## Kuru feasibility

The Kuru API successfully returned order-book data for all four requested states:

- `proposed`
- `voted`
- `finalized`
- `committed`

The initial probe on 2026-08-31 returned all four books successfully.

A second live probe on 2026-09-05 also returned all four books successfully.

In the 2026-09-05 observation:

- proposed update: `102191444`
- voted update: `102191444`
- finalized update: `102191444`
- committed update: `102191445`

The displayed best bid and best ask were identical across the four states in that observation.

A difference in update identifiers is evidence worth capturing repeatedly, but a single observation is not sufficient to infer a systematic finality, pricing, liquidity, or execution effect.

## Coinbase feasibility

Coinbase successfully returned a Level-2 `MON-USD` order book during both feasibility checks.

The 2026-09-05 observation returned:

- sequence: `1045281136`
- bid levels: `531`
- ask levels: `620`
- best bid: `0.025092`
- best ask: `0.0251`

## What Phase 0 proves

Phase 0 currently supports only the following claims:

1. The tested Kuru endpoint can return `MON_USDC` order books for the four requested consensus-state views.
2. Coinbase `MON-USD` Level-2 data is accessible as an external market reference.
3. State/update differences can occur in individual Kuru observations and can therefore be captured for further study.

## What Phase 0 does not prove

The current evidence does **not** establish that:

- finality causes a predictable price premium;
- proposed-state opportunities are profitable;
- any trading edge exists;
- finalized or committed liquidity is systematically better or safer;
- Kuru raw numeric fields can be normalized using Coinbase prices.

## Next gate

Before implementing market-microstructure analytics:

1. verify Kuru market precision and token-decimal metadata;
2. define deterministic price and size normalization;
3. build synchronized Kuru-state and Coinbase capture;
4. preserve capture timestamps, update identifiers and raw evidence;
5. measure repeated state transitions and quote survival;
6. only then calculate spread, depth, VWAP/slippage and cross-venue divergence.

No trading-performance or alpha claim is made.
