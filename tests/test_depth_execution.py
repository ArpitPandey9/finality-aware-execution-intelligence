from __future__ import annotations

import unittest
from decimal import Decimal

from finality_intelligence.depth_execution import (
    BUY,
    SELL,
    DEPTH_BANDS_BPS,
    FULLY_FILLED_IN_CAPTURED_BOOK,
    INSUFFICIENT_CAPTURED_DEPTH,
    TARGET_BASE_QUANTITIES,
    depth_within_bps,
    sweep_base_quantity,
    total_captured_depth,
    validate_and_normalize_book,
)


P = Decimal("1000000000000000000")
Q = Decimal("10000000000")


def raw_price(value: str) -> str:
    return str(
        int(
            Decimal(value)
            * P
        )
    )


def raw_quantity(value: str) -> str:
    return str(
        int(
            Decimal(value)
            * Q
        )
    )


def book(
    *,
    bids=None,
    asks=None,
):
    if bids is None:
        bids = [
            ("1.0000", "100"),
            ("0.9995", "200"),
            ("0.9990", "300"),
        ]

    if asks is None:
        asks = [
            ("1.0010", "100"),
            ("1.0015", "200"),
            ("1.0020", "300"),
        ]

    return {
        "b": [
            [
                raw_price(price),
                raw_quantity(quantity),
            ]
            for price, quantity in bids
        ],
        "a": [
            [
                raw_price(price),
                raw_quantity(quantity),
            ]
            for price, quantity in asks
        ],
    }


class TestDepthExecution(unittest.TestCase):
    def test_frozen_methodology_constants(self):
        self.assertEqual(
            DEPTH_BANDS_BPS,
            (
                Decimal("5"),
                Decimal("10"),
                Decimal("25"),
                Decimal("50"),
            ),
        )

        self.assertEqual(
            TARGET_BASE_QUANTITIES,
            (
                Decimal("200"),
                Decimal("2000"),
                Decimal("20000"),
                Decimal("200000"),
            ),
        )

    def test_valid_book_normalizes_exactly(self):
        result = validate_and_normalize_book(
            book()
        )

        self.assertEqual(
            result["best_bid"],
            Decimal("1"),
        )
        self.assertEqual(
            result["best_ask"],
            Decimal("1.001"),
        )
        self.assertEqual(
            result["bids"][0]["quantity"],
            Decimal("100"),
        )

    def test_level_must_contain_exactly_two_fields(self):
        source = book()
        source["b"][0].append("extra")

        with self.assertRaises(ValueError):
            validate_and_normalize_book(
                source
            )

    def test_decimal_raw_string_is_rejected(self):
        source = book()
        source["b"][0][0] = "1.0"

        with self.assertRaises(ValueError):
            validate_and_normalize_book(
                source
            )

    def test_zero_price_is_rejected(self):
        source = book()
        source["b"][0][0] = "0"

        with self.assertRaises(ValueError):
            validate_and_normalize_book(
                source
            )

    def test_zero_quantity_is_rejected(self):
        source = book()
        source["b"][0][1] = "0"

        with self.assertRaises(ValueError):
            validate_and_normalize_book(
                source
            )

    def test_bid_source_order_is_validated(self):
        source = book(
            bids=[
                ("1.0000", "100"),
                ("1.0005", "200"),
            ],
        )

        with self.assertRaises(ValueError):
            validate_and_normalize_book(
                source
            )

    def test_ask_source_order_is_validated(self):
        source = book(
            asks=[
                ("1.0010", "100"),
                ("1.0005", "200"),
            ],
        )

        with self.assertRaises(ValueError):
            validate_and_normalize_book(
                source
            )

    def test_crossed_book_is_rejected(self):
        source = book(
            bids=[
                ("1.0020", "100"),
            ],
            asks=[
                ("1.0010", "100"),
            ],
        )

        with self.assertRaises(ValueError):
            validate_and_normalize_book(
                source
            )

    def test_buy_depth_within_five_bps(self):
        source = book(
            asks=[
                ("1.0000", "100"),
                ("1.0005", "200"),
                ("1.0006", "300"),
            ],
        )

        normalized = (
            validate_and_normalize_book(
                source
            )
        )

        self.assertEqual(
            depth_within_bps(
                normalized,
                side=BUY,
                band_bps=Decimal("5"),
            ),
            Decimal("300"),
        )

    def test_sell_depth_within_ten_bps(self):
        source = book(
            bids=[
                ("1.0000", "100"),
                ("0.9990", "200"),
                ("0.9989", "300"),
            ],
        )

        normalized = (
            validate_and_normalize_book(
                source
            )
        )

        self.assertEqual(
            depth_within_bps(
                normalized,
                side=SELL,
                band_bps=Decimal("10"),
            ),
            Decimal("300"),
        )

    def test_non_frozen_band_is_rejected(self):
        normalized = (
            validate_and_normalize_book(
                book()
            )
        )

        with self.assertRaises(ValueError):
            depth_within_bps(
                normalized,
                side=BUY,
                band_bps=Decimal("7"),
            )

    def test_buy_sweep_partial_final_level(self):
        source = book(
            asks=[
                ("1.0000", "100"),
                ("1.0010", "500"),
            ],
        )

        normalized = (
            validate_and_normalize_book(
                source
            )
        )

        result = sweep_base_quantity(
            normalized,
            side=BUY,
            target_base=Decimal("200"),
        )

        expected_quote = (
            Decimal("100")
            * Decimal("1")
            + Decimal("100")
            * Decimal("1.001")
        )

        expected_vwap = (
            expected_quote
            / Decimal("200")
        )

        expected_slippage = (
            (
                expected_vwap
                / Decimal("1")
            )
            - Decimal("1")
        ) * Decimal("10000")

        self.assertEqual(
            result["fillability_status"],
            FULLY_FILLED_IN_CAPTURED_BOOK,
        )
        self.assertEqual(
            result["filled_base"],
            Decimal("200"),
        )
        self.assertEqual(
            result["levels_touched"],
            2,
        )
        self.assertTrue(
            result[
                "final_level_partially_consumed"
            ]
        )
        self.assertEqual(
            result["quote_amount"],
            expected_quote,
        )
        self.assertEqual(
            result["vwap"],
            expected_vwap,
        )
        self.assertEqual(
            result["slippage_bps"],
            expected_slippage,
        )

    def test_sell_sweep_vwap_and_slippage(self):
        source = book(
            bids=[
                ("1.0000", "100"),
                ("0.9990", "500"),
            ],
        )

        normalized = (
            validate_and_normalize_book(
                source
            )
        )

        result = sweep_base_quantity(
            normalized,
            side=SELL,
            target_base=Decimal("200"),
        )

        expected_quote = (
            Decimal("100")
            * Decimal("1")
            + Decimal("100")
            * Decimal("0.999")
        )

        expected_vwap = (
            expected_quote
            / Decimal("200")
        )

        expected_slippage = (
            Decimal("1")
            - (
                expected_vwap
                / Decimal("1")
            )
        ) * Decimal("10000")

        self.assertEqual(
            result["fillability_status"],
            FULLY_FILLED_IN_CAPTURED_BOOK,
        )
        self.assertEqual(
            result["vwap"],
            expected_vwap,
        )
        self.assertEqual(
            result["slippage_bps"],
            expected_slippage,
        )

    def test_insufficient_depth_has_no_full_target_vwap(self):
        source = book(
            asks=[
                ("1.0000", "50"),
                ("1.0010", "50"),
            ],
        )

        normalized = (
            validate_and_normalize_book(
                source
            )
        )

        result = sweep_base_quantity(
            normalized,
            side=BUY,
            target_base=Decimal("200"),
        )

        self.assertEqual(
            result["fillability_status"],
            INSUFFICIENT_CAPTURED_DEPTH,
        )
        self.assertEqual(
            result["filled_base"],
            Decimal("100"),
        )
        self.assertEqual(
            result["unfilled_base"],
            Decimal("100"),
        )
        self.assertIsNone(
            result["vwap"]
        )
        self.assertIsNone(
            result["slippage_bps"]
        )

    def test_non_frozen_target_is_rejected(self):
        normalized = (
            validate_and_normalize_book(
                book()
            )
        )

        with self.assertRaises(ValueError):
            sweep_base_quantity(
                normalized,
                side=BUY,
                target_base=Decimal("201"),
            )

    def test_float_target_is_rejected(self):
        normalized = (
            validate_and_normalize_book(
                book()
            )
        )

        with self.assertRaises(TypeError):
            sweep_base_quantity(
                normalized,
                side=BUY,
                target_base=200.0,
            )

    def test_total_captured_depth_uses_correct_side(self):
        normalized = (
            validate_and_normalize_book(
                book()
            )
        )

        self.assertEqual(
            total_captured_depth(
                normalized,
                side=BUY,
            ),
            Decimal("600"),
        )

        self.assertEqual(
            total_captured_depth(
                normalized,
                side=SELL,
            ),
            Decimal("600"),
        )


if __name__ == "__main__":
    unittest.main()
