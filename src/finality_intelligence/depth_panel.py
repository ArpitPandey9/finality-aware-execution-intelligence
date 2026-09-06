from __future__ import annotations

from decimal import Decimal

from finality_intelligence.depth_execution import (
    BUY,
    DEPTH_BANDS_BPS,
    SIDES,
    TARGET_BASE_QUANTITIES,
    depth_within_bps,
    sweep_base_quantity,
    total_captured_depth,
    validate_and_normalize_book,
)


SCHEMA_VERSION = (
    "phase1.state_conditioned_depth_execution.v1"
)

EXPECTED_KURU_MARKET = "MON_USDC"

STATE_ORDER = (
    "proposed",
    "voted",
    "finalized",
    "committed",
)

EXECUTION_PANEL_ELIGIBLE = (
    "EXECUTION_PANEL_ELIGIBLE"
)

INVALID_EXECUTION_STATE_PANEL = (
    "INVALID_EXECUTION_STATE_PANEL"
)

INSUFFICIENT_SOURCE_EVIDENCE = (
    "INSUFFICIENT_SOURCE_EVIDENCE"
)

PANEL_OUTCOMES = (
    EXECUTION_PANEL_ELIGIBLE,
    INVALID_EXECUTION_STATE_PANEL,
    INSUFFICIENT_SOURCE_EVIDENCE,
)

CLAIM_BOUNDARIES = (
    "Results describe deterministic simulated sweeps "
    "through captured displayed Kuru book levels.",
    "Insufficient captured depth does not prove that "
    "the venue itself could not execute the target.",
    "Simultaneous state-view contrasts are not temporal "
    "transitions or causal finality effects.",
    "No execution, arbitrage, alpha, profitability, "
    "latency, or finality-premium claim is implied.",
)


def _decimal_string(
    value: Decimal | None,
) -> str | None:
    if value is None:
        return None

    return str(value)


def _serialize_sweep(
    book: dict,
    *,
    side: str,
    target_base: Decimal,
) -> dict:
    result = sweep_base_quantity(
        book,
        side=side,
        target_base=target_base,
    )

    levels = (
        book["asks"]
        if side == BUY
        else book["bids"]
    )

    best_level = levels[0]

    return {
        "side": side,
        "target_base": str(
            result["target_base"]
        ),
        "best_price_raw":
            best_level["raw_price"],
        "best_quantity_raw":
            best_level["raw_quantity"],
        "best_price": str(
            result["best_price"]
        ),
        "best_quantity": str(
            best_level["quantity"]
        ),
        "captured_level_count":
            result["captured_level_count"],
        "total_captured_base_depth": str(
            result[
                "total_captured_base_depth"
            ]
        ),
        "fillability_status":
            result["fillability_status"],
        "filled_base": str(
            result["filled_base"]
        ),
        "unfilled_base": str(
            result["unfilled_base"]
        ),
        "levels_touched":
            result["levels_touched"],
        "final_level_partially_consumed":
            result[
                "final_level_partially_consumed"
            ],
        "quote_amount": str(
            result["quote_amount"]
        ),
        "vwap": _decimal_string(
            result["vwap"]
        ),
        "slippage_bps": _decimal_string(
            result["slippage_bps"]
        ),
    }


def _analyze_state(
    book: dict,
) -> dict:
    result = {
        "best_bid_raw":
            book["bids"][0]["raw_price"],
        "best_bid_quantity_raw":
            book["bids"][0]["raw_quantity"],
        "best_ask_raw":
            book["asks"][0]["raw_price"],
        "best_ask_quantity_raw":
            book["asks"][0]["raw_quantity"],
        "best_bid": str(
            book["best_bid"]
        ),
        "best_ask": str(
            book["best_ask"]
        ),
        "sides": {},
    }

    for side in SIDES:
        result["sides"][side] = {
            "captured_level_count": (
                len(
                    book["asks"]
                    if side == BUY
                    else book["bids"]
                )
            ),
            "total_captured_base_depth": str(
                total_captured_depth(
                    book,
                    side=side,
                )
            ),
            "depth_within_bps": {
                str(band): str(
                    depth_within_bps(
                        book,
                        side=side,
                        band_bps=band,
                    )
                )
                for band in DEPTH_BANDS_BPS
            },
            "sweeps": {
                str(target):
                    _serialize_sweep(
                        book,
                        side=side,
                        target_base=target,
                    )
                for target
                in TARGET_BASE_QUANTITIES
            },
        }

    return result


def analyze_record_depth_panel(
    record: dict,
    *,
    capture_id: str,
    record_index: int,
) -> dict:
    if (
        not isinstance(capture_id, str)
        or not capture_id
    ):
        raise ValueError(
            "capture_id must be a non-empty string."
        )

    if (
        isinstance(record_index, bool)
        or not isinstance(record_index, int)
        or record_index < 0
    ):
        raise ValueError(
            "record_index must be a "
            "non-negative integer."
        )

    base = {
        "capture_id": capture_id,
        "kuru_record_index": record_index,
        "received_at_utc": (
            record.get("received_at_utc")
            if isinstance(record, dict)
            else None
        ),
        "received_monotonic_ns": (
            record.get(
                "received_monotonic_ns"
            )
            if isinstance(record, dict)
            else None
        ),
        "U": (
            record.get("U")
            if isinstance(record, dict)
            else None
        ),
    }

    if not isinstance(record, dict):
        return {
            **base,
            "status":
                INVALID_EXECUTION_STATE_PANEL,
            "reasons": [
                "kuru_record_not_mapping"
            ],
        }

    raw_message = record.get(
        "raw_message"
    )

    if not isinstance(
        raw_message,
        dict,
    ):
        return {
            **base,
            "status":
                INVALID_EXECUTION_STATE_PANEL,
            "reasons": [
                "raw_message_missing_or_invalid"
            ],
        }

    raw_states = raw_message.get(
        "states"
    )

    if not isinstance(
        raw_states,
        dict,
    ):
        return {
            **base,
            "status":
                INVALID_EXECUTION_STATE_PANEL,
            "reasons": [
                "raw_states_missing_or_invalid"
            ],
        }

    normalized_states = {}
    reasons = []

    for state_name in STATE_ORDER:
        raw_book = raw_states.get(
            state_name
        )

        if not isinstance(
            raw_book,
            dict,
        ):
            reasons.append(
                f"{state_name}:missing_or_invalid"
            )
            continue

        try:
            normalized_states[
                state_name
            ] = (
                validate_and_normalize_book(
                    raw_book
                )
            )

        except (
            TypeError,
            ValueError,
            KeyError,
        ) as exc:
            reasons.append(
                f"{state_name}:"
                f"{type(exc).__name__}:"
                f"{exc}"
            )

    if reasons:
        return {
            **base,
            "status":
                INVALID_EXECUTION_STATE_PANEL,
            "reasons": reasons,
        }

    return {
        **base,
        "status":
            EXECUTION_PANEL_ELIGIBLE,
        "reasons": [],
        "states": {
            state_name:
                _analyze_state(
                    normalized_states[
                        state_name
                    ]
                )
            for state_name in STATE_ORDER
        },
    }


def _capture_source_reasons(
    capture: dict,
) -> list[str]:
    reasons = []

    gate = capture.get("gate")

    if (
        not isinstance(gate, dict)
        or gate.get("overall") != "PASS"
    ):
        reasons.append(
            "capture_gate_not_pass"
        )

    sources = capture.get(
        "sources"
    )

    if not isinstance(
        sources,
        dict,
    ):
        reasons.append(
            "sources_missing_or_invalid"
        )
        return reasons

    kuru = sources.get(
        "kuru"
    )

    if not isinstance(
        kuru,
        dict,
    ):
        reasons.append(
            "kuru_source_missing_or_invalid"
        )
        return reasons

    if (
        kuru.get("market")
        != EXPECTED_KURU_MARKET
    ):
        reasons.append(
            "kuru_market_identity_mismatch"
        )

    records = kuru.get(
        "records"
    )

    if (
        not isinstance(records, list)
        or not records
    ):
        reasons.append(
            "kuru_records_missing_or_empty"
        )

    return reasons


def analyze_capture_depth_panels(
    capture: dict,
    *,
    capture_id: str,
) -> dict:
    if not isinstance(
        capture,
        dict,
    ):
        raise TypeError(
            "capture must be a mapping."
        )

    if (
        not isinstance(capture_id, str)
        or not capture_id
    ):
        raise ValueError(
            "capture_id must be a non-empty string."
        )

    sources = capture.get(
        "sources"
    )

    kuru = (
        sources.get("kuru")
        if isinstance(sources, dict)
        else None
    )

    records = (
        kuru.get("records")
        if isinstance(kuru, dict)
        else []
    )

    if not isinstance(records, list):
        records = []

    source_reasons = (
        _capture_source_reasons(
            capture
        )
    )

    counts = {
        outcome: 0
        for outcome in PANEL_OUTCOMES
    }

    panels = []
    exclusions = []

    if source_reasons:
        counts[
            INSUFFICIENT_SOURCE_EVIDENCE
        ] = len(records)

        for record_index, record in enumerate(
            records
        ):
            exclusions.append(
                {
                    "capture_id":
                        capture_id,
                    "kuru_record_index":
                        record_index,
                    "received_at_utc": (
                        record.get(
                            "received_at_utc"
                        )
                        if isinstance(
                            record,
                            dict,
                        )
                        else None
                    ),
                    "received_monotonic_ns": (
                        record.get(
                            "received_monotonic_ns"
                        )
                        if isinstance(
                            record,
                            dict,
                        )
                        else None
                    ),
                    "U": (
                        record.get("U")
                        if isinstance(
                            record,
                            dict,
                        )
                        else None
                    ),
                    "status":
                        INSUFFICIENT_SOURCE_EVIDENCE,
                    "reasons":
                        list(source_reasons),
                }
            )

    else:
        for record_index, record in enumerate(
            records
        ):
            result = (
                analyze_record_depth_panel(
                    record,
                    capture_id=capture_id,
                    record_index=(
                        record_index
                    ),
                )
            )

            counts[
                result["status"]
            ] += 1

            if (
                result["status"]
                == EXECUTION_PANEL_ELIGIBLE
            ):
                panels.append(
                    result
                )
            else:
                exclusions.append(
                    result
                )

    if (
        sum(counts.values())
        != len(records)
    ):
        raise ValueError(
            "Panel outcome counts do not "
            "reconcile to Kuru observations."
        )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "capture_id":
            capture_id,
        "source_evidence_reasons":
            source_reasons,
        "summary": {
            "kuru_observations":
                len(records),
            "eligible_panels": (
                counts[
                    EXECUTION_PANEL_ELIGIBLE
                ]
            ),
            "panel_outcome_counts":
                counts,
        },
        "panels": panels,
        "exclusions": exclusions,
        "claim_boundaries":
            list(CLAIM_BOUNDARIES),
    }
