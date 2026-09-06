from __future__ import annotations

import unittest

from finality_intelligence.alignment import (
    ALIGNED,
    INSUFFICIENT_SOURCE_EVIDENCE,
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
    align_dual_capture,
)


def top(bid: str = "100", offer: str = "101") -> dict:
    return {
        "best_bid": bid,
        "best_bid_quantity": "10",
        "best_offer": offer,
        "best_offer_quantity": "11",
        "spread": str(int(offer) - int(bid)),
    }


def cb_record(
    ns: int,
    seq: int,
    *,
    snapshot: bool = False,
) -> dict:
    return {
        "channel": "l2_data",
        "target_event_types": ["snapshot" if snapshot else "update"],
        "snapshot_events": 1 if snapshot else 0,
        "received_at_utc": "2026-09-06T00:00:00+00:00",
        "received_monotonic_ns": ns,
        "sequence_num": seq,
        "target_product_id": "MON-USD",
        "book_top_after": top(),
        "crossed_or_locked": False,
    }


def kuru_record(ns: int, update_id: int = 1) -> dict:
    states = {
        state: {"best_bid_raw": "100", "best_ask_raw": "101"}
        for state in ("proposed", "voted", "finalized", "committed")
    }

    return {
        "received_at_utc": "2026-09-06T00:00:00+00:00",
        "received_monotonic_ns": ns,
        "U": update_id,
        "states": states,
    }


def capture(
    kuru_times: list[int],
    coinbase: list[dict],
    *,
    gate: str = "PASS",
) -> dict:
    return {
        "schema_version": "phase0.dual_ws_capture.v1",
        "gate": {"overall": gate},
        "sources": {
            "kuru": {
                "error": None,
                "market": "MON_USDC",
                "records": [
                    kuru_record(ns, index + 1)
                    for index, ns in enumerate(kuru_times)
                ],
            },
            "coinbase": {
                "error": None,
                "market": "MON-USD",
                "channel": "level2",
                "records": coinbase,
            },
        },
    }


class TestPointInTimeAlignment(unittest.TestCase):
    def test_latest_prior_reference_is_selected(self):
        result = align_dual_capture(
            capture(
                [100_000_000],
                [
                    cb_record(10_000_000, 0, snapshot=True),
                    cb_record(90_000_000, 1),
                    cb_record(110_000_000, 2),
                ],
            ),
            capture_id="capture-a",
            max_age_ms=20,
        )

        row = result["rows"][0]
        self.assertEqual(row["status"], ALIGNED)
        self.assertEqual(row["coinbase_reference"]["record_index"], 1)
        self.assertEqual(row["reference_age_ms"], "10")

    def test_future_reference_is_never_used(self):
        result = align_dual_capture(
            capture([50], [cb_record(100, 0, snapshot=True)]),
            capture_id="capture-a",
            max_age_ms=100,
        )

        self.assertEqual(
            result["rows"][0]["status"],
            NO_PRIOR_REFERENCE,
        )

    def test_equal_timestamp_is_eligible(self):
        result = align_dual_capture(
            capture([100], [cb_record(100, 0, snapshot=True)]),
            capture_id="capture-a",
            max_age_ms=0,
        )
        self.assertEqual(result["rows"][0]["status"], ALIGNED)

    def test_equal_time_tie_uses_later_record_index(self):
        result = align_dual_capture(
            capture(
                [100],
                [
                    cb_record(100, 0, snapshot=True),
                    cb_record(100, 1),
                ],
            ),
            capture_id="capture-a",
            max_age_ms=0,
        )
        self.assertEqual(
            result["rows"][0]["coinbase_reference"]["record_index"],
            1,
        )

    def test_reference_over_max_age_is_stale(self):
        result = align_dual_capture(
            capture(
                [11_000_001],
                [cb_record(10_000_000, 0, snapshot=True)],
            ),
            capture_id="capture-a",
            max_age_ms=1,
        )
        self.assertEqual(
            result["rows"][0]["status"],
            STALE_REFERENCE,
        )

    def test_reference_at_max_age_is_aligned(self):
        result = align_dual_capture(
            capture(
                [11_000_000],
                [cb_record(10_000_000, 0, snapshot=True)],
            ),
            capture_id="capture-a",
            max_age_ms=1,
        )
        self.assertEqual(result["rows"][0]["status"], ALIGNED)

    def test_failed_source_gate_preserves_insufficient_evidence(self):
        result = align_dual_capture(
            capture(
                [100],
                [cb_record(90, 0, snapshot=True)],
                gate="REVIEW",
            ),
            capture_id="capture-a",
            max_age_ms=10,
        )
        self.assertEqual(
            result["rows"][0]["status"],
            INSUFFICIENT_SOURCE_EVIDENCE,
        )

    def test_first_target_must_be_snapshot(self):
        result = align_dual_capture(
            capture([100], [cb_record(90, 0)]),
            capture_id="capture-a",
            max_age_ms=10,
        )
        self.assertEqual(
            result["rows"][0]["status"],
            INSUFFICIENT_SOURCE_EVIDENCE,
        )

    def test_same_reference_is_attached_to_four_state_message(self):
        result = align_dual_capture(
            capture([100], [cb_record(90, 0, snapshot=True)]),
            capture_id="capture-a",
            max_age_ms=10,
        )
        states = result["rows"][0]["kuru"]["states"]
        self.assertEqual(
            set(states),
            {"proposed", "voted", "finalized", "committed"},
        )

    def test_negative_max_age_is_rejected(self):
        with self.assertRaises(ValueError):
            align_dual_capture(
                capture([100], [cb_record(90, 0, snapshot=True)]),
                capture_id="capture-a",
                max_age_ms=-1,
            )

    def test_float_max_age_is_rejected(self):
        with self.assertRaises(TypeError):
            align_dual_capture(
                capture([100], [cb_record(90, 0, snapshot=True)]),
                capture_id="capture-a",
                max_age_ms=1.5,
            )


    def test_kuru_market_mismatch_is_insufficient_evidence(self):
        source = capture(
            [100],
            [cb_record(90, 0, snapshot=True)],
        )
        source["sources"]["kuru"]["market"] = "WRONG_MARKET"

        result = align_dual_capture(
            source,
            capture_id="capture-a",
            max_age_ms=1000,
        )

        self.assertEqual(
            result["rows"][0]["status"],
            INSUFFICIENT_SOURCE_EVIDENCE,
        )
        self.assertIn(
            "KURU_MARKET_MISMATCH",
            result["source_evidence_reasons"],
        )

    def test_coinbase_market_mismatch_is_insufficient_evidence(self):
        source = capture(
            [100],
            [cb_record(90, 0, snapshot=True)],
        )
        source["sources"]["coinbase"]["market"] = "WRONG-MARKET"

        result = align_dual_capture(
            source,
            capture_id="capture-a",
            max_age_ms=1000,
        )

        self.assertEqual(
            result["rows"][0]["status"],
            INSUFFICIENT_SOURCE_EVIDENCE,
        )
        self.assertIn(
            "COINBASE_MARKET_MISMATCH",
            result["source_evidence_reasons"],
        )

    def test_coinbase_channel_mismatch_is_insufficient_evidence(self):
        source = capture(
            [100],
            [cb_record(90, 0, snapshot=True)],
        )
        source["sources"]["coinbase"]["channel"] = "ticker"

        result = align_dual_capture(
            source,
            capture_id="capture-a",
            max_age_ms=1000,
        )

        self.assertEqual(
            result["rows"][0]["status"],
            INSUFFICIENT_SOURCE_EVIDENCE,
        )
        self.assertIn(
            "COINBASE_CHANNEL_MISMATCH",
            result["source_evidence_reasons"],
        )

    def test_coinbase_target_product_mismatch_is_insufficient_evidence(self):
        record = cb_record(90, 0, snapshot=True)
        record["target_product_id"] = "BTC-USD"

        result = align_dual_capture(
            capture([100], [record]),
            capture_id="capture-a",
            max_age_ms=1000,
        )

        self.assertEqual(
            result["rows"][0]["status"],
            INSUFFICIENT_SOURCE_EVIDENCE,
        )
        self.assertIn(
            "COINBASE_TARGET_PRODUCT_MISMATCH",
            result["source_evidence_reasons"],
        )


if __name__ == "__main__":
    unittest.main()
