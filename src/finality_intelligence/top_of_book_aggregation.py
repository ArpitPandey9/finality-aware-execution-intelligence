from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation

from finality_intelligence.staleness import percentile
from finality_intelligence.top_of_book import (
    CLAIM_BOUNDARIES,
    ECONOMICALLY_ELIGIBLE,
    ELIGIBILITY_OUTCOMES,
    STATE_ORDER,
)


SCHEMA_VERSION = "phase1.state_conditioned_top_of_book_aggregation.v1"

STATE_PAIRS = (
    ("proposed", "voted"),
    ("proposed", "finalized"),
    ("proposed", "committed"),
    ("voted", "finalized"),
    ("finalized", "committed"),
)

AGGREGATION_CLAIM_BOUNDARIES = (
    "Pooled summaries are descriptive only; capture windows are not assumed independent.",
    "The 250 ms, 500 ms, and 1000 ms bands are separate sensitivity analyses over overlapping observations.",
    "Coinbase reference-book statistics are calculated once per economically eligible panel, not once per Kuru state row.",
    "Paired state-view contrasts compare simultaneously observed state views and do not establish temporal quote progression or a causal effect of finality.",
)


def _decimal(value, *, field: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError(f"{field} must use an exact non-float value.")

    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid decimal value for {field}.") from None

    if not parsed.is_finite():
        raise ValueError(f"{field} must be finite.")

    return parsed


def _distribution(values) -> dict:
    xs = [
        _decimal(value, field="distribution value")
        for value in values
    ]

    if not xs:
        raise ValueError("Distribution requires at least one value.")

    return {
        "count": len(xs),
        "min": str(min(xs)),
        "p05": str(percentile(xs, "0.05")),
        "p25": str(percentile(xs, "0.25")),
        "p50": str(percentile(xs, "0.50")),
        "p75": str(percentile(xs, "0.75")),
        "p95": str(percentile(xs, "0.95")),
        "max": str(max(xs)),
    }


def _sign_counts(values) -> dict:
    xs = [
        _decimal(value, field="sign-count value")
        for value in values
    ]

    return {
        "positive": sum(value > 0 for value in xs),
        "zero": sum(value == 0 for value in xs),
        "negative": sum(value < 0 for value in xs),
    }


def _median(values) -> str:
    xs = [
        _decimal(value, field="median value")
        for value in values
    ]

    if not xs:
        raise ValueError("Median requires at least one value.")

    return str(percentile(xs, "0.50"))


def _group_capture_panels(analysis: dict) -> list[dict]:
    rows = analysis.get("rows")

    if not isinstance(rows, list):
        raise ValueError("Top-of-book analysis rows must be a list.")

    capture_id = analysis.get("capture_id")
    threshold = analysis.get("freshness_threshold_ms")

    grouped = defaultdict(dict)

    for row in rows:
        if row.get("capture_id") != capture_id:
            raise ValueError("Row capture_id does not match analysis capture_id.")

        if row.get("freshness_threshold_ms") != threshold:
            raise ValueError("Row freshness threshold does not match analysis.")

        state = row.get("state")

        if state not in STATE_ORDER:
            raise ValueError(f"Unexpected Kuru state: {state}")

        key = row.get("kuru_record_index")

        if state in grouped[key]:
            raise ValueError("Duplicate state row inside one economic panel.")

        grouped[key][state] = row

    panels = []

    for record_index, states in grouped.items():
        if set(states) != set(STATE_ORDER):
            raise ValueError("Economic panel must contain exactly four state rows.")

        ordered = {
            state: states[state]
            for state in STATE_ORDER
        }

        reference_identity = {
            (
                row.get("coinbase_record_index"),
                row.get("coinbase_sequence_num"),
                row.get("coinbase_received_monotonic_ns"),
                row.get("reference_age_ms"),
                row.get("coinbase_best_bid"),
                row.get("coinbase_best_offer"),
                row.get("coinbase_spread_bps"),
            )
            for row in ordered.values()
        }

        if len(reference_identity) != 1:
            raise ValueError("Four-state panel does not share one Coinbase reference.")

        panels.append({
            "capture_id": capture_id,
            "kuru_record_index": record_index,
            "states": ordered,
        })

    expected_rows = analysis.get("summary", {}).get("economic_rows")

    if expected_rows != len(rows):
        raise ValueError("Economic-row count does not match analysis summary.")

    if len(rows) != len(panels) * len(STATE_ORDER):
        raise ValueError("Economic rows do not form complete four-state panels.")

    return panels


def _aggregate_eligibility(
    analyses: list[dict],
    *,
    expected_panel_count: int,
) -> dict:
    totals = {
        outcome: 0
        for outcome in ELIGIBILITY_OUTCOMES
    }

    capture_summaries = {}
    total_observations = 0
    total_economic_rows = 0

    for analysis in analyses:
        capture_id = analysis["capture_id"]
        summary = analysis.get("summary")

        if not isinstance(summary, dict):
            raise ValueError(
                "Top-of-book analysis summary must be a mapping."
            )

        counts = summary.get("eligibility_counts")

        if not isinstance(counts, dict):
            raise ValueError(
                "Eligibility counts must be a mapping."
            )

        if set(counts) != set(ELIGIBILITY_OUTCOMES):
            raise ValueError(
                "Eligibility counts must contain exactly "
                "the defined eligibility outcomes."
            )

        parsed_counts = {}

        for outcome in ELIGIBILITY_OUTCOMES:
            value = counts[outcome]

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    "Eligibility counts must be "
                    "non-negative integers."
                )

            parsed_counts[outcome] = value
            totals[outcome] += value

        observations = summary.get("kuru_observations")
        economic_rows = summary.get("economic_rows")

        for name, value in (
            ("kuru_observations", observations),
            ("economic_rows", economic_rows),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"{name} must be a non-negative integer."
                )

        if sum(parsed_counts.values()) != observations:
            raise ValueError(
                "Eligibility counts do not reconcile "
                "to Kuru observation count."
            )

        expected_rows = (
            parsed_counts[ECONOMICALLY_ELIGIBLE]
            * len(STATE_ORDER)
        )

        if economic_rows != expected_rows:
            raise ValueError(
                "Economic-row count does not reconcile "
                "to economically eligible panels."
            )

        capture_summaries[capture_id] = {
            "kuru_observations": observations,
            "economic_panel_count": (
                parsed_counts[ECONOMICALLY_ELIGIBLE]
            ),
            "economic_rows": economic_rows,
            "eligibility_counts": parsed_counts,
        }

        total_observations += observations
        total_economic_rows += economic_rows

    if (
        totals[ECONOMICALLY_ELIGIBLE]
        != expected_panel_count
    ):
        raise ValueError(
            "Aggregated economically eligible count "
            "does not match derived panel count."
        )

    if (
        total_economic_rows
        != expected_panel_count * len(STATE_ORDER)
    ):
        raise ValueError(
            "Aggregated economic-row count "
            "does not match derived panel count."
        )

    return {
        "kuru_observations": total_observations,
        "economic_panel_count": expected_panel_count,
        "economic_rows": total_economic_rows,
        "eligibility_counts": totals,
        "capture_summaries": capture_summaries,
    }


def aggregate_top_of_book(analyses: list[dict]) -> dict:
    if not analyses:
        raise ValueError("At least one top-of-book analysis is required.")

    capture_ids = [analysis.get("capture_id") for analysis in analyses]

    if any(not capture_id for capture_id in capture_ids):
        raise ValueError("Every analysis requires a capture_id.")

    if len(set(capture_ids)) != len(capture_ids):
        raise ValueError("Capture identifiers must be unique.")

    thresholds = {
        analysis.get("freshness_threshold_ms")
        for analysis in analyses
    }

    if len(thresholds) != 1:
        raise ValueError("Aggregation requires one freshness threshold at a time.")

    threshold = next(iter(thresholds))

    panels = []
    panels_by_capture = {}

    for analysis in analyses:
        capture_panels = _group_capture_panels(analysis)
        panels.extend(capture_panels)
        panels_by_capture[analysis["capture_id"]] = capture_panels

    if not panels:
        raise ValueError("Aggregation requires economically eligible panels.")

    eligibility_summary = _aggregate_eligibility(
        analyses,
        expected_panel_count=len(panels),
    )

    state_summaries = {}

    for state in STATE_ORDER:
        pooled_rows = [
            panel["states"][state]
            for panel in panels
        ]

        spread_values = [
            row["kuru_spread_bps"]
            for row in pooled_rows
        ]
        reference_values = [
            row["reference_mid_difference_bps"]
            for row in pooled_rows
        ]

        capture_medians = {}

        for capture_id, capture_panels in panels_by_capture.items():
            capture_rows = [
                panel["states"][state]
                for panel in capture_panels
            ]

            capture_medians[capture_id] = {
                "count": len(capture_rows),
                "kuru_spread_bps_p50": _median(
                    row["kuru_spread_bps"]
                    for row in capture_rows
                ),
                "reference_mid_difference_bps_p50": _median(
                    row["reference_mid_difference_bps"]
                    for row in capture_rows
                ),
            }

        state_summaries[state] = {
            "count": len(pooled_rows),
            "kuru_spread_bps": _distribution(spread_values),
            "reference_mid_difference_bps": _distribution(reference_values),
            "reference_mid_difference_sign_counts": _sign_counts(reference_values),
            "capture_medians": capture_medians,
        }

    coinbase_values = [
        panel["states"]["proposed"]["coinbase_spread_bps"]
        for panel in panels
    ]

    coinbase_capture_medians = {}

    for capture_id, capture_panels in panels_by_capture.items():
        values = [
            panel["states"]["proposed"]["coinbase_spread_bps"]
            for panel in capture_panels
        ]

        coinbase_capture_medians[capture_id] = {
            "panel_count": len(values),
            "coinbase_spread_bps_p50": _median(values),
        }

    coinbase_summary = {
        "panel_count": len(panels),
        "coinbase_spread_bps": _distribution(coinbase_values),
        "capture_medians": coinbase_capture_medians,
    }

    paired = {}

    for state_a, state_b in STATE_PAIRS:
        spread_deltas = []
        reference_deltas = []
        exact_equal_count = 0

        capture_values = defaultdict(
            lambda: {
                "spread": [],
                "reference": [],
                "exact": 0,
                "count": 0,
            }
        )

        for panel in panels:
            first = panel["states"][state_a]
            second = panel["states"][state_b]

            spread_delta = (
                _decimal(second["kuru_spread_bps"], field="kuru_spread_bps")
                - _decimal(first["kuru_spread_bps"], field="kuru_spread_bps")
            )
            reference_delta = (
                _decimal(
                    second["reference_mid_difference_bps"],
                    field="reference_mid_difference_bps",
                )
                - _decimal(
                    first["reference_mid_difference_bps"],
                    field="reference_mid_difference_bps",
                )
            )

            exact_equal = (
                first["kuru_best_bid_raw"] == second["kuru_best_bid_raw"]
                and first["kuru_best_ask_raw"] == second["kuru_best_ask_raw"]
            )

            spread_deltas.append(spread_delta)
            reference_deltas.append(reference_delta)

            capture_id = panel["capture_id"]
            values = capture_values[capture_id]
            values["spread"].append(spread_delta)
            values["reference"].append(reference_delta)
            values["count"] += 1

            if exact_equal:
                exact_equal_count += 1
                values["exact"] += 1

        paired_count = len(panels)
        exact_rate = (
            Decimal(exact_equal_count)
            / Decimal(paired_count)
        )

        capture_summaries = {}

        for capture_id in sorted(capture_values):
            values = capture_values[capture_id]

            capture_summaries[capture_id] = {
                "paired_observation_count": values["count"],
                "exact_top_equal_count": values["exact"],
                "exact_top_equal_rate": str(
                    Decimal(values["exact"])
                    / Decimal(values["count"])
                ),
                "spread_delta_bps_p50": _median(values["spread"]),
                "reference_mid_difference_delta_bps_p50": _median(
                    values["reference"]
                ),
            }

        key = f"{state_a}__{state_b}"

        paired[key] = {
            "state_a": state_a,
            "state_b": state_b,
            "paired_observation_count": paired_count,
            "exact_top_equal_count": exact_equal_count,
            "exact_top_equal_rate": str(exact_rate),
            "spread_delta_bps": _distribution(spread_deltas),
            "spread_delta_sign_counts": _sign_counts(spread_deltas),
            "reference_mid_difference_delta_bps": _distribution(
                reference_deltas
            ),
            "reference_mid_difference_delta_sign_counts": _sign_counts(
                reference_deltas
            ),
            "capture_summaries": capture_summaries,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "freshness_threshold_ms": threshold,
        "capture_count": len(analyses),
        "economic_panel_count": len(panels),
        "eligibility_summary": eligibility_summary,
        "state_summaries": state_summaries,
        "coinbase_reference_summary": coinbase_summary,
        "paired_state_view_contrasts": paired,
        "claim_boundaries": [
            *CLAIM_BOUNDARIES,
            *AGGREGATION_CLAIM_BOUNDARIES,
        ],
    }
