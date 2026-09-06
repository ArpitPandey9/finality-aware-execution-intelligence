# Phase 1 — Coinbase MON-USD Quantity-Unit Evidence

## Status

**PASS — observed Coinbase MON-USD Level2 quantity representation is bound to MON base quantity.**

This evidence note supports the Coinbase historical full-L2 reconstruction gate and the later fixed-base-size cross-venue execution comparison.

The conclusion is scoped to the observed Coinbase MON-USD market and tested interfaces.

## Product Identity

Observed Coinbase product metadata:

- product ID: `MON-USD`;
- base currency ID: `MON`;
- quote currency ID: `USD`;
- base display symbol: `MON`;
- quote display symbol: `USD`;
- base increment: `1`;
- base minimum size: `1`;
- base maximum size: `400000000`;
- price increment: `0.000001`.

The product identity gate passed:

`PRODUCT_BASE_QUOTE_IDENTITY: PASS`

Therefore the Coinbase market's base asset is MON and its quote asset is USD.

## Level2 Quantity Semantics

The captured Coinbase Level2 stream represents each price-level mutation with:

- `price_level`;
- `new_quantity`;
- `side`.

The historical reconstruction contract treats `new_quantity` as the complete updated quantity at that price level rather than a delta.

A zero quantity removes that level.

The reconstruction layer preserves these quantities using exact Decimal arithmetic.

## Live WebSocket-to-REST Quantity Bridge

A fresh live empirical bridge was performed between:

- Coinbase Advanced Trade WebSocket Level2 snapshot for `MON-USD`; and
- Coinbase market REST product-book response for `MON-USD`.

For each comparison:

1. a fresh `MON-USD` Level2 snapshot was received;
2. WebSocket bid and offer price levels and `new_quantity` values were parsed exactly;
3. a fresh REST product book was fetched;
4. REST bid and ask `price` and `size` fields were parsed exactly;
5. exact price-and-size pairs were matched independently on both sides.

Frozen pass condition:

- five comparisons;
- every comparison must contain at least one exact bid price-size pair;
- every comparison must contain at least one exact ask price-size pair.

## Observed Bridge Results

### Comparison 1

- WebSocket bid levels: `584`;
- WebSocket offer levels: `601`;
- REST bid levels: `585`;
- REST ask levels: `601`;
- exact bid price-size pairs: `583`;
- exact ask price-size pairs: `600`;
- result: PASS.

### Comparison 2

- WebSocket bid levels: `583`;
- WebSocket offer levels: `595`;
- REST bid levels: `586`;
- REST ask levels: `594`;
- exact bid price-size pairs: `583`;
- exact ask price-size pairs: `591`;
- result: PASS.

### Comparison 3

- WebSocket bid levels: `585`;
- WebSocket offer levels: `593`;
- REST bid levels: `585`;
- REST ask levels: `593`;
- exact bid price-size pairs: `585`;
- exact ask price-size pairs: `593`;
- result: PASS.

### Comparison 4

- WebSocket bid levels: `578`;
- WebSocket offer levels: `595`;
- REST bid levels: `581`;
- REST ask levels: `595`;
- exact bid price-size pairs: `578`;
- exact ask price-size pairs: `593`;
- result: PASS.

### Comparison 5

- WebSocket bid levels: `584`;
- WebSocket offer levels: `595`;
- REST bid levels: `586`;
- REST ask levels: `596`;
- exact bid price-size pairs: `579`;
- exact ask price-size pairs: `585`;
- result: PASS.

Summary:

- comparisons: `5`;
- passing comparisons: `5`;
- `WS_REST_PRICE_SIZE_BINDING: PASS`.

## Unit Conclusion

The observed Coinbase market identity is:

`MON-USD`

with:

- base asset: `MON`;
- quote asset: `USD`.

The live WebSocket `new_quantity` values match REST product-book `size` values exactly at the same price levels across all five bridge comparisons.

Therefore, for the observed Coinbase MON-USD Level2 interface:

**`new_quantity` is treated as MON base quantity.**

Gate:

`COINBASE_MON_BASE_QUANTITY_BINDING: PASS`

No additional decimal scaling is applied to Coinbase Level2 quantities.

## Historical Reconstruction Evidence

Before this quantity-unit binding, the independent historical reconstruction module reproduced the frozen five captures with:

- stored Coinbase records: `1917`;
- target MON-USD Level2 records: `1912`;
- snapshots: `5`;
- updates: `1907`;
- price-level mutations: `22275`;
- zero-quantity deletions: `7424`;
- reconstructed top checks: `1917`;
- reconstructed bid-level-count checks: `1917`;
- reconstructed offer-level-count checks: `1917`;
- top mismatches: `0`;
- bid-level-count mismatches: `0`;
- offer-level-count mismatches: `0`;
- crossed reconstructed books: `0`.

Gate:

`COINBASE_REAL_MODULE_PARITY: PASS`

## Scope and Claim Boundaries

This evidence establishes numeric and product-unit binding for the observed Coinbase MON-USD interfaces.

It does not establish:

- that every Coinbase product uses identical quantity semantics;
- realized executable size;
- fill probability;
- queue position;
- market impact;
- fees;
- venue superiority;
- arbitrage;
- alpha;
- expected profit;
- causal finality effects.

The live WebSocket and REST requests are not simultaneous atomic snapshots.

Small differences in level counts or unmatched levels between the two interfaces are therefore not interpreted as data corruption or latency measurements.

The exact matching price-size pairs are used only as empirical representation evidence.

## Cross-Venue Basis Limitation

Coinbase and Kuru are not the same quoted market:

`Coinbase MON-USD != Kuru MON_USDC`

The common base asset permits fixed-MON quantity comparison.

The USD-versus-USDC quote-currency basis remains and must be preserved explicitly in all later price, VWAP, slippage, and cost interpretations.

This quantity-unit binding does not remove that basis difference.
