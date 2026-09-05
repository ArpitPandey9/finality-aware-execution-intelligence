from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from finality_intelligence.lineage_evidence import (
    build_empirical_evidence,
    render_markdown,
    write_capture_csv,
    write_json,
    write_markdown,
)


def state():
    return {
        "best_bid_raw": "100",
        "best_bid_quantity_raw": "10",
        "best_ask_raw": "101",
        "best_ask_quantity_raw": "11",
    }


def empty_state():
    return {
        "best_bid_raw": None,
        "best_bid_quantity_raw": None,
        "best_ask_raw": None,
        "best_ask_quantity_raw": None,
    }


def record(
    timestamp,
    u,
    *,
    proposed=None,
    voted=None,
    finalized=None,
    committed=None,
):
    return {
        "received_at_utc": timestamp,
        "U": u,
        "states": {
            "proposed": (
                proposed
                or empty_state()
            ),
            "voted": (
                voted
                or empty_state()
            ),
            "finalized": (
                finalized
                or empty_state()
            ),
            "committed": (
                committed
                or empty_state()
            ),
        },
    }


def write_capture(
    directory: Path,
    name: str,
) -> Path:
    quote = state()

    capture = {
        "schema_version": (
            "phase0.kuru_monad_depth_ws.v2"
        ),
        "gate": {
            "overall": "PASS",
        },
        "connection_completed_utc": (
            "2026-09-05T00:00:02+00:00"
        ),
        "summary": {
            "unique_U": 2,
        },
        "records": [
            record(
                "2026-09-05T00:00:00+00:00",
                99,
            ),
            record(
                "2026-09-05T00:00:00.100000+00:00",
                1,
                proposed=quote,
            ),
            record(
                "2026-09-05T00:00:00.200000+00:00",
                1,
                voted=quote,
            ),
            record(
                "2026-09-05T00:00:00.300000+00:00",
                1,
                finalized=quote,
                committed=quote,
            ),
        ],
    }

    path = directory / name

    encoded = (
        json.dumps(
            capture,
            indent=2,
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

    path.with_suffix(
        ".sha256"
    ).write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )

    return path


class TestLineageEvidence(
    unittest.TestCase
):
    def test_evidence_has_stable_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)

            capture = write_capture(
                directory,
                "capture.json",
            )

            first = build_empirical_evidence(
                [capture]
            )

            second = build_empirical_evidence(
                [capture]
            )

            self.assertEqual(
                first[
                    "dataset_fingerprint_sha256"
                ],
                second[
                    "dataset_fingerprint_sha256"
                ],
            )

            self.assertEqual(
                first[
                    "aggregation"
                ][
                    "capture_count"
                ],
                1,
            )

    def test_markdown_preserves_claim_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            capture = write_capture(
                Path(tmp),
                "capture.json",
            )

            evidence = (
                build_empirical_evidence(
                    [capture]
                )
            )

            text = render_markdown(
                evidence
            )

            self.assertIn(
                "not assumed to be "
                "statistically independent",
                text,
            )

            self.assertIn(
                "not",
                text.lower(),
            )

            self.assertIn(
                "protocol finality latency",
                text,
            )

            self.assertIn(
                "requires the listed source "
                "capture files",
                text,
            )

            self.assertIn(
                "trading edge",
                text,
            )

    def test_bundle_files_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)

            capture = write_capture(
                directory,
                "capture.json",
            )

            evidence = (
                build_empirical_evidence(
                    [capture]
                )
            )

            json_path = (
                directory
                / "result.json"
            )

            csv_path = (
                directory
                / "result.csv"
            )

            md_path = (
                directory
                / "result.md"
            )

            write_json(
                evidence,
                json_path,
            )

            write_capture_csv(
                evidence,
                csv_path,
            )

            write_markdown(
                evidence,
                md_path,
            )

            self.assertTrue(
                json_path.exists()
            )

            self.assertTrue(
                csv_path.exists()
            )

            self.assertTrue(
                md_path.exists()
            )

            self.assertIn(
                "price_quantity",
                csv_path.read_text(
                    encoding="utf-8"
                ),
            )


if __name__ == "__main__":
    unittest.main()
