from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation

from finality_intelligence.temporal_outcome import (
    EVALUABLE,
    ROW_STATUSES,
    analyze_temporal_capture,
)


SCHEMA_VERSION = (
    "phase3.market_instability.v1"
)

SOURCE_SCHEMA_VERSION = (
    "phase2.temporal_outcome.v1"
)

CLAIM_BOUNDARIES = (
    "Phase 3 measures descriptive association between "
    "simultaneous Kuru state disagreement magnitude and "
    "subsequent Coinbase midpoint-movement magnitude.",
    "The analysis does not establish prediction, alpha, "
    "arbitrage, causality, or a Kuru lead over Coinbase.",
    "The Coinbase future midpoint movement is not realized "
    "PnL, execution, market impact, or adverse selection "
    "actually suffered by a trader.",
    "Simultaneous Kuru state views are not temporal "
    "protocol-state transitions or finality-latency "
    "measurements.",
    "Overlapping future windows are not statistically "
    "independent observations.",
)


PHASE3_ECONOMIC_FIELDS = (
    "kuru_pf_gap_bps",
    "kuru_pf_abs_gap_bps",
    "coinbase_forward_mid_return_bps",
    "coinbase_abs_forward_mid_move_bps",
)


def _decimal(
    value,
    *,
    field: str,
) -> Decimal:
    if isinstance(
        value,
        (bool, float),
    ):
        raise TypeError(
            f"{field} must use an exact numeric "
            "representation."
        )

    try:
        parsed = Decimal(
            value
        )
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            f"Invalid {field}."
        ) from exc

    if not parsed.is_finite():
        raise ValueError(
            f"{field} must be finite."
        )

    return parsed


def _serialize_decimal(
    value: Decimal,
) -> str:
    if not value.is_finite():
        raise ValueError(
            "Cannot serialize non-finite Decimal."
        )

    return str(
        value
    )


def _phase3_row(
    temporal_row: dict,
) -> dict:
    status = temporal_row.get(
        "status"
    )

    if status not in ROW_STATUSES:
        raise ValueError(
            "Unknown temporal outcome status."
        )

    row = {
        "capture_id":
            temporal_row.get(
                "capture_id"
            ),
        "freshness_threshold_ms":
            temporal_row.get(
                "freshness_threshold_ms"
            ),
        "horizon_ms":
            temporal_row.get(
                "horizon_ms"
            ),
        "kuru_record_index":
            temporal_row.get(
                "kuru_record_index"
            ),
        "kuru_received_at_utc":
            temporal_row.get(
                "kuru_received_at_utc"
            ),
        "kuru_received_monotonic_ns":
            temporal_row.get(
                "kuru_received_monotonic_ns"
            ),
        "U":
            temporal_row.get(
                "U"
            ),
        "alignment_status":
            temporal_row.get(
                "alignment_status"
            ),
        "alignment_status_reason":
            list(
                temporal_row.get(
                    "alignment_status_reason",
                    [],
                )
            ),
        "reference_age_ms":
            temporal_row.get(
                "reference_age_ms"
            ),
        "future_horizon_monotonic_ns":
            temporal_row.get(
                "future_horizon_monotonic_ns"
            ),
        "future_asof_age_ms":
            temporal_row.get(
                "future_asof_age_ms"
            ),
        "status":
            status,
        "status_reason":
            list(
                temporal_row.get(
                    "status_reason",
                    [],
                )
            ),
        "kuru_pf_gap_bps":
            None,
        "kuru_pf_abs_gap_bps":
            None,
        "coinbase_forward_mid_return_bps":
            None,
        "coinbase_abs_forward_mid_move_bps":
            None,
    }

    if status != EVALUABLE:
        return row

    gap = _decimal(
        temporal_row.get(
            "kuru_proposed_finalized_mid_gap_bps"
        ),
        field=(
            "kuru_proposed_finalized_mid_gap_bps"
        ),
    )

    forward = _decimal(
        temporal_row.get(
            "coinbase_forward_mid_return_bps"
        ),
        field=(
            "coinbase_forward_mid_return_bps"
        ),
    )

    row[
        "kuru_pf_gap_bps"
    ] = _serialize_decimal(
        gap
    )

    row[
        "kuru_pf_abs_gap_bps"
    ] = _serialize_decimal(
        abs(
            gap
        )
    )

    row[
        "coinbase_forward_mid_return_bps"
    ] = _serialize_decimal(
        forward
    )

    row[
        "coinbase_abs_forward_mid_move_bps"
    ] = _serialize_decimal(
        abs(
            forward
        )
    )

    return row


def analyze_market_instability_capture(
    capture: dict,
    *,
    capture_id: str,
    max_age_ms,
    horizon_ms,
) -> dict:
    """
    Reuse the canonical Phase 2 temporal engine and
    transform its evaluable rows into the frozen
    Phase 3 magnitude exposure/outcome representation.
    """
    temporal = analyze_temporal_capture(
        capture,
        capture_id=capture_id,
        max_age_ms=max_age_ms,
        horizon_ms=horizon_ms,
    )

    if (
        temporal.get(
            "schema_version"
        )
        != SOURCE_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unexpected temporal source schema."
        )

    rows = [
        _phase3_row(
            row
        )
        for row in temporal.get(
            "rows",
            []
        )
    ]

    counts = Counter(
        row[
            "status"
        ]
        for row in rows
    )

    evaluable = [
        row
        for row in rows
        if row[
            "status"
        ]
        == EVALUABLE
    ]

    zero_exposure_count = sum(
        1
        for row in evaluable
        if _decimal(
            row[
                "kuru_pf_abs_gap_bps"
            ],
            field="kuru_pf_abs_gap_bps",
        )
        == 0
    )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "source_schema_version":
            SOURCE_SCHEMA_VERSION,
        "capture_id":
            temporal.get(
                "capture_id",
                capture_id,
            ),
        "freshness_threshold_ms":
            temporal.get(
                "freshness_threshold_ms",
                str(
                    max_age_ms
                ),
            ),
        "horizon_ms":
            temporal.get(
                "horizon_ms",
                str(
                    horizon_ms
                ),
            ),
        "source_evidence_reasons":
            list(
                temporal.get(
                    "source_evidence_reasons",
                    [],
                )
            ),
        "rows":
            rows,
        "summary": {
            "rows":
                len(
                    rows
                ),
            "evaluable":
                counts[
                    EVALUABLE
                ],
            "status_counts":
                dict(
                    sorted(
                        counts.items()
                    )
                ),
            "zero_exposure_count":
                zero_exposure_count,
            "nonzero_exposure_count":
                (
                    len(
                        evaluable
                    )
                    - zero_exposure_count
                ),
        },
        "claim_boundaries":
            list(
                CLAIM_BOUNDARIES
            ),
    }
