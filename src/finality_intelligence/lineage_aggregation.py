from __future__ import annotations

import hashlib
from pathlib import Path
from statistics import mean, median

from finality_intelligence.quote_lineage import (
    analyze_quote_lineage,
)


IDENTITY_MODES = (
    "price_quantity",
    "price",
)

LATENCY_STATES = (
    "voted",
    "finalized",
    "committed",
)


def verify_capture_hash(
    capture_path: Path,
) -> str:
    hash_path = capture_path.with_suffix(
        ".sha256"
    )

    if not hash_path.exists():
        raise FileNotFoundError(
            f"Missing SHA256 sidecar: {hash_path}"
        )

    line = hash_path.read_text(
        encoding="utf-8"
    ).strip()

    try:
        expected_hash, expected_name = (
            line.split("  ", 1)
        )
    except ValueError as exc:
        raise ValueError(
            "Invalid SHA256 sidecar format."
        ) from exc

    if expected_name != capture_path.name:
        raise ValueError(
            "SHA256 sidecar filename does not "
            "match capture filename."
        )

    actual_hash = hashlib.sha256(
        capture_path.read_bytes()
    ).hexdigest()

    if actual_hash != expected_hash:
        raise ValueError(
            f"SHA256 mismatch for {capture_path}"
        )

    return actual_hash


def _rate(
    numerator: int,
    denominator: int,
) -> float | None:
    if denominator == 0:
        return None

    return (
        numerator
        / denominator
    )


def _describe(
    values: list[float],
) -> dict:
    if not values:
        return {
            "count": 0,
            "min": None,
            "median": None,
            "mean": None,
            "max": None,
        }

    return {
        "count": len(values),
        "min": min(values),
        "median": median(values),
        "mean": mean(values),
        "max": max(values),
    }


def _latency_values(
    rows: list[dict],
    state: str,
) -> list[float]:
    key = f"{state}_delta_ms"

    return [
        row[key]
        for row in rows
        if (
            row["evaluable"]
            and row[
                "observed_later_progression"
            ]
            and row[key] is not None
        )
    ]


def aggregate_captures(
    captures: list[
        tuple[str, dict]
    ],
    *,
    minimum_followup_ms: float = 1000.0,
) -> dict:
    if minimum_followup_ms < 0:
        raise ValueError(
            "minimum_followup_ms must be "
            "non-negative"
        )

    per_capture = []

    totals = {
        mode: {
            "unique_proposed_keys": 0,
            "proposed_episodes": 0,
            "reentry_ambiguous_episodes": 0,
            "evaluable_episodes": 0,
            "evaluable_ordered": 0,
            "evaluable_later_progressions": 0,
            "evaluable_not_observed": 0,
        }
        for mode in IDENTITY_MODES
    }

    ordered_rates = {
        mode: []
        for mode in IDENTITY_MODES
    }

    later_rates = {
        mode: []
        for mode in IDENTITY_MODES
    }

    pooled_latencies = {
        mode: {
            state: []
            for state in LATENCY_STATES
        }
        for mode in IDENTITY_MODES
    }

    total_messages = 0
    summed_unique_u = 0

    for label, capture in captures:
        records = capture[
            "records"
        ]

        total_messages += len(
            records
        )

        unique_u = (
            capture.get(
                "summary",
                {},
            ).get(
                "unique_U"
            )
        )

        if unique_u is not None:
            summed_unique_u += (
                unique_u
            )

        capture_result = {
            "capture": label,
            "captured_messages": (
                len(records)
            ),
            "unique_U_within_capture": (
                unique_u
            ),
            "modes": {},
        }

        for mode in IDENTITY_MODES:
            analysis = (
                analyze_quote_lineage(
                    records,
                    identity_mode=mode,
                    capture_end_utc=(
                        capture[
                            "connection_completed_utc"
                        ]
                    ),
                    minimum_followup_ms=(
                        minimum_followup_ms
                    ),
                )
            )

            summary = analysis[
                "summary"
            ]

            evaluable = summary[
                "evaluable_episodes"
            ]

            ordered = summary[
                "evaluable_observed_ordered_all_states"
            ]

            later = summary[
                "evaluable_observed_later_progressions"
            ]

            not_observed = summary[
                "evaluable_not_observed_ordered_all_states"
            ]

            ordered_rate = _rate(
                ordered,
                evaluable,
            )

            later_rate = _rate(
                later,
                evaluable,
            )

            if ordered_rate is not None:
                ordered_rates[
                    mode
                ].append(
                    ordered_rate
                )

            if later_rate is not None:
                later_rates[
                    mode
                ].append(
                    later_rate
                )

            latency_summary = {}

            for state in (
                LATENCY_STATES
            ):
                values = (
                    _latency_values(
                        analysis["rows"],
                        state,
                    )
                )

                pooled_latencies[
                    mode
                ][
                    state
                ].extend(
                    values
                )

                latency_summary[
                    state
                ] = _describe(
                    values
                )

            mode_result = {
                "unique_proposed_keys": (
                    summary[
                        "unique_proposed_keys"
                    ]
                ),
                "proposed_episodes": (
                    summary[
                        "proposed_episodes"
                    ]
                ),
                "reentry_ambiguous_episodes": (
                    summary[
                        "reentry_ambiguous_episodes"
                    ]
                ),
                "evaluable_episodes": (
                    evaluable
                ),
                "evaluable_ordered": (
                    ordered
                ),
                "evaluable_later_progressions": (
                    later
                ),
                "evaluable_not_observed": (
                    not_observed
                ),
                "ordered_rate": (
                    ordered_rate
                ),
                "later_progression_rate": (
                    later_rate
                ),
                "latency_ms": (
                    latency_summary
                ),
            }

            capture_result[
                "modes"
            ][mode] = mode_result

            totals[
                mode
            ][
                "unique_proposed_keys"
            ] += mode_result[
                "unique_proposed_keys"
            ]

            totals[
                mode
            ][
                "proposed_episodes"
            ] += mode_result[
                "proposed_episodes"
            ]

            totals[
                mode
            ][
                "reentry_ambiguous_episodes"
            ] += mode_result[
                "reentry_ambiguous_episodes"
            ]

            totals[
                mode
            ][
                "evaluable_episodes"
            ] += evaluable

            totals[
                mode
            ][
                "evaluable_ordered"
            ] += ordered

            totals[
                mode
            ][
                "evaluable_later_progressions"
            ] += later

            totals[
                mode
            ][
                "evaluable_not_observed"
            ] += not_observed

        per_capture.append(
            capture_result
        )

    cross_capture = {}

    for mode in IDENTITY_MODES:
        mode_totals = totals[
            mode
        ]

        evaluable_total = (
            mode_totals[
                "evaluable_episodes"
            ]
        )

        cross_capture[
            mode
        ] = {
            "descriptive_pooled_totals": {
                **mode_totals,
                "ordered_rate": _rate(
                    mode_totals[
                        "evaluable_ordered"
                    ],
                    evaluable_total,
                ),
                "later_progression_rate": _rate(
                    mode_totals[
                        "evaluable_later_progressions"
                    ],
                    evaluable_total,
                ),
            },
            "capture_level_ordered_rate": (
                _describe(
                    ordered_rates[
                        mode
                    ]
                )
            ),
            "capture_level_later_progression_rate": (
                _describe(
                    later_rates[
                        mode
                    ]
                )
            ),
            "descriptive_pooled_latency_ms": {
                state: _describe(
                    pooled_latencies[
                        mode
                    ][state]
                )
                for state in (
                    LATENCY_STATES
                )
            },
        }

    return {
        "capture_count": (
            len(captures)
        ),
        "minimum_followup_ms": (
            minimum_followup_ms
        ),
        "captured_messages_total": (
            total_messages
        ),
        "sum_unique_U_within_captures": (
            summed_unique_u
        ),
        "per_capture": (
            per_capture
        ),
        "cross_capture": (
            cross_capture
        ),
        "claim_boundary": {
            "captures_are_not_assumed_independent": (
                True
            ),
            "pooled_rates_are_descriptive_only": (
                True
            ),
            "U_is_observed_grouping_field_only": (
                True
            ),
            "latencies_are_client_observed": (
                True
            ),
        },
    }
