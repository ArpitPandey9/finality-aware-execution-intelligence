from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import capture_series


def fake_capture(index: int) -> dict:
    return {
        "schema_version": "phase0.capture_cycle.v1",
        "capture_cycle_started_utc": (
            f"2026-09-05T15:00:0{index}+00:00"
        ),
        "capture_cycle_completed_utc": (
            f"2026-09-05T15:00:0{index}.100000+00:00"
        ),
        "gate": {
            "all_kuru_states_ok": True,
            "coinbase_ok": True,
            "overall": "PASS",
        },
    }


class TestCaptureSeries(unittest.TestCase):
    def test_three_successful_cycles(self):
        captures = [
            fake_capture(1),
            fake_capture(2),
            fake_capture(3),
        ]

        with patch.object(
            capture_series.capture_cycle,
            "capture_cycle",
            side_effect=captures,
        ), patch.object(
            capture_series.capture_cycle,
            "write_capture",
            side_effect=[
                (
                    Path("data/raw/c1.json"),
                    Path("data/raw/c1.sha256"),
                ),
                (
                    Path("data/raw/c2.json"),
                    Path("data/raw/c2.sha256"),
                ),
                (
                    Path("data/raw/c3.json"),
                    Path("data/raw/c3.sha256"),
                ),
            ],
        ), patch.object(
            capture_series.time,
            "sleep",
        ), patch.object(
            capture_series.time,
            "monotonic",
            side_effect=[
                0.0,
                0.1,
                5.0,
                5.1,
                10.0,
            ],
        ):
            result = capture_series.run_series(
                cycles=3,
                interval_seconds=5.0,
            )

        self.assertEqual(result["completed_cycles"], 3)
        self.assertEqual(result["pass_cycles"], 3)
        self.assertEqual(result["review_cycles"], 0)
        self.assertEqual(len(result["observations"]), 3)

    def test_review_cycle_is_counted(self):
        first = fake_capture(1)
        second = fake_capture(2)

        second["gate"] = {
            "all_kuru_states_ok": False,
            "coinbase_ok": True,
            "overall": "REVIEW",
        }

        with patch.object(
            capture_series.capture_cycle,
            "capture_cycle",
            side_effect=[first, second],
        ), patch.object(
            capture_series.capture_cycle,
            "write_capture",
            side_effect=[
                (
                    Path("data/raw/c1.json"),
                    Path("data/raw/c1.sha256"),
                ),
                (
                    Path("data/raw/c2.json"),
                    Path("data/raw/c2.sha256"),
                ),
            ],
        ), patch.object(
            capture_series.time,
            "sleep",
        ), patch.object(
            capture_series.time,
            "monotonic",
            side_effect=[
                0.0,
                0.1,
                5.0,
            ],
        ):
            result = capture_series.run_series(
                cycles=2,
                interval_seconds=5.0,
            )

        self.assertEqual(result["completed_cycles"], 2)
        self.assertEqual(result["pass_cycles"], 1)
        self.assertEqual(result["review_cycles"], 1)

    def test_invalid_cycle_count_is_rejected(self):
        with self.assertRaises(ValueError):
            capture_series.run_series(
                cycles=0,
                interval_seconds=5.0,
            )

    def test_negative_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            capture_series.run_series(
                cycles=1,
                interval_seconds=-1.0,
            )

    def test_manifest_has_matching_sha256(self):
        series = {
            "schema_version": "phase0.capture_series.v1",
            "completed_cycles": 1,
            "observations": [],
        }

        original_cwd = Path.cwd()

        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)

                manifest_path, hash_path = (
                    capture_series.write_manifest(series)
                )

                self.assertTrue(manifest_path.exists())
                self.assertTrue(hash_path.exists())

                loaded = json.loads(
                    manifest_path.read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(loaded, series)

                encoded = manifest_path.read_bytes()
                expected_hash = hashlib.sha256(
                    encoded
                ).hexdigest()

                hash_line = hash_path.read_text(
                    encoding="utf-8"
                ).strip()

                self.assertEqual(
                    hash_line,
                    f"{expected_hash}  {manifest_path.name}",
                )

            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
