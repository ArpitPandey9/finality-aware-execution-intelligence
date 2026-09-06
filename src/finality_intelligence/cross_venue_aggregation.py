from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation

from finality_intelligence.alignment import (
    ALIGNED,
    INSUFFICIENT_SOURCE_EVIDENCE,
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
)
from finality_intelligence.cross_venue_execution import (
    BOTH_FULL,
    CLAIM_BOUNDARIES,
    COINBASE_ONLY_FULL,
    ECONOMICALLY_ELIGIBLE,
    FILLABILITY_TRANSITIONS,
    INVALID_COINBASE_RECONSTRUCTION,
    INVALID_KURU_PANEL,
    KURU_ONLY_FULL,
    NEITHER_FULL,
    SCHEMA_VERSION as ANALYSIS_SCHEMA_VERSION,
    STATE_ORDER,
)
from finality_intelligence.depth_execution import (
    DEPTH_BANDS_BPS,
    FULLY_FILLED_IN_CAPTURED_BOOK,
    INSUFFICIENT_CAPTURED_DEPTH,
    SIDES,
    TARGET_BASE_QUANTITIES,
)
from finality_intelligence.staleness import (
    CORE_THRESHOLDS_MS,
    percentile,
)


SCHEMA_VERSION = (
    "phase1.cross_venue_execution_aggregation.v1"
)

ALIGNMENT_STATUSES = (
    ALIGNED,
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
    INSUFFICIENT_SOURCE_EVIDENCE,
)

ECONOMIC_OUTCOMES = (
    ECONOMICALLY_ELIGIBLE,
    INVALID_KURU_PANEL,
    INVALID_COINBASE_RECONSTRUCTION,
)

AGGREGATION_CLAIM_BOUNDARIES = (
    "Pooled cross-venue summaries are descriptive; "
    "the capture windows are not assumed to be "
    "independent observations.",
    "The 250 ms, 500 ms, and 1000 ms reference-age "
    "bands are nested sensitivity analyses over "
    "overlapping observations.",
    "Fillability transitions describe deterministic "
    "outcomes inside captured displayed books and are "
    "not execution probabilities.",
    "Slippage and displayed-depth gaps are static-book "
    "descriptive differences, not trading edge, "
    "arbitrage, profitability, or venue ranking.",
    "Cross-quote VWAP differences mix Kuru USDC quotes "
    "and Coinbase USD quotes; USD/USDC basis risk is "
    "not removed.",
    "State-conditioned summaries compare simultaneous "
    "Kuru state views against one selected Coinbase "
    "reference and do not establish a causal finality "
    "effect.",
)


def _decimal(
    value,
    *,
    name: str,
) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(
            f"{name} must use an exact numeric value."
        )

    if isinstance(value, float):
        raise TypeError(
            f"{name} must not use binary float."
        )

    if isinstance(value, Decimal):
        parsed = value

    elif isinstance(value, int):
        parsed = Decimal(value)

    elif isinstance(value, str):
        try:
            parsed = Decimal(value)
        except InvalidOperation:
            raise ValueError(
                f"{name} is not a valid Decimal."
            ) from None

    else:
        raise TypeError(
            f"{name} must be Decimal, int, or string."
        )

    if not parsed.is_finite():
        raise ValueError(
            f"{name} must be finite."
        )

    return parsed


def _nonnegative_int(
    value,
    *,
    name: str,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise ValueError(
            f"{name} must be a non-negative integer."
        )

    return value


def _distribution(
    values,
) -> dict:
    xs = [
        _decimal(
            value,
            name="distribution value",
        )
        for value in values
    ]

    if not xs:
        return {
            "count": 0,
            "min": None,
            "p05": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p95": None,
            "max": None,
        }

    return {
        "count": len(xs),
        "min": str(min(xs)),
        "p05": str(
            percentile(
                xs,
                Decimal("0.05"),
            )
        ),
        "p25": str(
            percentile(
                xs,
                Decimal("0.25"),
            )
        ),
        "p50": str(
            percentile(
                xs,
                Decimal("0.50"),
            )
        ),
        "p75": str(
            percentile(
                xs,
                Decimal("0.75"),
            )
        ),
        "p95": str(
            percentile(
                xs,
                Decimal("0.95"),
            )
        ),
        "max": str(max(xs)),
    }


def _median(
    values,
) -> str | None:
    xs = [
        _decimal(
            value,
            name="median value",
        )
        for value in values
    ]

    if not xs:
        return None

    return str(
        percentile(
            xs,
            Decimal("0.50"),
        )
    )


def _sign_counts(
    values,
) -> dict:
    xs = [
        _decimal(
            value,
            name="signed value",
        )
        for value in values
    ]

    return {
        "positive": sum(
            value > 0
            for value in xs
        ),
        "zero": sum(
            value == 0
            for value in xs
        ),
        "negative": sum(
            value < 0
            for value in xs
        ),
    }


def _normalize_counts(
    raw,
    *,
    allowed,
    name: str,
) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(
            f"{name} must be a mapping."
        )

    unexpected = (
        set(raw)
        - set(allowed)
    )

    if unexpected:
        raise ValueError(
            f"{name} contains unexpected outcomes: "
            f"{sorted(unexpected)}"
        )

    result = {}

    for outcome in allowed:
        value = raw.get(
            outcome,
            0,
        )

        result[outcome] = (
            _nonnegative_int(
                value,
                name=(
                    f"{name}:{outcome}"
                ),
            )
        )

    return result


def _expected_transition(
    kuru_status: str,
    coinbase_status: str,
) -> str:
    kuru_full = (
        kuru_status
        == FULLY_FILLED_IN_CAPTURED_BOOK
    )

    coinbase_full = (
        coinbase_status
        == FULLY_FILLED_IN_CAPTURED_BOOK
    )

    valid_statuses = {
        FULLY_FILLED_IN_CAPTURED_BOOK,
        INSUFFICIENT_CAPTURED_DEPTH,
    }

    if (
        kuru_status not in valid_statuses
        or coinbase_status not in valid_statuses
    ):
        raise ValueError(
            "Unexpected venue fillability status."
        )

    if kuru_full and coinbase_full:
        return BOTH_FULL

    if kuru_full:
        return KURU_ONLY_FULL

    if coinbase_full:
        return COINBASE_ONLY_FULL

    return NEITHER_FULL


def _validate_venue_execution(
    row: dict,
    *,
    venue: str,
    target: Decimal,
) -> None:
    status = row.get(
        f"{venue}_fillability_status"
    )

    filled = _decimal(
        row.get(
            f"{venue}_filled_base_MON"
        ),
        name=(
            f"{venue}_filled_base_MON"
        ),
    )

    total_depth = _decimal(
        row.get(
            f"{venue}_total_captured_depth_MON"
        ),
        name=(
            f"{venue}_total_captured_depth_MON"
        ),
    )

    best_price = _decimal(
        row.get(
            f"{venue}_best_price"
        ),
        name=(
            f"{venue}_best_price"
        ),
    )

    levels_touched = _nonnegative_int(
        row.get(
            f"{venue}_levels_touched"
        ),
        name=(
            f"{venue}_levels_touched"
        ),
    )

    if (
        filled < 0
        or total_depth < 0
        or best_price <= 0
        or levels_touched < 0
    ):
        raise ValueError(
            "Venue execution numeric fields invalid."
        )

    vwap_field = (
        "kuru_vwap_USDC_per_MON"
        if venue == "kuru"
        else "coinbase_vwap_USD_per_MON"
    )

    slippage_field = (
        f"{venue}_slippage_bps"
    )

    if (
        status
        == FULLY_FILLED_IN_CAPTURED_BOOK
    ):
        if filled != target:
            raise ValueError(
                "Full-fill quantity does not "
                "reconcile to target."
            )

        vwap = _decimal(
            row.get(vwap_field),
            name=vwap_field,
        )

        slippage = _decimal(
            row.get(slippage_field),
            name=slippage_field,
        )

        if (
            vwap <= 0
            or slippage < 0
        ):
            raise ValueError(
                "Full-fill VWAP/slippage invalid."
            )

    elif (
        status
        == INSUFFICIENT_CAPTURED_DEPTH
    ):
        if filled >= target:
            raise ValueError(
                "Insufficient-depth fill quantity "
                "must be below target."
            )

        if (
            row.get(vwap_field)
            is not None
            or row.get(
                slippage_field
            )
            is not None
        ):
            raise ValueError(
                "Insufficient-depth execution must "
                "not report target VWAP/slippage."
            )

    else:
        raise ValueError(
            "Unknown venue fillability status."
        )


def _validate_execution_row(
    row: dict,
    *,
    capture_id: str,
    threshold: Decimal,
) -> tuple:
    if not isinstance(row, dict):
        raise ValueError(
            "Execution row must be a mapping."
        )

    if (
        row.get("capture_id")
        != capture_id
    ):
        raise ValueError(
            "Execution row capture_id mismatch."
        )

    row_threshold = _decimal(
        row.get(
            "freshness_threshold_ms"
        ),
        name="freshness_threshold_ms",
    )

    if row_threshold != threshold:
        raise ValueError(
            "Execution row threshold mismatch."
        )

    record_index = _nonnegative_int(
        row.get(
            "kuru_record_index"
        ),
        name="kuru_record_index",
    )

    state = row.get("state")
    side = row.get("side")

    if state not in STATE_ORDER:
        raise ValueError(
            "Unexpected Kuru state."
        )

    if side not in SIDES:
        raise ValueError(
            "Unexpected execution side."
        )

    target = _decimal(
        row.get(
            "target_base_MON"
        ),
        name="target_base_MON",
    )

    if (
        target
        not in TARGET_BASE_QUANTITIES
    ):
        raise ValueError(
            "Execution target is not frozen."
        )

    if (
        row.get(
            "alignment_status"
        )
        != ALIGNED
    ):
        raise ValueError(
            "Economic execution row must be ALIGNED."
        )

    coinbase_index = (
        _nonnegative_int(
            row.get(
                "coinbase_record_index"
            ),
            name="coinbase_record_index",
        )
    )

    sequence_num = (
        _nonnegative_int(
            row.get(
                "coinbase_sequence_num"
            ),
            name="coinbase_sequence_num",
        )
    )

    kuru_ns = _nonnegative_int(
        row.get(
            "kuru_received_monotonic_ns"
        ),
        name=(
            "kuru_received_monotonic_ns"
        ),
    )

    coinbase_ns = _nonnegative_int(
        row.get(
            "coinbase_received_monotonic_ns"
        ),
        name=(
            "coinbase_received_monotonic_ns"
        ),
    )

    if coinbase_ns > kuru_ns:
        raise ValueError(
            "Future Coinbase reference detected."
        )

    age = _decimal(
        row.get(
            "reference_age_ms"
        ),
        name="reference_age_ms",
    )

    if (
        age < 0
        or age > threshold
    ):
        raise ValueError(
            "Execution reference age invalid."
        )

    _validate_venue_execution(
        row,
        venue="kuru",
        target=target,
    )

    _validate_venue_execution(
        row,
        venue="coinbase",
        target=target,
    )

    transition = row.get(
        "fillability_transition"
    )

    expected_transition = (
        _expected_transition(
            row.get(
                "kuru_fillability_status"
            ),
            row.get(
                "coinbase_fillability_status"
            ),
        )
    )

    if transition != expected_transition:
        raise ValueError(
            "Fillability transition does "
            "not reconcile."
        )

    if (
        transition
        not in FILLABILITY_TRANSITIONS
    ):
        raise ValueError(
            "Unexpected fillability transition."
        )

    if transition == BOTH_FULL:
        kuru_slippage = _decimal(
            row.get(
                "kuru_slippage_bps"
            ),
            name="kuru_slippage_bps",
        )

        coinbase_slippage = _decimal(
            row.get(
                "coinbase_slippage_bps"
            ),
            name="coinbase_slippage_bps",
        )

        gap = _decimal(
            row.get(
                "slippage_gap_bps"
            ),
            name="slippage_gap_bps",
        )

        if (
            gap
            !=
            kuru_slippage
            - coinbase_slippage
        ):
            raise ValueError(
                "Slippage gap arithmetic mismatch."
            )

        kuru_vwap = _decimal(
            row.get(
                "kuru_vwap_USDC_per_MON"
            ),
            name="kuru_vwap_USDC_per_MON",
        )

        coinbase_vwap = _decimal(
            row.get(
                "coinbase_vwap_USD_per_MON"
            ),
            name="coinbase_vwap_USD_per_MON",
        )

        cross_quote = _decimal(
            row.get(
                "cross_quote_vwap_difference_bps"
            ),
            name=(
                "cross_quote_vwap_difference_bps"
            ),
        )

        expected_cross_quote = (
            (
                kuru_vwap
                - coinbase_vwap
            )
            / coinbase_vwap
            * Decimal("10000")
        )

        if (
            cross_quote
            != expected_cross_quote
        ):
            raise ValueError(
                "Cross-quote VWAP difference "
                "arithmetic mismatch."
            )

    else:
        if (
            row.get(
                "slippage_gap_bps"
            )
            is not None
            or row.get(
                "cross_quote_vwap_difference_bps"
            )
            is not None
        ):
            raise ValueError(
                "Non-both-full row must not "
                "report cross-venue execution gaps."
            )

    key = (
        record_index,
        state,
        side,
        str(target),
    )

    reference = (
        coinbase_index,
        sequence_num,
        str(age),
    )

    return (
        key,
        record_index,
        reference,
    )


def _validate_depth_row(
    row: dict,
    *,
    capture_id: str,
    threshold: Decimal,
) -> tuple:
    if not isinstance(row, dict):
        raise ValueError(
            "Depth row must be a mapping."
        )

    if (
        row.get("capture_id")
        != capture_id
    ):
        raise ValueError(
            "Depth row capture_id mismatch."
        )

    row_threshold = _decimal(
        row.get(
            "freshness_threshold_ms"
        ),
        name="freshness_threshold_ms",
    )

    if row_threshold != threshold:
        raise ValueError(
            "Depth row threshold mismatch."
        )

    record_index = _nonnegative_int(
        row.get(
            "kuru_record_index"
        ),
        name="kuru_record_index",
    )

    state = row.get("state")
    side = row.get("side")

    if state not in STATE_ORDER:
        raise ValueError(
            "Unexpected Kuru state."
        )

    if side not in SIDES:
        raise ValueError(
            "Unexpected depth side."
        )

    band = _decimal(
        row.get(
            "band_bps"
        ),
        name="band_bps",
    )

    if band not in DEPTH_BANDS_BPS:
        raise ValueError(
            "Depth band is not frozen."
        )

    coinbase_index = (
        _nonnegative_int(
            row.get(
                "coinbase_record_index"
            ),
            name="coinbase_record_index",
        )
    )

    sequence_num = (
        _nonnegative_int(
            row.get(
                "coinbase_sequence_num"
            ),
            name="coinbase_sequence_num",
        )
    )

    age = _decimal(
        row.get(
            "reference_age_ms"
        ),
        name="reference_age_ms",
    )

    if (
        age < 0
        or age > threshold
    ):
        raise ValueError(
            "Depth reference age invalid."
        )

    kuru_depth = _decimal(
        row.get(
            "kuru_depth_MON"
        ),
        name="kuru_depth_MON",
    )

    coinbase_depth = _decimal(
        row.get(
            "coinbase_depth_MON"
        ),
        name="coinbase_depth_MON",
    )

    gap = _decimal(
        row.get(
            "depth_gap_MON"
        ),
        name="depth_gap_MON",
    )

    if (
        kuru_depth < 0
        or coinbase_depth < 0
    ):
        raise ValueError(
            "Displayed depth must be non-negative."
        )

    if (
        gap
        !=
        kuru_depth
        - coinbase_depth
    ):
        raise ValueError(
            "Depth-gap arithmetic mismatch."
        )

    key = (
        record_index,
        state,
        side,
        str(band),
    )

    reference = (
        coinbase_index,
        sequence_num,
        str(age),
    )

    return (
        key,
        record_index,
        reference,
    )


def _validate_analysis(
    analysis: dict,
) -> dict:
    if not isinstance(analysis, dict):
        raise ValueError(
            "Cross-venue analysis must be a mapping."
        )

    if (
        analysis.get(
            "schema_version"
        )
        != ANALYSIS_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unexpected cross-venue "
            "analysis schema version."
        )

    capture_id = analysis.get(
        "capture_id"
    )

    if (
        not isinstance(capture_id, str)
        or not capture_id
    ):
        raise ValueError(
            "Analysis capture_id invalid."
        )

    threshold = _decimal(
        analysis.get(
            "freshness_threshold_ms"
        ),
        name="freshness_threshold_ms",
    )

    if threshold not in CORE_THRESHOLDS_MS:
        raise ValueError(
            "Aggregation accepts only frozen "
            "reference-age thresholds."
        )

    reasons = analysis.get(
        "source_evidence_reasons"
    )

    if not isinstance(reasons, list):
        raise ValueError(
            "Source evidence reasons must be a list."
        )

    if reasons:
        raise ValueError(
            "Insufficient source evidence must not "
            "enter economic aggregation."
        )

    summary = analysis.get("summary")

    if not isinstance(summary, dict):
        raise ValueError(
            "Analysis summary missing."
        )

    observations = _nonnegative_int(
        summary.get(
            "kuru_observations"
        ),
        name="kuru_observations",
    )

    alignment_counts = (
        _normalize_counts(
            summary.get(
                "alignment_status_counts"
            ),
            allowed=ALIGNMENT_STATUSES,
            name="alignment_status_counts",
        )
    )

    economic_counts = (
        _normalize_counts(
            summary.get(
                "economic_eligibility_counts"
            ),
            allowed=ECONOMIC_OUTCOMES,
            name=(
                "economic_eligibility_counts"
            ),
        )
    )

    if (
        sum(
            alignment_counts.values()
        )
        != observations
    ):
        raise ValueError(
            "Alignment counts do not reconcile "
            "to Kuru observations."
        )

    if (
        sum(
            economic_counts.values()
        )
        != alignment_counts[ALIGNED]
    ):
        raise ValueError(
            "Economic eligibility outcomes do not "
            "reconcile to aligned observations."
        )

    eligible = economic_counts[
        ECONOMICALLY_ELIGIBLE
    ]

    execution_rows = analysis.get(
        "rows"
    )

    depth_rows = analysis.get(
        "depth_rows"
    )

    if not isinstance(
        execution_rows,
        list,
    ):
        raise ValueError(
            "Execution rows must be a list."
        )

    if not isinstance(
        depth_rows,
        list,
    ):
        raise ValueError(
            "Depth rows must be a list."
        )

    expected_execution_rows = (
        eligible
        * len(STATE_ORDER)
        * len(SIDES)
        * len(
            TARGET_BASE_QUANTITIES
        )
    )

    expected_depth_rows = (
        eligible
        * len(STATE_ORDER)
        * len(SIDES)
        * len(
            DEPTH_BANDS_BPS
        )
    )

    for name, expected, actual in (
        (
            "execution_rows",
            expected_execution_rows,
            len(execution_rows),
        ),
        (
            "depth_rows",
            expected_depth_rows,
            len(depth_rows),
        ),
    ):
        summary_value = _nonnegative_int(
            summary.get(name),
            name=name,
        )

        if (
            summary_value != actual
            or actual != expected
        ):
            raise ValueError(
                f"{name} does not reconcile "
                "to economic eligibility."
            )

    execution_keys = set()
    depth_keys = set()

    execution_combos = defaultdict(set)
    depth_combos = defaultdict(set)

    execution_refs = defaultdict(set)
    depth_refs = defaultdict(set)

    for row in execution_rows:
        (
            key,
            record_index,
            reference,
        ) = _validate_execution_row(
            row,
            capture_id=capture_id,
            threshold=threshold,
        )

        if key in execution_keys:
            raise ValueError(
                "Duplicate execution row."
            )

        execution_keys.add(key)

        execution_combos[
            record_index
        ].add(
            key[1:]
        )

        execution_refs[
            record_index
        ].add(reference)

    for row in depth_rows:
        (
            key,
            record_index,
            reference,
        ) = _validate_depth_row(
            row,
            capture_id=capture_id,
            threshold=threshold,
        )

        if key in depth_keys:
            raise ValueError(
                "Duplicate depth row."
            )

        depth_keys.add(key)

        depth_combos[
            record_index
        ].add(
            key[1:]
        )

        depth_refs[
            record_index
        ].add(reference)

    if (
        len(execution_combos)
        != eligible
        or len(depth_combos)
        != eligible
    ):
        raise ValueError(
            "Economic observation count mismatch."
        )

    if (
        set(execution_combos)
        != set(depth_combos)
    ):
        raise ValueError(
            "Execution and depth observations differ."
        )

    expected_execution_combos = {
        (
            state,
            side,
            str(target),
        )
        for state in STATE_ORDER
        for side in SIDES
        for target in TARGET_BASE_QUANTITIES
    }

    expected_depth_combos = {
        (
            state,
            side,
            str(band),
        )
        for state in STATE_ORDER
        for side in SIDES
        for band in DEPTH_BANDS_BPS
    }

    for record_index in (
        execution_combos
    ):
        if (
            execution_combos[
                record_index
            ]
            != expected_execution_combos
        ):
            raise ValueError(
                "Execution observation does not "
                "contain the complete frozen grid."
            )

        if (
            depth_combos[
                record_index
            ]
            != expected_depth_combos
        ):
            raise ValueError(
                "Depth observation does not contain "
                "the complete frozen grid."
            )

        if (
            len(
                execution_refs[
                    record_index
                ]
            )
            != 1
            or len(
                depth_refs[
                    record_index
                ]
            )
            != 1
        ):
            raise ValueError(
                "One Kuru observation must use one "
                "Coinbase reference."
            )

        if (
            next(
                iter(
                    execution_refs[
                        record_index
                    ]
                )
            )
            !=
            next(
                iter(
                    depth_refs[
                        record_index
                    ]
                )
            )
        ):
            raise ValueError(
                "Execution and depth rows must share "
                "the same Coinbase reference."
            )

    return {
        "capture_id": capture_id,
        "threshold": threshold,
        "kuru_observations":
            observations,
        "alignment_counts":
            alignment_counts,
        "economic_counts":
            economic_counts,
        "eligible_panels":
            eligible,
    }


def _transition_counts(
    rows,
) -> dict:
    counts = Counter(
        row[
            "fillability_transition"
        ]
        for row in rows
    )

    return {
        transition:
            counts[transition]
        for transition
        in FILLABILITY_TRANSITIONS
    }


def _eligibility_summary(
    analyses: list[dict],
    validated: list[dict],
) -> dict:
    alignment_totals = Counter()
    economic_totals = Counter()

    capture_summaries = []

    observations = 0
    eligible = 0

    for analysis, item in zip(
        analyses,
        validated,
    ):
        alignment_totals.update(
            item["alignment_counts"]
        )

        economic_totals.update(
            item["economic_counts"]
        )

        observations += (
            item["kuru_observations"]
        )

        eligible += (
            item["eligible_panels"]
        )

        capture_summaries.append(
            {
                "capture_id":
                    item["capture_id"],
                "kuru_observations":
                    item[
                        "kuru_observations"
                    ],
                "alignment_status_counts":
                    dict(
                        item[
                            "alignment_counts"
                        ]
                    ),
                "economic_eligibility_counts":
                    dict(
                        item[
                            "economic_counts"
                        ]
                    ),
                "execution_rows":
                    len(
                        analysis["rows"]
                    ),
                "depth_rows":
                    len(
                        analysis[
                            "depth_rows"
                        ]
                    ),
            }
        )

    return {
        "kuru_observations":
            observations,
        "economic_panel_count":
            eligible,
        "alignment_status_counts": {
            status:
                alignment_totals[
                    status
                ]
            for status
            in ALIGNMENT_STATUSES
        },
        "economic_eligibility_counts": {
            outcome:
                economic_totals[
                    outcome
                ]
            for outcome
            in ECONOMIC_OUTCOMES
        },
        "capture_summaries":
            capture_summaries,
    }


def _execution_summaries(
    analyses: list[dict],
) -> dict:
    result = {}

    for state in STATE_ORDER:
        result[state] = {}

        for side in SIDES:
            result[state][side] = {}

            for target in (
                TARGET_BASE_QUANTITIES
            ):
                target_key = str(target)

                pooled = [
                    row
                    for analysis
                    in analyses
                    for row
                    in analysis["rows"]
                    if (
                        row["state"]
                        == state
                        and row["side"]
                        == side
                        and row[
                            "target_base_MON"
                        ]
                        == target_key
                    )
                ]

                both_full = [
                    row
                    for row in pooled
                    if row[
                        "fillability_transition"
                    ]
                    == BOTH_FULL
                ]

                slippage_values = [
                    row[
                        "slippage_gap_bps"
                    ]
                    for row in both_full
                ]

                cross_quote_values = [
                    row[
                        "cross_quote_vwap_difference_bps"
                    ]
                    for row in both_full
                ]

                capture_summaries = []

                for analysis in analyses:
                    capture_rows = [
                        row
                        for row
                        in analysis["rows"]
                        if (
                            row["state"]
                            == state
                            and row["side"]
                            == side
                            and row[
                                "target_base_MON"
                            ]
                            == target_key
                        )
                    ]

                    capture_both = [
                        row
                        for row
                        in capture_rows
                        if row[
                            "fillability_transition"
                        ]
                        == BOTH_FULL
                    ]

                    capture_summaries.append(
                        {
                            "capture_id":
                                analysis[
                                    "capture_id"
                                ],
                            "row_count":
                                len(
                                    capture_rows
                                ),
                            "fillability_transition_counts":
                                _transition_counts(
                                    capture_rows
                                ),
                            "both_full_count":
                                len(
                                    capture_both
                                ),
                            "slippage_gap_bps_p50":
                                _median(
                                    row[
                                        "slippage_gap_bps"
                                    ]
                                    for row
                                    in capture_both
                                ),
                            "cross_quote_vwap_difference_bps_p50":
                                _median(
                                    row[
                                        "cross_quote_vwap_difference_bps"
                                    ]
                                    for row
                                    in capture_both
                                ),
                        }
                    )

                result[
                    state
                ][
                    side
                ][
                    target_key
                ] = {
                    "row_count":
                        len(pooled),
                    "fillability_transition_counts":
                        _transition_counts(
                            pooled
                        ),
                    "both_full_count":
                        len(both_full),
                    "slippage_gap_bps": {
                        "distribution":
                            _distribution(
                                slippage_values
                            ),
                        "sign_counts":
                            _sign_counts(
                                slippage_values
                            ),
                    },
                    "cross_quote_vwap_difference_bps": {
                        "distribution":
                            _distribution(
                                cross_quote_values
                            ),
                        "sign_counts":
                            _sign_counts(
                                cross_quote_values
                            ),
                    },
                    "capture_summaries":
                        capture_summaries,
                }

    return result


def _depth_summaries(
    analyses: list[dict],
) -> dict:
    result = {}

    for state in STATE_ORDER:
        result[state] = {}

        for side in SIDES:
            result[state][side] = {}

            for band in DEPTH_BANDS_BPS:
                band_key = str(band)

                pooled = [
                    row
                    for analysis
                    in analyses
                    for row
                    in analysis[
                        "depth_rows"
                    ]
                    if (
                        row["state"]
                        == state
                        and row["side"]
                        == side
                        and row[
                            "band_bps"
                        ]
                        == band_key
                    )
                ]

                values = [
                    row[
                        "depth_gap_MON"
                    ]
                    for row in pooled
                ]

                capture_summaries = []

                for analysis in analyses:
                    capture_rows = [
                        row
                        for row
                        in analysis[
                            "depth_rows"
                        ]
                        if (
                            row["state"]
                            == state
                            and row["side"]
                            == side
                            and row[
                                "band_bps"
                            ]
                            == band_key
                        )
                    ]

                    capture_summaries.append(
                        {
                            "capture_id":
                                analysis[
                                    "capture_id"
                                ],
                            "row_count":
                                len(
                                    capture_rows
                                ),
                            "depth_gap_MON_p50":
                                _median(
                                    row[
                                        "depth_gap_MON"
                                    ]
                                    for row
                                    in capture_rows
                                ),
                        }
                    )

                result[
                    state
                ][
                    side
                ][
                    band_key
                ] = {
                    "row_count":
                        len(pooled),
                    "depth_gap_MON": {
                        "distribution":
                            _distribution(
                                values
                            ),
                        "sign_counts":
                            _sign_counts(
                                values
                            ),
                    },
                    "capture_summaries":
                        capture_summaries,
                }

    return result


def aggregate_cross_venue_execution(
    analyses: list[dict],
) -> dict:
    if not analyses:
        raise ValueError(
            "At least one cross-venue analysis "
            "is required."
        )

    validated = [
        _validate_analysis(
            analysis
        )
        for analysis in analyses
    ]

    capture_ids = [
        item["capture_id"]
        for item in validated
    ]

    if (
        len(set(capture_ids))
        != len(capture_ids)
    ):
        raise ValueError(
            "Capture identifiers must be unique."
        )

    thresholds = {
        item["threshold"]
        for item in validated
    }

    if len(thresholds) != 1:
        raise ValueError(
            "Aggregation requires one freshness "
            "threshold at a time."
        )

    threshold = next(
        iter(thresholds)
    )

    eligible = sum(
        item[
            "eligible_panels"
        ]
        for item in validated
    )

    if eligible == 0:
        raise ValueError(
            "Aggregation requires at least one "
            "economically eligible observation."
        )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "freshness_threshold_ms":
            str(threshold),
        "capture_count":
            len(analyses),
        "economic_panel_count":
            eligible,
        "eligibility_summary":
            _eligibility_summary(
                analyses,
                validated,
            ),
        "execution_summaries":
            _execution_summaries(
                analyses
            ),
        "depth_summaries":
            _depth_summaries(
                analyses
            ),
        "claim_boundaries": [
            *CLAIM_BOUNDARIES,
            *AGGREGATION_CLAIM_BOUNDARIES,
        ],
    }
