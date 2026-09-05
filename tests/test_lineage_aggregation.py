from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from finality_intelligence.lineage_aggregation import (
    aggregate_captures,
    verify_capture_hash,
)


def state(
    *,
    bid_price="100",
    bid_qty="10",
    ask_price="101",
    ask_qty="11",
):
    return {
        "best_bid_raw": bid_price,
        "best_bid_quantity_raw": (
            bid_qty
        ),
        "best_ask_raw": ask_price,
        "best_ask_quantity_raw": (
            ask_qty
        ),
    }


def record(
    *,
    timestamp,
    u,
    proposed=None,
    voted=None,
    finalized=None,
    committed=None,
):
    empty = {
        "best_bid_raw": None,
        "best_bid_quantity_raw": None,
        "best_ask_raw": None,
        "best_ask_quantity_raw": None,
    }

    return {
        "received_at_utc": timestamp,
        "U": u,
        "states": {
            "proposed": (
                proposed
                if proposed is not None
                else empty.copy()
            ),
            "voted": (
                voted
                if voted is not None
                else empty.copy()
            ),
            "finalized": (
                finalized
                if finalized is not None
                else empty.copy()
            ),
            "committed": (
                committed
                if committed is not None
                else empty.copy()
            ),
        },
    }


def complete_capture():
    quote = state()

    return {
        "connection_completed_utc": (
            "2026-09-05T00:00:02+00:00"
        ),
        "summary": {
            "unique_U": 2,
        },
        "records": [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=99,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.100000+00:00"
                ),
                u=1,
                proposed=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.200000+00:00"
                ),
                u=1,
                voted=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.300000+00:00"
                ),
                u=1,
                finalized=quote,
                committed=quote,
            ),
        ],
    }


def unmatched_capture():
    quote = state()

    return {
        "connection_completed_utc": (
            "2026-09-05T00:00:02+00:00"
        ),
        "summary": {
            "unique_U": 2,
        },
        "records": [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=99,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.100000+00:00"
                ),
                u=2,
                proposed=quote,
            ),
        ],
    }


class TestLineageAggregation(
    unittest.TestCase
):
    def test_two_capture_totals(self):
        result = aggregate_captures(
            [
                (
                    "complete",
                    complete_capture(),
                ),
                (
                    "unmatched",
                    unmatched_capture(),
                ),
            ]
        )

        self.assertEqual(
            result["capture_count"],
            2,
        )

        self.assertEqual(
            result[
                "captured_messages_total"
            ],
            6,
        )

        exact = result[
            "cross_capture"
        ][
            "price_quantity"
        ][
            "descriptive_pooled_totals"
        ]

        self.assertEqual(
            exact[
                "evaluable_episodes"
            ],
            4,
        )

        self.assertEqual(
            exact[
                "evaluable_ordered"
            ],
            2,
        )

        self.assertEqual(
            exact[
                "ordered_rate"
            ],
            0.5,
        )

    def test_capture_level_rate_distribution(self):
        result = aggregate_captures(
            [
                (
                    "complete",
                    complete_capture(),
                ),
                (
                    "unmatched",
                    unmatched_capture(),
                ),
            ]
        )

        distribution = result[
            "cross_capture"
        ][
            "price"
        ][
            "capture_level_ordered_rate"
        ]

        self.assertEqual(
            distribution["count"],
            2,
        )

        self.assertEqual(
            distribution["min"],
            0.0,
        )

        self.assertEqual(
            distribution["median"],
            0.5,
        )

        self.assertEqual(
            distribution["max"],
            1.0,
        )

    def test_only_evaluable_later_progressions_feed_latency(self):
        result = aggregate_captures(
            [
                (
                    "complete",
                    complete_capture(),
                )
            ]
        )

        latency = result[
            "cross_capture"
        ][
            "price_quantity"
        ][
            "descriptive_pooled_latency_ms"
        ]

        self.assertEqual(
            latency[
                "voted"
            ][
                "count"
            ],
            2,
        )

        self.assertEqual(
            latency[
                "voted"
            ][
                "median"
            ],
            100.0,
        )

        self.assertEqual(
            latency[
                "finalized"
            ][
                "median"
            ],
            200.0,
        )

    def test_capture_hash_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = (
                Path(tmp)
                / "capture.json"
            )

            payload = {
                "hello": "world",
            }

            encoded = (
                json.dumps(
                    payload,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")

            path.write_bytes(
                encoded
            )

            digest = hashlib.sha256(
                encoded
            ).hexdigest()

            sidecar = path.with_suffix(
                ".sha256"
            )

            sidecar.write_text(
                (
                    f"{digest}  "
                    f"{path.name}\n"
                ),
                encoding="utf-8",
            )

            actual = (
                verify_capture_hash(
                    path
                )
            )

            self.assertEqual(
                actual,
                digest,
            )


if __name__ == "__main__":
    unittest.main()
