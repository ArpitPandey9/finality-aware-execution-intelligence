from __future__ import annotations

import unittest
from decimal import Decimal

from finality_intelligence.cross_venue_execution import (
    BOTH_FULL,
    COINBASE_ONLY_FULL,
    KURU_ONLY_FULL,
    NEITHER_FULL,
    SCHEMA_VERSION,
    _coinbase_book_to_execution_book,
    _cross_venue_metrics,
    _fillability_transition,
    analyze_cross_venue_capture,
    reconstruct_coinbase_books_at_indices,
)
from finality_intelligence.depth_execution import (
    FULLY_FILLED_IN_CAPTURED_BOOK,
    INSUFFICIENT_CAPTURED_DEPTH,
)


def level(
    side: str,
    price: str,
    quantity: str,
) -> dict:
    return {
        "side": side,
        "price_level": price,
        "new_quantity": quantity,
        "event_time":
            "2026-09-06T00:00:00Z",
    }


def cb_message(
    sequence_num: int,
    *,
    channel: str = "l2_data",
    event_type: str | None = None,
    updates: list[dict] | None = None,
) -> dict:
    events = []

    if event_type is not None:
        events.append(
            {
                "type": event_type,
                "product_id": "MON-USD",
                "updates": (
                    updates
                    if updates is not None
                    else []
                ),
            }
        )

    return {
        "channel": channel,
        "sequence_num": sequence_num,
        "events": events,
    }


def cb_record(
    sequence_num: int,
    *,
    raw_message: dict,
    received_ns: int,
    book_top_after: dict | None,
    bid_levels_after: int | None,
    offer_levels_after: int | None,
    snapshot_events: int = 0,
    update_events: int = 0,
    target_updates: int = 0,
    zero_quantity_updates: int = 0,
    target_event_types: list[str] | None = None,
) -> dict:
    return {
        "sequence_num": sequence_num,
        "channel": raw_message["channel"],
        "raw_message": raw_message,
        "received_monotonic_ns": received_ns,
        "received_at_utc":
            "2026-09-06T00:00:00+00:00",
        "timestamp":
            "2026-09-06T00:00:00Z",
        "target_product_id": (
            "MON-USD"
            if target_event_types
            else None
        ),
        "target_event_types": (
            target_event_types
            if target_event_types is not None
            else []
        ),
        "snapshot_events": snapshot_events,
        "update_events": update_events,
        "target_updates": target_updates,
        "zero_quantity_updates":
            zero_quantity_updates,
        "book_top_after": book_top_after,
        "bid_levels_after": bid_levels_after,
        "offer_levels_after":
            offer_levels_after,
        "crossed_or_locked": False,
    }


def simple_cb_snapshot_record(
    *,
    received_ns: int = 100,
) -> dict:
    raw = cb_message(
        0,
        event_type="snapshot",
        updates=[
            level(
                "bid",
                "1.00",
                "1000000",
            ),
            level(
                "offer",
                "1.01",
                "1000000",
            ),
        ],
    )

    return cb_record(
        0,
        raw_message=raw,
        received_ns=received_ns,
        book_top_after={
            "best_bid": "1.00",
            "best_bid_quantity":
                "1000000",
            "best_offer": "1.01",
            "best_offer_quantity":
                "1000000",
            "spread": "0.01",
        },
        bid_levels_after=1,
        offer_levels_after=1,
        snapshot_events=1,
        target_updates=2,
        target_event_types=[
            "snapshot"
        ],
    )


def kuru_book(
    *,
    bid_raw: int = 1000000000000000000,
    ask_raw: int = 1010000000000000000,
    qty_raw: int = 10000000000000000,
) -> dict:
    return {
        "b": [
            [
                bid_raw,
                qty_raw,
            ]
        ],
        "a": [
            [
                ask_raw,
                qty_raw,
            ]
        ],
    }


def capture(
    *,
    kuru_received_ns: int = 200,
) -> dict:
    raw_states = {
        "proposed": kuru_book(),
        "voted": kuru_book(),
        "finalized": kuru_book(),
        "committed": kuru_book(),
    }

    top_states = {
        state: {
            "best_bid_raw":
                "1000000000000000000",
            "best_bid_quantity_raw":
                "10000000000000000",
            "best_ask_raw":
                "1010000000000000000",
            "best_ask_quantity_raw":
                "10000000000000000",
        }
        for state in raw_states
    }

    return {
        "schema_version":
            "phase0.dual_ws_capture.v1",
        "gate": {
            "overall": "PASS",
        },
        "sources": {
            "kuru": {
                "market": "MON_USDC",
                "error": None,
                "records": [
                    {
                        "received_monotonic_ns":
                            kuru_received_ns,
                        "received_at_utc":
                            "2026-09-06T00:00:00+00:00",
                        "U": 123,
                        "states": top_states,
                        "raw_message": {
                            "states":
                                raw_states,
                        },
                    }
                ],
            },
            "coinbase": {
                "market": "MON-USD",
                "channel": "level2",
                "error": None,
                "records": [
                    simple_cb_snapshot_record()
                ],
            },
        },
    }


class TestCrossVenueExecution(
    unittest.TestCase
):
    def test_coinbase_book_adapter(
        self,
    ):
        result = (
            _coinbase_book_to_execution_book(
                {
                    "bids": (
                        (
                            Decimal("1.00"),
                            Decimal("10"),
                        ),
                    ),
                    "offers": (
                        (
                            Decimal("1.01"),
                            Decimal("20"),
                        ),
                    ),
                }
            )
        )

        self.assertEqual(
            result["best_bid"],
            Decimal("1.00"),
        )
        self.assertEqual(
            result["best_ask"],
            Decimal("1.01"),
        )
        self.assertEqual(
            result["bids"][0]["quantity"],
            Decimal("10"),
        )

    def test_coinbase_book_adapter_rejects_cross(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            _coinbase_book_to_execution_book(
                {
                    "bids": (
                        (
                            Decimal("1.02"),
                            Decimal("10"),
                        ),
                    ),
                    "offers": (
                        (
                            Decimal("1.01"),
                            Decimal("20"),
                        ),
                    ),
                }
            )

    def test_reconstruct_selected_index(
        self,
    ):
        record = (
            simple_cb_snapshot_record()
        )

        books = (
            reconstruct_coinbase_books_at_indices(
                [record],
                record_indices={0},
            )
        )

        self.assertEqual(
            set(books),
            {0},
        )
        self.assertEqual(
            books[0]["best_bid"],
            Decimal("1.00"),
        )

    def test_reconstruction_rejects_bad_index(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            reconstruct_coinbase_books_at_indices(
                [
                    simple_cb_snapshot_record()
                ],
                record_indices={1},
            )

    def test_fillability_both_full(
        self,
    ):
        self.assertEqual(
            _fillability_transition(
                FULLY_FILLED_IN_CAPTURED_BOOK,
                FULLY_FILLED_IN_CAPTURED_BOOK,
            ),
            BOTH_FULL,
        )

    def test_fillability_kuru_only(
        self,
    ):
        self.assertEqual(
            _fillability_transition(
                FULLY_FILLED_IN_CAPTURED_BOOK,
                INSUFFICIENT_CAPTURED_DEPTH,
            ),
            KURU_ONLY_FULL,
        )

    def test_fillability_coinbase_only(
        self,
    ):
        self.assertEqual(
            _fillability_transition(
                INSUFFICIENT_CAPTURED_DEPTH,
                FULLY_FILLED_IN_CAPTURED_BOOK,
            ),
            COINBASE_ONLY_FULL,
        )

    def test_fillability_neither(
        self,
    ):
        self.assertEqual(
            _fillability_transition(
                INSUFFICIENT_CAPTURED_DEPTH,
                INSUFFICIENT_CAPTURED_DEPTH,
            ),
            NEITHER_FULL,
        )

    def test_cross_metrics_second_venue_slippage(
        self,
    ):
        result = _cross_venue_metrics(
            kuru_sweep={
                "fillability_status":
                    FULLY_FILLED_IN_CAPTURED_BOOK,
                "slippage_bps":
                    Decimal("10"),
                "vwap":
                    Decimal("1.02"),
            },
            coinbase_sweep={
                "fillability_status":
                    FULLY_FILLED_IN_CAPTURED_BOOK,
                "slippage_bps":
                    Decimal("4"),
                "vwap":
                    Decimal("1.01"),
            },
        )

        self.assertEqual(
            result["slippage_gap_bps"],
            Decimal("6"),
        )

        self.assertEqual(
            result[
                "vwap_difference_bps"
            ],
            (
                Decimal("0.01")
                / Decimal("1.01")
                * Decimal("10000")
            ),
        )

    def test_cross_metrics_non_both_full_has_no_gap(
        self,
    ):
        result = _cross_venue_metrics(
            kuru_sweep={
                "fillability_status":
                    FULLY_FILLED_IN_CAPTURED_BOOK,
                "slippage_bps": None,
                "vwap": None,
            },
            coinbase_sweep={
                "fillability_status":
                    INSUFFICIENT_CAPTURED_DEPTH,
                "slippage_bps": None,
                "vwap": None,
            },
        )

        self.assertEqual(
            result["fillability_transition"],
            KURU_ONLY_FULL,
        )
        self.assertIsNone(
            result["slippage_gap_bps"]
        )
        self.assertIsNone(
            result[
                "vwap_difference_bps"
            ]
        )

    def test_analysis_reuses_alignment_and_four_states(
        self,
    ):
        result = analyze_cross_venue_capture(
            capture(),
            capture_id="capture-1",
            max_age_ms=Decimal(
                "0.0001"
            ),
        )

        self.assertEqual(
            result["schema_version"],
            SCHEMA_VERSION,
        )

        self.assertEqual(
            result[
                "freshness_threshold_ms"
            ],
            "0.0001",
        )

        self.assertEqual(
            len(result["rows"]),
            4 * 2 * 4,
        )

        self.assertEqual(
            len(result["depth_rows"]),
            4 * 2 * 4,
        )

        self.assertEqual(
            {
                row[
                    "coinbase_record_index"
                ]
                for row in result["rows"]
            },
            {0},
        )

    def test_same_coinbase_reference_for_all_states(
        self,
    ):
        result = analyze_cross_venue_capture(
            capture(),
            capture_id="capture-1",
            max_age_ms=Decimal(
                "1"
            ),
        )

        refs = {
            (
                row["state"],
                row[
                    "coinbase_record_index"
                ],
            )
            for row in result["rows"]
        }

        self.assertEqual(
            {
                index
                for _, index in refs
            },
            {0},
        )

        self.assertEqual(
            {
                state
                for state, _ in refs
            },
            {
                "proposed",
                "voted",
                "finalized",
                "committed",
            },
        )

    def test_stale_alignment_produces_no_economics(
        self,
    ):
        result = analyze_cross_venue_capture(
            capture(
                kuru_received_ns=
                    2_000_000
            ),
            capture_id="capture-1",
            max_age_ms=Decimal(
                "0.1"
            ),
        )

        self.assertEqual(
            result["rows"],
            [],
        )
        self.assertEqual(
            result["depth_rows"],
            [],
        )
        self.assertEqual(
            result["summary"][
                "alignment_status_counts"
            ][
                "STALE_REFERENCE"
            ],
            1,
        )

    def test_no_future_coinbase_reference(
        self,
    ):
        result = analyze_cross_venue_capture(
            capture(
                kuru_received_ns=50
            ),
            capture_id="capture-1",
            max_age_ms=Decimal(
                "1000"
            ),
        )

        self.assertEqual(
            result["rows"],
            [],
        )
        self.assertEqual(
            result["depth_rows"],
            [],
        )
        self.assertEqual(
            result["summary"][
                "alignment_status_counts"
            ][
                "NO_PRIOR_REFERENCE"
            ],
            1,
        )

    def test_summary_separates_alignment_from_economic_eligibility(
        self,
    ):
        result = analyze_cross_venue_capture(
            capture(),
            capture_id="capture-1",
            max_age_ms=Decimal("1"),
        )

        self.assertEqual(
            result["summary"][
                "alignment_status_counts"
            ],
            {"ALIGNED": 1},
        )

        self.assertEqual(
            result["summary"][
                "economic_eligibility_counts"
            ],
            {
                "ECONOMICALLY_ELIGIBLE": 1
            },
        )

    def test_summary_separates_alignment_from_economic_eligibility(
        self,
    ):
        result = analyze_cross_venue_capture(
            capture(),
            capture_id="capture-1",
            max_age_ms=Decimal("1"),
        )

        self.assertEqual(
            result["summary"][
                "alignment_status_counts"
            ],
            {"ALIGNED": 1},
        )

        self.assertEqual(
            result["summary"][
                "economic_eligibility_counts"
            ],
            {
                "ECONOMICALLY_ELIGIBLE": 1
            },
        )

    def test_missing_raw_message_invalidates_kuru_panel(
        self,
    ):
        source = capture()

        del source[
            "sources"
        ][
            "kuru"
        ][
            "records"
        ][0][
            "raw_message"
        ]

        result = analyze_cross_venue_capture(
            source,
            capture_id="capture-1",
            max_age_ms=Decimal("1"),
        )

        self.assertEqual(
            result["rows"],
            [],
        )

        self.assertEqual(
            result["depth_rows"],
            [],
        )

        self.assertEqual(
            result["summary"][
                "economic_eligibility_counts"
            ][
                "INVALID_KURU_PANEL"
            ],
            1,
        )

    def test_claim_boundaries_preserve_basis_risk(
        self,
    ):
        result = analyze_cross_venue_capture(
            capture(),
            capture_id="capture-1",
            max_age_ms=Decimal(
                "1"
            ),
        )

        joined = " ".join(
            result["claim_boundaries"]
        )

        self.assertIn(
            "USD/USDC basis risk",
            joined,
        )
        self.assertIn(
            "not trading edge",
            joined,
        )


if __name__ == "__main__":
    unittest.main()
