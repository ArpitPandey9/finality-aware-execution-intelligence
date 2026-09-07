from __future__ import annotations

from collections import Counter
from decimal import (
    Decimal,
    InvalidOperation,
    localcontext,
)

from finality_intelligence.alignment import (
    ALIGNED,
)
from finality_intelligence.market_instability import (
    PHASE3_ECONOMIC_FIELDS,
    SCHEMA_VERSION as SOURCE_SCHEMA_VERSION,
)
from finality_intelligence.staleness import (
    CORE_THRESHOLDS_MS,
    percentile,
)
from finality_intelligence.temporal_aggregation import (
    select_non_overlapping_rows,
)
from finality_intelligence.temporal_outcome import (
    EVALUABLE,
    FROZEN_HORIZONS_MS,
)


SCHEMA_VERSION = (
    "phase3.market_instability_aggregation.v1"
)

FROZEN_FRESHNESS_THRESHOLDS_MS = (
    CORE_THRESHOLDS_MS
)

MIN_DEFINED_CAPTURE_CORRELATIONS = 6

REQUIRED_CONFIRMATORY_CAPTURE_COUNT = 10

DEFINED = "DEFINED"
UNDEFINED = "UNDEFINED"

TOO_FEW_EVALUABLE_PAIRS = (
    "TOO_FEW_EVALUABLE_PAIRS"
)

ZERO_EXPOSURE_RANK_VARIANCE = (
    "ZERO_EXPOSURE_RANK_VARIANCE"
)

ZERO_OUTCOME_RANK_VARIANCE = (
    "ZERO_OUTCOME_RANK_VARIANCE"
)


CLAIM_BOUNDARIES = (
    "Spearman correlations are descriptive monotonic "
    "association measures and are not predictive or "
    "causal estimates.",
    "Pooled rows include overlapping future windows "
    "and are not statistically independent.",
    "Capture-level summaries are robustness views, "
    "not independent experimental replications.",
    "The deterministic non-overlapping sensitivity "
    "reduces mechanical overlap but does not create "
    "statistical independence.",
    "The 500 ms and 1000 ms baseline freshness "
    "populations are sensitivity analyses and cannot "
    "rescue an unfavorable 250 ms primary result.",
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
            "count": 0,
            "min": None,
            "p05": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p95": None,
            "max": None,
            "zero_count": 0,
        }

    return {
        "count":
            len(
                parsed
            ),
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
        "zero_count":
            sum(
                1
                for value in parsed
                if value == 0
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


def average_ranks(
    values,
) -> list[Decimal]:
    parsed = [
        _decimal(
            value,
            field="rank value",
        )
        for value in values
    ]

    indexed = sorted(
        enumerate(
            parsed
        ),
        key=lambda item: (
            item[1],
            item[0],
        ),
    )

    ranks = [
        Decimal("0")
        for _ in parsed
    ]

    position = 0

    while position < len(
        indexed
    ):
        end = position + 1

        while (
            end < len(indexed)
            and indexed[end][1]
            == indexed[position][1]
        ):
            end += 1

        first_rank = Decimal(
            position + 1
        )

        last_rank = Decimal(
            end
        )

        average = (
            first_rank
            + last_rank
        ) / Decimal("2")

        for offset in range(
            position,
            end,
        ):
            original_index = indexed[
                offset
            ][0]

            ranks[
                original_index
            ] = average

        position = end

    return ranks


def _undefined(
    *,
    pair_count: int,
    reason_code: str,
) -> dict:
    return {
        "status":
            UNDEFINED,
        "rho":
            None,
        "pair_count":
            pair_count,
        "reason_code":
            reason_code,
    }


def spearman_rank_correlation(
    exposures,
    outcomes,
) -> dict:
    x = [
        _decimal(
            value,
            field="exposure",
        )
        for value in exposures
    ]

    y = [
        _decimal(
            value,
            field="outcome",
        )
        for value in outcomes
    ]

    if len(x) != len(y):
        raise ValueError(
            "Exposure and outcome lengths differ."
        )

    n = len(x)

    if n < 2:
        return _undefined(
            pair_count=n,
            reason_code=(
                TOO_FEW_EVALUABLE_PAIRS
            ),
        )

    rx = average_ranks(
        x
    )

    ry = average_ranks(
        y
    )

    mean_x = sum(
        rx,
        Decimal("0"),
    ) / Decimal(n)

    mean_y = sum(
        ry,
        Decimal("0"),
    ) / Decimal(n)

    dx = [
        value - mean_x
        for value in rx
    ]

    dy = [
        value - mean_y
        for value in ry
    ]

    var_x = sum(
        (
            value * value
            for value in dx
        ),
        Decimal("0"),
    )

    var_y = sum(
        (
            value * value
            for value in dy
        ),
        Decimal("0"),
    )

    if var_x == 0:
        return _undefined(
            pair_count=n,
            reason_code=(
                ZERO_EXPOSURE_RANK_VARIANCE
            ),
        )

    if var_y == 0:
        return _undefined(
            pair_count=n,
            reason_code=(
                ZERO_OUTCOME_RANK_VARIANCE
            ),
        )

    covariance = sum(
        (
            left * right
            for left, right in zip(
                dx,
                dy,
            )
        ),
        Decimal("0"),
    )

    with localcontext() as context:
        context.prec = 50

        denominator = (
            var_x * var_y
        ).sqrt()

        rho = (
            covariance
            / denominator
        )

    return {
        "status":
            DEFINED,
        "rho":
            str(
                rho
            ),
        "pair_count":
            n,
        "reason_code":
            None,
    }


def _validate_analysis(
    analysis: dict,
) -> None:
    if (
        analysis.get(
            "schema_version"
        )
        != SOURCE_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unexpected Phase 3 analysis schema."
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
            "capture_id must be non-empty."
        )

    rows = analysis.get(
        "rows"
    )

    if not isinstance(
        rows,
        list,
    ):
        raise ValueError(
            "Phase 3 rows must be a list."
        )

    for row in rows:
        if (
            row.get(
                "capture_id"
            )
            != capture_id
        ):
            raise ValueError(
                "Phase 3 row capture_id mismatch."
            )

        if (
            row.get(
                "status"
            )
            == EVALUABLE
        ):
            for field in (
                PHASE3_ECONOMIC_FIELDS
            ):
                if row.get(
                    field
                ) is None:
                    raise ValueError(
                        "Evaluable Phase 3 row "
                        f"missing {field}."
                    )
        else:
            for field in (
                PHASE3_ECONOMIC_FIELDS
            ):
                if row.get(
                    field
                ) is not None:
                    raise ValueError(
                        "Non-evaluable Phase 3 row "
                        "carries economic values."
                    )


def _correlation_for_rows(
    rows: list[dict],
) -> dict:
    evaluable = [
        row
        for row in rows
        if row.get(
            "status"
        )
        == EVALUABLE
    ]

    return spearman_rank_correlation(
        [
            row[
                "kuru_pf_abs_gap_bps"
            ]
            for row in evaluable
        ],
        [
            row[
                "coinbase_abs_forward_mid_move_bps"
            ]
            for row in evaluable
        ],
    )


def _positive_defined(
    result: dict,
) -> bool:
    return (
        result.get(
            "status"
        )
        == DEFINED
        and _decimal(
            result[
                "rho"
            ],
            field="rho",
        )
        > 0
    )


def aggregate_market_instability(
    analyses: list[dict],
) -> dict:
    if (
        not isinstance(
            analyses,
            list,
        )
        or not analyses
    ):
        raise ValueError(
            "analyses must be a non-empty list."
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

    if len(
        set(
            capture_ids
        )
    ) != len(
        capture_ids
    ):
        raise ValueError(
            "Duplicate capture_id."
        )

    thresholds = {
        analysis[
            "freshness_threshold_ms"
        ]
        for analysis in analyses
    }

    horizons = {
        analysis[
            "horizon_ms"
        ]
        for analysis in analyses
    }

    if len(thresholds) != 1:
        raise ValueError(
            "Cannot mix freshness thresholds."
        )

    if len(horizons) != 1:
        raise ValueError(
            "Cannot mix horizons."
        )

    freshness = next(
        iter(
            thresholds
        )
    )

    horizon = next(
        iter(
            horizons
        )
    )

    if _decimal(
        freshness,
        field="freshness_threshold_ms",
    ) not in FROZEN_FRESHNESS_THRESHOLDS_MS:
        raise ValueError(
            "Non-frozen freshness threshold."
        )

    if _decimal(
        horizon,
        field="horizon_ms",
    ) not in FROZEN_HORIZONS_MS:
        raise ValueError(
            "Non-frozen horizon."
        )

    all_rows = [
        row
        for analysis in analyses
        for row in analysis[
            "rows"
        ]
    ]

    evaluable_rows = [
        row
        for row in all_rows
        if row[
            "status"
        ]
        == EVALUABLE
    ]

    pooled = _correlation_for_rows(
        all_rows
    )

    capture_correlations = []

    for analysis in analyses:
        result = _correlation_for_rows(
            analysis[
                "rows"
            ]
        )

        capture_correlations.append(
            {
                "capture_id":
                    analysis[
                        "capture_id"
                    ],
                **result,
            }
        )

    defined_capture_rhos = [
        item[
            "rho"
        ]
        for item
        in capture_correlations
        if item[
            "status"
        ]
        == DEFINED
    ]

    defined_capture_count = len(
        defined_capture_rhos
    )

    median_capture_rho = _median(
        defined_capture_rhos
    )

    non_overlapping_rows = []

    per_capture_selected_counts = {}

    for analysis in analyses:
        selected = select_non_overlapping_rows(
            analysis[
                "rows"
            ],
            horizon_ms=horizon,
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

    non_overlap = _correlation_for_rows(
        non_overlapping_rows
    )

    capture_median_positive = (
        median_capture_rho
        is not None
        and _decimal(
            median_capture_rho,
            field="median_capture_rho",
        )
        > 0
    )

    capture_robustness_available = (
        defined_capture_count
        >= MIN_DEFINED_CAPTURE_CORRELATIONS
    )

    capture_sample_complete = (
        len(
            analyses
        )
        == REQUIRED_CONFIRMATORY_CAPTURE_COUNT
    )

    directionally_supportive = (
        capture_sample_complete
        and _positive_defined(
            pooled
        )
        and capture_robustness_available
        and capture_median_positive
        and _positive_defined(
            non_overlap
        )
    )

    status_counts = Counter(
        row[
            "status"
        ]
        for row in all_rows
    )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "source_schema_version":
            SOURCE_SCHEMA_VERSION,
        "freshness_threshold_ms":
            freshness,
        "horizon_ms":
            horizon,
        "capture_count":
            len(
                analyses
            ),
        "capture_ids":
            list(
                capture_ids
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
            "evaluable_pairs":
                len(
                    evaluable_rows
                ),
            "spearman":
                pooled,
            "kuru_pf_abs_gap_bps":
                _distribution(
                    [
                        row[
                            "kuru_pf_abs_gap_bps"
                        ]
                        for row
                        in evaluable_rows
                    ]
                ),
            "coinbase_abs_forward_mid_move_bps":
                _distribution(
                    [
                        row[
                            "coinbase_abs_forward_mid_move_bps"
                        ]
                        for row
                        in evaluable_rows
                    ]
                ),
            "zero_exposure_count":
                sum(
                    1
                    for row
                    in evaluable_rows
                    if _decimal(
                        row[
                            "kuru_pf_abs_gap_bps"
                        ],
                        field=(
                            "kuru_pf_abs_gap_bps"
                        ),
                    )
                    == 0
                ),
        },
        "capture_level": {
            "correlations":
                capture_correlations,
            "defined_count":
                defined_capture_count,
            "undefined_count":
                (
                    len(
                        capture_correlations
                    )
                    - defined_capture_count
                ),
            "minimum_defined_required":
                MIN_DEFINED_CAPTURE_CORRELATIONS,
            "confirmatory_capture_count_required":
                REQUIRED_CONFIRMATORY_CAPTURE_COUNT,
            "capture_sample_complete":
                capture_sample_complete,
            "robustness_available":
                capture_robustness_available,
            "median_defined_rho":
                median_capture_rho,
        },
        "non_overlapping_sensitivity": {
            "selection_rule":
                (
                    "greedy_within_capture_"
                    "t_next_gte_t_keep_plus_horizon"
                ),
            "selected_rows":
                len(
                    non_overlapping_rows
                ),
            "per_capture_selected_counts":
                dict(
                    per_capture_selected_counts
                ),
            "spearman":
                non_overlap,
        },
        "descriptive_support": {
            "capture_sample_complete":
                capture_sample_complete,
            "pooled_defined_and_positive":
                _positive_defined(
                    pooled
                ),
            "capture_defined_count_sufficient":
                capture_robustness_available,
            "capture_median_positive":
                capture_median_positive,
            "non_overlap_defined_and_positive":
                _positive_defined(
                    non_overlap
                ),
            "directionally_supportive":
                directionally_supportive,
        },
        "claim_boundaries":
            list(
                CLAIM_BOUNDARIES
            ),
    }
