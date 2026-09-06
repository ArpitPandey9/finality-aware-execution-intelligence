# Phase 1 — Coinbase MON-USD Full-L2 Historical Reconstruction Contract

## Status

Methodology frozen before cross-venue executable-depth results.

## Objective

Reconstruct the captured Coinbase Advanced Trade MON-USD Level2 order book deterministically from preserved raw WebSocket messages.

The reconstructed book is intended to become the point-in-time Coinbase reference for a later Kuru-versus-Coinbase executable-depth comparison.

This contract does not itself perform that economic comparison.

## Source Identity

Expected product:

`MON-USD`

Subscription channel:

`level2`

Observed raw message channel:

`l2_data`

Only events whose `product_id` equals `MON-USD` may mutate the target book.

Messages or events for other products must not mutate the MON-USD book.

## Reconstruction Independence

Historical reconstruction must use the preserved raw Coinbase WebSocket payloads as its state input.

Capture-time derived fields such as:

- `book_top_after`;
- `bid_levels_after`;
- `offer_levels_after`;
- `target_event_types`;
- mutation counters;

must not be used to construct the book.

They may be used only as independent parity checks after reconstruction.

## Numeric Rules

Prices and quantities are parsed with exact `Decimal` arithmetic.

Binary floating-point inputs are rejected.

Prices must be finite and strictly positive.

Quantities must be finite and non-negative.

No rounding, interpolation, aggregation, inferred replacement, or future repair is permitted.

## Snapshot Semantics

A target `snapshot` event establishes a fresh MON-USD book.

When a snapshot is applied:

1. the prior bid book is discarded;
2. the prior offer book is discarded;
3. snapshot updates are applied in source order.

The first target MON-USD book event in a replay must be a snapshot.

A target update before a valid snapshot is an integrity failure.

A later snapshot may reset the existing book.

## Update Semantics

For a target Level2 update:

`price_level`

identifies the affected price level.

`new_quantity`

is the complete updated size at that price level, not a delta.

If:

`new_quantity > 0`

the level is inserted or replaced with exactly that quantity.

If:

`new_quantity == 0`

the price level is removed if present.

Deleting an absent level is permitted and remains a deterministic no-op.

## Side Semantics

Valid sides are:

- `bid`;
- `offer`.

Unknown sides are rejected.

Bids and offers are maintained separately.

## Wrapper Sequence Integrity

All stored Coinbase wrapper messages are processed in capture order, including non-target wrappers such as subscription messages.

The captured wrapper `sequence_num` must be a non-negative integer.

After the first wrapper, each next stored wrapper must have:

`sequence_num = previous_sequence_num + 1`

A gap, repeat, reversal, or malformed sequence is an integrity failure.

This is a capture-order integrity rule.

The wrapper sequence is not interpreted as:

- a MON-USD trade count;
- an exchange-engine event count;
- network latency;
- consensus latency;
- finality latency.

Target Level2 messages may therefore have sequence-number gaps relative to each other when an intervening non-target wrapper consumed a sequence number.

## Book Validity

After initialization, the reconstructed book must contain at least one bid and one offer.

Define:

`best_bid = max(bid prices)`

`best_offer = min(offer prices)`

The book is invalid if:

`best_offer < best_bid`

A locked book where:

`best_offer == best_bid`

is permitted by this reconstruction layer.

## Historical Ordering

Messages are applied strictly in captured source order.

No future message may modify an earlier reconstructed state.

No event-time sorting is performed.

No delayed message is inserted retrospectively into an earlier state.

Receive-order replay is therefore point-in-time conservative with respect to the captured process.

## Independent Parity Checks

For every initialized stored record, reconstruction may verify:

- stored wrapper sequence equals raw wrapper sequence;
- stored channel equals raw channel;
- reconstructed best bid;
- reconstructed best-bid quantity;
- reconstructed best offer;
- reconstructed best-offer quantity;
- reconstructed spread;
- reconstructed bid-level count;
- reconstructed offer-level count;
- target event-type classification;
- snapshot-event count;
- update-event count;
- target update count;
- zero-quantity update count.

Any mismatch is an integrity failure.

## Observed Five-Capture Feasibility Evidence

A read-only independent replay was performed before implementation.

Across the frozen five captures:

- stored Coinbase records: `1917`;
- target MON-USD Level2 records: `1912`;
- snapshots: `5`;
- updates: `1907`;
- raw price-level mutations: `22275`;
- zero-quantity removals: `7424`;
- reconstructed top checks: `1917`;
- top mismatches: `0`;
- bid-level-count mismatches: `0`;
- offer-level-count mismatches: `0`;
- crossed reconstructed books: `0`.

This establishes technical reconstruction feasibility for the captured dataset.

It does not establish economic comparability with Kuru.

## Quantity Claim Boundary

The reconstruction preserves Coinbase `new_quantity` exactly as the Level2 quantity field.

The current gate does not yet make a cross-venue economic claim that the quantity is directly comparable with Kuru MON base quantity.

A separate product/unit binding gate must be completed before Coinbase quantities are used in a Kuru-versus-Coinbase fixed-base-size sweep.

## Cross-Venue Boundary

This reconstruction gate does not remove the market-basis distinction:

`Kuru MON_USDC != Coinbase MON-USD`

Any later cross-venue comparison must preserve that basis limitation explicitly.

## Claim Boundaries

Successful reconstruction does not establish:

- executable arbitrage;
- venue superiority;
- alpha;
- expected profit;
- realized execution;
- fill probability;
- queue position;
- market impact;
- fees or gas;
- causal finality effects;
- exchange latency;
- network latency;
- consensus latency;
- protocol-finality latency.

The purpose of this gate is deterministic historical book reconstruction and provenance only.
