from __future__ import annotations

from decimal import Decimal
import unittest

from finality_intelligence import (
    market_instability_aggregation as agg,
)
from finality_intelligence.market_instability import (
    SCHEMA_VERSION,
)
from finality_intelligence.temporal_outcome import (
    EVALUABLE,
)


def analysis(
    capture_id: str,
    *,
    exposures=("1", "2", "3"),
    outcomes=("1", "2", "3"),
):
    rows = []

    for index, (
        exposure,
        outcome,
    ) in enumerate(
        zip(
            exposures,
            outcomes,
        )
    ):
        rows.append(
            {
                "capture_id":
                    capture_id,
                "freshness_threshold_ms":
                    "250",
                "horizon_ms":
                    "250",
                "kuru_record_index":
                    index,
                "kuru_received_monotonic_ns":
                    (
                        1_000_000_000
                        + index
                        * 300_000_000
                    ),
                "alignment_status":
                    "ALIGNED",
                "status":
                    EVALUABLE,
                "kuru_pf_gap_bps":
                    exposure,
                "kuru_pf_abs_gap_bps":
                    exposure,
                "coinbase_forward_mid_return_bps":
                    outcome,
                "coinbase_abs_forward_mid_move_bps":
                    outcome,
            }
        )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "capture_id":
            capture_id,
        "freshness_threshold_ms":
            "250",
        "horizon_ms":
            "250",
        "rows":
            rows,
    }


class TestMarketInstabilityAggregation(
    unittest.TestCase
):
    def test_average_ranks_use_average_for_ties(
        self,
    ):
        ranks = agg.average_ranks(
            ["10", "10", "20", "30"]
        )

        self.assertEqual(
            [
                str(
                    value
                )
                for value in ranks
            ],
            [
                "1.5",
                "1.5",
                "3",
                "4",
            ],
        )

    def test_perfect_positive_spearman(
        self,
    ):
        result = (
            agg.spearman_rank_correlation(
                ["1", "2", "3"],
                ["10", "20", "30"],
            )
        )

        self.assertEqual(
            result["status"],
            agg.DEFINED,
        )
        self.assertEqual(
            result["rho"],
            "1",
        )

    def test_perfect_negative_spearman(
        self,
    ):
        result = (
            agg.spearman_rank_correlation(
                ["1", "2", "3"],
                ["30", "20", "10"],
            )
        )

        self.assertEqual(
            result["status"],
            agg.DEFINED,
        )
        self.assertEqual(
            result["rho"],
            "-1",
        )

    def test_too_few_pairs_is_undefined(
        self,
    ):
        result = (
            agg.spearman_rank_correlation(
                ["1"],
                ["2"],
            )
        )

        self.assertEqual(
            result["status"],
            agg.UNDEFINED,
        )
        self.assertEqual(
            result["reason_code"],
            agg.TOO_FEW_EVALUABLE_PAIRS,
        )

    def test_zero_exposure_variance_is_undefined(
        self,
    ):
        result = (
            agg.spearman_rank_correlation(
                ["1", "1", "1"],
                ["1", "2", "3"],
            )
        )

        self.assertEqual(
            result["reason_code"],
            (
                agg
                .ZERO_EXPOSURE_RANK_VARIANCE
            ),
        )

    def test_zero_outcome_variance_is_undefined(
        self,
    ):
        result = (
            agg.spearman_rank_correlation(
                ["1", "2", "3"],
                ["4", "4", "4"],
            )
        )

        self.assertEqual(
            result["reason_code"],
            (
                agg
                .ZERO_OUTCOME_RANK_VARIANCE
            ),
        )

    def test_six_defined_positive_captures_support(
        self,
    ):
        analyses = [
            analysis(
                f"capture-{index}"
            )
            for index in range(
                6
            )
        ]

        analyses.extend(
            analysis(
                f"capture-{index}",
                exposures=("5", "5", "5"),
                outcomes=("5", "5", "5"),
            )
            for index in range(
                6,
                10,
            )
        )

        result = (
            agg.aggregate_market_instability(
                analyses
            )
        )

        self.assertEqual(
            Decimal(
                result["pooled"][
                    "spearman"
                ][
                    "rho"
                ]
            ),
            Decimal("1"),
        )

        self.assertEqual(
            result["capture_level"][
                "defined_count"
            ],
            6,
        )

        self.assertEqual(
            Decimal(
                result["capture_level"][
                    "median_defined_rho"
                ]
            ),
            Decimal("1"),
        )

        self.assertTrue(
            result[
                "descriptive_support"
            ][
                "directionally_supportive"
            ]
        )

    def test_six_total_captures_do_not_complete_confirmatory_sample(
        self,
    ):
        analyses = [
            analysis(
                f"capture-{index}"
            )
            for index in range(
                6
            )
        ]

        result = (
            agg.aggregate_market_instability(
                analyses
            )
        )

        self.assertFalse(
            result[
                "descriptive_support"
            ][
                "capture_sample_complete"
            ]
        )

        self.assertFalse(
            result[
                "descriptive_support"
            ][
                "directionally_supportive"
            ]
        )

    def test_fewer_than_six_defined_captures_not_supportive(
        self,
    ):
        analyses = [
            analysis(
                f"capture-{index}"
            )
            for index in range(
                5
            )
        ]

        result = (
            agg.aggregate_market_instability(
                analyses
            )
        )

        self.assertFalse(
            result[
                "descriptive_support"
            ][
                "capture_defined_count_sufficient"
            ]
        )

        self.assertFalse(
            result[
                "descriptive_support"
            ][
                "directionally_supportive"
            ]
        )

    def test_duplicate_capture_id_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            agg.aggregate_market_instability(
                [
                    analysis("same"),
                    analysis("same"),
                ]
            )


if __name__ == "__main__":
    unittest.main()
