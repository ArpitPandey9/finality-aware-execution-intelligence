from __future__ import annotations

import unittest
from decimal import Decimal

from finality_intelligence.normalization import (
    MON_USDC_SIZE_PRECISION,
    normalize_kuru_level,
    normalize_kuru_price,
    normalize_kuru_size,
)


class TestKuruNormalization(unittest.TestCase):
    def test_verified_bid_price(self):
        result = normalize_kuru_price("25184000000000000")
        self.assertEqual(result, Decimal("0.025184"))

    def test_verified_ask_price(self):
        result = normalize_kuru_price("25189000000000000")
        self.assertEqual(result, Decimal("0.025189"))

    def test_verified_bid_size(self):
        result = normalize_kuru_size("992530000000000")
        self.assertEqual(result, Decimal("99253"))

    def test_verified_ask_size(self):
        result = normalize_kuru_size("992490000000000")
        self.assertEqual(result, Decimal("99249"))

    def test_verified_bid_level(self):
        price, size = normalize_kuru_level(
            ["25184000000000000", "992530000000000"]
        )

        self.assertEqual(price, Decimal("0.025184"))
        self.assertEqual(size, Decimal("99253"))

    def test_verified_ask_level(self):
        price, size = normalize_kuru_level(
            ["25189000000000000", "992490000000000"]
        )

        self.assertEqual(price, Decimal("0.025189"))
        self.assertEqual(size, Decimal("99249"))

    def test_integer_input_is_supported(self):
        result = normalize_kuru_price(25184000000000000)
        self.assertEqual(result, Decimal("0.025184"))

    def test_zero_is_supported(self):
        self.assertEqual(
            normalize_kuru_price("0"),
            Decimal("0"),
        )

        self.assertEqual(
            normalize_kuru_size("0"),
            Decimal("0"),
        )

    def test_negative_integer_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kuru_price(-1)

    def test_negative_string_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kuru_price("-1")

    def test_decimal_string_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kuru_price("0.025184")

    def test_empty_string_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kuru_price("")

    def test_float_is_rejected(self):
        with self.assertRaises(TypeError):
            normalize_kuru_price(0.025184)

    def test_boolean_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kuru_price(True)

    def test_invalid_level_length_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kuru_level(["25184000000000000"])

    def test_zero_size_precision_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kuru_size(
                "992530000000000",
                size_precision=Decimal("0"),
            )

    def test_market_size_precision_constant(self):
        self.assertEqual(
            MON_USDC_SIZE_PRECISION,
            Decimal("10000000000"),
        )


if __name__ == "__main__":
    unittest.main()
