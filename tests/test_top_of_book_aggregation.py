from __future__ import annotations

import unittest
from decimal import Decimal

from finality_intelligence.alignment import (
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
)
from finality_intelligence.top_of_book import (
    ECONOMICALLY_ELIGIBLE,
    ELIGIBILITY_OUTCOMES,
)
from finality_intelligence.top_of_book_aggregation import (
    aggregate_top_of_book,
)


STATES = ("proposed", "voted", "finalized", "committed")


def analysis(
    capture_id: str,
    *,
    threshold: str = "500",
    panel_specs=None,
) -> dict:
    if panel_specs is None:
        panel_specs = [
            {
                "coinbase_spread": "2",
                "spread": {
                    "proposed": "3",
                    "voted": "3",
                    "finalized": "2",
                    "committed": "2",
                },
                "reference": {
                    "proposed": "1",
                    "voted": "1",
                    "finalized": "2",
                    "committed": "2",
                },
                "tops": {
                    "proposed": ("100", "103"),
                    "voted": ("100", "103"),
                    "finalized": ("101", "103"),
                    "committed": ("101", "103"),
                },
            }
        ]

    rows = []

    for index, spec in enumerate(panel_specs):
        for state in STATES:
            bid_raw, ask_raw = spec["tops"][state]

            rows.append({
                "capture_id": capture_id,
                "freshness_threshold_ms": threshold,
                "kuru_record_index": index,
                "state": state,
                "kuru_best_bid_raw": bid_raw,
                "kuru_best_ask_raw": ask_raw,
                "kuru_spread_bps": spec["spread"][state],
                "reference_mid_difference_bps": spec["reference"][state],
                "coinbase_record_index": index + 10,
                "coinbase_sequence_num": index + 100,
                "coinbase_received_monotonic_ns": 1_000 + index,
                "reference_age_ms": "100",
                "coinbase_best_bid": "0.0250",
                "coinbase_best_offer": "0.0251",
                "coinbase_spread_bps": spec["coinbase_spread"],
            })

    eligibility_counts = {
        outcome: 0
        for outcome in ELIGIBILITY_OUTCOMES
    }
    eligibility_counts[ECONOMICALLY_ELIGIBLE] = len(
        panel_specs
    )

    return {
        "capture_id": capture_id,
        "freshness_threshold_ms": threshold,
        "summary": {
            "kuru_observations": len(panel_specs),
            "eligibility_counts": eligibility_counts,
            "economic_rows": len(rows),
        },
        "rows": rows,
    }


class TestTopOfBookAggregation(unittest.TestCase):
    def test_state_summaries_and_capture_medians(self):
        result = aggregate_top_of_book([
            analysis("capture-a"),
            analysis("capture-b"),
        ])

        proposed = result["state_summaries"]["proposed"]

        self.assertEqual(proposed["count"], 2)
        self.assertEqual(
            Decimal(proposed["kuru_spread_bps"]["p50"]),
            Decimal("3"),
        )
        self.assertEqual(
            proposed["reference_mid_difference_sign_counts"],
            {"positive": 2, "zero": 0, "negative": 0},
        )
        self.assertEqual(
            Decimal(
                proposed["capture_medians"]["capture-a"][
                    "kuru_spread_bps_p50"
                ]
            ),
            Decimal("3"),
        )

    def test_coinbase_reference_is_counted_once_per_panel(self):
        source = analysis(
            "capture-a",
            panel_specs=[
                {
                    "coinbase_spread": "1",
                    "spread": {state: "2" for state in STATES},
                    "reference": {state: "0" for state in STATES},
                    "tops": {state: ("100", "101") for state in STATES},
                },
                {
                    "coinbase_spread": "3",
                    "spread": {state: "2" for state in STATES},
                    "reference": {state: "0" for state in STATES},
                    "tops": {state: ("100", "101") for state in STATES},
                },
            ],
        )

        result = aggregate_top_of_book([source])
        coinbase = result["coinbase_reference_summary"]

        self.assertEqual(coinbase["panel_count"], 2)
        self.assertEqual(coinbase["coinbase_spread_bps"]["count"], 2)
        self.assertEqual(
            Decimal(coinbase["coinbase_spread_bps"]["p50"]),
            Decimal("2"),
        )

    def test_paired_contrast_uses_within_panel_deltas(self):
        result = aggregate_top_of_book([analysis("capture-a")])
        pair = result["paired_state_view_contrasts"][
            "proposed__committed"
        ]

        self.assertEqual(pair["paired_observation_count"], 1)
        self.assertEqual(pair["exact_top_equal_count"], 0)
        self.assertEqual(Decimal(pair["exact_top_equal_rate"]), Decimal("0"))
        self.assertEqual(
            Decimal(pair["spread_delta_bps"]["p50"]),
            Decimal("-1"),
        )
        self.assertEqual(
            pair["spread_delta_sign_counts"],
            {"positive": 0, "zero": 0, "negative": 1},
        )
        self.assertEqual(
            Decimal(pair["reference_mid_difference_delta_bps"]["p50"]),
            Decimal("1"),
        )

    def test_finalized_committed_exact_equality_is_detected(self):
        result = aggregate_top_of_book([analysis("capture-a")])
        pair = result["paired_state_view_contrasts"][
            "finalized__committed"
        ]

        self.assertEqual(pair["exact_top_equal_count"], 1)
        self.assertEqual(Decimal(pair["exact_top_equal_rate"]), Decimal("1"))
        self.assertEqual(
            pair["spread_delta_sign_counts"],
            {"positive": 0, "zero": 1, "negative": 0},
        )

    def test_mixed_thresholds_are_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_top_of_book([
                analysis("capture-a", threshold="250"),
                analysis("capture-b", threshold="500"),
            ])

    def test_duplicate_capture_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            aggregate_top_of_book([
                analysis("capture-a"),
                analysis("capture-a"),
            ])

    def test_missing_state_row_is_rejected(self):
        source = analysis("capture-a")
        source["rows"] = [
            row
            for row in source["rows"]
            if row["state"] != "committed"
        ]
        source["summary"]["economic_rows"] = len(source["rows"])

        with self.assertRaises(ValueError):
            aggregate_top_of_book([source])

    def test_four_state_reference_mismatch_is_rejected(self):
        source = analysis("capture-a")
        source["rows"][1]["coinbase_sequence_num"] = 999

        with self.assertRaises(ValueError):
            aggregate_top_of_book([source])

    def test_float_metric_is_rejected(self):
        source = analysis("capture-a")
        source["rows"][0]["kuru_spread_bps"] = 3.0

        with self.assertRaises(ValueError):
            aggregate_top_of_book([source])


    def test_ineligible_observations_remain_auditable(self):
        source = analysis("capture-a")

        source["summary"]["kuru_observations"] = 3
        source["summary"]["eligibility_counts"][
            NO_PRIOR_REFERENCE
        ] = 1
        source["summary"]["eligibility_counts"][
            STALE_REFERENCE
        ] = 1

        result = aggregate_top_of_book([source])
        summary = result["eligibility_summary"]

        self.assertEqual(summary["kuru_observations"], 3)
        self.assertEqual(summary["economic_panel_count"], 1)
        self.assertEqual(summary["economic_rows"], 4)

        self.assertEqual(
            summary["eligibility_counts"][
                ECONOMICALLY_ELIGIBLE
            ],
            1,
        )
        self.assertEqual(
            summary["eligibility_counts"][
                NO_PRIOR_REFERENCE
            ],
            1,
        )
        self.assertEqual(
            summary["eligibility_counts"][
                STALE_REFERENCE
            ],
            1,
        )

        capture_summary = summary[
            "capture_summaries"
        ]["capture-a"]

        self.assertEqual(
            capture_summary["kuru_observations"],
            3,
        )
        self.assertEqual(
            capture_summary["economic_panel_count"],
            1,
        )

    def test_inconsistent_eligibility_counts_are_rejected(self):
        source = analysis("capture-a")

        source["summary"]["kuru_observations"] = 2

        with self.assertRaises(ValueError):
            aggregate_top_of_book([source])


    def test_claim_boundaries_are_preserved(self):
        result = aggregate_top_of_book([analysis("capture-a")])
        rendered = " ".join(result["claim_boundaries"])

        self.assertIn("distinct markets", rendered)
        self.assertIn("not assumed independent", rendered)
        self.assertIn("once per economically eligible panel", rendered)
        self.assertIn("simultaneously observed state views", rendered)


if __name__ == "__main__":
    unittest.main()
