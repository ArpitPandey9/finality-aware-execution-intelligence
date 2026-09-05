from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import build_observation_table


def make_response(
    *,
    block: int,
    bid: str,
    ask: str,
) -> dict:
    return {
        "ok": True,
        "request_started_utc": "2026-09-05T15:00:00+00:00",
        "request_completed_utc": "2026-09-05T15:00:00.1+00:00",
        "http_status": 200,
        "data": {
            "lastUpdateId": block,
            "E": 1000000,
            "T": 1000,
            "bids": [
                [
                    bid,
                    "992530000000000",
                ]
            ],
            "asks": [
                [
                    ask,
                    "992490000000000",
                ]
            ],
        },
    }


def write_capture_pair(
    directory: Path,
    capture: dict,
) -> tuple[Path, Path]:
    json_path = directory / "capture.json"

    encoded = (
        json.dumps(
            capture,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    json_path.write_bytes(encoded)

    digest = hashlib.sha256(
        encoded
    ).hexdigest()

    hash_path = directory / "capture.sha256"

    hash_path.write_text(
        f"{digest}  {json_path.name}\n",
        encoding="utf-8",
    )

    return json_path, hash_path


def sample_capture() -> dict:
    return {
        "capture_cycle_started_utc": (
            "2026-09-05T15:00:00+00:00"
        ),
        "capture_cycle_completed_utc": (
            "2026-09-05T15:00:01+00:00"
        ),
        "kuru": {
            "states": {
                "proposed": make_response(
                    block=101,
                    bid="25184000000000000",
                    ask="25189000000000000",
                ),
                "voted": make_response(
                    block=100,
                    bid="25184000000000000",
                    ask="25189000000000000",
                ),
                "finalized": make_response(
                    block=100,
                    bid="25184000000000000",
                    ask="25189000000000000",
                ),
                "committed": make_response(
                    block=101,
                    bid="25184000000000000",
                    ask="25189000000000000",
                ),
            },
        },
        "coinbase": {
            "MON-USD": {
                "ok": True,
                "request_started_utc": (
                    "2026-09-05T15:00:00+00:00"
                ),
                "request_completed_utc": (
                    "2026-09-05T15:00:00.1+00:00"
                ),
                "data": {
                    "sequence": 500,
                    "bids": [
                        ["0.02518", "10", "1"]
                    ],
                    "asks": [
                        ["0.02519", "20", "1"]
                    ],
                },
            }
        },
    }


class TestObservationTable(unittest.TestCase):
    def test_sha256_verification_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)

            json_path, hash_path = write_capture_pair(
                directory,
                sample_capture(),
            )

            build_observation_table.verify_sha256(
                json_path,
                hash_path,
            )

    def test_sha256_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)

            json_path, hash_path = write_capture_pair(
                directory,
                sample_capture(),
            )

            json_path.write_text(
                "{}",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                build_observation_table.verify_sha256(
                    json_path,
                    hash_path,
                )

    def test_build_row_normalizes_and_records_block_span(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)

            json_path, hash_path = write_capture_pair(
                directory,
                sample_capture(),
            )

            observation = {
                "index": 1,
                "gate": {
                    "overall": "PASS",
                },
                "raw_json": str(json_path),
                "sha256_file": str(hash_path),
            }

            row = build_observation_table.build_row(
                observation
            )

            self.assertEqual(
                row["kuru_proposed_best_bid"],
                "0.025184",
            )

            self.assertEqual(
                row["kuru_proposed_best_bid_size"],
                "99253",
            )

            self.assertEqual(
                row["kuru_block_span"],
                1,
            )

            self.assertFalse(
                row["kuru_all_states_same_block"]
            )

            self.assertTrue(
                row[
                    "kuru_all_states_same_top_of_book"
                ]
            )

            self.assertEqual(
                row["coinbase_sequence"],
                500,
            )

    def test_write_csv_creates_readable_table(self):
        rows = [
            {
                "cycle_index": 1,
                "cycle_gate": "PASS",
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            output_path = (
                Path(tmp)
                / "observations.csv"
            )

            build_observation_table.write_csv(
                rows,
                output_path,
            )

            with output_path.open(
                newline="",
                encoding="utf-8",
            ) as handle:
                loaded = list(
                    csv.DictReader(handle)
                )

            self.assertEqual(
                loaded[0]["cycle_index"],
                "1",
            )

            self.assertEqual(
                loaded[0]["cycle_gate"],
                "PASS",
            )


if __name__ == "__main__":
    unittest.main()
