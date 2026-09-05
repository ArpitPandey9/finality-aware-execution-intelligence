from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


KURU_STATES = (
    "proposed",
    "voted",
    "finalized",
    "committed",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(value) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def first_level(
    levels: list,
) -> tuple[str | None, str | None]:
    if not levels:
        return None, None

    level = levels[0]

    if (
        not isinstance(level, (list, tuple))
        or len(level) < 2
    ):
        return None, None

    return str(level[0]), str(level[1])


def normalize_monad_depth_event(
    message: dict,
    *,
    received_at_utc: str,
) -> dict | None:
    if message.get("e") != "monadDepthUpdate":
        return None

    state_payload = message.get("states") or {}

    states = {}
    signatures = []
    complete_top = True

    for state in KURU_STATES:
        book = state_payload.get(state) or {}

        bid, bid_qty = first_level(
            book.get("b", [])
        )

        ask, ask_qty = first_level(
            book.get("a", [])
        )

        states[state] = {
            "best_bid_raw": bid,
            "best_bid_quantity_raw": bid_qty,
            "best_ask_raw": ask,
            "best_ask_quantity_raw": ask_qty,
        }

        if bid is None or ask is None:
            complete_top = False

        signatures.append(
            (
                bid,
                bid_qty,
                ask,
                ask_qty,
            )
        )

    same_top = (
        complete_top
        and len(set(signatures)) == 1
    )

    return {
        "received_at_utc": received_at_utc,
        "event": message.get("e"),
        "symbol": message.get("s"),
        "U": message.get("U"),
        "E": message.get("E"),
        "T": message.get("T"),
        "all_states_same_top_of_book": same_top,
        "states": states,
        "raw_message": message,
    }


def _consecutive_equal_count(
    values: list,
) -> int:
    return sum(
        values[index]
        == values[index - 1]
        for index in range(
            1,
            len(values),
        )
    )


def summarize_records(
    records: list[dict],
) -> dict:
    update_ids = [
        record.get("U")
        for record in records
        if record.get("U") is not None
    ]

    raw_hashes = [
        canonical_hash(
            record.get("raw_message")
        )
        for record in records
    ]

    full_state_hashes = [
        canonical_hash(
            (
                record.get("raw_message")
                or {}
            ).get("states")
        )
        for record in records
    ]

    top_hashes = [
        canonical_hash(
            record.get("states")
        )
        for record in records
    ]

    same_top_count = sum(
        record.get(
            "all_states_same_top_of_book"
        )
        is True
        for record in records
    )

    different_top_count = sum(
        record.get(
            "all_states_same_top_of_book"
        )
        is False
        for record in records
    )

    return {
        "captured_messages": len(records),

        "messages_with_U": len(update_ids),
        "unique_U": len(set(update_ids)),
        "repeated_U_messages": (
            len(update_ids)
            - len(set(update_ids))
        ),
        "consecutive_repeated_U": (
            _consecutive_equal_count(
                update_ids
            )
        ),

        "unique_exact_raw_messages": (
            len(set(raw_hashes))
        ),
        "repeated_exact_raw_messages": (
            len(raw_hashes)
            - len(set(raw_hashes))
        ),
        "consecutive_identical_raw_messages": (
            _consecutive_equal_count(
                raw_hashes
            )
        ),

        "unique_full_state_payloads": (
            len(set(full_state_hashes))
        ),
        "repeated_full_state_payloads": (
            len(full_state_hashes)
            - len(set(full_state_hashes))
        ),
        "consecutive_identical_full_state_payloads": (
            _consecutive_equal_count(
                full_state_hashes
            )
        ),

        "unique_top_payloads": (
            len(set(top_hashes))
        ),
        "repeated_top_payloads": (
            len(top_hashes)
            - len(set(top_hashes))
        ),
        "consecutive_identical_top_payloads": (
            _consecutive_equal_count(
                top_hashes
            )
        ),

        "missing_E": sum(
            record.get("E") is None
            for record in records
        ),
        "missing_T": sum(
            record.get("T") is None
            for record in records
        ),

        "same_top_of_book_messages": (
            same_top_count
        ),
        "different_top_of_book_messages": (
            different_top_count
        ),
    }


def build_capture(
    *,
    records: list[dict],
    connection_started_utc: str,
    connection_completed_utc: str,
    requested_updates: int | None = None,
    requested_duration_seconds: float | None = None,
    error: str | None = None,
) -> dict:
    if (
        requested_updates is None
        and requested_duration_seconds is None
    ):
        raise ValueError(
            "A message-count or duration target is required."
        )

    if requested_duration_seconds is not None:
        capture_mode = "duration"
        success = (
            error is None
            and len(records) > 0
        )
    else:
        capture_mode = "message_count"
        success = (
            error is None
            and len(records)
            == requested_updates
        )

    return {
        "schema_version": (
            "phase0.kuru_monad_depth_ws.v2"
        ),
        "stream": "mon_usdc@monadDepth",
        "capture_mode": capture_mode,
        "requested_updates": requested_updates,
        "requested_duration_seconds": (
            requested_duration_seconds
        ),
        "connection_started_utc": (
            connection_started_utc
        ),
        "connection_completed_utc": (
            connection_completed_utc
        ),
        "writes_to_external_systems": False,
        "private_keys_used": False,
        "error": error,
        "summary": summarize_records(
            records
        ),
        "records": records,
        "gate": {
            "overall": (
                "PASS"
                if success
                else "REVIEW"
            )
        },
    }


def write_capture(
    capture: dict,
    *,
    output_dir: Path = Path("data/raw"),
) -> tuple[Path, Path]:
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    json_path = (
        output_dir
        / f"kuru_ws_{timestamp}.json"
    )

    hash_path = (
        output_dir
        / f"kuru_ws_{timestamp}.sha256"
    )

    encoded = (
        json.dumps(
            capture,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    json_path.write_bytes(encoded)

    digest = hashlib.sha256(
        encoded
    ).hexdigest()

    hash_path.write_text(
        f"{digest}  {json_path.name}\n",
        encoding="utf-8",
    )

    return json_path, hash_path
