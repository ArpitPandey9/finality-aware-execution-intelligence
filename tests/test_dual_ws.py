from __future__ import annotations

import hashlib
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from finality_intelligence.dual_ws import (
    build_dual_capture,
    process_coinbase_message,
    summarize_coinbase_messages,
    write_dual_capture,
)


def cb_message(
    *,
    sequence_num: int,
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
                    updates or []
                ),
            }
        )

    return {
        "channel": channel,
        "timestamp": (
            "2026-09-06T00:00:00Z"
        ),
        "sequence_num": sequence_num,
        "events": events,
    }


def level(
    side: str,
    price: str,
    quantity: str,
) -> dict:
    return {
        "side": side,
        "event_time": (
            "2026-09-06T00:00:00Z"
        ),
        "price_level": price,
        "new_quantity": quantity,
    }


def process(
    message: dict,
    *,
    ns: int,
    bids: dict,
    offers: dict,
) -> dict:
    return process_coinbase_message(
        message,
        received_at_utc=(
            "2026-09-06T00:00:00+00:00"
        ),
        received_monotonic_ns=ns,
        product_id="MON-USD",
        bids=bids,
        offers=offers,
    )


def kuru_record(
    *,
    ns: int,
    update_id: int,
) -> dict:
    states = {}

    for name in (
        "proposed",
        "voted",
        "finalized",
        "committed",
    ):
        states[name] = {
            "best_bid_raw": "100",
            "best_bid_quantity_raw": "10",
            "best_ask_raw": "101",
            "best_ask_quantity_raw": "11",
        }

    return {
        "received_at_utc": (
            "2026-09-06T00:00:00+00:00"
        ),
        "received_monotonic_ns": ns,
        "event": "monadDepthUpdate",
        "symbol": "0x065c9d28",
        "U": update_id,
        "E": 1,
        "T": 1,
        "all_states_same_top_of_book": (
            True
        ),
        "states": states,
        "raw_message": {
            "states": states,
            "U": update_id,
        },
    }


class TestDualWebSocketEvidence(
    unittest.TestCase
):
    def test_snapshot_initializes_book(self):
        bids = {}
        offers = {}

        record = process(
            cb_message(
                sequence_num=0,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "100",
                        "10",
                    ),
                    level(
                        "offer",
                        "101",
                        "11",
                    ),
                ],
            ),
            ns=1,
            bids=bids,
            offers=offers,
        )

        self.assertEqual(
            bids[
                Decimal("100")
            ],
            Decimal("10"),
        )

        self.assertEqual(
            offers[
                Decimal("101")
            ],
            Decimal("11"),
        )

        self.assertEqual(
            record[
                "book_top_after"
            ][
                "spread"
            ],
            "1",
        )

    def test_snapshot_resets_existing_book(self):
        bids = {}
        offers = {}

        process(
            cb_message(
                sequence_num=0,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "100",
                        "10",
                    ),
                    level(
                        "offer",
                        "101",
                        "11",
                    ),
                ],
            ),
            ns=1,
            bids=bids,
            offers=offers,
        )

        process(
            cb_message(
                sequence_num=1,
                event_type="update",
                updates=[
                    level(
                        "bid",
                        "99",
                        "5",
                    ),
                ],
            ),
            ns=2,
            bids=bids,
            offers=offers,
        )

        process(
            cb_message(
                sequence_num=2,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "98",
                        "7",
                    ),
                    level(
                        "offer",
                        "102",
                        "8",
                    ),
                ],
            ),
            ns=3,
            bids=bids,
            offers=offers,
        )

        self.assertEqual(
            set(bids),
            {
                Decimal("98"),
            },
        )

        self.assertEqual(
            set(offers),
            {
                Decimal("102"),
            },
        )

    def test_zero_quantity_removes_level(self):
        bids = {}
        offers = {}

        process(
            cb_message(
                sequence_num=0,
                event_type="snapshot",
                updates=[
                    level(
                        "bid",
                        "100",
                        "10",
                    ),
                    level(
                        "bid",
                        "99",
                        "9",
                    ),
                    level(
                        "offer",
                        "101",
                        "11",
                    ),
                ],
            ),
            ns=1,
            bids=bids,
            offers=offers,
        )

        record = process(
            cb_message(
                sequence_num=1,
                event_type="update",
                updates=[
                    level(
                        "bid",
                        "100",
                        "0",
                    ),
                ],
            ),
            ns=2,
            bids=bids,
            offers=offers,
        )

        self.assertNotIn(
            Decimal("100"),
            bids,
        )

        self.assertEqual(
            record[
                "book_top_after"
            ][
                "best_bid"
            ],
            "99",
        )

        self.assertEqual(
            record[
                "zero_quantity_updates"
            ],
            1,
        )

    def test_unknown_side_is_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            process(
                cb_message(
                    sequence_num=0,
                    event_type="snapshot",
                    updates=[
                        level(
                            "ask",
                            "101",
                            "11",
                        ),
                    ],
                ),
                ns=1,
                bids={},
                offers={},
            )

    def test_wrapper_sequence_can_be_contiguous_when_l2_skips(self):
        bids = {}
        offers = {}

        records = [
            process(
                cb_message(
                    sequence_num=0,
                    event_type="snapshot",
                    updates=[
                        level(
                            "bid",
                            "100",
                            "10",
                        ),
                        level(
                            "offer",
                            "101",
                            "11",
                        ),
                    ],
                ),
                ns=1,
                bids=bids,
                offers=offers,
            ),

            process(
                cb_message(
                    sequence_num=1,
                    channel="subscriptions",
                ),
                ns=2,
                bids=bids,
                offers=offers,
            ),

            process(
                cb_message(
                    sequence_num=2,
                    event_type="update",
                    updates=[
                        level(
                            "bid",
                            "100",
                            "12",
                        ),
                    ],
                ),
                ns=3,
                bids=bids,
                offers=offers,
            ),
        ]

        summary = (
            summarize_coinbase_messages(
                records
            )
        )

        self.assertEqual(
            summary[
                "wrapper_sequence_non_plus_one_transitions"
            ],
            0,
        )

        self.assertEqual(
            summary[
                "l2_sequence_delta_counts"
            ],
            {
                "2": 1,
            },
        )

    def test_dual_gate_passes_with_overlap(self):
        bids = {}
        offers = {}

        coinbase = [
            process(
                cb_message(
                    sequence_num=0,
                    event_type="snapshot",
                    updates=[
                        level(
                            "bid",
                            "100",
                            "10",
                        ),
                        level(
                            "offer",
                            "101",
                            "11",
                        ),
                    ],
                ),
                ns=1_100_000_000,
                bids=bids,
                offers=offers,
            ),

            process(
                cb_message(
                    sequence_num=1,
                    channel="subscriptions",
                ),
                ns=1_200_000_000,
                bids=bids,
                offers=offers,
            ),

            process(
                cb_message(
                    sequence_num=2,
                    event_type="update",
                    updates=[
                        level(
                            "bid",
                            "100",
                            "12",
                        ),
                    ],
                ),
                ns=2_000_000_000,
                bids=bids,
                offers=offers,
            ),
        ]

        capture = build_dual_capture(
            requested_duration_seconds=10,
            session_started_utc="start",
            session_completed_utc="end",

            kuru_records=[
                kuru_record(
                    ns=1_000_000_000,
                    update_id=1,
                ),
                kuru_record(
                    ns=2_100_000_000,
                    update_id=2,
                ),
            ],

            kuru_error=None,

            coinbase_records=coinbase,
            coinbase_error=None,
        )

        self.assertEqual(
            capture["gate"]["overall"],
            "PASS",
        )

        self.assertAlmostEqual(
            capture[
                "temporal_overlap"
            ][
                "target_message_envelope_overlap_seconds"
            ],
            0.9,
        )

    def test_dual_gate_reviews_update_before_snapshot(self):
        bids = {}
        offers = {}

        coinbase = [
            process(
                cb_message(
                    sequence_num=0,
                    event_type="update",
                    updates=[
                        level(
                            "bid",
                            "99",
                            "5",
                        ),
                    ],
                ),
                ns=1_100_000_000,
                bids=bids,
                offers=offers,
            ),

            process(
                cb_message(
                    sequence_num=1,
                    event_type="snapshot",
                    updates=[
                        level(
                            "bid",
                            "100",
                            "10",
                        ),
                        level(
                            "offer",
                            "101",
                            "11",
                        ),
                    ],
                ),
                ns=1_500_000_000,
                bids=bids,
                offers=offers,
            ),

            process(
                cb_message(
                    sequence_num=2,
                    event_type="update",
                    updates=[
                        level(
                            "bid",
                            "100",
                            "12",
                        ),
                    ],
                ),
                ns=2_000_000_000,
                bids=bids,
                offers=offers,
            ),
        ]

        capture = build_dual_capture(
            requested_duration_seconds=10,
            session_started_utc="start",
            session_completed_utc="end",

            kuru_records=[
                kuru_record(
                    ns=1_000_000_000,
                    update_id=1,
                ),
                kuru_record(
                    ns=2_100_000_000,
                    update_id=2,
                ),
            ],

            kuru_error=None,

            coinbase_records=coinbase,
            coinbase_error=None,
        )

        summary = capture[
            "sources"
        ][
            "coinbase"
        ][
            "summary"
        ]

        self.assertFalse(
            summary[
                "first_target_includes_snapshot"
            ]
        )

        self.assertEqual(
            summary[
                "target_l2_messages_before_first_snapshot"
            ],
            1,
        )

        self.assertEqual(
            capture[
                "gate"
            ][
                "coinbase"
            ],
            "REVIEW",
        )

        self.assertEqual(
            capture[
                "gate"
            ][
                "overall"
            ],
            "REVIEW",
        )

    def test_dual_gate_reviews_wrapper_gap(self):
        bids = {}
        offers = {}

        coinbase = [
            process(
                cb_message(
                    sequence_num=0,
                    event_type="snapshot",
                    updates=[
                        level(
                            "bid",
                            "100",
                            "10",
                        ),
                        level(
                            "offer",
                            "101",
                            "11",
                        ),
                    ],
                ),
                ns=1_100_000_000,
                bids=bids,
                offers=offers,
            ),

            process(
                cb_message(
                    sequence_num=2,
                    event_type="update",
                    updates=[
                        level(
                            "bid",
                            "100",
                            "12",
                        ),
                    ],
                ),
                ns=2_000_000_000,
                bids=bids,
                offers=offers,
            ),
        ]

        capture = build_dual_capture(
            requested_duration_seconds=10,
            session_started_utc="start",
            session_completed_utc="end",

            kuru_records=[
                kuru_record(
                    ns=1_000_000_000,
                    update_id=1,
                ),
                kuru_record(
                    ns=2_100_000_000,
                    update_id=2,
                ),
            ],

            kuru_error=None,

            coinbase_records=coinbase,
            coinbase_error=None,
        )

        self.assertEqual(
            capture[
                "gate"
            ][
                "coinbase"
            ],
            "REVIEW",
        )

        self.assertEqual(
            capture["gate"]["overall"],
            "REVIEW",
        )

    def test_write_dual_capture_hash_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "dual.json"
            )

            raw_path, hash_path = (
                write_dual_capture(
                    {
                        "hello": "world",
                    },
                    path,
                )
            )

            digest = hashlib.sha256(
                raw_path.read_bytes()
            ).hexdigest()

            expected = (
                hash_path.read_text(
                    encoding="utf-8"
                ).strip()
            )

            self.assertEqual(
                expected,
                (
                    f"{digest}  "
                    f"{raw_path.name}"
                ),
            )


if __name__ == "__main__":
    unittest.main()
