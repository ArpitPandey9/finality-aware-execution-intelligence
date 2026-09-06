# Phase 1 — Kuru WebSocket Full-Depth Normalization Evidence

## Status

**PASS — observed MON_USDC WebSocket full-depth numeric representation is bound to the previously verified Kuru normalization contract.**

This evidence closes the numeric-unit gate required before using Kuru multi-state WebSocket quantities for depth, VWAP, or simulated-slippage analysis.

## Scope

Market:

`MON_USDC`

WebSocket stream:

`mon_usdc@monadDepth`

States:

- proposed;
- voted;
- finalized;
- committed.

The conclusion applies to the observed Kuru MON_USDC market-data representation used by this repository.

It is not claimed as a universal protocol invariant for every Kuru market, deployment, or future API representation.

## Raw WebSocket Provenance

The Kuru WebSocket parser preserves the complete original message under `raw_message`.

For each state, the compact top-of-book fields are derived directly from the first raw bid and ask levels:

- `best_bid_raw`;
- `best_bid_quantity_raw`;
- `best_ask_raw`;
- `best_ask_quantity_raw`.

A provenance inspection over verified source capture:

`dual_ws_20260906T011119618860Z.json`

SHA256:

`7f9010c01afd278199e6b272e4f029673590afa8ffbaf9f99c0a4f4673654127`

checked all four state views across the capture.

Results:

- Kuru records: `1792`;
- raw-to-stored state checks: `7168`;
- mismatches: `0`;
- observed raw bid depth range: `12` to `14`;
- observed raw ask depth range: `20` to `20`.

Therefore the compact top fields are directly traceable to the preserved raw WebSocket state books in this capture.

## Existing REST-to-On-Chain Normalization

Phase 0 independently established the MON_USDC numeric representation through a same-block comparison between the Kuru committed REST depth endpoint and the MON_USDC OrderBook contract.

Verified relationships:

`human_price = REST_price_raw / 1e18`

`human_base_size = REST_quantity_raw / sizePrecision`

Verified MON_USDC market parameters include:

- `pricePrecision = 1e8`;
- `sizePrecision = 1e10`;
- base asset = native MON;
- base asset decimals = `18`;
- quote asset = USDC;
- quote asset decimals = `6`.

REST quantity strings matched the raw size returned by `getL2Book`.

The relationship was verified against both bid and ask evidence at the same committed block.

## Current REST Representation Check

A fresh committed REST depth request returned HTTP `200` when using the repository's established request User-Agent.

The response contained raw integer-string price and quantity levels.

Example bid:

`["25842000000000000", "966750000000000"]`

Normalized:

- price = `0.025842`;
- base size = `96675` MON.

Example ask:

`["25849000000000000", "1158750000000000"]`

Normalized:

- price = `0.025849`;
- base size = `115875` MON.

This confirms that the current observed REST representation remains consistent with the previously verified numeric contract.

## WebSocket-to-REST Raw Representation Binding

A live read-only comparison was performed between distinct committed WebSocket books and contemporaneous committed REST depth snapshots.

The comparison used exact raw `(price, quantity)` pairs.

The gate was frozen before observing results:

- compare at least `5` distinct committed WebSocket books;
- each comparison requires at least `1` exact bid price+quantity pair;
- each comparison requires at least `1` exact ask price+quantity pair.

Observed result:

- distinct committed WebSocket books compared: `5`;
- passing comparisons: `5 / 5`;
- aggregate exact bid price+quantity pair matches: `62`;
- aggregate exact ask price+quantity pair matches: `82`.

Every predefined comparison passed.

The WebSocket and REST observations were not required to share the same `U` or `lastUpdateId`.

Those identifiers are not equated by this evidence.

## Normalization Conclusion

For the observed Kuru MON_USDC `mon_usdc@monadDepth` representation used by this repository:

`human_price = WS_price_raw / 1e18`

and:

`human_base_size = WS_quantity_raw / 1e10`

This conclusion is supported by the evidence chain:

1. full raw WebSocket state books are preserved;
2. stored top fields are directly traceable to those raw books;
3. multiple exact raw WebSocket price+quantity pairs were observed in contemporaneous REST committed books;
4. REST raw quantity was previously verified against on-chain `getL2Book`;
5. the verified MON_USDC `sizePrecision` is `1e10`.

## Claim Boundary

This evidence establishes numeric representation and provenance.

It does not establish:

- that WebSocket `U` is a block number or protocol-finality identifier;
- that REST `lastUpdateId` and WebSocket `U` have identical semantics;
- venue, network, consensus, or finality latency;
- that every future Kuru market uses the same representation;
- that every displayed level is a resting limit order;
- that all displayed liquidity is executable;
- that captured WebSocket depth is necessarily the venue's complete economically available depth;
- arbitrage, alpha, profitability, or a finality premium.

Any downstream depth or simulated-execution result must preserve these boundaries.
