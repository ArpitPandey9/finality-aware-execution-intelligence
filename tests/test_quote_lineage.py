from __future__ import annotations

import unittest

from finality_intelligence.quote_lineage import (
    analyze_quote_lineage,
)


def state(
    *,
    bid_price="100",
    bid_qty="10",
    ask_price="101",
    ask_qty="11",
):
    return {
        "best_bid_raw": bid_price,
        "best_bid_quantity_raw": (
            bid_qty
        ),
        "best_ask_raw": ask_price,
        "best_ask_quantity_raw": (
            ask_qty
        ),
    }


def record(
    *,
    timestamp,
    u,
    proposed=None,
    voted=None,
    finalized=None,
    committed=None,
):
    empty = {
        "best_bid_raw": None,
        "best_bid_quantity_raw": None,
        "best_ask_raw": None,
        "best_ask_quantity_raw": None,
    }

    return {
        "received_at_utc": timestamp,
        "U": u,
        "states": {
            "proposed": (
                proposed
                if proposed is not None
                else empty.copy()
            ),
            "voted": (
                voted
                if voted is not None
                else empty.copy()
            ),
            "finalized": (
                finalized
                if finalized is not None
                else empty.copy()
            ),
            "committed": (
                committed
                if committed is not None
                else empty.copy()
            ),
        },
    }


class TestQuoteLineage(
    unittest.TestCase
):
    def test_exact_quote_progresses_through_states(self):
        quote = state()

        records = [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=1,
                proposed=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.100000+00:00"
                ),
                u=1,
                proposed=quote,
                voted=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.200000+00:00"
                ),
                u=1,
                proposed=quote,
                voted=quote,
                finalized=quote,
                committed=quote,
            ),
        ]

        result = analyze_quote_lineage(
            records,
            identity_mode=(
                "price_quantity"
            ),
        )

        self.assertEqual(
            result["summary"][
                "observed_ordered_all_states"
            ],
            2,
        )

        self.assertEqual(
            result["summary"][
                "observed_later_progressions"
            ],
            2,
        )

    def test_bid_and_ask_are_separate_candidates(self):
        quote = state()

        result = analyze_quote_lineage(
            [
                record(
                    timestamp=(
                        "2026-09-05T00:00:00+00:00"
                    ),
                    u=1,
                    proposed=quote,
                )
            ],
            identity_mode=(
                "price_quantity"
            ),
        )

        self.assertEqual(
            result["summary"][
                "proposed_candidates"
            ],
            2,
        )

    def test_same_u_is_required(self):
        quote = state()

        records = [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=1,
                proposed=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.100000+00:00"
                ),
                u=2,
                voted=quote,
                finalized=quote,
                committed=quote,
            ),
        ]

        result = analyze_quote_lineage(
            records,
            identity_mode=(
                "price_quantity"
            ),
        )

        self.assertEqual(
            result["summary"][
                "observed_ordered_all_states"
            ],
            0,
        )

    def test_quantity_change_breaks_exact_identity(self):
        proposed = state(
            bid_qty="10"
        )

        later = state(
            bid_qty="20"
        )

        records = [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=1,
                proposed=proposed,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.100000+00:00"
                ),
                u=1,
                voted=later,
                finalized=later,
                committed=later,
            ),
        ]

        exact = analyze_quote_lineage(
            records,
            identity_mode=(
                "price_quantity"
            ),
        )

        price = analyze_quote_lineage(
            records,
            identity_mode="price",
        )

        exact_bid = [
            row
            for row in exact["rows"]
            if row["side"] == "bid"
        ][0]

        price_bid = [
            row
            for row in price["rows"]
            if row["side"] == "bid"
        ][0]

        self.assertFalse(
            exact_bid[
                "observed_ordered_all_states"
            ]
        )

        self.assertTrue(
            price_bid[
                "observed_ordered_all_states"
            ]
        )

    def test_already_aligned_is_not_later_progression(self):
        quote = state()

        result = analyze_quote_lineage(
            [
                record(
                    timestamp=(
                        "2026-09-05T00:00:00+00:00"
                    ),
                    u=1,
                    proposed=quote,
                    voted=quote,
                    finalized=quote,
                    committed=quote,
                )
            ],
            identity_mode=(
                "price_quantity"
            ),
        )

        self.assertEqual(
            result["summary"][
                "already_aligned_same_record"
            ],
            2,
        )

        self.assertEqual(
            result["summary"][
                "observed_later_progressions"
            ],
            0,
        )

    def test_not_observed_is_not_called_failure(self):
        quote = state()

        result = analyze_quote_lineage(
            [
                record(
                    timestamp=(
                        "2026-09-05T00:00:00+00:00"
                    ),
                    u=1,
                    proposed=quote,
                )
            ],
            identity_mode=(
                "price_quantity"
            ),
        )

        summary = result["summary"]

        self.assertEqual(
            summary[
                "not_observed_ordered_all_states"
            ],
            2,
        )

        self.assertNotIn(
            "failed",
            summary,
        )

    def test_missing_u_records_are_excluded(self):
        quote = state()

        result = analyze_quote_lineage(
            [
                record(
                    timestamp=(
                        "2026-09-05T00:00:00+00:00"
                    ),
                    u=None,
                    proposed=quote,
                )
            ],
            identity_mode=(
                "price_quantity"
            ),
        )

        self.assertEqual(
            result["summary"][
                "records_missing_U"
            ],
            1,
        )

        self.assertEqual(
            result["summary"][
                "proposed_candidates"
            ],
            0,
        )

    def test_remaining_capture_time_is_recorded(self):
        quote = state()

        result = analyze_quote_lineage(
            [
                record(
                    timestamp=(
                        "2026-09-05T00:00:00+00:00"
                    ),
                    u=1,
                    proposed=quote,
                )
            ],
            identity_mode=(
                "price_quantity"
            ),
            capture_end_utc=(
                "2026-09-05T00:00:01+00:00"
            ),
        )

        self.assertEqual(
            result["rows"][0][
                "remaining_capture_ms"
            ],
            1000.0,
        )


    def test_preexisting_later_state_is_not_progression(self):
        quote = state()

        records = [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=1,
                voted=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.100000+00:00"
                ),
                u=1,
                proposed=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.200000+00:00"
                ),
                u=1,
                voted=quote,
                finalized=quote,
                committed=quote,
            ),
        ]

        result = analyze_quote_lineage(
            records,
            identity_mode="price",
        )

        self.assertEqual(
            result["summary"][
                "preexisting_later_state_candidates"
            ],
            2,
        )

        self.assertEqual(
            result["summary"][
                "observed_later_progressions"
            ],
            0,
        )

    def test_capture_start_candidate_is_not_evaluable(self):
        quote = state()

        records = [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=1,
                proposed=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.500000+00:00"
                ),
                u=1,
                voted=quote,
                finalized=quote,
                committed=quote,
            ),
        ]

        result = analyze_quote_lineage(
            records,
            identity_mode="price",
            capture_end_utc=(
                "2026-09-05T00:00:02+00:00"
            ),
        )

        self.assertEqual(
            result["summary"][
                "capture_start_candidates"
            ],
            2,
        )

        self.assertEqual(
            result["summary"][
                "evaluable_candidates"
            ],
            0,
        )

    def test_short_followup_is_right_censored(self):
        quote = state()

        records = [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=99,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.900000+00:00"
                ),
                u=1,
                proposed=quote,
            ),
        ]

        result = analyze_quote_lineage(
            records,
            identity_mode="price",
            capture_end_utc=(
                "2026-09-05T00:00:01+00:00"
            ),
            minimum_followup_ms=500.0,
        )

        self.assertEqual(
            result["summary"][
                "right_censored_candidates"
            ],
            2,
        )

        self.assertEqual(
            result["summary"][
                "evaluable_candidates"
            ],
            0,
        )

    def test_negative_followup_window_is_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            analyze_quote_lineage(
                [],
                identity_mode="price",
                minimum_followup_ms=-1,
            )


    def test_reentry_creates_distinct_episodes_and_is_ambiguous(self):
        quote = state()

        different = state(
            bid_price="90",
            bid_qty="5",
            ask_price="110",
            ask_qty="6",
        )

        records = [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=99,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.100000+00:00"
                ),
                u=1,
                proposed=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.200000+00:00"
                ),
                u=1,
                proposed=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.300000+00:00"
                ),
                u=1,
                proposed=different,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.400000+00:00"
                ),
                u=1,
                proposed=quote,
            ),
        ]

        result = analyze_quote_lineage(
            records,
            identity_mode=(
                "price_quantity"
            ),
            capture_end_utc=(
                "2026-09-05T00:00:02+00:00"
            ),
        )

        matching_bid_rows = [
            row
            for row in result["rows"]
            if (
                row["side"] == "bid"
                and row["identity"]
                == ("100", "10")
            )
        ]

        self.assertEqual(
            len(matching_bid_rows),
            2,
        )

        self.assertTrue(
            all(
                row[
                    "reentry_ambiguous"
                ]
                for row in matching_bid_rows
            )
        )

        self.assertTrue(
            all(
                not row["evaluable"]
                for row in matching_bid_rows
            )
        )

    def test_complete_lineage_near_capture_end_is_not_censored(self):
        quote = state()

        records = [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=99,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.900000+00:00"
                ),
                u=1,
                proposed=quote,
                voted=quote,
                finalized=quote,
                committed=quote,
            ),
        ]

        result = analyze_quote_lineage(
            records,
            identity_mode="price",
            capture_end_utc=(
                "2026-09-05T00:00:01+00:00"
            ),
            minimum_followup_ms=500.0,
        )

        quote_rows = [
            row
            for row in result["rows"]
            if row["U"] == 1
        ]

        self.assertEqual(
            len(quote_rows),
            2,
        )

        self.assertTrue(
            all(
                not row[
                    "right_censored"
                ]
                for row in quote_rows
            )
        )

        self.assertTrue(
            all(
                row[
                    "observed_ordered_all_states"
                ]
                for row in quote_rows
            )
        )

    def test_single_episode_can_be_evaluable(self):
        quote = state()

        records = [
            record(
                timestamp=(
                    "2026-09-05T00:00:00+00:00"
                ),
                u=99,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.100000+00:00"
                ),
                u=1,
                proposed=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.200000+00:00"
                ),
                u=1,
                voted=quote,
            ),
            record(
                timestamp=(
                    "2026-09-05T00:00:00.300000+00:00"
                ),
                u=1,
                finalized=quote,
                committed=quote,
            ),
        ]

        result = analyze_quote_lineage(
            records,
            identity_mode="price",
            capture_end_utc=(
                "2026-09-05T00:00:02+00:00"
            ),
        )

        self.assertEqual(
            result["summary"][
                "evaluable_observed_ordered_all_states"
            ],
            2,
        )

        self.assertEqual(
            result["summary"][
                "evaluable_observed_later_progressions"
            ],
            2,
        )


if __name__ == "__main__":
    unittest.main()
