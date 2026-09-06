from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_staleness import (
    build_report as build_staleness_report,
)
from scripts.analyze_top_of_book import (
    SCHEMA_VERSION,
    build_report,
    render_report,
    write_report,
)
from tests.test_top_of_book import capture


def write_capture(
    directory: Path,
    name: str,
    payload: dict,
) -> Path:
    path = directory / name
    raw = json.dumps(
        payload,
        sort_keys=True,
    ).encode("utf-8")
    path.write_bytes(raw)

    digest = hashlib.sha256(raw).hexdigest()
    path.with_suffix(".sha256").write_text(
        digest + "\n",
        encoding="utf-8",
    )

    return path


class TestAnalyzeTopOfBook(unittest.TestCase):
    def test_report_has_three_frozen_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = write_capture(
                directory,
                "a.json",
                capture(),
            )

            report = build_report([path])

            self.assertEqual(
                report["schema_version"],
                SCHEMA_VERSION,
            )
            self.assertEqual(
                report["core_thresholds_ms"],
                ["250", "500", "1000"],
            )

            for threshold in ("250", "500", "1000"):
                result = report[
                    "results_by_threshold_ms"
                ][threshold]

                self.assertEqual(
                    result["economic_panel_count"],
                    1,
                )
                self.assertEqual(
                    result["eligibility_summary"][
                        "kuru_observations"
                    ],
                    1,
                )
                self.assertEqual(
                    result["eligibility_summary"][
                        "economic_rows"
                    ],
                    4,
                )

    def test_fingerprint_matches_staleness_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = write_capture(
                directory,
                "a.json",
                capture(),
            )

            top = build_report([path])
            staleness = build_staleness_report([path])

            self.assertEqual(
                top["dataset_fingerprint"],
                staleness["dataset_fingerprint"],
            )

    def test_rendering_and_write_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = write_capture(
                directory,
                "a.json",
                capture(),
            )

            first = build_report([path])
            second = build_report([path])

            self.assertEqual(
                render_report(first),
                render_report(second),
            )

            first_path = directory / "first.json"
            second_path = directory / "second.json"

            write_report(first, first_path)
            write_report(second, second_path)

            self.assertEqual(
                first_path.read_bytes(),
                second_path.read_bytes(),
            )

    def test_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = write_capture(
                directory,
                "a.json",
                capture(),
            )

            path.with_suffix(".sha256").write_text(
                "0" * 64 + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                build_report([path])

    def test_source_identity_failure_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = capture()
            source["sources"]["kuru"]["market"] = (
                "WRONG_MARKET"
            )

            path = write_capture(
                directory,
                "a.json",
                source,
            )

            with self.assertRaises(ValueError):
                build_report([path])


if __name__ == "__main__":
    unittest.main()
