from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import (
    analyze_market_instability as report_module,
)


def frozen_paths():
    return [
        Path(
            f"capture-{index}.json"
        )
        for index in range(
            10
        )
    ]


def source_results():
    return [
        (
            {
                "synthetic_capture":
                    index,
            },
            {
                "capture_id":
                    f"capture-{index}.json",
                "sha256":
                    sha,
            },
        )
        for index, sha
        in enumerate(
            report_module
            .CONFIRMATORY_CAPTURE_SHA256
        )
    ]


def fake_analysis(
    capture,
    *,
    capture_id,
    max_age_ms,
    horizon_ms,
):
    return {
        "schema_version":
            "phase3.market_instability.v1",
        "capture_id":
            capture_id,
        "freshness_threshold_ms":
            str(
                max_age_ms
            ),
        "horizon_ms":
            str(
                horizon_ms
            ),
        "source_evidence_reasons":
            [],
        "rows":
            [],
    }


def fake_aggregate(
    analyses,
):
    freshness = analyses[
        0
    ][
        "freshness_threshold_ms"
    ]

    horizon = analyses[
        0
    ][
        "horizon_ms"
    ]

    support = (
        freshness == "250"
        and horizon
        in {
            "250",
            "1000",
            "10000",
        }
    )

    return {
        "freshness_threshold_ms":
            freshness,
        "horizon_ms":
            horizon,
        "capture_count":
            len(
                analyses
            ),
        "descriptive_support": {
            "directionally_supportive":
                support,
        },
    }


class TestAnalyzeMarketInstability(
    unittest.TestCase
):
    def test_frozen_hashes_produce_frozen_fingerprint(
        self,
    ):
        result = (
            report_module
            .dataset_fingerprint_from_hashes(
                report_module
                .CONFIRMATORY_CAPTURE_SHA256
            )
        )

        self.assertEqual(
            result,
            report_module
            .CONFIRMATORY_DATASET_FINGERPRINT,
        )

    def test_build_report_requires_exact_ten_paths(
        self,
    ):
        with patch.object(
            report_module,
            "load_verified_capture",
        ) as loader:
            with self.assertRaises(
                ValueError
            ):
                report_module.build_report(
                    frozen_paths()[:9]
                )

        loader.assert_not_called()

    def test_build_report_rejects_wrong_source_hash(
        self,
    ):
        sources = source_results()

        capture, source = sources[0]

        sources[0] = (
            capture,
            {
                **source,
                "sha256":
                    "0" * 64,
            },
        )

        with (
            patch.object(
                report_module,
                "load_verified_capture",
                side_effect=sources,
            ),
            patch.object(
                report_module,
                "analyze_market_instability_capture",
            ) as analyzer,
        ):
            with self.assertRaises(
                ValueError
            ):
                report_module.build_report(
                    frozen_paths()
                )

        analyzer.assert_not_called()

    def test_build_report_preserves_frozen_grid_and_support_rule(
        self,
    ):
        with (
            patch.object(
                report_module,
                "load_verified_capture",
                side_effect=source_results(),
            ),
            patch.object(
                report_module,
                "analyze_market_instability_capture",
                side_effect=fake_analysis,
            ) as analyzer,
            patch.object(
                report_module,
                "aggregate_market_instability",
                side_effect=fake_aggregate,
            ) as aggregator,
        ):
            report = (
                report_module.build_report(
                    frozen_paths()
                )
            )

        self.assertEqual(
            report[
                "dataset_fingerprint"
            ],
            report_module
            .CONFIRMATORY_DATASET_FINGERPRINT,
        )

        self.assertEqual(
            list(
                report[
                    "threshold_results"
                ].keys()
            ),
            [
                "250",
                "500",
                "1000",
            ],
        )

        for threshold in (
            "250",
            "500",
            "1000",
        ):
            self.assertEqual(
                list(
                    report[
                        "threshold_results"
                    ][
                        threshold
                    ].keys()
                ),
                [
                    "250",
                    "1000",
                    "5000",
                    "10000",
                ],
            )

        self.assertEqual(
            analyzer.call_count,
            120,
        )

        self.assertEqual(
            aggregator.call_count,
            12,
        )

        self.assertEqual(
            report[
                "primary_support"
            ][
                "supportive_primary_horizon_count"
            ],
            2,
        )

        self.assertEqual(
            report[
                "primary_support"
            ][
                "primary_relationship_status"
            ],
            report_module
            .PRIMARY_SUPPORT_OBSERVED,
        )

        self.assertFalse(
            report[
                "methodology"
            ][
                "posthoc_exposure_threshold"
            ]
        )

    def test_extended_horizon_does_not_rescue_primary_result(
        self,
    ):
        threshold_results = {
            "250": {
                "250": {
                    "descriptive_support": {
                        "directionally_supportive":
                            True,
                    },
                },
                "1000": {
                    "descriptive_support": {
                        "directionally_supportive":
                            False,
                    },
                },
                "5000": {
                    "descriptive_support": {
                        "directionally_supportive":
                            False,
                    },
                },
                "10000": {
                    "descriptive_support": {
                        "directionally_supportive":
                            True,
                    },
                },
            },
        }

        result = (
            report_module
            ._classify_primary_support(
                threshold_results
            )
        )

        self.assertEqual(
            result[
                "supportive_primary_horizon_count"
            ],
            1,
        )

        self.assertTrue(
            result[
                "extended_horizon_directionally_supportive"
            ]
        )

        self.assertFalse(
            result[
                "extended_horizon_counts_toward_primary"
            ]
        )

        self.assertEqual(
            result[
                "primary_relationship_status"
            ],
            report_module
            .PRIMARY_SUPPORT_NOT_ESTABLISHED,
        )

    def test_render_report_is_deterministic(
        self,
    ):
        report = {
            "b": 2,
            "a": 1,
        }

        first = (
            report_module.render_report(
                report
            )
        )

        second = (
            report_module.render_report(
                report
            )
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            json.loads(
                first
            ),
            report,
        )

        self.assertTrue(
            first.endswith(
                "\n"
            )
        )

    def test_write_report_is_byte_identical(
        self,
    ):
        report = {
            "schema_version":
                "synthetic",
            "value":
                1,
        }

        with TemporaryDirectory() as tmp:
            first = Path(
                tmp
            ) / "first.json"

            second = Path(
                tmp
            ) / "second.json"

            report_module.write_report(
                report,
                first,
            )

            report_module.write_report(
                report,
                second,
            )

            self.assertEqual(
                first.read_bytes(),
                second.read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
