from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation


SCHEMA_VERSION = "phase1.point_in_time_alignment.v1"

EXPECTED_KURU_MARKET = "MON_USDC"
EXPECTED_COINBASE_MARKET = "MON-USD"
EXPECTED_COINBASE_CHANNEL = "level2"

ALIGNED = "ALIGNED"
NO_PRIOR_REFERENCE = "NO_PRIOR_REFERENCE"
STALE_REFERENCE = "STALE_REFERENCE"
INSUFFICIENT_SOURCE_EVIDENCE = "INSUFFICIENT_SOURCE_EVIDENCE"


def _parse_max_age_ms(value) -> Decimal:
    if isinstance(value, (bool, float)):
        raise TypeError("max_age_ms must use an exact numeric representation.")

    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid max_age_ms.") from exc

    if not parsed.is_finite() or parsed < 0:
        raise ValueError("max_age_ms must be finite and non-negative.")

    return parsed


def _is_target_l2(record: dict) -> bool:
    return (
        record.get("channel") == "l2_data"
        and bool(record.get("target_event_types"))
    )



def is_target_l2_record(
    record: dict,
) -> bool:
    """Public wrapper for the canonical Phase 1 target-L2 predicate."""
    return _is_target_l2(record)


def _valid_monotonic(value) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    )


def _validate_source_capture(capture: dict) -> tuple[list[str], list[dict], list[tuple[int, dict]]]:
    reasons: list[str] = []

    if capture.get("schema_version") != "phase0.dual_ws_capture.v1":
        reasons.append("UNSUPPORTED_SOURCE_SCHEMA")

    if capture.get("gate", {}).get("overall") != "PASS":
        reasons.append("SOURCE_GATE_NOT_PASS")

    sources = capture.get("sources", {})
    kuru_source = sources.get("kuru", {})
    coinbase_source = sources.get("coinbase", {})

    if kuru_source.get("market") != EXPECTED_KURU_MARKET:
        reasons.append("KURU_MARKET_MISMATCH")

    if coinbase_source.get("market") != EXPECTED_COINBASE_MARKET:
        reasons.append("COINBASE_MARKET_MISMATCH")

    if coinbase_source.get("channel") != EXPECTED_COINBASE_CHANNEL:
        reasons.append("COINBASE_CHANNEL_MISMATCH")

    if kuru_source.get("error") is not None:
        reasons.append("KURU_SOURCE_ERROR")

    if coinbase_source.get("error") is not None:
        reasons.append("COINBASE_SOURCE_ERROR")

    kuru_records = kuru_source.get("records", [])
    coinbase_records = coinbase_source.get("records", [])

    if not isinstance(kuru_records, list) or not kuru_records:
        reasons.append("NO_KURU_RECORDS")
        kuru_records = []

    if not isinstance(coinbase_records, list) or not coinbase_records:
        reasons.append("NO_COINBASE_RECORDS")
        coinbase_records = []

    for record in kuru_records:
        if not _valid_monotonic(record.get("received_monotonic_ns")):
            reasons.append("INVALID_KURU_MONOTONIC_TIME")
            break

    sequences = [
        record.get("sequence_num")
        for record in coinbase_records
    ]

    if coinbase_records and any(
        not isinstance(value, int) or isinstance(value, bool)
        for value in sequences
    ):
        reasons.append("INVALID_COINBASE_WRAPPER_SEQUENCE")

    elif any(
        current - previous != 1
        for previous, current in zip(sequences, sequences[1:])
    ):
        reasons.append("COINBASE_WRAPPER_SEQUENCE_GAP")

    target_records = [
        (index, record)
        for index, record in enumerate(coinbase_records)
        if _is_target_l2(record)
    ]

    if not target_records:
        reasons.append("NO_COINBASE_TARGET_L2")
    else:
        first_target = target_records[0][1]

        if first_target.get("snapshot_events", 0) <= 0:
            reasons.append("FIRST_TARGET_NOT_SNAPSHOT")

        for _, record in target_records:
            if record.get("target_product_id") != EXPECTED_COINBASE_MARKET:
                reasons.append("COINBASE_TARGET_PRODUCT_MISMATCH")
                break

            if not _valid_monotonic(
                record.get("received_monotonic_ns")
            ):
                reasons.append("INVALID_COINBASE_MONOTONIC_TIME")
                break

            if record.get("book_top_after") is None:
                reasons.append("MISSING_COINBASE_BOOK_TOP")
                break

            if record.get("crossed_or_locked"):
                reasons.append("CROSSED_OR_LOCKED_COINBASE_BOOK")
                break

    return list(dict.fromkeys(reasons)), kuru_records, target_records


def _coinbase_reference(index: int, record: dict) -> dict:
    return {
        "record_index": index,
        "sequence_num": record.get("sequence_num"),
        "received_at_utc": record.get("received_at_utc"),
        "received_monotonic_ns": record.get("received_monotonic_ns"),
        "book_top_after": record.get("book_top_after"),
    }


def _kuru_view(index: int, record: dict) -> dict:
    return {
        "record_index": index,
        "received_at_utc": record.get("received_at_utc"),
        "received_monotonic_ns": record.get("received_monotonic_ns"),
        "U": record.get("U"),
        "states": record.get("states"),
    }


def align_dual_capture(
    capture: dict,
    *,
    capture_id: str,
    max_age_ms,
) -> dict:
    if not isinstance(capture_id, str) or not capture_id.strip():
        raise ValueError("capture_id must be a non-empty string.")

    threshold_ms = _parse_max_age_ms(max_age_ms)
    reasons, kuru_records, target_records = _validate_source_capture(capture)

    rows: list[dict] = []

    for kuru_index, kuru_record in enumerate(kuru_records):
        base = {
            "capture_id": capture_id,
            "kuru": _kuru_view(kuru_index, kuru_record),
            "coinbase_reference": None,
            "reference_age_ms": None,
        }

        if reasons:
            rows.append({
                **base,
                "status": INSUFFICIENT_SOURCE_EVIDENCE,
                "status_reason": reasons,
            })
            continue

        t_kuru = kuru_record["received_monotonic_ns"]

        prior = [
            (index, record)
            for index, record in target_records
            if record["received_monotonic_ns"] <= t_kuru
        ]

        if not prior:
            rows.append({
                **base,
                "status": NO_PRIOR_REFERENCE,
                "status_reason": ["NO_ELIGIBLE_PRIOR_COINBASE_RECORD"],
            })
            continue

        cb_index, cb_record = max(
            prior,
            key=lambda item: (
                item[1]["received_monotonic_ns"],
                item[0],
            ),
        )

        age_ns = t_kuru - cb_record["received_monotonic_ns"]
        age_ms = Decimal(age_ns) / Decimal(1_000_000)

        status = (
            STALE_REFERENCE
            if age_ms > threshold_ms
            else ALIGNED
        )

        rows.append({
            **base,
            "coinbase_reference": _coinbase_reference(cb_index, cb_record),
            "reference_age_ms": str(age_ms),
            "status": status,
            "status_reason": [
                "REFERENCE_TOO_OLD"
                if status == STALE_REFERENCE
                else "BACKWARD_ASOF_MATCH"
            ],
        })

    counts = Counter(row["status"] for row in rows)

    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": capture_id,
        "source_capture_schema_version": capture.get("schema_version"),
        "max_age_ms": str(threshold_ms),
        "source_evidence_reasons": reasons,
        "summary": {
            "kuru_observations": len(rows),
            "status_counts": dict(sorted(counts.items())),
        },
        "rows": rows,
    }
