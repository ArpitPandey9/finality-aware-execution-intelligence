from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation

from finality_intelligence.alignment import (
    ALIGNED,
)
from finality_intelligence.staleness import (
    CORE_THRESHOLDS_MS,
    percentile,
)
from finality_intelligence.temporal_outcome import (
    APPLICABLE_NONZERO_CONTRAST,
    EVALUABLE,
    FROZEN_HORIZONS_MS,
    NOT_APPLICABLE_ZERO_CONTRAST,
    RIGHT_CENSORED_CAPTURE_END,
    ROW_STATUSES,
)


SCHEMA_VERSION = (
    "phase2.temporal_outcome_aggregation.v1"
)

SOURCE_SCHEMA_VERSION = (
    "phase2.temporal_outcome.v1"
)

FROZEN_FRESHNESS_THRESHOLDS_MS = (
    CORE_THRESHOLDS_MS
)


CLAIM_BOUNDARIES = (
    "Phase 2 temporal aggregation is descriptive and does not establish "
    "prediction, alpha, arbitrage, or causal finality effects.",
    "Pooled temporal rows are overlapping observations and are not independent.",
    "Directional-concordance sign counts are not a win rate, hit rate, "
    "execution probability, or trading-performance statistic.",
    "Capture-level medians are descriptive robustness summaries and are not "
    "independent experimental replications.",
    "The deterministic non-overlapping sensitivity reduces horizon overlap "
    "but must not be described as statistically independent.",
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
            f"{field} must use an exact numeric representation."
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


def _nonnegative_int(
    value,
    *,
    field: str,
) -> int:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
    ):
        raise TypeError(
            f"{field} must be int."
        )

    if value < 0:
        raise ValueError(
            f"{field} must be non-negative."
        )

    return value


def _sign(
    value: Decimal,
) -> str:
    if value > 0:
        return "POSITIVE"

    if value < 0:
        return "NEGATIVE"

    return "ZERO"


def _sign_counts(
    values,
) -> dict:
    counts = Counter(
        _sign(
            _decimal(
                value,
                field="distribution value",
            )
        )
        for value in values
    )

    return {
        "NEGATIVE":
            counts[
                "NEGATIVE"
            ],
        "POSITIVE":
            counts[
                "POSITIVE"
            ],
        "ZERO":
            counts[
                "ZERO"
            ],
    }


def _distribution(
    values,
) -> dict:
    parsed = [
        _decimal(
            value,
            field="distribution value",
        )
        for value in values
    ]

    if not parsed:
        return {
            "count":
                0,
            "min":
                None,
            "p05":
                None,
            "p25":
                None,
            "p50":
                None,
            "p75":
                None,
            "p95":
                None,
            "max":
                None,
            "sign_counts": {
                "NEGATIVE": 0,
                "POSITIVE": 0,
                "ZERO": 0,
            },
        }

    return {
        "count":
            len(parsed),
        "min":
            str(
                min(
                    parsed
                )
            ),
        "p05":
            str(
                percentile(
                    parsed,
                    Decimal("0.05"),
                )
            ),
        "p25":
            str(
                percentile(
                    parsed,
                    Decimal("0.25"),
                )
            ),
        "p50":
            str(
                percentile(
                    parsed,
                    Decimal("0.50"),
                )
            ),
        "p75":
            str(
                percentile(
                    parsed,
                    Decimal("0.75"),
                )
            ),
        "p95":
            str(
                percentile(
                    parsed,
                    Decimal("0.95"),
                )
            ),
        "max":
            str(
                max(
                    parsed
                )
            ),
        "sign_counts":
            _sign_counts(
                parsed
            ),
    }


def _median(
    values,
) -> str | None:
    parsed = [
        _decimal(
            value,
            field="median value",
        )
        for value in values
    ]

    if not parsed:
        return None

    result = percentile(
        parsed,
        Decimal("0.50"),
    )

    if result is None:
        return None

    return str(
        result
    )


def _contrast_sign_counts(
    rows: list[dict],
) -> dict:
    counts = Counter(
        row[
            "contrast_sign"
        ]
        for row in rows
    )

    return {
        "NEGATIVE":
            counts[
                "NEGATIVE"
            ],
        "POSITIVE":
            counts[
                "POSITIVE"
            ],
        "ZERO":
            counts[
                "ZERO"
            ],
    }


def _parse_freshness_threshold(
    value,
) -> Decimal:
    parsed = _decimal(
        value,
        field="freshness_threshold_ms",
    )

    if (
        parsed
        not in FROZEN_FRESHNESS_THRESHOLDS_MS
    ):
        raise ValueError(
            "freshness_threshold_ms is not "
            "a frozen Phase 2 threshold."
        )

    return parsed


def _parse_horizon(
    value,
) -> Decimal:
    parsed = _decimal(
        value,
        field="horizon_ms",
    )

    if (
        parsed
        not in FROZEN_HORIZONS_MS
    ):
        raise ValueError(
            "horizon_ms is not a frozen "
            "Phase 2 horizon."
        )

    return parsed


def _validate_evaluable_row(
    row: dict,
) -> None:
    forward = _decimal(
        row.get(
            "coinbase_forward_mid_return_bps"
        ),
        field="coinbase_forward_mid_return_bps",
    )

    contrast = _decimal(
        row.get(
            "kuru_proposed_finalized_mid_gap_bps"
        ),
        field="kuru_proposed_finalized_mid_gap_bps",
    )

    future_age = _decimal(
        row.get(
            "future_asof_age_ms"
        ),
        field="future_asof_age_ms",
    )

    if future_age < 0:
        raise ValueError(
            "future_asof_age_ms must be non-negative."
        )

    expected_sign = _sign(
        contrast
    )

    if (
        row.get(
            "contrast_sign"
        )
        != expected_sign
    ):
        raise ValueError(
            "contrast_sign is inconsistent "
            "with the proposed-finalized gap."
        )

    concordance_status = row.get(
        "directional_concordance_status"
    )

    concordance_value = row.get(
        "directional_concordance_bps"
    )

    if expected_sign == "ZERO":
        if (
            concordance_status
            != NOT_APPLICABLE_ZERO_CONTRAST
        ):
            raise ValueError(
                "Zero contrast must be marked "
                "not applicable for concordance."
            )

        if concordance_value is not None:
            raise ValueError(
                "Zero contrast must not carry "
                "directional concordance."
            )

        return

    if (
        concordance_status
        != APPLICABLE_NONZERO_CONTRAST
    ):
        raise ValueError(
            "Non-zero contrast must expose "
            "applicable concordance status."
        )

    observed = _decimal(
        concordance_value,
        field="directional_concordance_bps",
    )

    direction = (
        Decimal("1")
        if expected_sign
        == "POSITIVE"
        else Decimal("-1")
    )

    expected = (
        direction
        * forward
    )

    if observed != expected:
        raise ValueError(
            "directional_concordance_bps "
            "is arithmetically inconsistent."
        )


def _validate_non_evaluable_row(
    row: dict,
) -> None:
    if (
        row.get(
            "coinbase_forward_mid_return_bps"
        )
        is not None
    ):
        raise ValueError(
            "Non-evaluable temporal row "
            "must not carry a forward return."
        )

    if (
        row.get(
            "directional_concordance_bps"
        )
        is not None
    ):
        raise ValueError(
            "Non-evaluable temporal row "
            "must not carry concordance."
        )


def _validate_analysis(
    analysis: dict,
) -> None:
    if not isinstance(
        analysis,
        dict,
    ):
        raise TypeError(
            "Temporal analysis must be a mapping."
        )

    if (
        analysis.get(
            "schema_version"
        )
        != SOURCE_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported temporal outcome schema."
        )

    capture_id = analysis.get(
        "capture_id"
    )

    if (
        not isinstance(
            capture_id,
            str,
        )
        or not capture_id.strip()
    ):
        raise ValueError(
            "capture_id must be a non-empty string."
        )

    freshness = _parse_freshness_threshold(
        analysis.get(
            "freshness_threshold_ms"
        )
    )

    horizon = _parse_horizon(
        analysis.get(
            "horizon_ms"
        )
    )

    rows = analysis.get(
        "rows"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise TypeError(
            "Temporal rows must be a list."
        )

    actual_counts = Counter()

    for row in rows:
        if not isinstance(
            row,
            dict,
        ):
            raise TypeError(
                "Temporal row must be a mapping."
            )

        if (
            row.get(
                "capture_id"
            )
            != capture_id
        ):
            raise ValueError(
                "Temporal row capture_id mismatch."
            )

        if (
            _parse_freshness_threshold(
                row.get(
                    "freshness_threshold_ms"
                )
            )
            != freshness
        ):
            raise ValueError(
                "Temporal row freshness threshold mismatch."
            )

        if (
            _parse_horizon(
                row.get(
                    "horizon_ms"
                )
            )
            != horizon
        ):
            raise ValueError(
                "Temporal row horizon mismatch."
            )

        _nonnegative_int(
            row.get(
                "kuru_record_index"
            ),
            field="kuru_record_index",
        )

        _nonnegative_int(
            row.get(
                "kuru_received_monotonic_ns"
            ),
            field="kuru_received_monotonic_ns",
        )

        status = row.get(
            "status"
        )

        if status not in ROW_STATUSES:
            raise ValueError(
                "Unknown temporal outcome status."
            )

        actual_counts[
            status
        ] += 1

        if status == EVALUABLE:
            if (
                row.get(
                    "alignment_status"
                )
                != ALIGNED
            ):
                raise ValueError(
                    "Evaluable temporal row must "
                    "have ALIGNED baseline status."
                )

            _validate_evaluable_row(
                row
            )
        else:
            _validate_non_evaluable_row(
                row
            )

    summary = analysis.get(
        "summary"
    )

    if not isinstance(
        summary,
        dict,
    ):
        raise TypeError(
            "Temporal summary must be a mapping."
        )

    if (
        summary.get(
            "rows"
        )
        != len(rows)
    ):
        raise ValueError(
            "Temporal summary row count mismatch."
        )

    if (
        summary.get(
            "kuru_observations"
        )
        != len(rows)
    ):
        raise ValueError(
            "Temporal Kuru observation count mismatch."
        )

    summary_counts = summary.get(
        "status_counts"
    )

    if not isinstance(
        summary_counts,
        dict,
    ):
        raise TypeError(
            "Temporal status_counts must be a mapping."
        )

    normalized_summary_counts = {
        key:
            value
        for key, value
        in summary_counts.items()
        if value != 0
    }

    expected_counts = dict(
        sorted(
            actual_counts.items()
        )
    )

    if (
        normalized_summary_counts
        != expected_counts
    ):
        raise ValueError(
            "Temporal status_counts do not "
            "reconcile with rows."
        )

    if (
        summary.get(
            "evaluable"
        )
        != actual_counts[
            EVALUABLE
        ]
    ):
        raise ValueError(
            "Temporal evaluable summary count mismatch."
        )

    if (
        summary.get(
            "right_censored"
        )
        != actual_counts[
            RIGHT_CENSORED_CAPTURE_END
        ]
    ):
        raise ValueError(
            "Temporal right-censored summary count mismatch."
        )


def select_non_overlapping_rows(
    rows: list[dict],
    *,
    horizon_ms,
) -> list[dict]:
    if not isinstance(
        rows,
        list,
    ):
        raise TypeError(
            "rows must be a list."
        )

    horizon = _parse_horizon(
        horizon_ms
    )

    horizon_ns_decimal = (
        horizon
        * Decimal("1000000")
    )

    if (
        horizon_ns_decimal
        != horizon_ns_decimal.to_integral_value()
    ):
        raise ValueError(
            "horizon_ms does not map to exact nanoseconds."
        )

    horizon_ns = int(
        horizon_ns_decimal
    )

    evaluable = [
        row
        for row in rows
        if row.get(
            "status"
        )
        == EVALUABLE
    ]

    if not evaluable:
        return []

    capture_ids = {
        row.get(
            "capture_id"
        )
        for row in evaluable
    }

    if len(
        capture_ids
    ) != 1:
        raise ValueError(
            "Non-overlapping selection must "
            "operate within one capture."
        )

    ordered = sorted(
        evaluable,
        key=lambda row: (
            _nonnegative_int(
                row.get(
                    "kuru_received_monotonic_ns"
                ),
                field="kuru_received_monotonic_ns",
            ),
            _nonnegative_int(
                row.get(
                    "kuru_record_index"
                ),
                field="kuru_record_index",
            ),
        ),
    )

    selected = []

    last_keep_ns = None

    for row in ordered:
        t0_ns = _nonnegative_int(
            row.get(
                "kuru_received_monotonic_ns"
            ),
            field="kuru_received_monotonic_ns",
        )

        if (
            last_keep_ns is None
            or t0_ns
            >= last_keep_ns
            + horizon_ns
        ):
            selected.append(
                row
            )

            last_keep_ns = t0_ns

    return selected


def _capture_summary(
    analysis: dict,
) -> dict:
    rows = analysis[
        "rows"
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

    concordance_values = [
        row[
            "directional_concordance_bps"
        ]
        for row in evaluable
        if row[
            "directional_concordance_bps"
        ]
        is not None
    ]

    return {
        "capture_id":
            analysis[
                "capture_id"
            ],
        "rows":
            len(rows),
        "baseline_aligned_panels":
            sum(
                1
                for row in rows
                if row.get(
                    "alignment_status"
                )
                == ALIGNED
            ),
        "evaluable":
            counts[
                EVALUABLE
            ],
        "right_censored":
            counts[
                RIGHT_CENSORED_CAPTURE_END
            ],
        "status_counts":
            dict(
                sorted(
                    counts.items()
                )
            ),
        "contrast_sign_counts":
            _contrast_sign_counts(
                evaluable
            ),
        "forward_return_bps_median":
            _median(
                [
                    row[
                        "coinbase_forward_mid_return_bps"
                    ]
                    for row in evaluable
                ]
            ),
        "directional_concordance_bps_median":
            _median(
                concordance_values
            ),
        "future_asof_age_ms":
            _distribution(
                [
                    row[
                        "future_asof_age_ms"
                    ]
                    for row in evaluable
                ]
            ),
    }


def aggregate_temporal_outcomes(
    analyses: list[dict],
) -> dict:
    if not isinstance(
        analyses,
        list,
    ):
        raise TypeError(
            "analyses must be a list."
        )

    if not analyses:
        raise ValueError(
            "analyses must not be empty."
        )

    for analysis in analyses:
        _validate_analysis(
            analysis
        )

    capture_ids = [
        analysis[
            "capture_id"
        ]
        for analysis in analyses
    ]

    if (
        len(
            set(
                capture_ids
            )
        )
        != len(
            capture_ids
        )
    ):
        raise ValueError(
            "Duplicate capture_id in temporal aggregation."
        )

    thresholds = {
        analysis[
            "freshness_threshold_ms"
        ]
        for analysis in analyses
    }

    if len(
        thresholds
    ) != 1:
        raise ValueError(
            "Temporal aggregation cannot mix "
            "freshness thresholds."
        )

    horizons = {
        analysis[
            "horizon_ms"
        ]
        for analysis in analyses
    }

    if len(
        horizons
    ) != 1:
        raise ValueError(
            "Temporal aggregation cannot mix horizons."
        )

    freshness_threshold_ms = next(
        iter(
            thresholds
        )
    )

    horizon_ms = next(
        iter(
            horizons
        )
    )

    all_rows = [
        row
        for analysis in analyses
        for row in analysis[
            "rows"
        ]
    ]

    status_counts = Counter(
        row[
            "status"
        ]
        for row in all_rows
    )

    evaluable_rows = [
        row
        for row in all_rows
        if row[
            "status"
        ]
        == EVALUABLE
    ]

    forward_values = [
        row[
            "coinbase_forward_mid_return_bps"
        ]
        for row in evaluable_rows
    ]

    contrast_values = [
        row[
            "kuru_proposed_finalized_mid_gap_bps"
        ]
        for row in evaluable_rows
    ]

    future_age_values = [
        row[
            "future_asof_age_ms"
        ]
        for row in evaluable_rows
    ]

    concordance_values = [
        row[
            "directional_concordance_bps"
        ]
        for row in evaluable_rows
        if row[
            "directional_concordance_bps"
        ]
        is not None
    ]

    contrast_counts = (
        _contrast_sign_counts(
            evaluable_rows
        )
    )

    capture_summaries = [
        _capture_summary(
            analysis
        )
        for analysis in analyses
    ]

    non_overlapping_rows = []

    per_capture_selected_counts = {}

    for analysis in analyses:
        selected = (
            select_non_overlapping_rows(
                analysis[
                    "rows"
                ],
                horizon_ms=
                    horizon_ms,
            )
        )

        per_capture_selected_counts[
            analysis[
                "capture_id"
            ]
        ] = len(
            selected
        )

        non_overlapping_rows.extend(
            selected
        )

    non_overlap_concordance = [
        row[
            "directional_concordance_bps"
        ]
        for row in non_overlapping_rows
        if row[
            "directional_concordance_bps"
        ]
        is not None
    ]

    return {
        "schema_version":
            SCHEMA_VERSION,
        "source_schema_version":
            SOURCE_SCHEMA_VERSION,
        "freshness_threshold_ms":
            freshness_threshold_ms,
        "horizon_ms":
            horizon_ms,
        "capture_count":
            len(
                analyses
            ),
        "capture_ids":
            list(
                capture_ids
            ),
        "claim_boundaries":
            list(
                CLAIM_BOUNDARIES
            ),
        "rows":
            len(
                all_rows
            ),
        "baseline_aligned_panels":
            sum(
                1
                for row in all_rows
                if row.get(
                    "alignment_status"
                )
                == ALIGNED
            ),
        "status_counts":
            dict(
                sorted(
                    status_counts.items()
                )
            ),
        "pooled": {
            "evaluable_rows":
                len(
                    evaluable_rows
                ),
            "forward_return_bps":
                _distribution(
                    forward_values
                ),
            "proposed_finalized_mid_gap_bps":
                _distribution(
                    contrast_values
                ),
            "directional_concordance_bps":
                _distribution(
                    concordance_values
                ),
            "future_asof_age_ms":
                _distribution(
                    future_age_values
                ),
            "contrast_sign_counts":
                contrast_counts,
            "zero_contrast_count":
                contrast_counts[
                    "ZERO"
                ],
            "nonzero_contrast_count":
                (
                    contrast_counts[
                        "POSITIVE"
                    ]
                    + contrast_counts[
                        "NEGATIVE"
                    ]
                ),
        },
        "capture_summaries":
            capture_summaries,
        "non_overlapping_sensitivity": {
            "selection_rule":
                "greedy_within_capture_t_next_gte_t_keep_plus_horizon",
            "selected_rows":
                len(
                    non_overlapping_rows
                ),
            "per_capture_selected_counts":
                dict(
                    per_capture_selected_counts
                ),
            "forward_return_bps":
                _distribution(
                    [
                        row[
                            "coinbase_forward_mid_return_bps"
                        ]
                        for row
                        in non_overlapping_rows
                    ]
                ),
            "proposed_finalized_mid_gap_bps":
                _distribution(
                    [
                        row[
                            "kuru_proposed_finalized_mid_gap_bps"
                        ]
                        for row
                        in non_overlapping_rows
                    ]
                ),
            "directional_concordance_bps":
                _distribution(
                    non_overlap_concordance
                ),
            "future_asof_age_ms":
                _distribution(
                    [
                        row[
                            "future_asof_age_ms"
                        ]
                        for row
                        in non_overlapping_rows
                    ]
                ),
            "contrast_sign_counts":
                _contrast_sign_counts(
                    non_overlapping_rows
                ),
        },
    }
