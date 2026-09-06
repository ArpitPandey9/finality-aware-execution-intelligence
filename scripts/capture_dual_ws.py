from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from finality_intelligence.dual_ws import (
    build_dual_capture,
    process_coinbase_message,
    write_dual_capture,
)
from finality_intelligence.kuru_ws import (
    normalize_monad_depth_event,
    utc_now,
)


KURU_URL = "wss://exchange.kuru.io/ws"

KURU_SUBSCRIBE = {
    "method": "SUBSCRIBE",
    "params": [
        "mon_usdc@monadDepth",
    ],
    "id": 1,
}

COINBASE_URL = (
    "wss://advanced-trade-ws.coinbase.com"
)

COINBASE_PRODUCT_ID = "MON-USD"

COINBASE_SUBSCRIBE = {
    "type": "subscribe",
    "product_ids": [
        COINBASE_PRODUCT_ID,
    ],
    "channel": "level2",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture Kuru multi-state and "
            "Coinbase MON-USD level2 WebSocket "
            "evidence concurrently."
        )
    )

    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=10.0,
    )

    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=20.0,
    )

    parser.add_argument(
        "--output-dir",
        default="data/raw",
    )

    args = parser.parse_args()

    if args.duration_seconds <= 0:
        parser.error(
            "--duration-seconds must be "
            "greater than zero"
        )

    if args.timeout_seconds <= 0:
        parser.error(
            "--timeout-seconds must be "
            "greater than zero"
        )

    return args


async def collect_kuru(
    *,
    duration_seconds: float,
    timeout_seconds: float,
) -> tuple[list[dict], str | None]:
    import websockets

    records = []
    error = None

    try:
        async with websockets.connect(
            KURU_URL,
            open_timeout=10,
            close_timeout=5,
            ping_interval=20,
            max_size=4 * 1024 * 1024,
        ) as ws:
            await ws.send(
                json.dumps(
                    KURU_SUBSCRIBE
                )
            )

            print(
                "kuru_subscription_sent:",
                KURU_SUBSCRIBE,
            )

            loop = asyncio.get_running_loop()

            deadline = (
                loop.time()
                + duration_seconds
            )

            while True:
                remaining = (
                    deadline
                    - loop.time()
                )

                if remaining <= 0:
                    break

                try:
                    raw = await asyncio.wait_for(
                        ws.recv(),
                        timeout=min(
                            timeout_seconds,
                            remaining,
                        ),
                    )
                except asyncio.TimeoutError:
                    if loop.time() >= deadline:
                        break

                    raise

                received_at = utc_now()

                received_monotonic_ns = (
                    time.monotonic_ns()
                )

                message = json.loads(
                    raw
                )

                if message.get("id") == 1:
                    print(
                        "kuru_subscription_response:",
                        message,
                    )
                    continue

                record = (
                    normalize_monad_depth_event(
                        message,
                        received_at_utc=(
                            received_at
                        ),
                    )
                )

                if record is None:
                    continue

                record[
                    "received_monotonic_ns"
                ] = received_monotonic_ns

                records.append(
                    record
                )

                if (
                    len(records) <= 5
                    or len(records) % 100 == 0
                ):
                    print(
                        "kuru_message",
                        len(records),
                        "U=",
                        record.get("U"),
                    )

    except Exception as exc:
        error = (
            f"{type(exc).__name__}: {exc}"
        )

    return records, error


async def collect_coinbase(
    *,
    duration_seconds: float,
    timeout_seconds: float,
) -> tuple[list[dict], str | None]:
    import websockets

    bids = {}
    offers = {}

    records = []
    error = None

    try:
        async with websockets.connect(
            COINBASE_URL,
            open_timeout=10,
            close_timeout=5,
            ping_interval=20,
            max_size=16 * 1024 * 1024,
        ) as ws:
            await ws.send(
                json.dumps(
                    COINBASE_SUBSCRIBE
                )
            )

            print(
                "coinbase_subscription_sent:",
                COINBASE_SUBSCRIBE,
            )

            loop = asyncio.get_running_loop()

            deadline = (
                loop.time()
                + duration_seconds
            )

            target_count = 0

            while True:
                remaining = (
                    deadline
                    - loop.time()
                )

                if remaining <= 0:
                    break

                try:
                    raw = await asyncio.wait_for(
                        ws.recv(),
                        timeout=min(
                            timeout_seconds,
                            remaining,
                        ),
                    )
                except asyncio.TimeoutError:
                    if loop.time() >= deadline:
                        break

                    raise

                received_at = utc_now()

                received_monotonic_ns = (
                    time.monotonic_ns()
                )

                message = json.loads(
                    raw
                )

                record = (
                    process_coinbase_message(
                        message,
                        received_at_utc=(
                            received_at
                        ),
                        received_monotonic_ns=(
                            received_monotonic_ns
                        ),
                        product_id=(
                            COINBASE_PRODUCT_ID
                        ),
                        bids=bids,
                        offers=offers,
                    )
                )

                # Preserve every Coinbase wrapper
                # message because wrapper-level
                # sequence continuity is audited.
                records.append(
                    record
                )

                if record[
                    "target_event_types"
                ]:
                    target_count += 1

                    if (
                        target_count <= 5
                        or target_count % 25 == 0
                    ):
                        print(
                            "coinbase_l2_message",
                            target_count,
                            "sequence=",
                            record.get(
                                "sequence_num"
                            ),
                            "events=",
                            record[
                                "target_event_types"
                            ],
                            "top=",
                            record[
                                "book_top_after"
                            ],
                        )

    except Exception as exc:
        error = (
            f"{type(exc).__name__}: {exc}"
        )

    return records, error


async def collect_dual(
    *,
    duration_seconds: float,
    timeout_seconds: float,
) -> dict:
    session_started_utc = utc_now()

    kuru_task = asyncio.create_task(
        collect_kuru(
            duration_seconds=(
                duration_seconds
            ),
            timeout_seconds=(
                timeout_seconds
            ),
        )
    )

    coinbase_task = asyncio.create_task(
        collect_coinbase(
            duration_seconds=(
                duration_seconds
            ),
            timeout_seconds=(
                timeout_seconds
            ),
        )
    )

    (
        kuru_result,
        coinbase_result,
    ) = await asyncio.gather(
        kuru_task,
        coinbase_task,
    )

    session_completed_utc = utc_now()

    kuru_records, kuru_error = (
        kuru_result
    )

    (
        coinbase_records,
        coinbase_error,
    ) = coinbase_result

    return build_dual_capture(
        requested_duration_seconds=(
            duration_seconds
        ),
        session_started_utc=(
            session_started_utc
        ),
        session_completed_utc=(
            session_completed_utc
        ),
        kuru_records=kuru_records,
        kuru_error=kuru_error,
        coinbase_records=(
            coinbase_records
        ),
        coinbase_error=(
            coinbase_error
        ),
    )


def print_summary(
    capture: dict,
) -> None:
    kuru = capture[
        "sources"
    ][
        "kuru"
    ]

    coinbase = capture[
        "sources"
    ][
        "coinbase"
    ]

    print()
    print(
        "===== DUAL WS CAPTURE SUMMARY ====="
    )

    print(
        "schema_version:",
        capture["schema_version"],
    )

    print(
        "requested_duration_seconds:",
        capture[
            "requested_duration_seconds"
        ],
    )

    print()
    print(
        "===== KURU ====="
    )

    print(
        "error:",
        kuru["error"],
    )

    print(
        "captured_messages:",
        kuru[
            "summary"
        ][
            "captured_messages"
        ],
    )

    print(
        "unique_U:",
        kuru[
            "summary"
        ][
            "unique_U"
        ],
    )

    print()
    print(
        "===== COINBASE ====="
    )

    print(
        "error:",
        coinbase["error"],
    )

    for key in (
        "messages_received",
        "target_l2_messages",
        "first_target_includes_snapshot",
        "target_l2_messages_before_first_snapshot",
        "target_l2_messages_without_top_after_snapshot",
        "snapshot_events",
        "update_events",
        "target_updates",
        "zero_quantity_updates",
        "messages_missing_sequence",
        "wrapper_sequence_non_plus_one_transitions",
        "crossed_or_locked_messages",
        "final_bid_levels",
        "final_offer_levels",
    ):
        print(
            f"{key}:",
            coinbase[
                "summary"
            ][key],
        )

    print(
        "l2_sequence_delta_counts:",
        coinbase[
            "summary"
        ][
            "l2_sequence_delta_counts"
        ],
    )

    print(
        "final_top:",
        coinbase[
            "summary"
        ][
            "final_top"
        ],
    )

    print()
    print(
        "===== TEMPORAL OVERLAP ====="
    )

    for key, value in capture[
        "temporal_overlap"
    ].items():
        print(
            f"{key}:",
            value,
        )

    print()
    print(
        "===== GATE ====="
    )

    for key, value in capture[
        "gate"
    ].items():
        print(
            f"{key}:",
            value,
        )


def main() -> int:
    args = parse_args()

    stamp = datetime.now(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    capture = asyncio.run(
        collect_dual(
            duration_seconds=(
                args.duration_seconds
            ),
            timeout_seconds=(
                args.timeout_seconds
            ),
        )
    )

    output_path = (
        Path(args.output_dir)
        / f"dual_ws_{stamp}.json"
    )

    raw_path, hash_path = (
        write_dual_capture(
            capture,
            output_path,
        )
    )

    print_summary(
        capture
    )

    print()

    print(
        "raw_json:",
        raw_path,
    )

    print(
        "sha256_file:",
        hash_path,
    )

    return (
        0
        if capture[
            "gate"
        ][
            "overall"
        ]
        == "PASS"
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
