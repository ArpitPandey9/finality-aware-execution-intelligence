from __future__ import annotations

from decimal import Decimal

from finality_intelligence.alignment import (
    ALIGNED,
    INSUFFICIENT_SOURCE_EVIDENCE,
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
    align_dual_capture,
)
from finality_intelligence.metrics import (
    midpoint,
    reference_mid_difference,
    reference_mid_difference_bps,
    spread,
    spread_bps,
)
from finality_intelligence.normalization import normalize_kuru_price


SCHEMA_VERSION = "phase1.state_conditioned_top_of_book.v1"

STATE_ORDER = (
    "proposed",
    "voted",
    "finalized",
    "committed",
)

ECONOMICALLY_ELIGIBLE = "ECONOMICALLY_ELIGIBLE"
INVALID_STATE_PANEL = "INVALID_STATE_PANEL"
INVALID_REFERENCE_TOP = "INVALID_REFERENCE_TOP"

ELIGIBILITY_OUTCOMES = (
    ECONOMICALLY_ELIGIBLE,
    INVALID_STATE_PANEL,
    INVALID_REFERENCE_TOP,
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
    INSUFFICIENT_SOURCE_EVIDENCE,
)


CLAIM_BOUNDARIES = (
    "Kuru MON_USDC and Coinbase MON-USD are distinct markets; "
    "point-in-time alignment does not remove USD/USDC basis risk.",
    "Cross-venue midpoint differences are descriptive reference metrics, "
    "not automatically arbitrage, executable spread, alpha, finality premium, "
    "profit, or evidence of venue advantage.",
    "Reference age is a same-process local receive-age measure, not network, "
    "exchange, consensus, or protocol-finality latency.",
    "Kuru U is preserved only as an observed stream grouping field.",
)


def _market_metrics(bid, ask) -> dict:
    mid = midpoint(bid, ask)

    if mid <= 0:
        raise ValueError("Top-of-book midpoint must be greater than zero.")

    return {
        "bid": bid,
        "ask": ask,
        "midpoint": mid,
        "spread": spread(bid, ask),
        "spread_bps": spread_bps(bid, ask),
    }


def _derive_kuru_state(state_view: dict) -> dict:
    if not isinstance(state_view, dict):
        raise ValueError("Kuru state view must be a mapping.")

    raw_bid = state_view.get("best_bid_raw")
    raw_ask = state_view.get("best_ask_raw")

    bid = normalize_kuru_price(raw_bid)
    ask = normalize_kuru_price(raw_ask)
    metrics = _market_metrics(bid, ask)

    return {
        "best_bid_raw": raw_bid,
        "best_ask_raw": raw_ask,
        **metrics,
    }



def derive_kuru_state(
    state_view: dict,
) -> dict:
    """Public wrapper for canonical Phase 1 Kuru top derivation."""
    return _derive_kuru_state(
        state_view
    )


def _derive_coinbase_reference(reference: dict) -> dict:
    if not isinstance(reference, dict):
        raise ValueError("Coinbase reference must be a mapping.")

    top = reference.get("book_top_after")

    if not isinstance(top, dict):
        raise ValueError("Coinbase reference top is missing.")

    metrics = _market_metrics(
        top.get("best_bid"),
        top.get("best_offer"),
    )

    return {
        "record_index": reference.get("record_index"),
        "sequence_num": reference.get("sequence_num"),
        "received_at_utc": reference.get("received_at_utc"),
        "received_monotonic_ns": reference.get("received_monotonic_ns"),
        "best_bid": metrics["bid"],
        "best_offer": metrics["ask"],
        "midpoint": metrics["midpoint"],
        "spread": metrics["spread"],
        "spread_bps": metrics["spread_bps"],
    }


def _serialize_decimal(value: Decimal) -> str:
    return str(value)


def analyze_capture_top_of_book(
    capture: dict,
    *,
    capture_id: str,
    max_age_ms,
) -> dict:
    alignment = align_dual_capture(
        capture,
        capture_id=capture_id,
        max_age_ms=max_age_ms,
    )

    eligibility_counts = {
        outcome: 0
        for outcome in ELIGIBILITY_OUTCOMES
    }
    economic_rows: list[dict] = []

    for aligned_row in alignment["rows"]:
        alignment_status = aligned_row["status"]

        if alignment_status != ALIGNED:
            eligibility_counts[alignment_status] += 1
            continue

        try:
            coinbase = _derive_coinbase_reference(
                aligned_row["coinbase_reference"]
            )
        except (ArithmeticError, TypeError, ValueError):
            eligibility_counts[INVALID_REFERENCE_TOP] += 1
            continue

        states = aligned_row["kuru"].get("states")
        derived_states: dict[str, dict] = {}

        try:
            if not isinstance(states, dict):
                raise ValueError("Kuru states must be a mapping.")

            for state_name in STATE_ORDER:
                if state_name not in states:
                    raise ValueError(
                        f"Missing Kuru state: {state_name}"
                    )

                derived_states[state_name] = _derive_kuru_state(
                    states[state_name]
                )
        except (ArithmeticError, TypeError, ValueError):
            eligibility_counts[INVALID_STATE_PANEL] += 1
            continue

        eligibility_counts[ECONOMICALLY_ELIGIBLE] += 1

        coinbase_mid = coinbase["midpoint"]

        for state_name in STATE_ORDER:
            kuru = derived_states[state_name]
            kuru_mid = kuru["midpoint"]

            economic_rows.append({
                "capture_id": capture_id,
                "freshness_threshold_ms": alignment["max_age_ms"],
                "kuru_record_index": aligned_row["kuru"]["record_index"],
                "kuru_received_at_utc": aligned_row["kuru"]["received_at_utc"],
                "kuru_received_monotonic_ns": aligned_row["kuru"]["received_monotonic_ns"],
                "U": aligned_row["kuru"]["U"],
                "state": state_name,
                "kuru_best_bid_raw": kuru["best_bid_raw"],
                "kuru_best_ask_raw": kuru["best_ask_raw"],
                "kuru_best_bid": _serialize_decimal(kuru["bid"]),
                "kuru_best_ask": _serialize_decimal(kuru["ask"]),
                "kuru_midpoint": _serialize_decimal(kuru_mid),
                "kuru_spread": _serialize_decimal(kuru["spread"]),
                "kuru_spread_bps": _serialize_decimal(kuru["spread_bps"]),
                "coinbase_record_index": coinbase["record_index"],
                "coinbase_sequence_num": coinbase["sequence_num"],
                "coinbase_received_at_utc": coinbase["received_at_utc"],
                "coinbase_received_monotonic_ns": coinbase["received_monotonic_ns"],
                "coinbase_best_bid": _serialize_decimal(coinbase["best_bid"]),
                "coinbase_best_offer": _serialize_decimal(coinbase["best_offer"]),
                "coinbase_midpoint": _serialize_decimal(coinbase_mid),
                "coinbase_spread": _serialize_decimal(coinbase["spread"]),
                "coinbase_spread_bps": _serialize_decimal(coinbase["spread_bps"]),
                "reference_age_ms": aligned_row["reference_age_ms"],
                "alignment_status": alignment_status,
                "reference_mid_difference": _serialize_decimal(
                    reference_mid_difference(kuru_mid, coinbase_mid)
                ),
                "reference_mid_difference_bps": _serialize_decimal(
                    reference_mid_difference_bps(kuru_mid, coinbase_mid)
                ),
            })

    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": capture_id,
        "source_capture_schema_version": alignment["source_capture_schema_version"],
        "freshness_threshold_ms": alignment["max_age_ms"],
        "source_evidence_reasons": alignment["source_evidence_reasons"],
        "claim_boundaries": list(CLAIM_BOUNDARIES),
        "summary": {
            "kuru_observations": alignment["summary"]["kuru_observations"],
            "eligibility_counts": eligibility_counts,
            "economic_rows": len(economic_rows),
        },
        "rows": economic_rows,
    }
