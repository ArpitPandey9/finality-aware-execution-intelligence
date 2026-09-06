from __future__ import annotations

import unittest
from decimal import Decimal

from finality_intelligence.depth_execution import (
    BUY,
    SELL,
    FULLY_FILLED_IN_CAPTURED_BOOK,
    INSUFFICIENT_CAPTURED_DEPTH,
)
from finality_intelligence.depth_panel import (
    CLAIM_BOUNDARIES,
    EXECUTION_PANEL_ELIGIBLE,
    INSUFFICIENT_SOURCE_EVIDENCE,
    INVALID_EXECUTION_STATE_PANEL,
    SCHEMA_VERSION,
    STATE_ORDER,
    analyze_capture_depth_panels,
)


PRICE_SCALE = Decimal(
    "1000000000000000000"
)
SIZE_SCALE = Decimal(
    "10000000000"
)


def raw_price(value: str) -> str:
    return str(
        int(
            Decimal(value)
            * PRICE_SCALE
        )
    )


def raw_quantity(value: str) -> str:
    return str(
        int(
            Decimal(value)
            * SIZE_SCALE
        )
    )


def state_book() -> dict:
    return {
        "b": [
            [
                raw_price("1.0000"),
                raw_quantity("100"),
            ],
            [
                raw_price("0.9995"),
                raw_quantity("200"),
            ],
            [
                raw_price("0.9990"),
                raw_quantity("300"),
            ],
        ],
        "a": [
            [
                raw_price("1.0010"),
                raw_quantity("100"),
            ],
            [
                raw_price("1.0015"),
                raw_quantity("200"),
            ],
            [
                raw_price("1.0020"),
                raw_quantity("300"),
            ],
        ],
    }


def record(
    *,
    ns: int = 100,
    update_id: int = 10,
) -> dict:
    states = {
        state_name: state_book()
        for state_name in STATE_ORDER
    }

    return {
        "received_at_utc":
            "2026-09-06T00:00:00+00:00",
        "received_monotonic_ns": ns,
        "U": update_id,
        "raw_message": {
            "states": states,
            "U": update_id,
        },
    }


def capture(
    *,
    records=None,
    gate: str = "PASS",
    market: str = "MON_USDC",
) -> dict:
    if records is None:
        records = [
            record()
        ]

    return {
        "gate": {
            "overall": gate,
        },
        "sources": {
            "kuru": {
                "market": market,
                "records": records,
            },
        },
    }


class TestDepthPanel(unittest.TestCase):
    def test_complete_panel_emits_four_state_execution_analysis(
        self,
    ):
        result = (
            analyze_capture_depth_panels(
                capture(),
                capture_id="capture-a.json",
            )
        )

        self.assertEqual(
            result["summary"][
                "eligible_panels"
            ],
            1,
        )

        panel = result["panels"][0]

        self.assertEqual(
            panel["status"],
            EXECUTION_PANEL_ELIGIBLE,
        )

        self.assertEqual(
            tuple(panel["states"]),
            STATE_ORDER,
        )

        proposed = panel[
            "states"
        ]["proposed"]

        self.assertEqual(
            proposed["sides"][BUY][
                "depth_within_bps"
            ]["5"],
            "300",
        )

        self.assertEqual(
            proposed["sides"][SELL][
                "depth_within_bps"
            ]["10"],
            "600",
        )

        self.assertEqual(
            proposed["sides"][BUY][
                "sweeps"
            ]["200"][
                "fillability_status"
            ],
            FULLY_FILLED_IN_CAPTURED_BOOK,
        )

        self.assertEqual(
            proposed["sides"][BUY][
                "sweeps"
            ]["2000"][
                "fillability_status"
            ],
            INSUFFICIENT_CAPTURED_DEPTH,
        )

    def test_provenance_is_preserved(self):
        result = (
            analyze_capture_depth_panels(
                capture(
                    records=[
                        record(
                            ns=123456,
                            update_id=77,
                        )
                    ]
                ),
                capture_id="source.json",
            )
        )

        panel = result["panels"][0]

        self.assertEqual(
            panel["capture_id"],
            "source.json",
        )
        self.assertEqual(
            panel["kuru_record_index"],
            0,
        )
        self.assertEqual(
            panel[
                "received_monotonic_ns"
            ],
            123456,
        )
        self.assertEqual(
            panel["U"],
            77,
        )

        sweep = panel[
            "states"
        ]["committed"][
            "sides"
        ][BUY]["sweeps"]["200"]

        self.assertEqual(
            sweep["best_price_raw"],
            raw_price("1.0010"),
        )
        self.assertEqual(
            sweep["best_quantity_raw"],
            raw_quantity("100"),
        )
        self.assertEqual(
            sweep["best_price"],
            "1.001",
        )
        self.assertEqual(
            sweep["best_quantity"],
            "100",
        )

    def test_missing_state_invalidates_complete_panel(
        self,
    ):
        source = capture()

        del source[
            "sources"
        ]["kuru"]["records"][0][
            "raw_message"
        ]["states"]["finalized"]

        result = (
            analyze_capture_depth_panels(
                source,
                capture_id="source.json",
            )
        )

        self.assertEqual(
            result["summary"][
                "panel_outcome_counts"
            ][
                INVALID_EXECUTION_STATE_PANEL
            ],
            1,
        )
        self.assertEqual(
            result["panels"],
            [],
        )

    def test_unordered_state_invalidates_complete_panel(
        self,
    ):
        source = capture()

        raw_book = source[
            "sources"
        ]["kuru"]["records"][0][
            "raw_message"
        ]["states"]["voted"]

        raw_book["b"][1][0] = (
            raw_price("1.0005")
        )

        result = (
            analyze_capture_depth_panels(
                source,
                capture_id="source.json",
            )
        )

        self.assertEqual(
            result["summary"][
                "panel_outcome_counts"
            ][
                INVALID_EXECUTION_STATE_PANEL
            ],
            1,
        )
        self.assertEqual(
            len(result["exclusions"]),
            1,
        )

    def test_missing_raw_message_invalidates_panel(
        self,
    ):
        source_record = record()
        del source_record["raw_message"]

        result = (
            analyze_capture_depth_panels(
                capture(
                    records=[
                        source_record
                    ]
                ),
                capture_id="source.json",
            )
        )

        self.assertEqual(
            result["summary"][
                "panel_outcome_counts"
            ][
                INVALID_EXECUTION_STATE_PANEL
            ],
            1,
        )

    def test_failed_source_gate_is_auditable(
        self,
    ):
        result = (
            analyze_capture_depth_panels(
                capture(
                    records=[
                        record(
                            update_id=1
                        ),
                        record(
                            update_id=2
                        ),
                    ],
                    gate="REVIEW",
                ),
                capture_id="source.json",
            )
        )

        self.assertEqual(
            result[
                "source_evidence_reasons"
            ],
            [
                "capture_gate_not_pass"
            ],
        )

        self.assertEqual(
            result["summary"][
                "panel_outcome_counts"
            ][
                INSUFFICIENT_SOURCE_EVIDENCE
            ],
            2,
        )

        self.assertEqual(
            result["panels"],
            [],
        )
        self.assertEqual(
            len(result["exclusions"]),
            2,
        )

    def test_market_mismatch_is_auditable(
        self,
    ):
        result = (
            analyze_capture_depth_panels(
                capture(
                    market="WRONG_MARKET",
                ),
                capture_id="source.json",
            )
        )

        self.assertIn(
            "kuru_market_identity_mismatch",
            result[
                "source_evidence_reasons"
            ],
        )

        self.assertEqual(
            result["summary"][
                "panel_outcome_counts"
            ][
                INSUFFICIENT_SOURCE_EVIDENCE
            ],
            1,
        )

        self.assertEqual(
            result["panels"],
            [],
        )

    def test_schema_and_claim_boundaries_are_preserved(
        self,
    ):
        result = (
            analyze_capture_depth_panels(
                capture(),
                capture_id="source.json",
            )
        )

        self.assertEqual(
            result["schema_version"],
            SCHEMA_VERSION,
        )

        self.assertEqual(
            result["claim_boundaries"],
            list(CLAIM_BOUNDARIES),
        )

        joined = " ".join(
            result["claim_boundaries"]
        ).lower()

        self.assertIn(
            "not temporal transitions",
            joined,
        )
        self.assertIn(
            "no execution",
            joined,
        )


if __name__ == "__main__":
    unittest.main()
