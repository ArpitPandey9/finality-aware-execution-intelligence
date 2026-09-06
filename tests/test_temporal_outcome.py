from __future__ import annotations

import unittest
from decimal import Decimal

from finality_intelligence.alignment import (
    STALE_REFERENCE,
)
from finality_intelligence.temporal_outcome import (
    COINBASE_RECONSTRUCTION_FAILURE,
    EVALUABLE,
    FROZEN_HORIZONS_MS,
    INVALID_KURU_PANEL,
    NOT_APPLICABLE_ZERO_CONTRAST,
    RIGHT_CENSORED_CAPTURE_END,
    SCHEMA_VERSION,
    analyze_temporal_capture,
    select_future_coinbase_record_index,
)


PRICE_SCALE = Decimal(
    "1000000000000000000"
)


def raw_price(
    value: str,
) -> str:
    parsed = Decimal(value)

    raw = (
        parsed
        * PRICE_SCALE
    )

    assert (
        raw
        == raw.to_integral_value()
    )

    return str(
        int(raw)
    )


def kuru_state(
    bid: str,
    ask: str,
) -> dict:
    return {
        "best_bid_raw":
            raw_price(bid),
        "best_ask_raw":
            raw_price(ask),
        "best_bid_quantity_raw":
            "10000000000000",
        "best_ask_quantity_raw":
            "10000000000000",
    }


def kuru_record(
    ns: int,
    *,
    proposed=(
        "1.03",
        "1.05",
    ),
    finalized=(
        "1.01",
        "1.03",
    ),
) -> dict:
    return {
        "received_at_utc":
            "2026-09-06T00:00:01+00:00",
        "received_monotonic_ns":
            ns,
        "U":
            123,
        "states": {
            "proposed":
                kuru_state(
                    *proposed
                ),
            "voted":
                kuru_state(
                    "1.02",
                    "1.04",
                ),
            "finalized":
                kuru_state(
                    *finalized
                ),
            "committed":
                kuru_state(
                    *finalized
                ),
        },
    }


def level(
    side: str,
    price: str,
    quantity: str,
) -> dict:
    return {
        "side":
            side,
        "price_level":
            price,
        "new_quantity":
            quantity,
        "event_time":
            "2026-09-06T00:00:00Z",
    }


def message(
    sequence_num: int,
    *,
    event_type: str,
    updates: list[dict],
) -> dict:
    return {
        "channel":
            "l2_data",
        "sequence_num":
            sequence_num,
        "timestamp":
            "2026-09-06T00:00:00Z",
        "events": [
            {
                "type":
                    event_type,
                "product_id":
                    "MON-USD",
                "updates":
                    updates,
            }
        ],
    }


def stored_record(
    raw_message: dict,
    *,
    received_ns: int,
    best_bid: str,
    best_offer: str,
    snapshot_events: int,
    update_events: int,
    target_updates: int,
    zero_quantity_updates: int,
) -> dict:
    spread = (
        Decimal(best_offer)
        - Decimal(best_bid)
    )

    event_type = (
        "snapshot"
        if snapshot_events
        else "update"
    )

    return {
        "raw_message":
            raw_message,
        "sequence_num":
            raw_message[
                "sequence_num"
            ],
        "channel":
            "l2_data",
        "received_at_utc":
            "2026-09-06T00:00:00+00:00",
        "received_monotonic_ns":
            received_ns,
        "timestamp":
            "2026-09-06T00:00:00Z",
        "target_product_id":
            "MON-USD",
        "target_event_types":
            [event_type],
        "snapshot_events":
            snapshot_events,
        "update_events":
            update_events,
        "target_updates":
            target_updates,
        "zero_quantity_updates":
            zero_quantity_updates,
        "book_top_after": {
            "best_bid":
                best_bid,
            "best_bid_quantity":
                "10",
            "best_offer":
                best_offer,
            "best_offer_quantity":
                "10",
            "spread":
                str(spread),
        },
        "bid_levels_after":
            1,
        "offer_levels_after":
            1,
        "crossed_or_locked":
            False,
    }


def snapshot_record(
    *,
    received_ns: int,
    sequence_num: int = 0,
    bid: str = "1.00",
    offer: str = "1.02",
) -> dict:
    raw = message(
        sequence_num,
        event_type="snapshot",
        updates=[
            level(
                "bid",
                bid,
                "10",
            ),
            level(
                "offer",
                offer,
                "10",
            ),
        ],
    )

    return stored_record(
        raw,
        received_ns=received_ns,
        best_bid=bid,
        best_offer=offer,
        snapshot_events=1,
        update_events=0,
        target_updates=2,
        zero_quantity_updates=0,
    )


def move_record(
    *,
    sequence_num: int,
    received_ns: int,
    old_bid: str,
    old_offer: str,
    new_bid: str,
    new_offer: str,
) -> dict:
    raw = message(
        sequence_num,
        event_type="update",
        updates=[
            level(
                "bid",
                old_bid,
                "0",
            ),
            level(
                "offer",
                old_offer,
                "0",
            ),
            level(
                "bid",
                new_bid,
                "10",
            ),
            level(
                "offer",
                new_offer,
                "10",
            ),
        ],
    )

    return stored_record(
        raw,
        received_ns=received_ns,
        best_bid=new_bid,
        best_offer=new_offer,
        snapshot_events=0,
        update_events=1,
        target_updates=4,
        zero_quantity_updates=2,
    )


def source_capture(
    *,
    kuru_ns: int = 1_000_000_000,
    coinbase_records: list[dict],
    proposed=(
        "1.03",
        "1.05",
    ),
    finalized=(
        "1.01",
        "1.03",
    ),
) -> dict:
    return {
        "schema_version":
            "phase0.dual_ws_capture.v1",
        "gate": {
            "overall":
                "PASS",
        },
        "sources": {
            "kuru": {
                "market":
                    "MON_USDC",
                "error":
                    None,
                "records": [
                    kuru_record(
                        kuru_ns,
                        proposed=proposed,
                        finalized=finalized,
                    )
                ],
            },
            "coinbase": {
                "market":
                    "MON-USD",
                "channel":
                    "level2",
                "error":
                    None,
                "records":
                    coinbase_records,
            },
        },
    }


def moving_capture() -> dict:
    return source_capture(
        coinbase_records=[
            snapshot_record(
                received_ns=
                    900_000_000,
            ),
            move_record(
                sequence_num=1,
                received_ns=
                    1_900_000_000,
                old_bid="1.00",
                old_offer="1.02",
                new_bid="1.02",
                new_offer="1.04",
            ),
            move_record(
                sequence_num=2,
                received_ns=
                    2_100_000_000,
                old_bid="1.02",
                old_offer="1.04",
                new_bid="1.03",
                new_offer="1.05",
            ),
        ],
    )


class TestTemporalOutcome(
    unittest.TestCase
):
    def analyze(
        self,
        source: dict,
        *,
        max_age_ms=250,
        horizon_ms=1000,
    ) -> dict:
        return analyze_temporal_capture(
            source,
            capture_id="capture-a",
            max_age_ms=max_age_ms,
            horizon_ms=horizon_ms,
        )

    def test_schema_and_frozen_horizons(
        self,
    ):
        self.assertEqual(
            SCHEMA_VERSION,
            "phase2.temporal_outcome.v1",
        )

        self.assertEqual(
            FROZEN_HORIZONS_MS,
            (
                Decimal("250"),
                Decimal("1000"),
                Decimal("5000"),
                Decimal("10000"),
            ),
        )

    def test_baseline_uses_phase1_alignment(
        self,
    ):
        result = self.analyze(
            moving_capture(),
            max_age_ms=50,
        )

        row = result["rows"][0]

        self.assertEqual(
            row["status"],
            STALE_REFERENCE,
        )

        self.assertEqual(
            row["alignment_status"],
            STALE_REFERENCE,
        )

        self.assertIsNone(
            row[
                "coinbase_forward_mid_return_bps"
            ]
        )

    def test_future_asof_uses_latest_target_before_horizon(
        self,
    ):
        result = self.analyze(
            moving_capture(),
            horizon_ms=1000,
        )

        row = result["rows"][0]

        self.assertEqual(
            row["status"],
            EVALUABLE,
        )

        self.assertEqual(
            row[
                "baseline_coinbase_record_index"
            ],
            0,
        )

        self.assertEqual(
            row[
                "future_coinbase_record_index"
            ],
            1,
        )

        self.assertEqual(
            row[
                "future_horizon_monotonic_ns"
            ],
            2_000_000_000,
        )

    def test_first_target_after_horizon_is_never_used(
        self,
    ):
        source = source_capture(
            coinbase_records=[
                snapshot_record(
                    received_ns=
                        900_000_000,
                ),
                move_record(
                    sequence_num=1,
                    received_ns=
                        1_250_000_001,
                    old_bid="1.00",
                    old_offer="1.02",
                    new_bid="1.02",
                    new_offer="1.04",
                ),
            ],
        )

        result = self.analyze(
            source,
            horizon_ms=250,
        )

        row = result["rows"][0]

        self.assertEqual(
            row["status"],
            EVALUABLE,
        )

        self.assertEqual(
            row[
                "future_coinbase_record_index"
            ],
            0,
        )

        self.assertEqual(
            Decimal(
                row[
                    "coinbase_forward_mid_return_bps"
                ]
            ),
            Decimal("0"),
        )

    def test_equal_time_future_tie_uses_later_original_index(
        self,
    ):
        source = source_capture(
            coinbase_records=[
                snapshot_record(
                    received_ns=
                        900_000_000,
                ),
                move_record(
                    sequence_num=1,
                    received_ns=
                        1_900_000_000,
                    old_bid="1.00",
                    old_offer="1.02",
                    new_bid="1.01",
                    new_offer="1.03",
                ),
                move_record(
                    sequence_num=2,
                    received_ns=
                        1_900_000_000,
                    old_bid="1.01",
                    old_offer="1.03",
                    new_bid="1.02",
                    new_offer="1.04",
                ),
                move_record(
                    sequence_num=3,
                    received_ns=
                        2_100_000_000,
                    old_bid="1.02",
                    old_offer="1.04",
                    new_bid="1.03",
                    new_offer="1.05",
                ),
            ],
        )

        result = self.analyze(
            source,
            horizon_ms=1000,
        )

        row = result["rows"][0]

        self.assertEqual(
            row[
                "future_coinbase_record_index"
            ],
            2,
        )

    def test_selector_uses_target_record_only(
        self,
    ):
        records = (
            moving_capture()[
                "sources"
            ][
                "coinbase"
            ][
                "records"
            ]
        )

        self.assertEqual(
            select_future_coinbase_record_index(
                records,
                horizon_monotonic_ns=
                    2_000_000_000,
            ),
            1,
        )

    def test_unchanged_book_is_valid_state(
        self,
    ):
        source = source_capture(
            coinbase_records=[
                snapshot_record(
                    received_ns=
                        900_000_000,
                ),
                move_record(
                    sequence_num=1,
                    received_ns=
                        1_500_000_000,
                    old_bid="1.00",
                    old_offer="1.02",
                    new_bid="1.02",
                    new_offer="1.04",
                ),
            ],
        )

        result = self.analyze(
            source,
            horizon_ms=250,
        )

        row = result["rows"][0]

        self.assertEqual(
            row[
                "baseline_coinbase_record_index"
            ],
            row[
                "future_coinbase_record_index"
            ],
        )

        self.assertEqual(
            Decimal(
                row[
                    "coinbase_forward_mid_return_bps"
                ]
            ),
            Decimal("0"),
        )

    def test_capture_end_is_right_censored(
        self,
    ):
        source = source_capture(
            coinbase_records=[
                snapshot_record(
                    received_ns=
                        900_000_000,
                ),
            ],
        )

        result = self.analyze(
            source,
            horizon_ms=250,
        )

        row = result["rows"][0]

        self.assertEqual(
            row["status"],
            RIGHT_CENSORED_CAPTURE_END,
        )

        self.assertIsNone(
            row[
                "future_coinbase_record_index"
            ]
        )

    def test_invalid_kuru_four_state_panel_is_explicit(
        self,
    ):
        source = moving_capture()

        del (
            source[
                "sources"
            ][
                "kuru"
            ][
                "records"
            ][0][
                "states"
            ][
                "committed"
            ]
        )

        result = self.analyze(
            source
        )

        self.assertEqual(
            result[
                "rows"
            ][0][
                "status"
            ],
            INVALID_KURU_PANEL,
        )

    def test_exact_decimal_forward_return(
        self,
    ):
        result = self.analyze(
            moving_capture(),
            horizon_ms=1000,
        )

        row = result["rows"][0]

        expected = (
            (
                Decimal("1.03")
                / Decimal("1.01")
            )
            - Decimal("1")
        ) * Decimal("10000")

        self.assertEqual(
            Decimal(
                row[
                    "baseline_coinbase_midpoint"
                ]
            ),
            Decimal("1.01"),
        )

        self.assertEqual(
            Decimal(
                row[
                    "future_coinbase_midpoint"
                ]
            ),
            Decimal("1.03"),
        )

        self.assertEqual(
            Decimal(
                row[
                    "coinbase_forward_mid_return_bps"
                ]
            ),
            expected,
        )

    def test_proposed_finalized_contrast_is_exact(
        self,
    ):
        result = self.analyze(
            moving_capture(),
            horizon_ms=1000,
        )

        row = result["rows"][0]

        expected = (
            (
                Decimal("1.04")
                / Decimal("1.02")
            )
            - Decimal("1")
        ) * Decimal("10000")

        self.assertEqual(
            Decimal(
                row[
                    "kuru_proposed_midpoint"
                ]
            ),
            Decimal("1.04"),
        )

        self.assertEqual(
            Decimal(
                row[
                    "kuru_finalized_midpoint"
                ]
            ),
            Decimal("1.02"),
        )

        self.assertEqual(
            Decimal(
                row[
                    "kuru_proposed_finalized_mid_gap_bps"
                ]
            ),
            expected,
        )

        self.assertEqual(
            row[
                "contrast_sign"
            ],
            "POSITIVE",
        )

    def test_directional_concordance_uses_contrast_sign(
        self,
    ):
        result = self.analyze(
            moving_capture(),
            horizon_ms=1000,
        )

        row = result["rows"][0]

        self.assertEqual(
            Decimal(
                row[
                    "directional_concordance_bps"
                ]
            ),
            Decimal(
                row[
                    "coinbase_forward_mid_return_bps"
                ]
            ),
        )

    def test_zero_contrast_is_not_applicable(
        self,
    ):
        source = moving_capture()

        record = (
            source[
                "sources"
            ][
                "kuru"
            ][
                "records"
            ][0]
        )

        record[
            "states"
        ][
            "proposed"
        ] = kuru_state(
            "1.01",
            "1.03",
        )

        result = self.analyze(
            source,
            horizon_ms=1000,
        )

        row = result["rows"][0]

        self.assertEqual(
            Decimal(
                row[
                    "kuru_proposed_finalized_mid_gap_bps"
                ]
            ),
            Decimal("0"),
        )

        self.assertEqual(
            row[
                "directional_concordance_status"
            ],
            NOT_APPLICABLE_ZERO_CONTRAST,
        )

        self.assertIsNone(
            row[
                "directional_concordance_bps"
            ]
        )

    def test_one_panel_emits_one_temporal_row(
        self,
    ):
        result = self.analyze(
            moving_capture()
        )

        self.assertEqual(
            len(
                result[
                    "rows"
                ]
            ),
            1,
        )

    def test_non_frozen_horizon_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            self.analyze(
                moving_capture(),
                horizon_ms=2000,
            )

    def test_float_horizon_is_rejected(
        self,
    ):
        with self.assertRaises(
            TypeError
        ):
            self.analyze(
                moving_capture(),
                horizon_ms=250.0,
            )

    def test_reconstruction_failure_is_explicit(
        self,
    ):
        source = moving_capture()

        source[
            "sources"
        ][
            "coinbase"
        ][
            "records"
        ][1][
            "book_top_after"
        ][
            "best_bid"
        ] = "9.99"

        result = self.analyze(
            source,
            horizon_ms=1000,
        )

        self.assertEqual(
            result[
                "rows"
            ][0][
                "status"
            ],
            COINBASE_RECONSTRUCTION_FAILURE,
        )

    def test_claim_boundaries_are_preserved(
        self,
    ):
        result = self.analyze(
            moving_capture()
        )

        rendered = " ".join(
            result[
                "claim_boundaries"
            ]
        ).lower()

        self.assertIn(
            "not prediction",
            rendered,
        )

        self.assertIn(
            "not alpha",
            rendered,
        )

        self.assertIn(
            "not arbitrage",
            rendered,
        )

        self.assertIn(
            "not causal",
            rendered,
        )

        self.assertIn(
            "not a win rate",
            rendered,
        )


if __name__ == "__main__":
    unittest.main()
