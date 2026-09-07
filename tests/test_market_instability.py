from __future__ import annotations

import unittest
from unittest.mock import patch

from finality_intelligence import (
    market_instability as phase3,
)
from finality_intelligence.temporal_outcome import (
    EVALUABLE,
    RIGHT_CENSORED_CAPTURE_END,
)


def temporal_result(
    *,
    status=EVALUABLE,
    gap="-2.5",
    forward="-4",
):
    row = {
        "capture_id": "capture-a",
        "freshness_threshold_ms": "250",
        "horizon_ms": "1000",
        "kuru_record_index": 7,
        "kuru_received_at_utc":
            "2026-09-07T12:00:00Z",
        "kuru_received_monotonic_ns":
            1_000_000_000,
        "U": 10,
        "alignment_status": "ALIGNED",
        "alignment_status_reason": [],
        "reference_age_ms": "10",
        "future_horizon_monotonic_ns":
            2_000_000_000,
        "future_asof_age_ms": "5",
        "status": status,
        "status_reason": [],
        "kuru_proposed_finalized_mid_gap_bps":
            gap,
        "coinbase_forward_mid_return_bps":
            forward,
    }

    return {
        "schema_version":
            "phase2.temporal_outcome.v1",
        "capture_id":
            "capture-a",
        "freshness_threshold_ms":
            "250",
        "horizon_ms":
            "1000",
        "source_evidence_reasons":
            [],
        "rows":
            [row],
    }


class TestMarketInstability(
    unittest.TestCase
):
    def test_evaluable_row_uses_absolute_magnitudes(
        self,
    ):
        with patch.object(
            phase3,
            "analyze_temporal_capture",
            return_value=temporal_result(),
        ) as mocked:
            result = (
                phase3
                .analyze_market_instability_capture(
                    {},
                    capture_id="capture-a",
                    max_age_ms="250",
                    horizon_ms="1000",
                )
            )

        mocked.assert_called_once_with(
            {},
            capture_id="capture-a",
            max_age_ms="250",
            horizon_ms="1000",
        )

        row = result["rows"][0]

        self.assertEqual(
            row["kuru_pf_gap_bps"],
            "-2.5",
        )
        self.assertEqual(
            row["kuru_pf_abs_gap_bps"],
            "2.5",
        )
        self.assertEqual(
            row["coinbase_forward_mid_return_bps"],
            "-4",
        )
        self.assertEqual(
            row[
                "coinbase_abs_forward_mid_move_bps"
            ],
            "4",
        )

    def test_zero_exposure_remains_evaluable(
        self,
    ):
        source = temporal_result(
            gap="0",
            forward="3",
        )

        with patch.object(
            phase3,
            "analyze_temporal_capture",
            return_value=source,
        ):
            result = (
                phase3
                .analyze_market_instability_capture(
                    {},
                    capture_id="capture-a",
                    max_age_ms="250",
                    horizon_ms="1000",
                )
            )

        self.assertEqual(
            result["summary"][
                "zero_exposure_count"
            ],
            1,
        )
        self.assertEqual(
            result["summary"][
                "evaluable"
            ],
            1,
        )

    def test_non_evaluable_row_has_no_phase3_economics(
        self,
    ):
        source = temporal_result(
            status=RIGHT_CENSORED_CAPTURE_END,
        )

        with patch.object(
            phase3,
            "analyze_temporal_capture",
            return_value=source,
        ):
            result = (
                phase3
                .analyze_market_instability_capture(
                    {},
                    capture_id="capture-a",
                    max_age_ms="250",
                    horizon_ms="1000",
                )
            )

        row = result["rows"][0]

        for field in (
            phase3.PHASE3_ECONOMIC_FIELDS
        ):
            self.assertIsNone(
                row[field]
            )

    def test_source_evidence_reasons_are_preserved(
        self,
    ):
        source = temporal_result()
        source[
            "source_evidence_reasons"
        ] = [
            "SYNTHETIC_REASON"
        ]

        with patch.object(
            phase3,
            "analyze_temporal_capture",
            return_value=source,
        ):
            result = (
                phase3
                .analyze_market_instability_capture(
                    {},
                    capture_id="capture-a",
                    max_age_ms="250",
                    horizon_ms="1000",
                )
            )

        self.assertEqual(
            result[
                "source_evidence_reasons"
            ],
            [
                "SYNTHETIC_REASON"
            ],
        )

    def test_wrong_temporal_schema_is_rejected(
        self,
    ):
        source = temporal_result()
        source["schema_version"] = "wrong"

        with patch.object(
            phase3,
            "analyze_temporal_capture",
            return_value=source,
        ):
            with self.assertRaises(
                ValueError
            ):
                (
                    phase3
                    .analyze_market_instability_capture(
                        {},
                        capture_id="capture-a",
                        max_age_ms="250",
                        horizon_ms="1000",
                    )
                )


if __name__ == "__main__":
    unittest.main()
