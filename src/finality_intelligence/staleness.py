from __future__ import annotations

from decimal import Decimal, InvalidOperation
from statistics import mean, median

from finality_intelligence.alignment import align_dual_capture


CORE_THRESHOLDS_MS = (
    Decimal("250"),
    Decimal("500"),
    Decimal("1000"),
)


def _parse_threshold(value) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("Thresholds must use exact non-float values.")

    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid threshold.") from None

    if not parsed.is_finite() or parsed < 0:
        raise ValueError("Thresholds must be finite and non-negative.")

    return parsed


def _parse_thresholds(values) -> tuple[Decimal, ...]:
    parsed = tuple(_parse_threshold(value) for value in values)

    if not parsed:
        raise ValueError("At least one threshold is required.")

    if len(set(parsed)) != len(parsed):
        raise ValueError("Thresholds must be unique.")

    return tuple(sorted(parsed))


def percentile(values, q) -> Decimal | None:
    xs = sorted(Decimal(str(value)) for value in values)

    if not xs:
        return None

    quantile = Decimal(str(q))

    if not quantile.is_finite() or quantile < 0 or quantile > 1:
        raise ValueError("q must be between 0 and 1.")

    if len(xs) == 1:
        return xs[0]

    position = Decimal(len(xs) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(xs) - 1)
    fraction = position - Decimal(lower)

    return xs[lower] + (xs[upper] - xs[lower]) * fraction


def _distribution(values) -> dict:
    xs = [Decimal(str(value)) for value in values]

    if not xs:
        return {
            "count": 0,
            "min_ms": None,
            "p50_ms": None,
            "p90_ms": None,
            "p95_ms": None,
            "p99_ms": None,
            "max_ms": None,
        }

    return {
        "count": len(xs),
        "min_ms": str(min(xs)),
        "p50_ms": str(percentile(xs, "0.50")),
        "p90_ms": str(percentile(xs, "0.90")),
        "p95_ms": str(percentile(xs, "0.95")),
        "p99_ms": str(percentile(xs, "0.99")),
        "max_ms": str(max(xs)),
    }


def _coinbase_target_times(capture: dict) -> list[int]:
    records = capture["sources"]["coinbase"]["records"]

    return [
        record["received_monotonic_ns"]
        for record in records
        if (
            record.get("channel") == "l2_data"
            and record.get("target_event_types")
            and record.get("book_top_after") is not None
        )
    ]


def _coinbase_interarrival_ms(capture: dict) -> list[Decimal]:
    times = _coinbase_target_times(capture)

    return [
        Decimal(current - previous) / Decimal(1_000_000)
        for previous, current in zip(times, times[1:])
    ]


def analyze_capture_staleness(
    capture: dict,
    *,
    capture_id: str,
    thresholds_ms=CORE_THRESHOLDS_MS,
) -> dict:
    thresholds = _parse_thresholds(thresholds_ms)

    alignment = align_dual_capture(
        capture,
        capture_id=capture_id,
        max_age_ms=max(thresholds),
    )

    reasons = alignment["source_evidence_reasons"]

    if reasons:
        return {
            "capture_id": capture_id,
            "source_evidence_reasons": reasons,
            "kuru_observations": len(alignment["rows"]),
            "no_prior_reference": 0,
            "reference_age": _distribution([]),
            "coinbase_interarrival": _distribution([]),
            "thresholds": {},
        }

    rows = alignment["rows"]
    ages = [
        Decimal(row["reference_age_ms"])
        for row in rows
        if row["coinbase_reference"] is not None
    ]

    no_prior = sum(
        row["status"] == "NO_PRIOR_REFERENCE"
        for row in rows
    )

    threshold_results = {}

    for threshold in thresholds:
        aligned = sum(age <= threshold for age in ages)
        stale = len(ages) - aligned

        aligned_pct = (
            Decimal(aligned)
            / Decimal(len(ages))
            * Decimal(100)
            if ages
            else Decimal(0)
        )

        threshold_results[str(threshold)] = {
            "aligned": aligned,
            "stale": stale,
            "aligned_pct": str(aligned_pct),
        }

    return {
        "capture_id": capture_id,
        "source_evidence_reasons": [],
        "kuru_observations": len(rows),
        "no_prior_reference": no_prior,
        "reference_age": _distribution(ages),
        "coinbase_interarrival": _distribution(
            _coinbase_interarrival_ms(capture)
        ),
        "thresholds": threshold_results,
        "_reference_ages_ms": [str(value) for value in ages],
        "_coinbase_interarrival_ms": [
            str(value)
            for value in _coinbase_interarrival_ms(capture)
        ],
    }


def aggregate_staleness(analyses: list[dict]) -> dict:
    if not analyses:
        raise ValueError("At least one capture analysis is required.")

    ids = [item["capture_id"] for item in analyses]

    if len(ids) != len(set(ids)):
        raise ValueError("Capture IDs must be unique.")

    failed = [
        item["capture_id"]
        for item in analyses
        if item["source_evidence_reasons"]
    ]

    if failed:
        raise ValueError(
            "Cannot aggregate captures with insufficient source evidence: "
            + ", ".join(failed)
        )

    all_ages = [
        Decimal(value)
        for item in analyses
        for value in item["_reference_ages_ms"]
    ]

    all_interarrival = [
        Decimal(value)
        for item in analyses
        for value in item["_coinbase_interarrival_ms"]
    ]

    threshold_keys = tuple(analyses[0]["thresholds"].keys())

    if any(
        tuple(item["thresholds"].keys()) != threshold_keys
        for item in analyses[1:]
    ):
        raise ValueError("All captures must use identical thresholds.")

    pooled_thresholds = {}

    for key in threshold_keys:
        aligned = sum(
            item["thresholds"][key]["aligned"]
            for item in analyses
        )
        stale = sum(
            item["thresholds"][key]["stale"]
            for item in analyses
        )
        total = aligned + stale

        capture_rates = [
            Decimal(item["thresholds"][key]["aligned_pct"])
            for item in analyses
        ]

        pooled_thresholds[key] = {
            "aligned": aligned,
            "stale": stale,
            "aligned_pct": str(
                Decimal(aligned) / Decimal(total) * Decimal(100)
                if total
                else Decimal(0)
            ),
            "capture_aligned_pct": {
                "min": str(min(capture_rates)),
                "median": str(median(capture_rates)),
                "mean": str(mean(capture_rates)),
                "max": str(max(capture_rates)),
            },
        }

    return {
        "capture_count": len(analyses),
        "capture_ids": ids,
        "kuru_observations": sum(
            item["kuru_observations"] for item in analyses
        ),
        "no_prior_reference": sum(
            item["no_prior_reference"] for item in analyses
        ),
        "reference_age": _distribution(all_ages),
        "coinbase_interarrival": _distribution(all_interarrival),
        "thresholds": pooled_thresholds,
        "claim_boundary": (
            "Monotonic receive timestamps are compared only within each "
            "capture process. Pooled values combine derived within-capture "
            "durations and are descriptive only."
        ),
    }
