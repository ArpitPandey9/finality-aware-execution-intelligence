import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_staleness import (
    SCHEMA_VERSION,
    build_report,
    load_verified_capture,
)
from tests.test_alignment import cb_record, capture


def write_capture(directory: Path, name: str, payload: dict) -> Path:
    path = directory / name
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    path.with_suffix(".sha256").write_text(digest + "\n")
    return path


class TestStalenessScript(unittest.TestCase):
    def test_verified_capture_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = capture(
                [1_100_000_000],
                [cb_record(1_000_000_000, 0, snapshot=True)],
            )
            path = write_capture(directory, "a.json", source)

            loaded, provenance = load_verified_capture(path)

            self.assertEqual(loaded, source)
            self.assertEqual(provenance["capture_id"], "a.json")

    def test_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = capture(
                [1_100_000_000],
                [cb_record(1_000_000_000, 0, snapshot=True)],
            )
            path = write_capture(directory, "a.json", source)
            path.with_suffix(".sha256").write_text("0" * 64 + "\n")

            with self.assertRaises(ValueError):
                load_verified_capture(path)

    def test_non_pass_source_gate_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = capture(
                [1_100_000_000],
                [cb_record(1_000_000_000, 0, snapshot=True)],
                gate="REVIEW",
            )
            path = write_capture(directory, "a.json", source)

            with self.assertRaises(ValueError):
                load_verified_capture(path)

    def test_report_has_provenance_and_core_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = capture(
                [1_100_000_000, 1_400_000_000],
                [cb_record(1_000_000_000, 0, snapshot=True)],
            )
            path = write_capture(directory, "a.json", source)

            report = build_report([path])

            self.assertEqual(report["schema_version"], SCHEMA_VERSION)
            self.assertEqual(
                report["core_thresholds_ms"],
                ["250", "500", "1000"],
            )
            self.assertEqual(report["result"]["reference_age"]["count"], 2)
            self.assertEqual(len(report["source_captures"]), 1)

    def test_dataset_fingerprint_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = capture(
                [1_100_000_000],
                [cb_record(1_000_000_000, 0, snapshot=True)],
            )
            path = write_capture(directory, "a.json", source)

            first = build_report([path])
            second = build_report([path])

            self.assertEqual(
                first["dataset_fingerprint"],
                second["dataset_fingerprint"],
            )


if __name__ == "__main__":
    unittest.main()
