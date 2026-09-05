from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import capture_cycle


def fake_kuru_response(state: str) -> dict:
    return {
        "ok": True,
        "request_started_utc": "2026-09-05T15:00:00+00:00",
        "request_completed_utc": "2026-09-05T15:00:00.100000+00:00",
        "http_status": 200,
        "url": f"https://example.test/kuru/{state}",
        "data": {
            "lastUpdateId": 100,
            "E": 1000000,
            "T": 1000,
            "bids": [["25184000000000000", "992530000000000"]],
            "asks": [["25189000000000000", "992490000000000"]],
        },
    }


def fake_coinbase_response() -> dict:
    return {
        "ok": True,
        "request_started_utc": "2026-09-05T15:00:00+00:00",
        "request_completed_utc": "2026-09-05T15:00:00.100000+00:00",
        "http_status": 200,
        "url": "https://example.test/coinbase",
        "data": {
            "sequence": 500,
            "bids": [["0.02518", "10", "1"]],
            "asks": [["0.02519", "10", "1"]],
        },
    }


class TestCaptureCycle(unittest.TestCase):
    def test_all_sources_success_produces_pass(self):
        def fake_get_json(url: str) -> dict:
            if "coinbase" in url:
                return fake_coinbase_response()

            for state in capture_cycle.KURU_STATES:
                if f"state={state}" in url:
                    return fake_kuru_response(state)

            raise AssertionError(f"Unexpected URL: {url}")

        with patch.object(
            capture_cycle,
            "get_json",
            side_effect=fake_get_json,
        ):
            result = capture_cycle.capture_cycle()

        self.assertEqual(result["gate"]["overall"], "PASS")
        self.assertTrue(result["gate"]["all_kuru_states_ok"])
        self.assertTrue(result["gate"]["coinbase_ok"])

        self.assertEqual(
            set(result["kuru"]["states"]),
            set(capture_cycle.KURU_STATES),
        )

        self.assertEqual(
            result["markets"],
            {
                "kuru": "MON_USDC",
                "coinbase": "MON-USD",
            },
        )

    def test_one_kuru_failure_produces_review(self):
        def fake_get_json(url: str) -> dict:
            if "coinbase" in url:
                return fake_coinbase_response()

            if "state=finalized" in url:
                return {
                    "ok": False,
                    "error": "synthetic finalized failure",
                }

            for state in capture_cycle.KURU_STATES:
                if f"state={state}" in url:
                    return fake_kuru_response(state)

            raise AssertionError(f"Unexpected URL: {url}")

        with patch.object(
            capture_cycle,
            "get_json",
            side_effect=fake_get_json,
        ):
            result = capture_cycle.capture_cycle()

        self.assertEqual(result["gate"]["overall"], "REVIEW")
        self.assertFalse(result["gate"]["all_kuru_states_ok"])
        self.assertTrue(result["gate"]["coinbase_ok"])

    def test_coinbase_failure_produces_review(self):
        def fake_get_json(url: str) -> dict:
            if "coinbase" in url:
                return {
                    "ok": False,
                    "error": "synthetic Coinbase failure",
                }

            for state in capture_cycle.KURU_STATES:
                if f"state={state}" in url:
                    return fake_kuru_response(state)

            raise AssertionError(f"Unexpected URL: {url}")

        with patch.object(
            capture_cycle,
            "get_json",
            side_effect=fake_get_json,
        ):
            result = capture_cycle.capture_cycle()

        self.assertEqual(result["gate"]["overall"], "REVIEW")
        self.assertTrue(result["gate"]["all_kuru_states_ok"])
        self.assertFalse(result["gate"]["coinbase_ok"])

    def test_write_capture_creates_valid_json_and_matching_sha256(self):
        capture = {
            "schema_version": "phase0.capture_cycle.v1",
            "gate": {
                "overall": "PASS",
            },
        }

        original_cwd = Path.cwd()

        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)

                json_path, hash_path = capture_cycle.write_capture(
                    capture
                )

                self.assertTrue(json_path.exists())
                self.assertTrue(hash_path.exists())

                loaded = json.loads(
                    json_path.read_text(encoding="utf-8")
                )
                self.assertEqual(loaded, capture)

                encoded = json_path.read_bytes()
                expected_hash = hashlib.sha256(encoded).hexdigest()

                hash_line = hash_path.read_text(
                    encoding="utf-8"
                ).strip()

                self.assertEqual(
                    hash_line,
                    f"{expected_hash}  {json_path.name}",
                )

            finally:
                os.chdir(original_cwd)

    def test_capture_schema_version_is_present(self):
        def fake_get_json(url: str) -> dict:
            if "coinbase" in url:
                return fake_coinbase_response()

            for state in capture_cycle.KURU_STATES:
                if f"state={state}" in url:
                    return fake_kuru_response(state)

            raise AssertionError(f"Unexpected URL: {url}")

        with patch.object(
            capture_cycle,
            "get_json",
            side_effect=fake_get_json,
        ):
            result = capture_cycle.capture_cycle()

        self.assertEqual(
            result["schema_version"],
            "phase0.capture_cycle.v1",
        )


if __name__ == "__main__":
    unittest.main()
