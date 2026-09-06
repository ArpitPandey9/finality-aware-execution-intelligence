from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_cross_venue_execution import (
    SCHEMA_VERSION,
    build_report,
    render_report,
    write_report,
)
from tests.test_cross_venue_execution import (
    capture,
)


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

    path.write_bytes(
        raw
    )

    digest = hashlib.sha256(
        raw
    ).hexdigest()

    path.with_suffix(
        ".sha256"
    ).write_text(
        digest + "\n",
        encoding="utf-8",
    )

    return path


class TestAnalyzeCrossVenueExecution(
    unittest.TestCase
):
    def test_report_preserves_frozen_methodology(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)

            path = write_capture(
                directory,
                "a.json",
                capture(),
            )

            report = build_report(
                [path]
            )

            self.assertEqual(
                report[
                    "schema_version"
                ],
                SCHEMA_VERSION,
            )

            methodology = report[
                "methodology"
            ]

            self.assertEqual(
                methodology[
                    "kuru_market"
                ],
                "MON_USDC",
            )

            self.assertEqual(
                methodology[
                    "coinbase_market"
                ],
                "MON-USD",
            )

            self.assertEqual(
                methodology[
                    "coinbase_channel"
                ],
                "level2",
            )

            self.assertEqual(
                methodology[
                    "common_base_asset"
                ],
                "MON",
            )

            self.assertFalse(
                methodology[
                    "quote_basis_normalized"
                ]
            )

            self.assertEqual(
                methodology[
                    "coinbase_reference_age_thresholds_ms"
                ],
                [
                    "250",
                    "500",
                    "1000",
                ],
            )

            self.assertEqual(
                tuple(
                    report[
                        "threshold_results"
                    ]
                ),
                (
                    "250",
                    "500",
                    "1000",
                ),
            )

            for threshold in (
                "250",
                "500",
                "1000",
            ):
                self.assertEqual(
                    report[
                        "threshold_results"
                    ][
                        threshold
                    ][
                        "economic_panel_count"
                    ],
                    1,
                )

    def test_dataset_fingerprint_is_stable_and_order_sensitive(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)

            first = write_capture(
                directory,
                "a.json",
                capture(),
            )

            second = write_capture(
                directory,
                "b.json",
                capture(),
            )

            one = build_report(
                [
                    first,
                    second,
                ]
            )

            two = build_report(
                [
                    first,
                    second,
                ]
            )

            reversed_report = (
                build_report(
                    [
                        second,
                        first,
                    ]
                )
            )

            self.assertEqual(
                one[
                    "dataset_fingerprint"
                ],
                two[
                    "dataset_fingerprint"
                ],
            )

            self.assertNotEqual(
                one[
                    "dataset_fingerprint"
                ],
                reversed_report[
                    "dataset_fingerprint"
                ],
            )

    def test_render_and_write_are_deterministic(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)

            path = write_capture(
                directory,
                "a.json",
                capture(),
            )

            first = build_report(
                [path]
            )

            second = build_report(
                [path]
            )

            self.assertEqual(
                render_report(first),
                render_report(second),
            )

            first_path = (
                directory
                / "first.json"
            )

            second_path = (
                directory
                / "second.json"
            )

            write_report(
                first,
                first_path,
            )

            write_report(
                second,
                second_path,
            )

            self.assertEqual(
                first_path.read_bytes(),
                second_path.read_bytes(),
            )

    def test_hash_mismatch_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)

            path = write_capture(
                directory,
                "a.json",
                capture(),
            )

            path.with_suffix(
                ".sha256"
            ).write_text(
                "0" * 64 + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                ValueError
            ):
                build_report(
                    [path]
                )

    def test_source_identity_failure_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)

            source = capture()

            source[
                "sources"
            ][
                "coinbase"
            ][
                "market"
            ] = "WRONG-MARKET"

            path = write_capture(
                directory,
                "a.json",
                source,
            )

            with self.assertRaises(
                ValueError
            ):
                build_report(
                    [path]
                )


if __name__ == "__main__":
    unittest.main()
