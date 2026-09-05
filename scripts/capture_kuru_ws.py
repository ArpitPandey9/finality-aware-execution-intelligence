from __future__ import annotations

import argparse
import asyncio
import json

from finality_intelligence.kuru_ws import (
    build_capture,
    normalize_monad_depth_event,
    utc_now,
    write_capture,
)


URL = "wss://exchange.kuru.io/ws"

SUBSCRIBE = {
    "method": "SUBSCRIBE",
    "params": [
        "mon_usdc@monadDepth",
    ],
    "id": 1,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture Kuru multi-state "
            "order-book WebSocket evidence."
        )
    )

    target = (
        parser.add_mutually_exclusive_group()
    )

    target.add_argument(
        "--updates",
        type=int,
        default=None,
        help=(
            "Stop after this many target "
            "messages."
        ),
    )

    target.add_argument(
        "--duration-seconds",
        type=float,
        default=None,
        help=(
            "Capture messages for this "
            "wall-clock duration."
        ),
    )

    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=20.0,
    )

    args = parser.parse_args()

    if (
        args.updates is None
        and args.duration_seconds is None
    ):
        args.duration_seconds = 10.0

    if (
        args.updates is not None
        and args.updates <= 0
    ):
        parser.error(
            "--updates must be greater than zero"
        )

    if (
        args.duration_seconds is not None
        and args.duration_seconds <= 0
    ):
        parser.error(
            "--duration-seconds must be greater than zero"
        )

    if args.timeout_seconds <= 0:
        parser.error(
            "--timeout-seconds must be greater than zero"
        )

    return args


async def collect_updates(
    *,
    requested_updates: int | None,
    duration_seconds: float | None,
    timeout_seconds: float,
) -> tuple[
    str,
    str,
    list[dict],
    str | None,
]:
    try:
        import websockets
    except ImportError:
        started = utc_now()
        completed = utc_now()

        return (
            started,
            completed,
            [],
            "ImportError: websockets package is not installed",
        )

    started = utc_now()
    records = []
    error = None

    try:
        async with websockets.connect(
            URL,
            open_timeout=10,
            close_timeout=5,
            ping_interval=20,
            max_size=4 * 1024 * 1024,
        ) as ws:
            await ws.send(
                json.dumps(SUBSCRIBE)
            )

            print(
                "subscription_sent:",
                SUBSCRIBE,
            )

            loop = asyncio.get_running_loop()

            deadline = (
                loop.time()
                + duration_seconds
                if duration_seconds
                is not None
                else None
            )

            while True:
                if (
                    requested_updates
                    is not None
                    and len(records)
                    >= requested_updates
                ):
                    break

                if deadline is not None:
                    remaining = (
                        deadline
                        - loop.time()
                    )

                    if remaining <= 0:
                        break

                    receive_timeout = min(
                        timeout_seconds,
                        remaining,
                    )
                else:
                    receive_timeout = (
                        timeout_seconds
                    )

                try:
                    raw = (
                        await asyncio.wait_for(
                            ws.recv(),
                            timeout=receive_timeout,
                        )
                    )
                except asyncio.TimeoutError:
                    if (
                        deadline is not None
                        and loop.time()
                        >= deadline
                    ):
                        break

                    raise

                received_at = utc_now()

                message = json.loads(raw)

                if message.get("id") == 1:
                    print(
                        "subscription_response:",
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

                records.append(record)

                if (
                    len(records) <= 10
                    or len(records) % 100 == 0
                ):
                    print(
                        "message",
                        len(records),
                        "U=",
                        record.get("U"),
                        "same_top=",
                        record.get(
                            "all_states_same_top_of_book"
                        ),
                    )

    except Exception as exc:
        error = (
            f"{type(exc).__name__}: {exc}"
        )

    completed = utc_now()

    return (
        started,
        completed,
        records,
        error,
    )


def print_summary(
    capture: dict,
) -> None:
    print()
    print(
        "===== WS CAPTURE SUMMARY ====="
    )

    print(
        "schema_version:",
        capture["schema_version"],
    )

    print(
        "capture_mode:",
        capture["capture_mode"],
    )

    print(
        "stream:",
        capture["stream"],
    )

    print(
        "gate:",
        capture["gate"],
    )

    print(
        "error:",
        capture["error"],
    )

    for key, value in (
        capture["summary"].items()
    ):
        print(
            f"{key}:",
            value,
        )


async def async_main() -> int:
    args = parse_args()

    (
        started,
        completed,
        records,
        error,
    ) = await collect_updates(
        requested_updates=args.updates,
        duration_seconds=(
            args.duration_seconds
        ),
        timeout_seconds=(
            args.timeout_seconds
        ),
    )

    capture = build_capture(
        records=records,
        requested_updates=args.updates,
        requested_duration_seconds=(
            args.duration_seconds
        ),
        connection_started_utc=started,
        connection_completed_utc=completed,
        error=error,
    )

    json_path, hash_path = (
        write_capture(capture)
    )

    print_summary(capture)

    print(
        "raw_json:",
        json_path,
    )

    print(
        "sha256_file:",
        hash_path,
    )

    return (
        0
        if capture["gate"]["overall"]
        == "PASS"
        else 1
    )


def main() -> int:
    return asyncio.run(
        async_main()
    )


if __name__ == "__main__":
    raise SystemExit(main())
