from __future__ import annotations

import unittest
from decimal import Decimal

from finality_intelligence.depth_aggregation import (
    AGGREGATION_CLAIM_BOUNDARIES,
    SCHEMA_VERSION,
    aggregate_depth_panels,
)
from finality_intelligence.depth_panel import (
    EXECUTION_PANEL_ELIGIBLE,
    INVALID_EXECUTION_STATE_PANEL,
    analyze_capture_depth_panels,
)
from tests.test_depth_panel import (
    capture,
    raw_price,
    raw_quantity,
    record,
)


def analyze(
    source,
    *,
    capture_id: str,
):
    return analyze_capture_depth_panels(
        source,
        capture_id=capture_id,
    )


class TestDepthAggregation(unittest.TestCase):
    def test_eligibility_reconciles_across_captures(
        self,
    ):
        first = analyze(
            capture(),
            capture_id="a.json",
        )

        source = capture(
            records=[
                record(update_id=1),
                record(update_id=2),
            ]
        )

        del source[
            "sources"
        ]["kuru"]["records"][1][
            "raw_message"
        ]["states"]["finalized"]

        second = analyze(
            source,
            capture_id="b.json",
        )

        result = aggregate_depth_panels(
            [first, second]
        )

        eligibility = result[
            "eligibility_summary"
        ]

        self.assertEqual(
            eligibility[
                "kuru_observations"
            ],
            3,
        )
        self.assertEqual(
            eligibility[
                "eligible_panels"
            ],
            2,
        )
        self.assertEqual(
            eligibility[
                "panel_outcome_counts"
            ][EXECUTION_PANEL_ELIGIBLE],
            2,
        )
        self.assertEqual(
            eligibility[
                "panel_outcome_counts"
            ][INVALID_EXECUTION_STATE_PANEL],
            1,
        )

    def test_state_fill_counts_are_auditable(
        self,
    ):
        first = analyze(
            capture(),
            capture_id="a.json",
        )

        source = capture()

        source[
            "sources"
        ]["kuru"]["records"][0][
            "raw_message"
        ]["states"]["proposed"]["a"] = [
            [
                raw_price("1.0010"),
                raw_quantity("100"),
            ]
        ]

        second = analyze(
            source,
            capture_id="b.json",
        )

        result = aggregate_depth_panels(
            [first, second]
        )

        target = result[
            "state_summaries"
        ]["proposed"]["BUY"][
            "targets"
        ]["200"]

        self.assertEqual(
            target["eligible_panel_count"],
            2,
        )
        self.assertEqual(
            target["fully_filled_count"],
            1,
        )
        self.assertEqual(
            target[
                "insufficient_captured_depth_count"
            ],
            1,
        )
        self.assertEqual(
            Decimal(
                target["full_fill_rate"]
            ),
            Decimal("0.5"),
        )
        self.assertEqual(
            target[
                "slippage_bps_distribution"
            ]["count"],
            1,
        )

    def test_depth_distribution_and_capture_medians(
        self,
    ):
        first = analyze(
            capture(),
            capture_id="a.json",
        )

        source = capture()

        source[
            "sources"
        ]["kuru"]["records"][0][
            "raw_message"
        ]["states"]["proposed"]["a"] = [
            [
                raw_price("1.0010"),
                raw_quantity("400"),
            ],
            [
                raw_price("1.0020"),
                raw_quantity("200"),
            ],
        ]

        second = analyze(
            source,
            capture_id="b.json",
        )

        result = aggregate_depth_panels(
            [first, second]
        )

        depth = result[
            "state_summaries"
        ]["proposed"]["BUY"][
            "depth_within_bps"
        ]["5"]

        self.assertEqual(
            depth["distribution"]["count"],
            2,
        )
        self.assertEqual(
            depth["distribution"]["min"],
            "300",
        )
        self.assertEqual(
            depth["distribution"]["max"],
            "400",
        )
        self.assertEqual(
            [
                row["median"]
                for row
                in depth["capture_medians"]
            ],
            [
                "300",
                "400",
            ],
        )

    def test_pair_fillability_transition_is_directional(
        self,
    ):
        source = capture()

        states = source[
            "sources"
        ]["kuru"]["records"][0][
            "raw_message"
        ]["states"]

        states["proposed"]["a"] = [
            [
                raw_price("1.0010"),
                raw_quantity("100"),
            ]
        ]

        result = aggregate_depth_panels(
            [
                analyze(
                    source,
                    capture_id="a.json",
                )
            ]
        )

        pair = result[
            "paired_state_view_contrasts"
        ]["proposed__committed"][
            "BUY"
        ]["targets"]["200"]

        self.assertEqual(
            pair[
                "only_second_fully_filled"
            ],
            1,
        )
        self.assertEqual(
            pair[
                "only_first_fully_filled"
            ],
            0,
        )
        self.assertEqual(
            pair["both_fully_filled"],
            0,
        )
        self.assertEqual(
            pair[
                "slippage_delta_bps"
            ]["distribution"]["count"],
            0,
        )

    def test_pair_slippage_delta_is_within_panel(
        self,
    ):
        source = capture()

        states = source[
            "sources"
        ]["kuru"]["records"][0][
            "raw_message"
        ]["states"]

        states["proposed"]["a"] = [
            [
                raw_price("1.0010"),
                raw_quantity("100"),
            ],
            [
                raw_price("1.0020"),
                raw_quantity("100"),
            ],
        ]

        states["committed"]["a"] = [
            [
                raw_price("1.0010"),
                raw_quantity("100"),
            ],
            [
                raw_price("1.0015"),
                raw_quantity("100"),
            ],
        ]

        result = aggregate_depth_panels(
            [
                analyze(
                    source,
                    capture_id="a.json",
                )
            ]
        )

        pair = result[
            "paired_state_view_contrasts"
        ]["proposed__committed"][
            "BUY"
        ]["targets"]["200"]

        distribution = pair[
            "slippage_delta_bps"
        ]["distribution"]

        self.assertEqual(
            distribution["count"],
            1,
        )

        self.assertLess(
            Decimal(
                distribution["p50"]
            ),
            Decimal("0"),
        )

        self.assertEqual(
            pair[
                "slippage_delta_bps"
            ]["sign_counts"]["negative"],
            1,
        )

    def test_depth_delta_direction_is_second_minus_first(
        self,
    ):
        source = capture()

        states = source[
            "sources"
        ]["kuru"]["records"][0][
            "raw_message"
        ]["states"]

        states["proposed"]["a"] = [
            [
                raw_price("1.0010"),
                raw_quantity("100"),
            ],
            [
                raw_price("1.0020"),
                raw_quantity("500"),
            ],
        ]

        result = aggregate_depth_panels(
            [
                analyze(
                    source,
                    capture_id="a.json",
                )
            ]
        )

        pair = result[
            "paired_state_view_contrasts"
        ]["proposed__committed"][
            "BUY"
        ]["depth_bands"]["5"][
            "depth_delta_base"
        ]

        self.assertEqual(
            pair["distribution"]["p50"],
            "200",
        )
        self.assertEqual(
            pair[
                "sign_counts"
            ]["positive"],
            1,
        )

    def test_duplicate_capture_ids_are_rejected(
        self,
    ):
        source = analyze(
            capture(),
            capture_id="same.json",
        )

        with self.assertRaises(ValueError):
            aggregate_depth_panels(
                [source, source]
            )

    def test_inconsistent_summary_is_rejected(
        self,
    ):
        source = analyze(
            capture(),
            capture_id="a.json",
        )

        source["summary"][
            "kuru_observations"
        ] = 2

        with self.assertRaises(ValueError):
            aggregate_depth_panels(
                [source]
            )

    def test_schema_and_claim_boundaries(
        self,
    ):
        result = aggregate_depth_panels(
            [
                analyze(
                    capture(),
                    capture_id="a.json",
                )
            ]
        )

        self.assertEqual(
            result["schema_version"],
            SCHEMA_VERSION,
        )

        joined = " ".join(
            result["claim_boundaries"]
        ).lower()

        self.assertIn(
            "not assumed",
            joined,
        )
        self.assertIn(
            "not execution probabilities",
            joined,
        )
        self.assertIn(
            "not temporal",
            joined,
        )

        for boundary in (
            AGGREGATION_CLAIM_BOUNDARIES
        ):
            self.assertIn(
                boundary,
                result["claim_boundaries"],
            )


if __name__ == "__main__":
    unittest.main()
