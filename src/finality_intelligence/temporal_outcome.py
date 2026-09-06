from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation

from finality_intelligence.alignment import (
    ALIGNED,
    INSUFFICIENT_SOURCE_EVIDENCE,
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
    align_dual_capture,
    is_target_l2_record,
)
from finality_intelligence.cross_venue_execution import (
    reconstruct_coinbase_books_at_indices,
)
from finality_intelligence.metrics import (
    BPS_SCALE,
    midpoint,
)
from finality_intelligence.top_of_book import (
    STATE_ORDER,
    derive_kuru_state,
)


SCHEMA_VERSION = (
    "phase2.temporal_outcome.v1"
)

FROZEN_HORIZONS_MS = (
    Decimal("250"),
    Decimal("1000"),
    Decimal("5000"),
    Decimal("10000"),
)

PRIMARY_HORIZONS_MS = (
    Decimal("250"),
    Decimal("1000"),
    Decimal("5000"),
)

EXTENDED_HORIZON_MS = (
    Decimal("10000")
)


EVALUABLE = "EVALUABLE"

RIGHT_CENSORED_CAPTURE_END = (
    "RIGHT_CENSORED_CAPTURE_END"
)

INVALID_KURU_PANEL = (
    "INVALID_KURU_PANEL"
)

COINBASE_RECONSTRUCTION_FAILURE = (
    "COINBASE_RECONSTRUCTION_FAILURE"
)

APPLICABLE_NONZERO_CONTRAST = (
    "APPLICABLE_NONZERO_CONTRAST"
)

NOT_APPLICABLE_ZERO_CONTRAST = (
    "NOT_APPLICABLE_ZERO_CONTRAST"
)


CLAIM_BOUNDARIES = (
    "The temporal result is descriptive market-state evidence, "
    "not prediction, not alpha, and not arbitrage.",
    "Directional concordance is not causal evidence and does not "
    "establish that a Kuru state view leads Coinbase.",
    "Directional-concordance sign counts are not a win rate or "
    "execution probability.",
    "A Coinbase forward midpoint change is not realized trading PnL "
    "or a realizable strategy return.",
    "Simultaneous Kuru state views are not temporal protocol-state "
    "transitions or finality-latency measurements.",
    "Overlapping future windows are not independent observations.",
)


ROW_STATUSES = (
    EVALUABLE,
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
    RIGHT_CENSORED_CAPTURE_END,
    INSUFFICIENT_SOURCE_EVIDENCE,
    INVALID_KURU_PANEL,
    COINBASE_RECONSTRUCTION_FAILURE,
)


def _parse_horizon_ms(
    value,
) -> Decimal:
    if isinstance(
        value,
        (bool, float),
    ):
        raise TypeError(
            "horizon_ms must use an exact "
            "numeric representation."
        )

    try:
        parsed = Decimal(value)
    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Invalid horizon_ms."
        ) from exc

    if (
        not parsed.is_finite()
        or parsed <= 0
    ):
        raise ValueError(
            "horizon_ms must be finite "
            "and positive."
        )

    if (
        parsed
        not in FROZEN_HORIZONS_MS
    ):
        raise ValueError(
            "horizon_ms is not part of "
            "the frozen Phase 2 horizon set."
        )

    return parsed


def _valid_monotonic_ns(
    value,
) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    )


def _horizon_ns(
    horizon_ms: Decimal,
) -> int:
    value = (
        horizon_ms
        * Decimal("1000000")
    )

    integral = (
        value.to_integral_value()
    )

    if value != integral:
        raise ValueError(
            "Frozen horizon must map to "
            "an exact integer nanosecond value."
        )

    return int(integral)


def _serialize_decimal(
    value: Decimal | None,
) -> str | None:
    if value is None:
        return None

    return str(value)


def select_future_coinbase_record_index(
    records: list[dict],
    *,
    horizon_monotonic_ns: int,
) -> int | None:
    """
    Select the latest canonical Coinbase target-L2
    record observed at or before the frozen horizon.

    Equal receive times are resolved by later original
    wrapper index, matching the Phase 1 tie convention.
    """
    if not isinstance(
        records,
        list,
    ):
        raise TypeError(
            "Coinbase records must be a list."
        )

    if (
        isinstance(
            horizon_monotonic_ns,
            bool,
        )
        or not isinstance(
            horizon_monotonic_ns,
            int,
        )
    ):
        raise TypeError(
            "horizon_monotonic_ns must be int."
        )

    if horizon_monotonic_ns < 0:
        raise ValueError(
            "horizon_monotonic_ns must "
            "be non-negative."
        )

    selected: tuple[
        int,
        int,
    ] | None = None

    for index, record in enumerate(
        records
    ):
        if not isinstance(
            record,
            dict,
        ):
            raise TypeError(
                "Coinbase record must "
                "be a mapping."
            )

        if not is_target_l2_record(
            record
        ):
            continue

        received_ns = record.get(
            "received_monotonic_ns"
        )

        if not _valid_monotonic_ns(
            received_ns
        ):
            raise ValueError(
                "Target Coinbase record has "
                "invalid monotonic receive time."
            )

        if (
            received_ns
            > horizon_monotonic_ns
        ):
            continue

        candidate = (
            received_ns,
            index,
        )

        if (
            selected is None
            or candidate > selected
        ):
            selected = candidate

    if selected is None:
        return None

    return selected[1]


def _capture_continues_through(
    records: list[dict],
    *,
    horizon_monotonic_ns: int,
) -> bool:
    """
    Conservative continuity proof required by the contract:
    at least one stored Coinbase wrapper exists at or after
    the horizon.
    """
    for record in records:
        if not isinstance(
            record,
            dict,
        ):
            continue

        received_ns = record.get(
            "received_monotonic_ns"
        )

        if (
            _valid_monotonic_ns(
                received_ns
            )
            and received_ns
            >= horizon_monotonic_ns
        ):
            return True

    return False


def _derive_kuru_panel(
    states,
) -> dict:
    if not isinstance(
        states,
        dict,
    ):
        raise ValueError(
            "Kuru states must be a mapping."
        )

    derived = {}

    for state_name in STATE_ORDER:
        if state_name not in states:
            raise ValueError(
                "Missing Kuru state: "
                f"{state_name}"
            )

        derived[state_name] = (
            derive_kuru_state(
                states[
                    state_name
                ]
            )
        )

    return derived


def _contrast_sign(
    value: Decimal,
) -> str:
    if value > 0:
        return "POSITIVE"

    if value < 0:
        return "NEGATIVE"

    return "ZERO"


def _base_row(
    aligned_row: dict,
    *,
    freshness_threshold_ms: str,
    horizon_ms: Decimal,
    horizon_ns: int,
) -> dict:
    kuru = aligned_row["kuru"]

    t0_ns = kuru[
        "received_monotonic_ns"
    ]

    reference = aligned_row.get(
        "coinbase_reference"
    )

    horizon_time_ns = (
        t0_ns
        + horizon_ns
    )

    return {
        "capture_id":
            aligned_row[
                "capture_id"
            ],
        "freshness_threshold_ms":
            freshness_threshold_ms,
        "horizon_ms":
            str(horizon_ms),
        "kuru_record_index":
            kuru[
                "record_index"
            ],
        "kuru_received_at_utc":
            kuru[
                "received_at_utc"
            ],
        "kuru_received_monotonic_ns":
            t0_ns,
        "U":
            kuru["U"],
        "alignment_status":
            aligned_row[
                "status"
            ],
        "alignment_status_reason":
            list(
                aligned_row.get(
                    "status_reason",
                    [],
                )
            ),
        "reference_age_ms":
            aligned_row.get(
                "reference_age_ms"
            ),
        "baseline_coinbase_record_index":
            (
                reference[
                    "record_index"
                ]
                if reference
                is not None
                else None
            ),
        "baseline_coinbase_received_monotonic_ns":
            (
                reference[
                    "received_monotonic_ns"
                ]
                if reference
                is not None
                else None
            ),
        "future_horizon_monotonic_ns":
            horizon_time_ns,
        "future_coinbase_record_index":
            None,
        "future_coinbase_received_monotonic_ns":
            None,
        "future_asof_age_ms":
            None,
        "baseline_coinbase_midpoint":
            None,
        "future_coinbase_midpoint":
            None,
        "coinbase_forward_mid_return_bps":
            None,
        "kuru_proposed_midpoint":
            None,
        "kuru_finalized_midpoint":
            None,
        "kuru_proposed_finalized_mid_gap_bps":
            None,
        "contrast_sign":
            None,
        "directional_concordance_status":
            None,
        "directional_concordance_bps":
            None,
        "status":
            None,
        "status_reason":
            [],
    }


def analyze_temporal_capture(
    capture: dict,
    *,
    capture_id: str,
    max_age_ms,
    horizon_ms,
) -> dict:
    """
    Compose existing Phase 1 primitives into the
    pre-registered Phase 2 temporal outcome layer.

    No new market-data normalization, Coinbase replay,
    or baseline alignment semantics are introduced here.
    """
    horizon = _parse_horizon_ms(
        horizon_ms
    )

    horizon_delta_ns = (
        _horizon_ns(
            horizon
        )
    )

    alignment = align_dual_capture(
        capture,
        capture_id=capture_id,
        max_age_ms=max_age_ms,
    )

    sources = capture.get(
        "sources",
        {},
    )

    coinbase_source = sources.get(
        "coinbase",
        {},
    )

    coinbase_records = (
        coinbase_source.get(
            "records",
            [],
        )
    )

    if not isinstance(
        coinbase_records,
        list,
    ):
        coinbase_records = []

    rows: list[dict] = []

    reconstruction_candidates = []

    requested_indices: set[int] = set()

    for aligned_row in alignment[
        "rows"
    ]:
        row = _base_row(
            aligned_row,
            freshness_threshold_ms=
                alignment[
                    "max_age_ms"
                ],
            horizon_ms=horizon,
            horizon_ns=
                horizon_delta_ns,
        )

        rows.append(
            row
        )

        alignment_status = (
            aligned_row[
                "status"
            ]
        )

        if (
            alignment_status
            != ALIGNED
        ):
            row["status"] = (
                alignment_status
            )

            row[
                "status_reason"
            ] = list(
                aligned_row.get(
                    "status_reason",
                    [],
                )
            )

            continue

        try:
            derived_states = (
                _derive_kuru_panel(
                    aligned_row[
                        "kuru"
                    ].get(
                        "states"
                    )
                )
            )
        except (
            ArithmeticError,
            TypeError,
            ValueError,
        ):
            row["status"] = (
                INVALID_KURU_PANEL
            )

            row[
                "status_reason"
            ] = [
                "INVALID_COMPLETE_FOUR_STATE_PANEL"
            ]

            continue

        proposed_mid = (
            derived_states[
                "proposed"
            ][
                "midpoint"
            ]
        )

        finalized_mid = (
            derived_states[
                "finalized"
            ][
                "midpoint"
            ]
        )

        if finalized_mid <= 0:
            row["status"] = (
                INVALID_KURU_PANEL
            )

            row[
                "status_reason"
            ] = [
                "INVALID_FINALIZED_MIDPOINT"
            ]

            continue

        contrast_bps = (
            (
                proposed_mid
                / finalized_mid
            )
            - Decimal("1")
        ) * BPS_SCALE

        sign = _contrast_sign(
            contrast_bps
        )

        row[
            "kuru_proposed_midpoint"
        ] = _serialize_decimal(
            proposed_mid
        )

        row[
            "kuru_finalized_midpoint"
        ] = _serialize_decimal(
            finalized_mid
        )

        row[
            "kuru_proposed_finalized_mid_gap_bps"
        ] = _serialize_decimal(
            contrast_bps
        )

        row[
            "contrast_sign"
        ] = sign

        horizon_time_ns = row[
            "future_horizon_monotonic_ns"
        ]

        if not _capture_continues_through(
            coinbase_records,
            horizon_monotonic_ns=
                horizon_time_ns,
        ):
            row["status"] = (
                RIGHT_CENSORED_CAPTURE_END
            )

            row[
                "status_reason"
            ] = [
                "NO_STORED_COINBASE_WRAPPER_AT_OR_AFTER_HORIZON"
            ]

            continue

        try:
            future_index = (
                select_future_coinbase_record_index(
                    coinbase_records,
                    horizon_monotonic_ns=
                        horizon_time_ns,
                )
            )
        except (
            ArithmeticError,
            TypeError,
            ValueError,
        ):
            row["status"] = (
                INSUFFICIENT_SOURCE_EVIDENCE
            )

            row[
                "status_reason"
            ] = [
                "INVALID_FUTURE_TARGET_INDEX_EVIDENCE"
            ]

            continue

        if future_index is None:
            row["status"] = (
                INSUFFICIENT_SOURCE_EVIDENCE
            )

            row[
                "status_reason"
            ] = [
                "NO_COINBASE_TARGET_RECORD_ASOF_HORIZON"
            ]

            continue

        baseline_index = row[
            "baseline_coinbase_record_index"
        ]

        if (
            not isinstance(
                baseline_index,
                int,
            )
            or isinstance(
                baseline_index,
                bool,
            )
        ):
            row["status"] = (
                INSUFFICIENT_SOURCE_EVIDENCE
            )

            row[
                "status_reason"
            ] = [
                "INVALID_BASELINE_RECORD_INDEX"
            ]

            continue

        future_record = (
            coinbase_records[
                future_index
            ]
        )

        future_received_ns = (
            future_record.get(
                "received_monotonic_ns"
            )
        )

        if not _valid_monotonic_ns(
            future_received_ns
        ):
            row["status"] = (
                INSUFFICIENT_SOURCE_EVIDENCE
            )

            row[
                "status_reason"
            ] = [
                "INVALID_FUTURE_RECEIVE_TIME"
            ]

            continue

        future_age_ms = (
            Decimal(
                horizon_time_ns
                - future_received_ns
            )
            / Decimal(
                "1000000"
            )
        )

        if future_age_ms < 0:
            raise AssertionError(
                "Future as-of record cannot "
                "occur after the horizon."
            )

        row[
            "future_coinbase_record_index"
        ] = future_index

        row[
            "future_coinbase_received_monotonic_ns"
        ] = future_received_ns

        row[
            "future_asof_age_ms"
        ] = _serialize_decimal(
            future_age_ms
        )

        requested_indices.add(
            baseline_index
        )

        requested_indices.add(
            future_index
        )

        reconstruction_candidates.append(
            {
                "row":
                    row,
                "baseline_index":
                    baseline_index,
                "future_index":
                    future_index,
                "contrast_bps":
                    contrast_bps,
                "contrast_sign":
                    sign,
            }
        )

    books: dict[int, dict] = {}

    reconstruction_failed = False

    if reconstruction_candidates:
        try:
            books = (
                reconstruct_coinbase_books_at_indices(
                    coinbase_records,
                    record_indices=
                        requested_indices,
                )
            )
        except (
            ArithmeticError,
            KeyError,
            TypeError,
            ValueError,
        ):
            reconstruction_failed = True

    if reconstruction_failed:
        for candidate in (
            reconstruction_candidates
        ):
            row = candidate[
                "row"
            ]

            row["status"] = (
                COINBASE_RECONSTRUCTION_FAILURE
            )

            row[
                "status_reason"
            ] = [
                "CANONICAL_COINBASE_REPLAY_FAILED"
            ]
    else:
        for candidate in (
            reconstruction_candidates
        ):
            row = candidate[
                "row"
            ]

            baseline_book = books[
                candidate[
                    "baseline_index"
                ]
            ]

            future_book = books[
                candidate[
                    "future_index"
                ]
            ]

            baseline_mid = midpoint(
                baseline_book[
                    "best_bid"
                ],
                baseline_book[
                    "best_ask"
                ],
            )

            future_mid = midpoint(
                future_book[
                    "best_bid"
                ],
                future_book[
                    "best_ask"
                ],
            )

            if baseline_mid <= 0:
                row["status"] = (
                    COINBASE_RECONSTRUCTION_FAILURE
                )

                row[
                    "status_reason"
                ] = [
                    "NONPOSITIVE_BASELINE_COINBASE_MIDPOINT"
                ]

                continue

            forward_return_bps = (
                (
                    future_mid
                    / baseline_mid
                )
                - Decimal("1")
            ) * BPS_SCALE

            row[
                "baseline_coinbase_midpoint"
            ] = _serialize_decimal(
                baseline_mid
            )

            row[
                "future_coinbase_midpoint"
            ] = _serialize_decimal(
                future_mid
            )

            row[
                "coinbase_forward_mid_return_bps"
            ] = _serialize_decimal(
                forward_return_bps
            )

            if (
                candidate[
                    "contrast_sign"
                ]
                == "ZERO"
            ):
                row[
                    "directional_concordance_status"
                ] = (
                    NOT_APPLICABLE_ZERO_CONTRAST
                )

                row[
                    "directional_concordance_bps"
                ] = None

            else:
                direction = (
                    Decimal("1")
                    if candidate[
                        "contrast_sign"
                    ]
                    == "POSITIVE"
                    else Decimal("-1")
                )

                concordance = (
                    direction
                    * forward_return_bps
                )

                row[
                    "directional_concordance_status"
                ] = (
                    APPLICABLE_NONZERO_CONTRAST
                )

                row[
                    "directional_concordance_bps"
                ] = _serialize_decimal(
                    concordance
                )

            row["status"] = (
                EVALUABLE
            )

            row[
                "status_reason"
            ] = [
                "TEMPORAL_OUTCOME_EVALUABLE"
            ]

    counts = Counter(
        row["status"]
        for row in rows
    )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "capture_id":
            capture_id,
        "source_capture_schema_version":
            alignment[
                "source_capture_schema_version"
            ],
        "freshness_threshold_ms":
            alignment[
                "max_age_ms"
            ],
        "horizon_ms":
            str(horizon),
        "primary_horizon":
            (
                horizon
                in PRIMARY_HORIZONS_MS
            ),
        "source_evidence_reasons":
            list(
                alignment[
                    "source_evidence_reasons"
                ]
            ),
        "claim_boundaries":
            list(
                CLAIM_BOUNDARIES
            ),
        "summary": {
            "kuru_observations":
                alignment[
                    "summary"
                ][
                    "kuru_observations"
                ],
            "rows":
                len(rows),
            "status_counts":
                dict(
                    sorted(
                        counts.items()
                    )
                ),
            "evaluable":
                counts[
                    EVALUABLE
                ],
            "right_censored":
                counts[
                    RIGHT_CENSORED_CAPTURE_END
                ],
        },
        "rows":
            rows,
    }
