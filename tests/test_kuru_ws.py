from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from finality_intelligence.kuru_ws import (
    build_capture,
    normalize_monad_depth_event,
    summarize_records,
    write_capture,
)


def sample_message(
    *,
    update_id: int = 100,
    event_time=None,
    block_time=None,
    same_top: bool = True,
) -> dict:
    proposed_bid = (
        "25283000000000000"
    )

    voted_bid = (
        proposed_bid
        if same_top
        else "25282000000000000"
    )

    def book(bid: str) -> dict:
        return {
            "b": [
                [
                    bid,
                    "988360000000000",
                ],
                [
                    "25280000000000000",
                    "100000000000000",
                ],
            ],
            "a": [
                [
                    "25294000000000000",
                    "988360000000000",
                ],
                [
                    "25300000000000000",
                    "100000000000000",
                ],
            ],
        }

    return {
        "e": "monadDepthUpdate",
        "s": "0x065c9d28",
        "U": update_id,
        "E": event_time,
        "T": block_time,
        "states": {
            "proposed": book(
                proposed_bid
            ),
            "voted": book(
                voted_bid
            ),
            "finalized": book(
                proposed_bid
            ),
            "committed": book(
                proposed_bid
            ),
        },
    }


def record_from(
    message: dict,
    received: str = "received",
) -> dict:
    return normalize_monad_depth_event(
        message,
        received_at_utc=received,
    )


class TestKuruWebSocketEvidence(
    unittest.TestCase
):
    def test_missing_timestamps_are_preserved(self):
        record = record_from(
            sample_message()
        )

        self.assertIsNone(
            record["E"]
        )
        self.assertIsNone(
            record["T"]
        )

    def test_same_top_is_detected(self):
        record = record_from(
            sample_message(
                same_top=True
            )
        )

        self.assertTrue(
            record[
                "all_states_same_top_of_book"
            ]
        )

    def test_different_top_is_detected(self):
        record = record_from(
            sample_message(
                same_top=False
            )
        )

        self.assertFalse(
            record[
                "all_states_same_top_of_book"
            ]
        )

    def test_non_target_event_is_ignored(self):
        result = normalize_monad_depth_event(
            {
                "e": "otherEvent",
            },
            received_at_utc="received",
        )

        self.assertIsNone(
            result
        )

    def test_repeated_u_is_not_called_duplicate(self):
        records = [
            record_from(
                sample_message(
                    update_id=100,
                )
            ),
            record_from(
                sample_message(
                    update_id=101,
                    event_time=1,
                    block_time=1,
                )
            ),
            record_from(
                sample_message(
                    update_id=101,
                    event_time=1,
                    block_time=1,
                )
            ),
        ]

        summary = summarize_records(
            records
        )

        self.assertEqual(
            summary["captured_messages"],
            3,
        )

        self.assertEqual(
            summary["unique_U"],
            2,
        )

        self.assertEqual(
            summary[
                "repeated_U_messages"
            ],
            1,
        )

        self.assertEqual(
            summary[
                "consecutive_repeated_U"
            ],
            1,
        )

    def test_identical_raw_messages_are_counted(self):
        message = sample_message(
            update_id=200,
            event_time=1,
            block_time=1,
        )

        records = [
            record_from(
                copy.deepcopy(message),
                "a",
            ),
            record_from(
                copy.deepcopy(message),
                "b",
            ),
        ]

        summary = summarize_records(
            records
        )

        self.assertEqual(
            summary[
                "unique_exact_raw_messages"
            ],
            1,
        )

        self.assertEqual(
            summary[
                "repeated_exact_raw_messages"
            ],
            1,
        )

        self.assertEqual(
            summary[
                "consecutive_identical_raw_messages"
            ],
            1,
        )

    def test_same_u_can_change_deeper_book_without_top_change(self):
        first = sample_message(
            update_id=300,
            event_time=1,
            block_time=1,
        )

        second = copy.deepcopy(
            first
        )

        second[
            "states"
        ][
            "proposed"
        ][
            "b"
        ][1][1] = (
            "200000000000000"
        )

        records = [
            record_from(
                first,
                "a",
            ),
            record_from(
                second,
                "b",
            ),
        ]

        summary = summarize_records(
            records
        )

        self.assertEqual(
            summary["unique_U"],
            1,
        )

        self.assertEqual(
            summary[
                "unique_exact_raw_messages"
            ],
            2,
        )

        self.assertEqual(
            summary[
                "unique_full_state_payloads"
            ],
            2,
        )

        self.assertEqual(
            summary[
                "unique_top_payloads"
            ],
            1,
        )

    def test_duration_capture_gate_passes_with_evidence(self):
        record = record_from(
            sample_message()
        )

        capture = build_capture(
            records=[record],
            requested_duration_seconds=5.0,
            connection_started_utc="start",
            connection_completed_utc="end",
        )

        self.assertEqual(
            capture["capture_mode"],
            "duration",
        )

        self.assertEqual(
            capture["gate"]["overall"],
            "PASS",
        )

    def test_capture_hash_matches(self):
        record = record_from(
            sample_message()
        )

        capture = build_capture(
            records=[record],
            requested_updates=1,
            connection_started_utc="start",
            connection_completed_utc="end",
        )

        with tempfile.TemporaryDirectory() as tmp:
            json_path, hash_path = (
                write_capture(
                    capture,
                    output_dir=Path(tmp),
                )
            )

            actual_hash = hashlib.sha256(
                json_path.read_bytes()
            ).hexdigest()

            line = hash_path.read_text(
                encoding="utf-8"
            ).strip()

            expected_hash, expected_name = (
                line.split("  ", 1)
            )

            self.assertEqual(
                actual_hash,
                expected_hash,
            )

            self.assertEqual(
                expected_name,
                json_path.name,
            )

            loaded = json.loads(
                json_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                loaded["gate"]["overall"],
                "PASS",
            )


if __name__ == "__main__":
    unittest.main()
