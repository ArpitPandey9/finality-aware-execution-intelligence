from __future__ import annotations

import unittest
from decimal import Decimal

from finality_intelligence.alignment import (
    INSUFFICIENT_SOURCE_EVIDENCE,
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
)
from finality_intelligence.top_of_book import (
    ECONOMICALLY_ELIGIBLE,
    INVALID_REFERENCE_TOP,
    INVALID_STATE_PANEL,
    STATE_ORDER,
    analyze_capture_top_of_book,
)


def state(
    bid: str = "25000000000000000",
    ask: str = "25200000000000000",
) -> dict:
    return {
        "best_bid_raw": bid,
        "best_ask_raw": ask,
        "best_bid_quantity_raw": "10000000000000",
        "best_ask_quantity_raw": "10000000000000",
    }


def kuru_record(ns: int) -> dict:
    return {
        "received_at_utc": "2026-09-06T00:00:01+00:00",
        "received_monotonic_ns": ns,
        "U": 123,
        "states": {
            name: state()
            for name in STATE_ORDER
        },
    }


def cb_record(
    ns: int,
    *,
    bid="0.0250",
    offer="0.0252",
) -> dict:
    return {
        "channel": "l2_data",
        "target_event_types": ["snapshot"],
        "snapshot_events": 1,
        "received_at_utc": "2026-09-06T00:00:00+00:00",
        "received_monotonic_ns": ns,
        "sequence_num": 0,
        "target_product_id": "MON-USD",
        "book_top_after": {
            "best_bid": bid,
            "best_bid_quantity": "10",
            "best_offer": offer,
            "best_offer_quantity": "11",
            "spread": "0.0002",
        },
        "crossed_or_locked": False,
    }


def capture(
    kuru_ns: int = 1_000_000_000,
    cb_ns: int = 900_000_000,
) -> dict:
    return {
        "schema_version": "phase0.dual_ws_capture.v1",
        "gate": {"overall": "PASS"},
        "sources": {
            "kuru": {
                "error": None,
                "market": "MON_USDC",
                "records": [kuru_record(kuru_ns)],
            },
            "coinbase": {
                "error": None,
                "market": "MON-USD",
                "channel": "level2",
                "records": [cb_record(cb_ns)],
            },
        },
    }


class TestTopOfBookAnalysis(unittest.TestCase):
    def analyze(self, source: dict, max_age_ms=500) -> dict:
        return analyze_capture_top_of_book(
            source,
            capture_id="capture-a",
            max_age_ms=max_age_ms,
        )

    def test_complete_panel_emits_four_rows_with_same_reference(self):
        result = self.analyze(capture())

        self.assertEqual(result["summary"]["economic_rows"], 4)
        self.assertEqual(
            result["summary"]["eligibility_counts"][ECONOMICALLY_ELIGIBLE],
            1,
        )
        self.assertEqual(
            [row["state"] for row in result["rows"]],
            list(STATE_ORDER),
        )
        self.assertEqual(
            {row["coinbase_record_index"] for row in result["rows"]},
            {0},
        )
        self.assertEqual(
            {row["coinbase_sequence_num"] for row in result["rows"]},
            {0},
        )

    def test_metric_values_use_exact_decimal_arithmetic(self):
        source = capture()
        source["sources"]["kuru"]["records"][0]["states"]["proposed"] = state(
            "25200000000000000",
            "25400000000000000",
        )

        result = self.analyze(source)
        row = result["rows"][0]

        self.assertEqual(Decimal(row["kuru_best_bid"]), Decimal("0.0252"))
        self.assertEqual(Decimal(row["kuru_best_ask"]), Decimal("0.0254"))
        self.assertEqual(Decimal(row["kuru_midpoint"]), Decimal("0.0253"))
        self.assertEqual(Decimal(row["coinbase_midpoint"]), Decimal("0.0251"))
        self.assertEqual(
            Decimal(row["reference_mid_difference"]),
            Decimal("0.0002"),
        )
        self.assertEqual(
            Decimal(row["reference_mid_difference_bps"]),
            Decimal("0.0002") / Decimal("0.0251") * Decimal("10000"),
        )

    def test_stale_reference_is_counted_without_economic_rows(self):
        source = capture(
            kuru_ns=1_000_000_000,
            cb_ns=400_000_000,
        )

        result = self.analyze(source, max_age_ms=500)

        self.assertEqual(result["summary"]["economic_rows"], 0)
        self.assertEqual(
            result["summary"]["eligibility_counts"][STALE_REFERENCE],
            1,
        )

    def test_no_prior_reference_is_counted_without_economic_rows(self):
        result = self.analyze(
            capture(
                kuru_ns=1_000_000_000,
                cb_ns=1_100_000_000,
            )
        )

        self.assertEqual(result["summary"]["economic_rows"], 0)
        self.assertEqual(
            result["summary"]["eligibility_counts"][NO_PRIOR_REFERENCE],
            1,
        )

    def test_missing_state_invalidates_complete_panel(self):
        source = capture()
        del source["sources"]["kuru"]["records"][0]["states"]["committed"]

        result = self.analyze(source)

        self.assertEqual(result["summary"]["economic_rows"], 0)
        self.assertEqual(
            result["summary"]["eligibility_counts"][INVALID_STATE_PANEL],
            1,
        )

    def test_crossed_kuru_state_invalidates_complete_panel(self):
        source = capture()
        source["sources"]["kuru"]["records"][0]["states"]["voted"] = state(
            "25300000000000000",
            "25200000000000000",
        )

        result = self.analyze(source)

        self.assertEqual(result["summary"]["economic_rows"], 0)
        self.assertEqual(
            result["summary"]["eligibility_counts"][INVALID_STATE_PANEL],
            1,
        )

    def test_invalid_coinbase_top_is_auditable_exclusion(self):
        source = capture()
        source["sources"]["coinbase"]["records"][0]["book_top_after"][
            "best_bid"
        ] = "not-a-number"

        result = self.analyze(source)

        self.assertEqual(result["summary"]["economic_rows"], 0)
        self.assertEqual(
            result["summary"]["eligibility_counts"][INVALID_REFERENCE_TOP],
            1,
        )

    def test_float_coinbase_price_is_rejected(self):
        source = capture()
        source["sources"]["coinbase"]["records"][0]["book_top_after"][
            "best_bid"
        ] = 0.025

        result = self.analyze(source)

        self.assertEqual(result["summary"]["economic_rows"], 0)
        self.assertEqual(
            result["summary"]["eligibility_counts"][INVALID_REFERENCE_TOP],
            1,
        )

    def test_source_evidence_failure_produces_no_economic_rows(self):
        source = capture()
        source["sources"]["kuru"]["market"] = "WRONG_MARKET"

        result = self.analyze(source)

        self.assertEqual(result["summary"]["economic_rows"], 0)
        self.assertEqual(
            result["summary"]["eligibility_counts"][
                INSUFFICIENT_SOURCE_EVIDENCE
            ],
            1,
        )


    def test_provenance_and_claim_boundaries_are_preserved(self):
        result = self.analyze(capture(), max_age_ms=500)
        row = result["rows"][0]

        self.assertEqual(row["capture_id"], "capture-a")
        self.assertEqual(row["freshness_threshold_ms"], "500")
        self.assertEqual(row["kuru_record_index"], 0)
        self.assertEqual(
            row["kuru_received_monotonic_ns"],
            1_000_000_000,
        )
        self.assertEqual(row["U"], 123)

        self.assertEqual(row["coinbase_record_index"], 0)
        self.assertEqual(row["coinbase_sequence_num"], 0)
        self.assertEqual(
            row["coinbase_received_monotonic_ns"],
            900_000_000,
        )
        self.assertEqual(row["reference_age_ms"], "100")
        self.assertEqual(row["alignment_status"], "ALIGNED")

        self.assertEqual(len(result["claim_boundaries"]), 4)
        rendered = " ".join(result["claim_boundaries"])

        self.assertIn("distinct markets", rendered)
        self.assertIn("USD/USDC basis risk", rendered)
        self.assertIn("not automatically arbitrage", rendered)
        self.assertIn("not network", rendered)
        self.assertIn("observed stream grouping field", rendered)


if __name__ == "__main__":
    unittest.main()
