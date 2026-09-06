import unittest
from decimal import Decimal

from finality_intelligence.staleness import (
    CORE_THRESHOLDS_MS,
    aggregate_staleness,
    analyze_capture_staleness,
    percentile,
)
from tests.test_alignment import cb_record, capture


class TestStalenessAnalysis(unittest.TestCase):
    def test_percentile_uses_linear_interpolation(self):
        values = [Decimal("0"), Decimal("10"), Decimal("20")]
        self.assertEqual(percentile(values, "0.75"), Decimal("15"))

    def test_core_thresholds_are_frozen(self):
        self.assertEqual(
            CORE_THRESHOLDS_MS,
            (Decimal("250"), Decimal("500"), Decimal("1000")),
        )

    def test_reference_age_sensitivity(self):
        source = capture(
            [
                1_100_000_000,
                1_400_000_000,
                1_900_000_000,
            ],
            [
                cb_record(
                    1_000_000_000,
                    0,
                    snapshot=True,
                ),
            ],
        )

        result = analyze_capture_staleness(
            source,
            capture_id="capture-a",
        )

        self.assertEqual(result["reference_age"]["count"], 3)
        self.assertEqual(result["thresholds"]["250"]["aligned"], 1)
        self.assertEqual(result["thresholds"]["500"]["aligned"], 2)
        self.assertEqual(result["thresholds"]["1000"]["aligned"], 3)

    def test_no_prior_reference_is_preserved(self):
        source = capture(
            [1_000_000_000, 2_100_000_000],
            [
                cb_record(
                    2_000_000_000,
                    0,
                    snapshot=True,
                ),
            ],
        )

        result = analyze_capture_staleness(
            source,
            capture_id="capture-a",
        )

        self.assertEqual(result["no_prior_reference"], 1)
        self.assertEqual(result["reference_age"]["count"], 1)

    def test_interarrival_is_computed_within_capture(self):
        first = capture(
            [1_150_000_000],
            [
                cb_record(
                    1_000_000_000,
                    0,
                    snapshot=True,
                ),
                cb_record(1_100_000_000, 1),
            ],
        )

        second = capture(
            [9_150_000_000],
            [
                cb_record(
                    9_000_000_000,
                    0,
                    snapshot=True,
                ),
                cb_record(9_100_000_000, 1),
            ],
        )

        a = analyze_capture_staleness(first, capture_id="a")
        b = analyze_capture_staleness(second, capture_id="b")
        pooled = aggregate_staleness([a, b])

        self.assertEqual(
            pooled["coinbase_interarrival"]["count"],
            2,
        )
        self.assertEqual(
            pooled["coinbase_interarrival"]["max_ms"],
            "100",
        )

    def test_duplicate_capture_ids_are_rejected(self):
        source = capture(
            [1_100_000_000],
            [
                cb_record(
                    1_000_000_000,
                    0,
                    snapshot=True,
                ),
            ],
        )

        a = analyze_capture_staleness(source, capture_id="same")
        b = analyze_capture_staleness(source, capture_id="same")

        with self.assertRaises(ValueError):
            aggregate_staleness([a, b])

    def test_float_threshold_is_rejected(self):
        source = capture(
            [1_100_000_000],
            [
                cb_record(
                    1_000_000_000,
                    0,
                    snapshot=True,
                ),
            ],
        )

        with self.assertRaises(ValueError):
            analyze_capture_staleness(
                source,
                capture_id="capture-a",
                thresholds_ms=(250.0,),
            )


if __name__ == "__main__":
    unittest.main()
