from __future__ import annotations

from decimal import Decimal, InvalidOperation

from finality_intelligence.depth_execution import (
    DEPTH_BANDS_BPS,
    FULLY_FILLED_IN_CAPTURED_BOOK,
    INSUFFICIENT_CAPTURED_DEPTH,
    SIDES,
    TARGET_BASE_QUANTITIES,
)
from finality_intelligence.depth_panel import (
    CLAIM_BOUNDARIES as PANEL_CLAIM_BOUNDARIES,
    EXECUTION_PANEL_ELIGIBLE,
    PANEL_OUTCOMES,
    SCHEMA_VERSION as PANEL_SCHEMA_VERSION,
    STATE_ORDER,
)
from finality_intelligence.staleness import (
    percentile,
)


SCHEMA_VERSION = (
    "phase1.state_conditioned_depth_aggregation.v1"
)

STATE_PAIRS = (
    ("proposed", "voted"),
    ("proposed", "finalized"),
    ("proposed", "committed"),
    ("voted", "finalized"),
    ("finalized", "committed"),
)

AGGREGATION_CLAIM_BOUNDARIES = (
    "Pooled depth and simulated-execution summaries "
    "are descriptive; capture windows are not assumed "
    "to be independent observations.",
    "Full-fill proportions describe deterministic "
    "outcomes inside captured displayed books, not "
    "execution probabilities.",
    "Paired state-view deltas compare simultaneous "
    "views and do not establish temporal progression "
    "or causal finality effects.",
)


def _decimal(
    value,
    *,
    name: str,
) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(
            f"{name} must be an exact numeric value."
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
    xs = list(values)

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


def _rate(
    numerator: int,
    denominator: int,
) -> str | None:
    if denominator == 0:
        return None

    return str(
        Decimal(numerator)
        / Decimal(denominator)
    )


def _validate_sweep(
    sweep: dict,
    *,
    side: str,
    target: Decimal,
    total_depth: Decimal,
) -> None:
    if not isinstance(sweep, dict):
        raise ValueError(
            "Sweep payload must be a mapping."
        )

    if sweep.get("side") != side:
        raise ValueError(
            "Sweep side does not match summary side."
        )

    observed_target = _decimal(
        sweep.get("target_base"),
        name="target_base",
    )

    if observed_target != target:
        raise ValueError(
            "Sweep target does not match frozen target."
        )

    observed_total = _decimal(
        sweep.get(
            "total_captured_base_depth"
        ),
        name="total_captured_base_depth",
    )

    if observed_total != total_depth:
        raise ValueError(
            "Sweep total depth does not reconcile."
        )

    filled = _decimal(
        sweep.get("filled_base"),
        name="filled_base",
    )
    unfilled = _decimal(
        sweep.get("unfilled_base"),
        name="unfilled_base",
    )
    quote_amount = _decimal(
        sweep.get("quote_amount"),
        name="quote_amount",
    )
    best_price = _decimal(
        sweep.get("best_price"),
        name="best_price",
    )

    if (
        filled < 0
        or unfilled < 0
        or quote_amount < 0
        or best_price <= 0
    ):
        raise ValueError(
            "Sweep numeric fields are invalid."
        )

    if filled + unfilled != target:
        raise ValueError(
            "Filled and unfilled quantity "
            "do not reconcile to target."
        )

    _nonnegative_int(
        sweep.get("captured_level_count"),
        name="captured_level_count",
    )
    _nonnegative_int(
        sweep.get("levels_touched"),
        name="levels_touched",
    )

    if not isinstance(
        sweep.get(
            "final_level_partially_consumed"
        ),
        bool,
    ):
        raise ValueError(
            "Partial-level flag must be boolean."
        )

    status = sweep.get(
        "fillability_status"
    )

    if status == FULLY_FILLED_IN_CAPTURED_BOOK:
        if (
            filled != target
            or unfilled != 0
        ):
            raise ValueError(
                "Full-fill status does not reconcile."
            )

        vwap = _decimal(
            sweep.get("vwap"),
            name="vwap",
        )
        slippage = _decimal(
            sweep.get("slippage_bps"),
            name="slippage_bps",
        )

        if vwap <= 0 or slippage < 0:
            raise ValueError(
                "Full-fill VWAP/slippage invalid."
            )

    elif status == INSUFFICIENT_CAPTURED_DEPTH:
        if filled >= target:
            raise ValueError(
                "Insufficient-depth status "
                "does not reconcile."
            )

        if (
            sweep.get("vwap") is not None
            or sweep.get(
                "slippage_bps"
            ) is not None
        ):
            raise ValueError(
                "Insufficient-depth sweep must not "
                "report full-target VWAP/slippage."
            )

    else:
        raise ValueError(
            "Unknown fillability status."
        )


def _validate_panel(
    panel: dict,
    *,
    capture_id: str,
) -> None:
    if not isinstance(panel, dict):
        raise ValueError(
            "Execution panel must be a mapping."
        )

    if (
        panel.get("capture_id")
        != capture_id
    ):
        raise ValueError(
            "Panel capture identifier mismatch."
        )

    if (
        panel.get("status")
        != EXECUTION_PANEL_ELIGIBLE
    ):
        raise ValueError(
            "Only eligible panels may enter "
            "economic aggregation."
        )

    _nonnegative_int(
        panel.get("kuru_record_index"),
        name="kuru_record_index",
    )

    states = panel.get("states")

    if not isinstance(states, dict):
        raise ValueError(
            "Panel states must be a mapping."
        )

    if tuple(states) != STATE_ORDER:
        raise ValueError(
            "Panel must contain the exact "
            "four frozen state views."
        )

    for state_name in STATE_ORDER:
        state = states[state_name]

        if not isinstance(state, dict):
            raise ValueError(
                "State payload must be a mapping."
            )

        sides = state.get("sides")

        if not isinstance(sides, dict):
            raise ValueError(
                "State sides must be a mapping."
            )

        if tuple(sides) != SIDES:
            raise ValueError(
                "State must contain exact frozen sides."
            )

        for side in SIDES:
            side_payload = sides[side]

            total_depth = _decimal(
                side_payload.get(
                    "total_captured_base_depth"
                ),
                name="total_captured_base_depth",
            )

            if total_depth < 0:
                raise ValueError(
                    "Captured depth must be non-negative."
                )

            _nonnegative_int(
                side_payload.get(
                    "captured_level_count"
                ),
                name="captured_level_count",
            )

            depth = side_payload.get(
                "depth_within_bps"
            )

            if not isinstance(depth, dict):
                raise ValueError(
                    "Depth-band payload "
                    "must be a mapping."
                )

            expected_bands = tuple(
                str(band)
                for band in DEPTH_BANDS_BPS
            )

            if tuple(depth) != expected_bands:
                raise ValueError(
                    "Depth bands do not match "
                    "frozen methodology."
                )

            previous = Decimal("-1")

            for band in DEPTH_BANDS_BPS:
                value = _decimal(
                    depth[str(band)],
                    name="depth_within_bps",
                )

                if value < 0:
                    raise ValueError(
                        "Depth-band value "
                        "must be non-negative."
                    )

                if value < previous:
                    raise ValueError(
                        "Depth must not decrease "
                        "as the band widens."
                    )

                if value > total_depth:
                    raise ValueError(
                        "Depth band exceeds "
                        "total captured depth."
                    )

                previous = value

            sweeps = side_payload.get(
                "sweeps"
            )

            if not isinstance(sweeps, dict):
                raise ValueError(
                    "Sweep payload must be a mapping."
                )

            expected_targets = tuple(
                str(target)
                for target
                in TARGET_BASE_QUANTITIES
            )

            if tuple(sweeps) != expected_targets:
                raise ValueError(
                    "Sweep targets do not match "
                    "frozen methodology."
                )

            for target in (
                TARGET_BASE_QUANTITIES
            ):
                _validate_sweep(
                    sweeps[str(target)],
                    side=side,
                    target=target,
                    total_depth=total_depth,
                )


def _validate_analysis(
    analysis: dict,
) -> None:
    if not isinstance(analysis, dict):
        raise ValueError(
            "Analysis must be a mapping."
        )

    if (
        analysis.get("schema_version")
        != PANEL_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unexpected panel schema version."
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

    summary = analysis.get("summary")

    if not isinstance(summary, dict):
        raise ValueError(
            "Analysis summary missing."
        )

    observations = _nonnegative_int(
        summary.get("kuru_observations"),
        name="kuru_observations",
    )

    eligible = _nonnegative_int(
        summary.get("eligible_panels"),
        name="eligible_panels",
    )

    counts = summary.get(
        "panel_outcome_counts"
    )

    if not isinstance(counts, dict):
        raise ValueError(
            "Panel outcome counts missing."
        )

    if set(counts) != set(PANEL_OUTCOMES):
        raise ValueError(
            "Panel outcome count keys invalid."
        )

    for outcome in PANEL_OUTCOMES:
        _nonnegative_int(
            counts[outcome],
            name=f"count:{outcome}",
        )

    if sum(counts.values()) != observations:
        raise ValueError(
            "Panel outcome counts do not reconcile."
        )

    if (
        counts[
            EXECUTION_PANEL_ELIGIBLE
        ]
        != eligible
    ):
        raise ValueError(
            "Eligible-panel summary mismatch."
        )

    panels = analysis.get("panels")
    exclusions = analysis.get(
        "exclusions"
    )

    if not isinstance(panels, list):
        raise ValueError(
            "Panels must be a list."
        )

    if not isinstance(exclusions, list):
        raise ValueError(
            "Exclusions must be a list."
        )

    if len(panels) != eligible:
        raise ValueError(
            "Panel list does not reconcile "
            "to eligible count."
        )

    if (
        len(exclusions)
        != observations - eligible
    ):
        raise ValueError(
            "Exclusions do not reconcile "
            "to observation count."
        )

    seen_indexes = set()

    for panel in panels:
        _validate_panel(
            panel,
            capture_id=capture_id,
        )

        index = panel[
            "kuru_record_index"
        ]

        if index in seen_indexes:
            raise ValueError(
                "Duplicate record index "
                "inside capture."
            )

        seen_indexes.add(index)


def _eligibility_summary(
    analyses: list[dict],
) -> dict:
    totals = {
        outcome: 0
        for outcome in PANEL_OUTCOMES
    }

    capture_summaries = []
    observations = 0
    eligible = 0

    for analysis in analyses:
        summary = analysis["summary"]

        observations += summary[
            "kuru_observations"
        ]
        eligible += summary[
            "eligible_panels"
        ]

        for outcome in PANEL_OUTCOMES:
            totals[outcome] += (
                summary[
                    "panel_outcome_counts"
                ][outcome]
            )

        capture_summaries.append(
            {
                "capture_id":
                    analysis["capture_id"],
                "kuru_observations":
                    summary[
                        "kuru_observations"
                    ],
                "eligible_panels":
                    summary[
                        "eligible_panels"
                    ],
                "panel_outcome_counts":
                    dict(
                        summary[
                            "panel_outcome_counts"
                        ]
                    ),
            }
        )

    if totals[
        EXECUTION_PANEL_ELIGIBLE
    ] != eligible:
        raise ValueError(
            "Aggregate eligible count mismatch."
        )

    return {
        "kuru_observations":
            observations,
        "eligible_panels":
            eligible,
        "panel_outcome_counts":
            totals,
        "capture_summaries":
            capture_summaries,
    }


def _capture_distribution(
    analyses,
    getter,
) -> list[dict]:
    rows = []

    for analysis in analyses:
        values = [
            getter(panel)
            for panel in analysis["panels"]
        ]

        rows.append(
            {
                "capture_id":
                    analysis["capture_id"],
                "count": len(values),
                "median": _median(values),
            }
        )

    return rows


def _state_summaries(
    analyses: list[dict],
) -> dict:
    panels = [
        panel
        for analysis in analyses
        for panel in analysis["panels"]
    ]

    result = {}

    for state_name in STATE_ORDER:
        state_result = {}

        for side in SIDES:
            def side_payload(panel):
                return (
                    panel["states"][state_name]
                    ["sides"][side]
                )

            total_values = [
                side_payload(panel)[
                    "total_captured_base_depth"
                ]
                for panel in panels
            ]

            depth_bands = {}

            for band in DEPTH_BANDS_BPS:
                key = str(band)

                values = [
                    side_payload(panel)[
                        "depth_within_bps"
                    ][key]
                    for panel in panels
                ]

                depth_bands[key] = {
                    "distribution":
                        _distribution(values),
                    "capture_medians":
                        _capture_distribution(
                            analyses,
                            lambda panel,
                            state_name=state_name,
                            side=side,
                            key=key: (
                                panel["states"][
                                    state_name
                                ]["sides"][side][
                                    "depth_within_bps"
                                ][key]
                            ),
                        ),
                }

            targets = {}

            for target in (
                TARGET_BASE_QUANTITIES
            ):
                key = str(target)

                sweeps = [
                    side_payload(panel)[
                        "sweeps"
                    ][key]
                    for panel in panels
                ]

                full = [
                    sweep
                    for sweep in sweeps
                    if (
                        sweep[
                            "fillability_status"
                        ]
                        == FULLY_FILLED_IN_CAPTURED_BOOK
                    )
                ]

                insufficient = (
                    len(sweeps)
                    - len(full)
                )

                capture_fill = []

                for analysis in analyses:
                    capture_sweeps = [
                        panel["states"][
                            state_name
                        ]["sides"][side][
                            "sweeps"
                        ][key]
                        for panel
                        in analysis["panels"]
                    ]

                    capture_full = [
                        sweep
                        for sweep
                        in capture_sweeps
                        if (
                            sweep[
                                "fillability_status"
                            ]
                            == FULLY_FILLED_IN_CAPTURED_BOOK
                        )
                    ]

                    capture_fill.append(
                        {
                            "capture_id":
                                analysis[
                                    "capture_id"
                                ],
                            "eligible_panel_count":
                                len(
                                    capture_sweeps
                                ),
                            "fully_filled_count":
                                len(
                                    capture_full
                                ),
                            "insufficient_captured_depth_count":
                                (
                                    len(
                                        capture_sweeps
                                    )
                                    - len(
                                        capture_full
                                    )
                                ),
                            "median_slippage_bps":
                                _median(
                                    sweep[
                                        "slippage_bps"
                                    ]
                                    for sweep
                                    in capture_full
                                ),
                        }
                    )

                targets[key] = {
                    "eligible_panel_count":
                        len(sweeps),
                    "fully_filled_count":
                        len(full),
                    "insufficient_captured_depth_count":
                        insufficient,
                    "full_fill_rate":
                        _rate(
                            len(full),
                            len(sweeps),
                        ),
                    "vwap_distribution":
                        _distribution(
                            sweep["vwap"]
                            for sweep in full
                        ),
                    "slippage_bps_distribution":
                        _distribution(
                            sweep[
                                "slippage_bps"
                            ]
                            for sweep in full
                        ),
                    "capture_fill_summaries":
                        capture_fill,
                }

            state_result[side] = {
                "eligible_panel_count":
                    len(panels),
                "total_captured_base_depth": {
                    "distribution":
                        _distribution(
                            total_values
                        ),
                    "capture_medians":
                        _capture_distribution(
                            analyses,
                            lambda panel,
                            state_name=state_name,
                            side=side: (
                                panel["states"][
                                    state_name
                                ]["sides"][side][
                                    "total_captured_base_depth"
                                ]
                            ),
                        ),
                },
                "depth_within_bps":
                    depth_bands,
                "targets":
                    targets,
            }

        result[state_name] = (
            state_result
        )

    return result


def _paired_summaries(
    analyses: list[dict],
) -> dict:
    panels = [
        panel
        for analysis in analyses
        for panel in analysis["panels"]
    ]

    result = {}

    for state_a, state_b in STATE_PAIRS:
        pair_key = (
            f"{state_a}__{state_b}"
        )
        pair_result = {}

        for side in SIDES:
            targets = {}

            for target in (
                TARGET_BASE_QUANTITIES
            ):
                key = str(target)

                transition_counts = {
                    "both_fully_filled": 0,
                    "only_first_fully_filled": 0,
                    "only_second_fully_filled": 0,
                    "neither_fully_filled": 0,
                }

                deltas = []

                for panel in panels:
                    first = (
                        panel["states"][
                            state_a
                        ]["sides"][side][
                            "sweeps"
                        ][key]
                    )
                    second = (
                        panel["states"][
                            state_b
                        ]["sides"][side][
                            "sweeps"
                        ][key]
                    )

                    first_full = (
                        first[
                            "fillability_status"
                        ]
                        == FULLY_FILLED_IN_CAPTURED_BOOK
                    )
                    second_full = (
                        second[
                            "fillability_status"
                        ]
                        == FULLY_FILLED_IN_CAPTURED_BOOK
                    )

                    if (
                        first_full
                        and second_full
                    ):
                        transition_counts[
                            "both_fully_filled"
                        ] += 1

                        deltas.append(
                            _decimal(
                                second[
                                    "slippage_bps"
                                ],
                                name=(
                                    "second "
                                    "slippage_bps"
                                ),
                            )
                            - _decimal(
                                first[
                                    "slippage_bps"
                                ],
                                name=(
                                    "first "
                                    "slippage_bps"
                                ),
                            )
                        )

                    elif first_full:
                        transition_counts[
                            "only_first_fully_filled"
                        ] += 1

                    elif second_full:
                        transition_counts[
                            "only_second_fully_filled"
                        ] += 1

                    else:
                        transition_counts[
                            "neither_fully_filled"
                        ] += 1

                if (
                    sum(
                        transition_counts.values()
                    )
                    != len(panels)
                ):
                    raise ValueError(
                        "Pair transition counts "
                        "do not reconcile."
                    )

                capture_rows = []

                for analysis in analyses:
                    capture_counts = {
                        key_name: 0
                        for key_name
                        in transition_counts
                    }
                    capture_deltas = []

                    for panel in (
                        analysis["panels"]
                    ):
                        first = (
                            panel["states"][
                                state_a
                            ]["sides"][side][
                                "sweeps"
                            ][key]
                        )
                        second = (
                            panel["states"][
                                state_b
                            ]["sides"][side][
                                "sweeps"
                            ][key]
                        )

                        first_full = (
                            first[
                                "fillability_status"
                            ]
                            == FULLY_FILLED_IN_CAPTURED_BOOK
                        )
                        second_full = (
                            second[
                                "fillability_status"
                            ]
                            == FULLY_FILLED_IN_CAPTURED_BOOK
                        )

                        if (
                            first_full
                            and second_full
                        ):
                            capture_counts[
                                "both_fully_filled"
                            ] += 1

                            capture_deltas.append(
                                _decimal(
                                    second[
                                        "slippage_bps"
                                    ],
                                    name="slippage_bps",
                                )
                                - _decimal(
                                    first[
                                        "slippage_bps"
                                    ],
                                    name="slippage_bps",
                                )
                            )

                        elif first_full:
                            capture_counts[
                                "only_first_fully_filled"
                            ] += 1

                        elif second_full:
                            capture_counts[
                                "only_second_fully_filled"
                            ] += 1

                        else:
                            capture_counts[
                                "neither_fully_filled"
                            ] += 1

                    capture_rows.append(
                        {
                            "capture_id":
                                analysis[
                                    "capture_id"
                                ],
                            "paired_panel_count":
                                len(
                                    analysis[
                                        "panels"
                                    ]
                                ),
                            **capture_counts,
                            "median_slippage_delta_bps":
                                _median(
                                    capture_deltas
                                ),
                        }
                    )

                targets[key] = {
                    "paired_panel_count":
                        len(panels),
                    **transition_counts,
                    "slippage_delta_bps": {
                        "distribution":
                            _distribution(
                                deltas
                            ),
                        "sign_counts":
                            _sign_counts(
                                deltas
                            ),
                    },
                    "capture_summaries":
                        capture_rows,
                }

            depth_bands = {}

            for band in DEPTH_BANDS_BPS:
                key = str(band)

                deltas = [
                    (
                        _decimal(
                            panel["states"][
                                state_b
                            ]["sides"][side][
                                "depth_within_bps"
                            ][key],
                            name="second depth",
                        )
                        - _decimal(
                            panel["states"][
                                state_a
                            ]["sides"][side][
                                "depth_within_bps"
                            ][key],
                            name="first depth",
                        )
                    )
                    for panel in panels
                ]

                capture_rows = []

                for analysis in analyses:
                    capture_deltas = [
                        (
                            _decimal(
                                panel["states"][
                                    state_b
                                ]["sides"][side][
                                    "depth_within_bps"
                                ][key],
                                name="second depth",
                            )
                            - _decimal(
                                panel["states"][
                                    state_a
                                ]["sides"][side][
                                    "depth_within_bps"
                                ][key],
                                name="first depth",
                            )
                        )
                        for panel
                        in analysis["panels"]
                    ]

                    capture_rows.append(
                        {
                            "capture_id":
                                analysis[
                                    "capture_id"
                                ],
                            "paired_panel_count":
                                len(
                                    capture_deltas
                                ),
                            "median_depth_delta_base":
                                _median(
                                    capture_deltas
                                ),
                        }
                    )

                depth_bands[key] = {
                    "paired_panel_count":
                        len(panels),
                    "depth_delta_base": {
                        "distribution":
                            _distribution(
                                deltas
                            ),
                        "sign_counts":
                            _sign_counts(
                                deltas
                            ),
                    },
                    "capture_summaries":
                        capture_rows,
                }

            pair_result[side] = {
                "targets": targets,
                "depth_bands":
                    depth_bands,
            }

        result[pair_key] = (
            pair_result
        )

    return result


def aggregate_depth_panels(
    analyses: list[dict],
) -> dict:
    if not isinstance(analyses, list):
        raise TypeError(
            "analyses must be a list."
        )

    if not analyses:
        raise ValueError(
            "At least one capture analysis "
            "is required."
        )

    capture_ids = []

    for analysis in analyses:
        _validate_analysis(
            analysis
        )
        capture_ids.append(
            analysis["capture_id"]
        )

    if (
        len(set(capture_ids))
        != len(capture_ids)
    ):
        raise ValueError(
            "Capture identifiers must be unique."
        )

    eligibility = (
        _eligibility_summary(
            analyses
        )
    )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "capture_count":
            len(analyses),
        "eligible_panel_count":
            eligibility[
                "eligible_panels"
            ],
        "eligibility_summary":
            eligibility,
        "state_summaries":
            _state_summaries(
                analyses
            ),
        "paired_state_view_contrasts":
            _paired_summaries(
                analyses
            ),
        "claim_boundaries": list(
            PANEL_CLAIM_BOUNDARIES
            + AGGREGATION_CLAIM_BOUNDARIES
        ),
    }
