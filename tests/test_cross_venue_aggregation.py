from __future__ import annotations

import copy
import unittest
from decimal import Decimal

from finality_intelligence.cross_venue_aggregation import (
    AGGREGATION_CLAIM_BOUNDARIES,
    SCHEMA_VERSION,
    aggregate_cross_venue_execution,
)
from finality_intelligence.cross_venue_execution import (
    BOTH_FULL,
    analyze_cross_venue_capture,
)
from tests.test_cross_venue_execution import (
    capture,
)


def analyze(
    *,
    capture_id: str = "a.json",
    threshold: str = "250",
) -> dict:
    return analyze_cross_venue_capture(
        capture(),
        capture_id=capture_id,
        max_age_ms=Decimal(
            threshold
        ),
    )


class TestCrossVenueAggregation(
    unittest.TestCase
):
    def test_zero_gap_distributions_and_capture_medians(
        self,
    ):
        result = (
            aggregate_cross_venue_execution(
                [analyze()]
            )
        )

        execution = result[
            "execution_summaries"
        ][
            "proposed"
        ][
            "BUY"
        ][
            "200"
        ]

        self.assertEqual(
            execution[
                "fillability_transition_counts"
            ][BOTH_FULL],
            1,
        )

        self.assertEqual(
            Decimal(
                execution[
                    "slippage_gap_bps"
                ][
                    "distribution"
                ][
                    "p50"
                ]
            ),
            Decimal("0"),
        )

        self.assertEqual(
            Decimal(
                execution[
                    "cross_quote_vwap_difference_bps"
                ][
                    "distribution"
                ][
                    "p50"
                ]
            ),
            Decimal("0"),
        )

        capture_summary = (
            execution[
                "capture_summaries"
            ][0]
        )

        self.assertEqual(
            Decimal(
                capture_summary[
                    "slippage_gap_bps_p50"
                ]
            ),
            Decimal("0"),
        )

        depth = result[
            "depth_summaries"
        ][
            "proposed"
        ][
            "BUY"
        ][
            "5"
        ]

        self.assertEqual(
            Decimal(
                depth[
                    "depth_gap_MON"
                ][
                    "distribution"
                ][
                    "p50"
                ]
            ),
            Decimal("0"),
        )

        self.assertEqual(
            Decimal(
                depth[
                    "capture_summaries"
                ][0][
                    "depth_gap_MON_p50"
                ]
            ),
            Decimal("0"),
        )

    def test_all_frozen_dimensions_are_present(
        self,
    ):
        result = (
            aggregate_cross_venue_execution(
                [analyze()]
            )
        )

        self.assertEqual(
            tuple(
                result[
                    "execution_summaries"
                ]
            ),
            (
                "proposed",
                "voted",
                "finalized",
                "committed",
            ),
        )

        self.assertEqual(
            tuple(
                result[
                    "execution_summaries"
                ][
                    "proposed"
                ]
            ),
            (
                "BUY",
                "SELL",
            ),
        )

        self.assertEqual(
            tuple(
                result[
                    "execution_summaries"
                ][
                    "proposed"
                ][
                    "BUY"
                ]
            ),
            (
                "200",
                "2000",
                "20000",
                "200000",
            ),
        )

        self.assertEqual(
            tuple(
                result[
                    "depth_summaries"
                ][
                    "proposed"
                ][
                    "BUY"
                ]
            ),
            (
                "5",
                "10",
                "25",
                "50",
            ),
        )

    def test_eligibility_reconciles(
        self,
    ):
        result = (
            aggregate_cross_venue_execution(
                [analyze()]
            )
        )

        eligibility = result[
            "eligibility_summary"
        ]

        self.assertEqual(
            eligibility[
                "kuru_observations"
            ],
            1,
        )

        self.assertEqual(
            eligibility[
                "economic_panel_count"
            ],
            1,
        )

        self.assertEqual(
            eligibility[
                "alignment_status_counts"
            ][
                "ALIGNED"
            ],
            1,
        )

        self.assertEqual(
            eligibility[
                "economic_eligibility_counts"
            ][
                "ECONOMICALLY_ELIGIBLE"
            ],
            1,
        )

    def test_duplicate_capture_ids_are_rejected(
        self,
    ):
        first = analyze(
            capture_id="same.json"
        )

        second = analyze(
            capture_id="same.json"
        )

        with self.assertRaises(
            ValueError
        ):
            aggregate_cross_venue_execution(
                [
                    first,
                    second,
                ]
            )

    def test_mixed_thresholds_are_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            aggregate_cross_venue_execution(
                [
                    analyze(
                        capture_id="a.json",
                        threshold="250",
                    ),
                    analyze(
                        capture_id="b.json",
                        threshold="500",
                    ),
                ]
            )

    def test_inconsistent_economic_summary_is_rejected(
        self,
    ):
        source = analyze()

        source = copy.deepcopy(
            source
        )

        source[
            "summary"
        ][
            "economic_eligibility_counts"
        ][
            "ECONOMICALLY_ELIGIBLE"
        ] = 0

        with self.assertRaises(
            ValueError
        ):
            aggregate_cross_venue_execution(
                [source]
            )

    def test_future_reference_is_rejected(
        self,
    ):
        source = copy.deepcopy(
            analyze()
        )

        source[
            "rows"
        ][0][
            "coinbase_received_monotonic_ns"
        ] = (
            source[
                "rows"
            ][0][
                "kuru_received_monotonic_ns"
            ]
            + 1
        )

        with self.assertRaises(
            ValueError
        ):
            aggregate_cross_venue_execution(
                [source]
            )

    def test_schema_and_claim_boundaries(
        self,
    ):
        result = (
            aggregate_cross_venue_execution(
                [analyze()]
            )
        )

        self.assertEqual(
            result[
                "schema_version"
            ],
            SCHEMA_VERSION,
        )

        joined = " ".join(
            result[
                "claim_boundaries"
            ]
        ).lower()

        self.assertIn(
            "not execution probabilities",
            joined,
        )

        self.assertIn(
            "not trading edge",
            joined,
        )

        self.assertIn(
            "usd/usdc basis risk",
            joined,
        )

        self.assertIn(
            "causal finality",
            joined,
        )

        for boundary in (
            AGGREGATION_CLAIM_BOUNDARIES
        ):
            self.assertIn(
                boundary,
                result[
                    "claim_boundaries"
                ],
            )


if __name__ == "__main__":
    unittest.main()
