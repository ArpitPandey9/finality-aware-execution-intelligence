from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

from finality_intelligence.kuru_ws import summarize_records


SCHEMA_VERSION = "phase0.dual_ws_capture.v1"


def _best_top(
    bids: dict[Decimal, Decimal],
    offers: dict[Decimal, Decimal],
) -> dict | None:
    if not bids or not offers:
        return None

    best_bid = max(bids)
    best_offer = min(offers)

    return {
        "best_bid": str(best_bid),
        "best_bid_quantity": str(bids[best_bid]),
        "best_offer": str(best_offer),
        "best_offer_quantity": str(
            offers[best_offer]
        ),
        "spread": str(
            best_offer - best_bid
        ),
    }


def process_coinbase_message(
    message: dict,
    *,
    received_at_utc: str,
    received_monotonic_ns: int,
    product_id: str,
    bids: dict[Decimal, Decimal],
    offers: dict[Decimal, Decimal],
) -> dict:
    event_types = []
    snapshot_events = 0
    update_events = 0
    target_updates = 0
    zero_quantity_updates = 0

    for event in message.get("events", []):
        if event.get("product_id") != product_id:
            continue

        event_type = event.get("type")
        event_types.append(event_type)

        if event_type == "snapshot":
            snapshot_events += 1

            # A snapshot establishes a fresh
            # local book baseline.
            bids.clear()
            offers.clear()

        elif event_type == "update":
            update_events += 1

        for update in event.get(
            "updates",
            [],
        ):
            side = update.get("side")

            if side == "bid":
                book = bids
            elif side == "offer":
                book = offers
            else:
                raise ValueError(
                    f"Unknown Coinbase side: {side}"
                )

            price = Decimal(
                update["price_level"]
            )

            quantity = Decimal(
                update["new_quantity"]
            )

            if price < 0 or quantity < 0:
                raise ValueError(
                    "Coinbase price and quantity "
                    "must be non-negative."
                )

            target_updates += 1

            if quantity == 0:
                book.pop(
                    price,
                    None,
                )

                zero_quantity_updates += 1
            else:
                # Coinbase level2 new_quantity
                # is treated as the current
                # quantity at that price level.
                book[price] = quantity

    top = _best_top(
        bids,
        offers,
    )

    crossed_or_locked = (
        top is not None
        and Decimal(
            top["best_bid"]
        )
        >= Decimal(
            top["best_offer"]
        )
    )

    return {
        "received_at_utc": received_at_utc,
        "received_monotonic_ns": (
            received_monotonic_ns
        ),
        "channel": message.get("channel"),
        "timestamp": message.get(
            "timestamp"
        ),
        "sequence_num": message.get(
            "sequence_num"
        ),
        "target_product_id": product_id,
        "target_event_types": event_types,
        "snapshot_events": snapshot_events,
        "update_events": update_events,
        "target_updates": target_updates,
        "zero_quantity_updates": (
            zero_quantity_updates
        ),
        "bid_levels_after": len(bids),
        "offer_levels_after": len(offers),
        "book_top_after": top,
        "crossed_or_locked": (
            crossed_or_locked
        ),
        "raw_message": message,
    }


def _sequence_deltas(
    values: list[int],
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for previous, current in zip(
        values,
        values[1:],
    ):
        key = str(
            current - previous
        )

        counts[key] = (
            counts.get(key, 0) + 1
        )

    return counts


def summarize_coinbase_messages(
    records: list[dict],
) -> dict:
    sequence_values = [
        record["sequence_num"]
        for record in records
        if isinstance(
            record.get("sequence_num"),
            int,
        )
    ]

    missing_sequence = sum(
        not isinstance(
            record.get("sequence_num"),
            int,
        )
        for record in records
    )

    wrapper_gaps = [
        {
            "previous": previous,
            "current": current,
            "delta": current - previous,
        }
        for previous, current in zip(
            sequence_values,
            sequence_values[1:],
        )
        if current - previous != 1
    ]

    target_l2_records = [
        record
        for record in records
        if (
            record.get("channel")
            == "l2_data"
            and record.get(
                "target_event_types"
            )
        )
    ]

    l2_sequences = [
        record["sequence_num"]
        for record in target_l2_records
        if isinstance(
            record.get("sequence_num"),
            int,
        )
    ]

    last_target = (
        target_l2_records[-1]
        if target_l2_records
        else None
    )

    first_target = (
        target_l2_records[0]
        if target_l2_records
        else None
    )

    first_snapshot_index = next(
        (
            index
            for index, record
            in enumerate(
                target_l2_records
            )
            if record[
                "snapshot_events"
            ] > 0
        ),
        None,
    )

    target_l2_messages_before_first_snapshot = (
        first_snapshot_index
        if first_snapshot_index
        is not None
        else len(
            target_l2_records
        )
    )

    target_l2_messages_without_top_after_snapshot = (
        sum(
            record[
                "book_top_after"
            ]
            is None
            for record in (
                target_l2_records[
                    first_snapshot_index:
                ]
            )
        )
        if first_snapshot_index
        is not None
        else len(
            target_l2_records
        )
    )

    return {
        "messages_received": len(records),

        "messages_missing_sequence": (
            missing_sequence
        ),

        "wrapper_sequence_count": len(
            sequence_values
        ),

        "wrapper_sequence_first": (
            sequence_values[0]
            if sequence_values
            else None
        ),

        "wrapper_sequence_last": (
            sequence_values[-1]
            if sequence_values
            else None
        ),

        "wrapper_sequence_unique": len(
            set(sequence_values)
        ),

        "wrapper_sequence_non_plus_one_transitions": (
            len(wrapper_gaps)
        ),

        "wrapper_sequence_gap_examples": (
            wrapper_gaps[:10]
        ),

        "target_l2_messages": len(
            target_l2_records
        ),

        "first_target_event_types": (
            first_target[
                "target_event_types"
            ]
            if first_target
            else []
        ),

        "first_target_includes_snapshot": (
            first_target is not None
            and first_target[
                "snapshot_events"
            ] > 0
        ),

        "target_l2_messages_before_first_snapshot": (
            target_l2_messages_before_first_snapshot
        ),

        "target_l2_messages_without_top_after_snapshot": (
            target_l2_messages_without_top_after_snapshot
        ),

        "snapshot_events": sum(
            record["snapshot_events"]
            for record in records
        ),

        "update_events": sum(
            record["update_events"]
            for record in records
        ),

        "target_updates": sum(
            record["target_updates"]
            for record in records
        ),

        "zero_quantity_updates": sum(
            record[
                "zero_quantity_updates"
            ]
            for record in records
        ),

        # L2-only sequence deltas are
        # descriptive. They are NOT required
        # to be +1 because non-L2 wrapper
        # messages can consume a sequence.
        "l2_sequence_delta_counts": (
            _sequence_deltas(
                l2_sequences
            )
        ),

        "crossed_or_locked_messages": sum(
            record.get(
                "crossed_or_locked"
            )
            is True
            for record in target_l2_records
        ),

        "final_bid_levels": (
            last_target[
                "bid_levels_after"
            ]
            if last_target
            else 0
        ),

        "final_offer_levels": (
            last_target[
                "offer_levels_after"
            ]
            if last_target
            else 0
        ),

        "final_top": (
            last_target[
                "book_top_after"
            ]
            if last_target
            else None
        ),
    }


def _target_time_bounds(
    records: list[dict],
) -> tuple[int | None, int | None]:
    values = [
        record[
            "received_monotonic_ns"
        ]
        for record in records
        if isinstance(
            record.get(
                "received_monotonic_ns"
            ),
            int,
        )
    ]

    if not values:
        return None, None

    return min(values), max(values)


def build_dual_capture(
    *,
    requested_duration_seconds: float,
    session_started_utc: str,
    session_completed_utc: str,
    kuru_records: list[dict],
    kuru_error: str | None,
    coinbase_records: list[dict],
    coinbase_error: str | None,
) -> dict:
    if requested_duration_seconds <= 0:
        raise ValueError(
            "requested_duration_seconds "
            "must be greater than zero"
        )

    kuru_summary = summarize_records(
        kuru_records
    )

    coinbase_summary = (
        summarize_coinbase_messages(
            coinbase_records
        )
    )

    coinbase_target_records = [
        record
        for record in coinbase_records
        if (
            record.get("channel")
            == "l2_data"
            and record.get(
                "target_event_types"
            )
        )
    ]

    kuru_first, kuru_last = (
        _target_time_bounds(
            kuru_records
        )
    )

    coinbase_first, coinbase_last = (
        _target_time_bounds(
            coinbase_target_records
        )
    )

    overlap_ns = None
    first_receive_skew_ms = None

    if (
        kuru_first is not None
        and kuru_last is not None
        and coinbase_first is not None
        and coinbase_last is not None
    ):
        overlap_ns = max(
            0,
            min(
                kuru_last,
                coinbase_last,
            )
            - max(
                kuru_first,
                coinbase_first,
            ),
        )

        first_receive_skew_ms = (
            coinbase_first
            - kuru_first
        ) / 1_000_000

    kuru_pass = (
        kuru_error is None
        and kuru_summary[
            "captured_messages"
        ] > 0
    )

    coinbase_pass = (
        coinbase_error is None
        and coinbase_summary[
            "target_l2_messages"
        ] > 0
        and coinbase_summary[
            "snapshot_events"
        ] >= 1
        and coinbase_summary[
            "first_target_includes_snapshot"
        ]
        is True
        and coinbase_summary[
            "target_l2_messages_before_first_snapshot"
        ] == 0
        and coinbase_summary[
            "target_l2_messages_without_top_after_snapshot"
        ] == 0
        and coinbase_summary[
            "update_events"
        ] >= 1
        and coinbase_summary[
            "final_bid_levels"
        ] > 0
        and coinbase_summary[
            "final_offer_levels"
        ] > 0
        and coinbase_summary[
            "messages_missing_sequence"
        ] == 0
        and coinbase_summary[
            "wrapper_sequence_non_plus_one_transitions"
        ] == 0
        and coinbase_summary[
            "crossed_or_locked_messages"
        ] == 0
    )

    overlap_pass = (
        overlap_ns is not None
        and overlap_ns > 0
    )

    overall = (
        "PASS"
        if (
            kuru_pass
            and coinbase_pass
            and overlap_pass
        )
        else "REVIEW"
    )

    return {
        "schema_version": (
            SCHEMA_VERSION
        ),

        "requested_duration_seconds": (
            requested_duration_seconds
        ),

        "session_started_utc": (
            session_started_utc
        ),

        "session_completed_utc": (
            session_completed_utc
        ),

        "sources": {
            "kuru": {
                "stream": (
                    "mon_usdc@monadDepth"
                ),
                "market": "MON_USDC",
                "error": kuru_error,
                "summary": (
                    kuru_summary
                ),
                "records": (
                    kuru_records
                ),
            },

            "coinbase": {
                "channel": "level2",
                "market": "MON-USD",
                "error": coinbase_error,
                "summary": (
                    coinbase_summary
                ),
                "records": (
                    coinbase_records
                ),
            },
        },

        "temporal_overlap": {
            "kuru_first_target_monotonic_ns": (
                kuru_first
            ),

            "kuru_last_target_monotonic_ns": (
                kuru_last
            ),

            "coinbase_first_target_monotonic_ns": (
                coinbase_first
            ),

            "coinbase_last_target_monotonic_ns": (
                coinbase_last
            ),

            "target_message_envelope_overlap_seconds": (
                overlap_ns / 1_000_000_000
                if overlap_ns is not None
                else None
            ),

            "first_target_message_receive_skew_ms_coinbase_minus_kuru": (
                first_receive_skew_ms
            ),

            "definition": (
                "Overlap between intervals bracketed "
                "by the first and last observed target "
                "message receive times for each source."
            ),
        },

        "gate": {
            "kuru": (
                "PASS"
                if kuru_pass
                else "REVIEW"
            ),

            "coinbase": (
                "PASS"
                if coinbase_pass
                else "REVIEW"
            ),

            "temporal_overlap": (
                "PASS"
                if overlap_pass
                else "REVIEW"
            ),

            "overall": overall,
        },

        "claim_boundary": {
            "receive_times_are_client_observed": (
                True
            ),

            "streams_are_not_exchange_clock_synchronized": (
                True
            ),

            "kuru_U_semantics_not_assumed": (
                True
            ),

            "coinbase_wrapper_sequence_is_connection_observation": (
                True
            ),

            "mon_usdc_and_mon_usd_are_distinct_markets": (
                True
            ),

            "usd_usdc_basis_not_modeled": (
                True
            ),

            "no_trading_edge_claim": True,

            "no_finality_premium_claim": True,
        },
    }


def write_dual_capture(
    capture: dict,
    path: Path,
) -> tuple[Path, Path]:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = (
        json.dumps(
            capture,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    path.write_bytes(
        encoded
    )

    digest = hashlib.sha256(
        encoded
    ).hexdigest()

    hash_path = path.with_suffix(
        ".sha256"
    )

    hash_path.write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )

    return path, hash_path
