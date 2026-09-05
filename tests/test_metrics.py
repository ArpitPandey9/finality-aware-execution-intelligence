from __future__ import annotations

import unittest
from decimal import Decimal

from finality_intelligence.metrics import (
    midpoint,
    reference_mid_difference,
    reference_mid_difference_bps,
    spread,
    spread_bps,
)


class TestMarketMetrics(unittest.TestCase):
    def test_midpoint(self):
        result = midpoint(
            "0.025184",
            "0.025189",
        )

        self.assertEqual(
            result,
            Decimal("0.0251865"),
        )

    def test_spread(self):
        result = spread(
            "0.025184",
            "0.025189",
        )

        self.assertEqual(
            result,
            Decimal("0.000005"),
        )

    def test_spread_bps_is_positive(self):
        result = spread_bps(
            "0.025184",
            "0.025189",
        )

        self.assertGreater(
            result,
            Decimal("0"),
        )

    def test_locked_market_zero_midpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            spread_bps(
                "0",
                "0",
            )

    def test_crossed_market_is_rejected(self):
        with self.assertRaises(ValueError):
            midpoint(
                "0.02520",
                "0.02510",
            )

    def test_reference_mid_difference(self):
        result = reference_mid_difference(
            "0.0251865",
            "0.025185",
        )

        self.assertEqual(
            result,
            Decimal("0.0000015"),
        )

    def test_reference_mid_difference_bps_is_positive(self):
        result = reference_mid_difference_bps(
            "0.0251865",
            "0.025185",
        )

        self.assertGreater(
            result,
            Decimal("0"),
        )

    def test_float_is_rejected(self):
        with self.assertRaises(TypeError):
            midpoint(
                0.025184,
                "0.025189",
            )


if __name__ == "__main__":
    unittest.main()
