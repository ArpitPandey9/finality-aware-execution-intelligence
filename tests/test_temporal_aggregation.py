from __future__ import annotations

import unittest
from collections import Counter
from decimal import Decimal

from finality_intelligence.alignment import (
    ALIGNED,
    STALE_REFERENCE,
)
from finality_intelligence.temporal_outcome import (
    APPLICABLE_NONZERO_CONTRAST,
    EVALUABLE,
    NOT_APPLICABLE_ZERO_CONTRAST,
    RIGHT_CENSORED_CAPTURE_END,
)
from finality_intelligence.temporal_aggregation import (
    SCHEMA_VERSION,
    aggregate_temporal_outcomes,
    select_non_overlapping_rows,
)


def evaluable_row(
    capture_id: str,
    index: int,
    t0_ns: int,
    *,
    forward_bps: str,
    contrast_gap_bps: str,
    future_age_ms: str = "50",
    concordance_bps: str | None = None,
) -> dict:
    forward = Decimal(
        forward_bps
    )

    contrast = Decimal(
        contrast_gap_bps
    )

    if contrast > 0:
        sign = "POSITIVE"
        direction = Decimal("1")
    elif contrast < 0:
        sign = "NEGATIVE"
        direction = Decimal("-1")
    else:
        sign = "ZERO"
        direction = Decimal("0")

    if sign == "ZERO":
        concordance_status = (
            NOT_APPLICABLE_ZERO_CONTRAST
        )

        concordance = None
    else:
        concordance_status = (
            APPLICABLE_NONZERO_CONTRAST
        )

        concordance = (
            direction
            * forward
            if concordance_bps
            is None
            else Decimal(
                concordance_bps
            )
        )

    return {
        "capture_id":
            capture_id,
        "freshness_threshold_ms":
            "250",
        "horizon_ms":
            "1000",
        "kuru_record_index":
            index,
        "kuru_received_monotonic_ns":
            t0_ns,
        "alignment_status":
            ALIGNED,
        "status":
            EVALUABLE,
        "coinbase_forward_mid_return_bps":
            str(forward),
        "kuru_proposed_finalized_mid_gap_bps":
            str(contrast),
        "contrast_sign":
            sign,
        "directional_concordance_status":
            concordance_status,
        "directional_concordance_bps":
            (
                None
                if concordance is None
                else str(
                    concordance
                )
            ),
        "future_asof_age_ms":
            future_age_ms,
    }


def censored_row(
    capture_id: str,
    index: int,
    t0_ns: int,
) -> dict:
    return {
        "capture_id":
            capture_id,
        "freshness_threshold_ms":
            "250",
        "horizon_ms":
            "1000",
        "kuru_record_index":
            index,
        "kuru_received_monotonic_ns":
            t0_ns,
        "alignment_status":
            ALIGNED,
        "status":
            RIGHT_CENSORED_CAPTURE_END,
        "coinbase_forward_mid_return_bps":
            None,
        "kuru_proposed_finalized_mid_gap_bps":
            "10",
        "contrast_sign":
            "POSITIVE",
        "directional_concordance_status":
            None,
        "directional_concordance_bps":
            None,
        "future_asof_age_ms":
            None,
    }


def stale_row(
    capture_id: str,
    index: int,
    t0_ns: int,
) -> dict:
    return {
        "capture_id":
            capture_id,
        "freshness_threshold_ms":
            "250",
        "horizon_ms":
            "1000",
        "kuru_record_index":
            index,
        "kuru_received_monotonic_ns":
            t0_ns,
        "alignment_status":
            STALE_REFERENCE,
        "status":
            STALE_REFERENCE,
        "coinbase_forward_mid_return_bps":
            None,
        "kuru_proposed_finalized_mid_gap_bps":
            None,
        "contrast_sign":
            None,
        "directional_concordance_status":
            None,
        "directional_concordance_bps":
            None,
        "future_asof_age_ms":
            None,
    }


def analysis(
    capture_id: str,
    rows: list[dict],
    *,
    freshness_threshold_ms: str = "250",
    horizon_ms: str = "1000",
) -> dict:
    copied = []

    for row in rows:
        item = dict(
            row
        )

        item[
            "capture_id"
        ] = capture_id

        item[
            "freshness_threshold_ms"
        ] = freshness_threshold_ms

        item[
            "horizon_ms"
        ] = horizon_ms

        copied.append(
            item
        )

    counts = Counter(
        row[
            "status"
        ]
        for row in copied
    )

    return {
        "schema_version":
            "phase2.temporal_outcome.v1",
        "capture_id":
            capture_id,
        "source_capture_schema_version":
            "phase0.dual_ws_capture.v1",
        "freshness_threshold_ms":
            freshness_threshold_ms,
        "horizon_ms":
            horizon_ms,
        "primary_horizon":
            (
                horizon_ms
                in {
                    "250",
                    "1000",
                    "5000",
                }
            ),
        "claim_boundaries": [
            "synthetic test boundary"
        ],
        "summary": {
            "kuru_observations":
                len(copied),
            "rows":
                len(copied),
            "status_counts":
                dict(
                    sorted(
                        counts.items()
                    )
                ),
            "evaluable":
                counts[
                    EVALUABLE
                ],
            "right_censored":
                counts[
                    RIGHT_CENSORED_CAPTURE_END
                ],
        },
        "rows":
            copied,
    }


class TestTemporalAggregation(
    unittest.TestCase
):
    def test_schema_and_primary_dimensions(
        self,
    ):
        result = aggregate_temporal_outcomes(
            [
                analysis(
                    "capture-a",
                    [
                        evaluable_row(
                            "capture-a",
                            0,
                            1_000_000_000,
                            forward_bps="10",
                            contrast_gap_bps="5",
                        )
                    ],
                )
            ]
        )

        self.assertEqual(
            SCHEMA_VERSION,
            "phase2.temporal_outcome_aggregation.v1",
        )

        self.assertEqual(
            result[
                "freshness_threshold_ms"
            ],
            "250",
        )

        self.assertEqual(
            result[
                "horizon_ms"
            ],
            "1000",
        )

        self.assertEqual(
            result[
                "capture_count"
            ],
            1,
        )

    def test_status_accounting_and_baseline_aligned_count(
        self,
    ):
        result = aggregate_temporal_outcomes(
            [
                analysis(
                    "capture-a",
                    [
                        evaluable_row(
                            "capture-a",
                            0,
                            0,
                            forward_bps="10",
                            contrast_gap_bps="5",
                        ),
                        censored_row(
                            "capture-a",
                            1,
                            1_000_000_000,
                        ),
                        stale_row(
                            "capture-a",
                            2,
                            2_000_000_000,
                        ),
                    ],
                )
            ]
        )

        self.assertEqual(
            result[
                "status_counts"
            ][
                EVALUABLE
            ],
            1,
        )

        self.assertEqual(
            result[
                "status_counts"
            ][
                RIGHT_CENSORED_CAPTURE_END
            ],
            1,
        )

        self.assertEqual(
            result[
                "status_counts"
            ][
                STALE_REFERENCE
            ],
            1,
        )

        self.assertEqual(
            result[
                "baseline_aligned_panels"
            ],
            2,
        )

    def test_pooled_forward_distribution_and_sign_counts(
        self,
    ):
        result = aggregate_temporal_outcomes(
            [
                analysis(
                    "capture-a",
                    [
                        evaluable_row(
                            "capture-a",
                            0,
                            0,
                            forward_bps="-10",
                            contrast_gap_bps="5",
                        ),
                        evaluable_row(
                            "capture-a",
                            1,
                            1_000_000_000,
                            forward_bps="0",
                            contrast_gap_bps="-5",
                        ),
                    ],
                ),
                analysis(
                    "capture-b",
                    [
                        evaluable_row(
                            "capture-b",
                            0,
                            0,
                            forward_bps="20",
                            contrast_gap_bps="5",
                        )
                    ],
                ),
            ]
        )

        distribution = result[
            "pooled"
        ][
            "forward_return_bps"
        ]

        self.assertEqual(
            distribution[
                "count"
            ],
            3,
        )

        self.assertEqual(
            Decimal(
                distribution[
                    "min"
                ]
            ),
            Decimal("-10"),
        )

        self.assertEqual(
            Decimal(
                distribution[
                    "p50"
                ]
            ),
            Decimal("0"),
        )

        self.assertEqual(
            Decimal(
                distribution[
                    "max"
                ]
            ),
            Decimal("20"),
        )

        self.assertEqual(
            distribution[
                "sign_counts"
            ],
            {
                "NEGATIVE": 1,
                "POSITIVE": 1,
                "ZERO": 1,
            },
        )

    def test_zero_contrast_remains_in_forward_distribution(
        self,
    ):
        result = aggregate_temporal_outcomes(
            [
                analysis(
                    "capture-a",
                    [
                        evaluable_row(
                            "capture-a",
                            0,
                            0,
                            forward_bps="15",
                            contrast_gap_bps="0",
                        ),
                        evaluable_row(
                            "capture-a",
                            1,
                            1_000_000_000,
                            forward_bps="-5",
                            contrast_gap_bps="10",
                        ),
                    ],
                )
            ]
        )

        pooled = result[
            "pooled"
        ]

        self.assertEqual(
            pooled[
                "forward_return_bps"
            ][
                "count"
            ],
            2,
        )

        self.assertEqual(
            pooled[
                "contrast_sign_counts"
            ][
                "ZERO"
            ],
            1,
        )

        self.assertEqual(
            pooled[
                "directional_concordance_bps"
            ][
                "count"
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
            1,
        )

    def test_capture_level_medians_are_preserved(
        self,
    ):
        result = aggregate_temporal_outcomes(
            [
                analysis(
                    "capture-a",
                    [
                        evaluable_row(
                            "capture-a",
                            0,
                            0,
                            forward_bps="-10",
                            contrast_gap_bps="5",
                        ),
                        evaluable_row(
                            "capture-a",
                            1,
                            1_000_000_000,
                            forward_bps="10",
                            contrast_gap_bps="5",
                        ),
                    ],
                ),
                analysis(
                    "capture-b",
                    [
                        evaluable_row(
                            "capture-b",
                            0,
                            0,
                            forward_bps="20",
                            contrast_gap_bps="5",
                        ),
                        evaluable_row(
                            "capture-b",
                            1,
                            1_000_000_000,
                            forward_bps="40",
                            contrast_gap_bps="5",
                        ),
                    ],
                ),
            ]
        )

        by_capture = {
            item[
                "capture_id"
            ]:
                item
            for item in result[
                "capture_summaries"
            ]
        }

        self.assertEqual(
            Decimal(
                by_capture[
                    "capture-a"
                ][
                    "forward_return_bps_median"
                ]
            ),
            Decimal("0"),
        )

        self.assertEqual(
            Decimal(
                by_capture[
                    "capture-b"
                ][
                    "forward_return_bps_median"
                ]
            ),
            Decimal("30"),
        )

    def test_non_overlapping_selection_is_greedy_and_deterministic(
        self,
    ):
        rows = [
            evaluable_row(
                "capture-a",
                0,
                0,
                forward_bps="1",
                contrast_gap_bps="1",
            ),
            evaluable_row(
                "capture-a",
                1,
                500_000_000,
                forward_bps="2",
                contrast_gap_bps="1",
            ),
            evaluable_row(
                "capture-a",
                2,
                1_000_000_000,
                forward_bps="3",
                contrast_gap_bps="1",
            ),
            evaluable_row(
                "capture-a",
                3,
                1_500_000_000,
                forward_bps="4",
                contrast_gap_bps="1",
            ),
            evaluable_row(
                "capture-a",
                4,
                2_000_000_000,
                forward_bps="5",
                contrast_gap_bps="1",
            ),
        ]

        selected = (
            select_non_overlapping_rows(
                rows,
                horizon_ms=
                    Decimal("1000"),
            )
        )

        self.assertEqual(
            [
                row[
                    "kuru_record_index"
                ]
                for row in selected
            ],
            [
                0,
                2,
                4,
            ],
        )

    def test_aggregate_contains_non_overlapping_sensitivity(
        self,
    ):
        rows = [
            evaluable_row(
                "capture-a",
                index,
                index
                * 500_000_000,
                forward_bps=str(
                    index + 1
                ),
                contrast_gap_bps="1",
            )
            for index in range(
                5
            )
        ]

        result = aggregate_temporal_outcomes(
            [
                analysis(
                    "capture-a",
                    rows,
                )
            ]
        )

        sensitivity = result[
            "non_overlapping_sensitivity"
        ]

        self.assertEqual(
            sensitivity[
                "selected_rows"
            ],
            3,
        )

        self.assertEqual(
            sensitivity[
                "per_capture_selected_counts"
            ][
                "capture-a"
            ],
            3,
        )

        self.assertEqual(
            sensitivity[
                "forward_return_bps"
            ][
                "count"
            ],
            3,
        )

    def test_duplicate_capture_ids_are_rejected(
        self,
    ):
        item = analysis(
            "capture-a",
            [
                evaluable_row(
                    "capture-a",
                    0,
                    0,
                    forward_bps="1",
                    contrast_gap_bps="1",
                )
            ],
        )

        with self.assertRaises(
            ValueError
        ):
            aggregate_temporal_outcomes(
                [
                    item,
                    item,
                ]
            )

    def test_mixed_thresholds_are_rejected(
        self,
    ):
        first = analysis(
            "capture-a",
            [
                evaluable_row(
                    "capture-a",
                    0,
                    0,
                    forward_bps="1",
                    contrast_gap_bps="1",
                )
            ],
        )

        second = analysis(
            "capture-b",
            [
                evaluable_row(
                    "capture-b",
                    0,
                    0,
                    forward_bps="1",
                    contrast_gap_bps="1",
                )
            ],
            freshness_threshold_ms=
                "500",
        )

        with self.assertRaises(
            ValueError
        ):
            aggregate_temporal_outcomes(
                [
                    first,
                    second,
                ]
            )

    def test_mixed_horizons_are_rejected(
        self,
    ):
        first = analysis(
            "capture-a",
            [
                evaluable_row(
                    "capture-a",
                    0,
                    0,
                    forward_bps="1",
                    contrast_gap_bps="1",
                )
            ],
        )

        second = analysis(
            "capture-b",
            [
                evaluable_row(
                    "capture-b",
                    0,
                    0,
                    forward_bps="1",
                    contrast_gap_bps="1",
                )
            ],
            horizon_ms=
                "5000",
        )

        with self.assertRaises(
            ValueError
        ):
            aggregate_temporal_outcomes(
                [
                    first,
                    second,
                ]
            )

    def test_inconsistent_summary_is_rejected(
        self,
    ):
        item = analysis(
            "capture-a",
            [
                evaluable_row(
                    "capture-a",
                    0,
                    0,
                    forward_bps="1",
                    contrast_gap_bps="1",
                )
            ],
        )

        item[
            "summary"
        ][
            "evaluable"
        ] = 999

        with self.assertRaises(
            ValueError
        ):
            aggregate_temporal_outcomes(
                [
                    item
                ]
            )

    def test_non_evaluable_row_cannot_carry_forward_return(
        self,
    ):
        row = censored_row(
            "capture-a",
            0,
            0,
        )

        row[
            "coinbase_forward_mid_return_bps"
        ] = "100"

        with self.assertRaises(
            ValueError
        ):
            aggregate_temporal_outcomes(
                [
                    analysis(
                        "capture-a",
                        [
                            row
                        ],
                    )
                ]
            )

    def test_inconsistent_directional_concordance_is_rejected(
        self,
    ):
        row = evaluable_row(
            "capture-a",
            0,
            0,
            forward_bps="10",
            contrast_gap_bps="5",
            concordance_bps="-10",
        )

        with self.assertRaises(
            ValueError
        ):
            aggregate_temporal_outcomes(
                [
                    analysis(
                        "capture-a",
                        [
                            row
                        ],
                    )
                ]
            )

    def test_claim_boundaries_are_preserved(
        self,
    ):
        result = aggregate_temporal_outcomes(
            [
                analysis(
                    "capture-a",
                    [
                        evaluable_row(
                            "capture-a",
                            0,
                            0,
                            forward_bps="1",
                            contrast_gap_bps="1",
                        )
                    ],
                )
            ]
        )

        rendered = " ".join(
            result[
                "claim_boundaries"
            ]
        ).lower()

        self.assertIn(
            "not independent",
            rendered,
        )

        self.assertIn(
            "not a win rate",
            rendered,
        )

        self.assertIn(
            "descriptive",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
