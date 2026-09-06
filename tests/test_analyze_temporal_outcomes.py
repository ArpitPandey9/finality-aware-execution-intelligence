from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_temporal_outcomes import (
    SCHEMA_VERSION,
    build_report,
    render_report,
    write_report,
)
from tests.test_temporal_outcome import (
    moving_capture,
)


def write_capture(
    directory: Path,
    name: str,
    payload: dict,
) -> Path:
    path = (
        directory
        / name
    )

    raw = json.dumps(
        payload,
        sort_keys=True,
    ).encode(
        "utf-8"
    )

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


class TestAnalyzeTemporalOutcomes(
    unittest.TestCase
):
    def test_schema_and_exact_frozen_grid(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(
                tmp
            )

            path = write_capture(
                directory,
                "a.json",
                moving_capture(),
            )

            report = build_report(
                [
                    path
                ]
            )

            self.assertEqual(
                report[
                    "schema_version"
                ],
                SCHEMA_VERSION,
            )

            self.assertEqual(
                SCHEMA_VERSION,
                "phase2.temporal_outcome_report.v1",
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
                    tuple(
                        report[
                            "threshold_results"
                        ][
                            threshold
                        ]
                    ),
                    (
                        "250",
                        "1000",
                        "5000",
                        "10000",
                    ),
                )

    def test_primary_baseline_is_explicit(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_capture(
                Path(tmp),
                "a.json",
                moving_capture(),
            )

            report = build_report(
                [
                    path
                ]
            )

            methodology = report[
                "methodology"
            ]

            self.assertEqual(
                methodology[
                    "baseline_freshness_thresholds_ms"
                ],
                [
                    "250",
                    "500",
                    "1000",
                ],
            )

            self.assertEqual(
                methodology[
                    "primary_baseline_freshness_threshold_ms"
                ],
                "250",
            )

    def test_primary_extended_and_excluded_horizons(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_capture(
                Path(tmp),
                "a.json",
                moving_capture(),
            )

            report = build_report(
                [
                    path
                ]
            )

            methodology = report[
                "methodology"
            ]

            self.assertEqual(
                methodology[
                    "future_horizons_ms"
                ],
                [
                    "250",
                    "1000",
                    "5000",
                    "10000",
                ],
            )

            self.assertEqual(
                methodology[
                    "primary_future_horizons_ms"
                ],
                [
                    "250",
                    "1000",
                    "5000",
                ],
            )

            self.assertEqual(
                methodology[
                    "extended_future_horizon_ms"
                ],
                "10000",
            )

            self.assertEqual(
                methodology[
                    "excluded_initial_horizon_ms"
                ],
                "30000",
            )

            for threshold in (
                "250",
                "500",
                "1000",
            ):
                self.assertNotIn(
                    "30000",
                    report[
                        "threshold_results"
                    ][
                        threshold
                    ],
                )

    def test_methodology_preserves_temporal_semantics(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_capture(
                Path(tmp),
                "a.json",
                moving_capture(),
            )

            report = build_report(
                [
                    path
                ]
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
                    "unit_of_observation"
                ],
                "one Kuru four-state panel",
            )

            self.assertFalse(
                methodology[
                    "future_price_interpolation"
                ]
            )

            self.assertFalse(
                methodology[
                    "cross_capture_stitching"
                ]
            )

    def test_report_preserves_status_and_censoring_counts(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_capture(
                Path(tmp),
                "a.json",
                moving_capture(),
            )

            report = build_report(
                [
                    path
                ]
            )

            for threshold in (
                "250",
                "500",
                "1000",
            ):
                short = report[
                    "threshold_results"
                ][
                    threshold
                ][
                    "250"
                ]

                one_second = report[
                    "threshold_results"
                ][
                    threshold
                ][
                    "1000"
                ]

                five_second = report[
                    "threshold_results"
                ][
                    threshold
                ][
                    "5000"
                ]

                ten_second = report[
                    "threshold_results"
                ][
                    threshold
                ][
                    "10000"
                ]

                self.assertEqual(
                    short[
                        "status_counts"
                    ][
                        "EVALUABLE"
                    ],
                    1,
                )

                self.assertEqual(
                    one_second[
                        "status_counts"
                    ][
                        "EVALUABLE"
                    ],
                    1,
                )

                self.assertEqual(
                    five_second[
                        "status_counts"
                    ][
                        "RIGHT_CENSORED_CAPTURE_END"
                    ],
                    1,
                )

                self.assertEqual(
                    ten_second[
                        "status_counts"
                    ][
                        "RIGHT_CENSORED_CAPTURE_END"
                    ],
                    1,
                )

    def test_zero_contrast_accounting_is_preserved(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            source = moving_capture()

            states = (
                source[
                    "sources"
                ][
                    "kuru"
                ][
                    "records"
                ][0][
                    "states"
                ]
            )

            states[
                "proposed"
            ] = dict(
                states[
                    "finalized"
                ]
            )

            path = write_capture(
                Path(tmp),
                "a.json",
                source,
            )

            report = build_report(
                [
                    path
                ]
            )

            pooled = report[
                "threshold_results"
            ][
                "250"
            ][
                "250"
            ][
                "pooled"
            ]

            self.assertEqual(
                pooled[
                    "evaluable_rows"
                ],
                1,
            )

            self.assertEqual(
                pooled[
                    "zero_contrast_count"
                ],
                1,
            )

            self.assertEqual(
                pooled[
                    "nonzero_contrast_count"
                ],
                0,
            )

            self.assertEqual(
                pooled[
                    "directional_concordance_bps"
                ][
                    "count"
                ],
                0,
            )

    def test_non_overlapping_sensitivity_is_preserved(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_capture(
                Path(tmp),
                "a.json",
                moving_capture(),
            )

            report = build_report(
                [
                    path
                ]
            )

            sensitivity = report[
                "threshold_results"
            ][
                "250"
            ][
                "250"
            ][
                "non_overlapping_sensitivity"
            ]

            self.assertEqual(
                sensitivity[
                    "selected_rows"
                ],
                1,
            )

            self.assertEqual(
                sensitivity[
                    "per_capture_selected_counts"
                ][
                    "a.json"
                ],
                1,
            )

    def test_dataset_fingerprint_is_stable(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(
                tmp
            )

            first = write_capture(
                directory,
                "a.json",
                moving_capture(),
            )

            second = write_capture(
                directory,
                "b.json",
                moving_capture(),
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

            self.assertEqual(
                one[
                    "dataset_fingerprint"
                ],
                two[
                    "dataset_fingerprint"
                ],
            )

    def test_dataset_fingerprint_is_order_sensitive(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(
                tmp
            )

            first = write_capture(
                directory,
                "a.json",
                moving_capture(),
            )

            second = write_capture(
                directory,
                "b.json",
                moving_capture(),
            )

            forward = build_report(
                [
                    first,
                    second,
                ]
            )

            reversed_report = build_report(
                [
                    second,
                    first,
                ]
            )

            self.assertNotEqual(
                forward[
                    "dataset_fingerprint"
                ],
                reversed_report[
                    "dataset_fingerprint"
                ],
            )

    def test_source_provenance_is_preserved_in_order(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(
                tmp
            )

            first = write_capture(
                directory,
                "a.json",
                moving_capture(),
            )

            second = write_capture(
                directory,
                "b.json",
                moving_capture(),
            )

            report = build_report(
                [
                    first,
                    second,
                ]
            )

            self.assertEqual(
                [
                    item[
                        "capture_id"
                    ]
                    for item
                    in report[
                        "source_captures"
                    ]
                ],
                [
                    "a.json",
                    "b.json",
                ],
            )

            for source in report[
                "source_captures"
            ]:
                self.assertEqual(
                    len(
                        source[
                            "sha256"
                        ]
                    ),
                    64,
                )

    def test_render_report_is_deterministic(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_capture(
                Path(tmp),
                "a.json",
                moving_capture(),
            )

            first = build_report(
                [
                    path
                ]
            )

            second = build_report(
                [
                    path
                ]
            )

            self.assertEqual(
                render_report(
                    first
                ),
                render_report(
                    second
                ),
            )

            self.assertTrue(
                render_report(
                    first
                ).endswith(
                    "\n"
                )
            )

    def test_two_writes_are_byte_identical(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(
                tmp
            )

            path = write_capture(
                directory,
                "a.json",
                moving_capture(),
            )

            first = build_report(
                [
                    path
                ]
            )

            second = build_report(
                [
                    path
                ]
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
            directory = Path(
                tmp
            )

            path = write_capture(
                directory,
                "a.json",
                moving_capture(),
            )

            path.with_suffix(
                ".sha256"
            ).write_text(
                "0" * 64
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(
                ValueError
            ):
                build_report(
                    [
                        path
                    ]
                )

    def test_source_identity_failure_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            source = moving_capture()

            source[
                "sources"
            ][
                "coinbase"
            ][
                "market"
            ] = "WRONG-MARKET"

            path = write_capture(
                Path(tmp),
                "a.json",
                source,
            )

            with self.assertRaises(
                ValueError
            ):
                build_report(
                    [
                        path
                    ]
                )

    def test_claim_boundaries_are_preserved(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_capture(
                Path(tmp),
                "a.json",
                moving_capture(),
            )

            report = build_report(
                [
                    path
                ]
            )

            rendered = " ".join(
                report[
                    "claim_boundaries"
                ]
            ).lower()

            self.assertIn(
                "not prediction",
                rendered,
            )

            self.assertIn(
                "not alpha",
                rendered,
            )

            self.assertIn(
                "not arbitrage",
                rendered,
            )

            self.assertIn(
                "not a win rate",
                rendered,
            )

            self.assertIn(
                "not causal",
                rendered,
            )


if __name__ == "__main__":
    unittest.main()
