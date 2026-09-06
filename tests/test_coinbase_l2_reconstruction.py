from __future__ import annotations

import unittest
from decimal import Decimal

from finality_intelligence.coinbase_l2_reconstruction import (
    CoinbaseL2Reconstructor,
    verify_capture_records,
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


def message(
    sequence_num: int,
    *,
    channel: str = "l2_data",
    event_type: str | None = None,
    product_id: str = "MON-USD",
    updates=None,
) -> dict:
    events = []

    if event_type is not None:
        events.append(
            {
                "type":
                    event_type,
                "product_id":
                    product_id,
                "updates":
                    (
                        []
                        if updates is None
                        else updates
                    ),
            }
        )

    return {
        "channel":
            channel,
        "sequence_num":
            sequence_num,
        "timestamp":
            "2026-09-06T00:00:00Z",
        "events":
            events,
    }


def stored_record(
    raw_message: dict,
    *,
    best_bid: str,
    best_bid_quantity: str,
    best_offer: str,
    best_offer_quantity: str,
    spread: str,
    bid_count: int,
    offer_count: int,
    target_event_types,
    snapshot_events: int,
    update_events: int,
    target_updates: int,
    zero_quantity_updates: int,
) -> dict:
    return {
        "raw_message":
            raw_message,
        "sequence_num":
            raw_message[
                "sequence_num"
            ],
        "channel":
            raw_message[
                "channel"
            ],
        "book_top_after": {
            "best_bid":
                best_bid,
            "best_bid_quantity":
                best_bid_quantity,
            "best_offer":
                best_offer,
            "best_offer_quantity":
                best_offer_quantity,
            "spread":
                spread,
        },
        "bid_levels_after":
            bid_count,
        "offer_levels_after":
            offer_count,
        "target_event_types":
            list(
                target_event_types
            ),
        "snapshot_events":
            snapshot_events,
        "update_events":
            update_events,
        "target_updates":
            target_updates,
        "zero_quantity_updates":
            zero_quantity_updates,
    }


class TestCoinbaseL2Reconstruction(
    unittest.TestCase
):
    def test_snapshot_initializes_exact_book(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        result = book.apply_message(
            message(
                0,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "1.00",
                        "5",
                    ),
                    level(
                        "offer",
                        "2.00",
                        "4",
                    ),
                ],
            )
        )

        self.assertTrue(
            book.initialized
        )

        self.assertEqual(
            result[
                "book_top_after"
            ]["best_bid"],
            Decimal("1.00"),
        )

        self.assertEqual(
            result[
                "book_top_after"
            ]["best_offer"],
            Decimal("2.00"),
        )

    def test_update_replaces_absolute_quantity(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        book.apply_message(
            message(
                0,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "1",
                        "5",
                    ),
                    level(
                        "offer",
                        "2",
                        "4",
                    ),
                ],
            )
        )

        book.apply_message(
            message(
                1,
                event_type="update",
                updates=[
                    level(
                        "bid",
                        "1",
                        "7",
                    ),
                ],
            )
        )

        self.assertEqual(
            book.bids[
                Decimal("1")
            ],
            Decimal("7"),
        )

    def test_zero_quantity_deletes_level(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        book.apply_message(
            message(
                0,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "1",
                        "5",
                    ),
                    level(
                        "bid",
                        "0.9",
                        "2",
                    ),
                    level(
                        "offer",
                        "2",
                        "4",
                    ),
                ],
            )
        )

        book.apply_message(
            message(
                1,
                event_type="update",
                updates=[
                    level(
                        "bid",
                        "1",
                        "0",
                    ),
                ],
            )
        )

        self.assertNotIn(
            Decimal("1"),
            book.bids,
        )

        self.assertEqual(
            book.current_top()[
                "best_bid"
            ],
            Decimal("0.9"),
        )

    def test_snapshot_resets_existing_book(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        book.apply_message(
            message(
                0,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "1",
                        "5",
                    ),
                    level(
                        "offer",
                        "2",
                        "4",
                    ),
                ],
            )
        )

        book.apply_message(
            message(
                1,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "3",
                        "8",
                    ),
                    level(
                        "offer",
                        "4",
                        "9",
                    ),
                ],
            )
        )

        self.assertEqual(
            set(book.bids),
            {
                Decimal("3")
            },
        )

        self.assertEqual(
            set(book.offers),
            {
                Decimal("4")
            },
        )

    def test_update_before_snapshot_is_rejected(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        with self.assertRaises(
            ValueError
        ):
            book.apply_message(
                message(
                    0,
                    event_type="update",
                    updates=[
                        level(
                            "bid",
                            "1",
                            "5",
                        )
                    ],
                )
            )

    def test_wrapper_sequence_gap_is_rejected(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        book.apply_message(
            message(
                0,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "1",
                        "5",
                    ),
                    level(
                        "offer",
                        "2",
                        "4",
                    ),
                ],
            )
        )

        with self.assertRaises(
            ValueError
        ):
            book.apply_message(
                message(
                    2,
                    event_type="update",
                    updates=[],
                )
            )

    def test_non_target_wrapper_preserves_book_and_sequence(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        book.apply_message(
            message(
                0,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "1",
                        "5",
                    ),
                    level(
                        "offer",
                        "2",
                        "4",
                    ),
                ],
            )
        )

        before = (
            book.current_book()
        )

        result = book.apply_message(
            message(
                1,
                channel="subscriptions",
            )
        )

        self.assertFalse(
            result[
                "target_record"
            ]
        )

        self.assertEqual(
            book.current_book(),
            before,
        )

        book.apply_message(
            message(
                2,
                event_type="update",
                updates=[],
            )
        )

    def test_other_product_l2_event_is_ignored(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        book.apply_message(
            message(
                0,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "1",
                        "5",
                    ),
                    level(
                        "offer",
                        "2",
                        "4",
                    ),
                ],
            )
        )

        before = (
            book.current_book()
        )

        result = book.apply_message(
            message(
                1,
                event_type="update",
                product_id="BTC-USD",
                updates=[
                    level(
                        "bid",
                        "100",
                        "10",
                    )
                ],
            )
        )

        self.assertFalse(
            result[
                "target_record"
            ]
        )

        self.assertEqual(
            book.current_book(),
            before,
        )

    def test_float_numeric_input_is_rejected(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        raw = message(
            0,
            event_type="snapshot",
            updates=[
                level(
                    "bid",
                    "1",
                    "5",
                ),
                level(
                    "offer",
                    "2",
                    "4",
                ),
            ],
        )

        raw["events"][0][
            "updates"
        ][0]["price_level"] = 1.0

        with self.assertRaises(
            TypeError
        ):
            book.apply_message(
                raw
            )

    def test_unknown_side_is_rejected(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        with self.assertRaises(
            ValueError
        ):
            book.apply_message(
                message(
                    0,
                    event_type="snapshot",
                    updates=[
                        level(
                            "wrong",
                            "1",
                            "5",
                        ),
                        level(
                            "offer",
                            "2",
                            "4",
                        ),
                    ],
                )
            )

    def test_crossed_book_is_rejected(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        with self.assertRaises(
            ValueError
        ):
            book.apply_message(
                message(
                    0,
                    event_type="snapshot",
                    updates=[
                        level(
                            "bid",
                            "3",
                            "5",
                        ),
                        level(
                            "offer",
                            "2",
                            "4",
                        ),
                    ],
                )
            )

    def test_stored_top_mismatch_is_rejected(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        raw = message(
            0,
            event_type="snapshot",
            updates=[
                level(
                    "bid",
                    "1",
                    "5",
                ),
                level(
                    "offer",
                    "2",
                    "4",
                ),
            ],
        )

        record = stored_record(
            raw,
            best_bid="9",
            best_bid_quantity="5",
            best_offer="2",
            best_offer_quantity="4",
            spread="1",
            bid_count=1,
            offer_count=1,
            target_event_types=[
                "snapshot"
            ],
            snapshot_events=1,
            update_events=0,
            target_updates=2,
            zero_quantity_updates=0,
        )

        with self.assertRaises(
            ValueError
        ):
            book.verify_stored_record(
                record
            )

    def test_stored_level_count_mismatch_is_rejected(
        self,
    ):
        book = (
            CoinbaseL2Reconstructor()
        )

        raw = message(
            0,
            event_type="snapshot",
            updates=[
                level(
                    "bid",
                    "1",
                    "5",
                ),
                level(
                    "offer",
                    "2",
                    "4",
                ),
            ],
        )

        record = stored_record(
            raw,
            best_bid="1",
            best_bid_quantity="5",
            best_offer="2",
            best_offer_quantity="4",
            spread="1",
            bid_count=99,
            offer_count=1,
            target_event_types=[
                "snapshot"
            ],
            snapshot_events=1,
            update_events=0,
            target_updates=2,
            zero_quantity_updates=0,
        )

        with self.assertRaises(
            ValueError
        ):
            book.verify_stored_record(
                record
            )

    def test_capture_summary_reconciles(
        self,
    ):
        snapshot = message(
            0,
            event_type="snapshot",
            updates=[
                level(
                    "bid",
                    "1",
                    "5",
                ),
                level(
                    "offer",
                    "2",
                    "4",
                ),
            ],
        )

        subscription = message(
            1,
            channel="subscriptions",
        )

        update = message(
            2,
            event_type="update",
            updates=[
                level(
                    "bid",
                    "1",
                    "7",
                ),
                level(
                    "offer",
                    "2",
                    "0",
                ),
                level(
                    "offer",
                    "3",
                    "1",
                ),
            ],
        )

        records = [
            stored_record(
                snapshot,
                best_bid="1",
                best_bid_quantity="5",
                best_offer="2",
                best_offer_quantity="4",
                spread="1",
                bid_count=1,
                offer_count=1,
                target_event_types=[
                    "snapshot"
                ],
                snapshot_events=1,
                update_events=0,
                target_updates=2,
                zero_quantity_updates=0,
            ),
            stored_record(
                subscription,
                best_bid="1",
                best_bid_quantity="5",
                best_offer="2",
                best_offer_quantity="4",
                spread="1",
                bid_count=1,
                offer_count=1,
                target_event_types=[],
                snapshot_events=0,
                update_events=0,
                target_updates=0,
                zero_quantity_updates=0,
            ),
            stored_record(
                update,
                best_bid="1",
                best_bid_quantity="7",
                best_offer="3",
                best_offer_quantity="1",
                spread="2",
                bid_count=1,
                offer_count=1,
                target_event_types=[
                    "update"
                ],
                snapshot_events=0,
                update_events=1,
                target_updates=3,
                zero_quantity_updates=1,
            ),
        ]

        result = (
            verify_capture_records(
                records
            )
        )

        self.assertEqual(
            result["records"],
            3,
        )
        self.assertEqual(
            result[
                "target_l2_records"
            ],
            2,
        )
        self.assertEqual(
            result["snapshots"],
            1,
        )
        self.assertEqual(
            result["updates"],
            1,
        )
        self.assertEqual(
            result[
                "price_level_mutations"
            ],
            5,
        )
        self.assertEqual(
            result[
                "zero_quantity_deletes"
            ],
            1,
        )
        self.assertEqual(
            result["top_checks"],
            3,
        )


if __name__ == "__main__":
    unittest.main()
