from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


HEADERS = {
    "User-Agent": "finality-aware-execution-intelligence/0.1"
}

KURU_STATES = (
    "proposed",
    "voted",
    "finalized",
    "committed",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_json(url: str) -> dict:
    started = utc_now()
    request = urllib.request.Request(url, headers=HEADERS)

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.load(response)

        completed = utc_now()

        return {
            "ok": True,
            "request_started_utc": started,
            "request_completed_utc": completed,
            "http_status": response.status,
            "url": url,
            "data": payload,
        }

    except Exception as exc:
        completed = utc_now()

        return {
            "ok": False,
            "request_started_utc": started,
            "request_completed_utc": completed,
            "url": url,
            "error": f"{type(exc).__name__}: {exc}",
        }


def capture_cycle() -> dict:
    cycle_started = utc_now()

    kuru_books = {}

    for state in KURU_STATES:
        url = (
            "https://exchange.kuru.io/api/v3/depth"
            f"?symbol=MON_USDC&limit=20&state={state}"
        )
        kuru_books[state] = get_json(url)

    coinbase = get_json(
        "https://api.exchange.coinbase.com/"
        "products/MON-USD/book?level=2"
    )

    cycle_completed = utc_now()

    all_kuru_ok = all(
        kuru_books[state].get("ok") is True
        for state in KURU_STATES
    )

    coinbase_ok = coinbase.get("ok") is True

    return {
        "schema_version": "phase0.capture_cycle.v1",
        "capture_cycle_started_utc": cycle_started,
        "capture_cycle_completed_utc": cycle_completed,
        "writes_to_external_systems": False,
        "private_keys_used": False,
        "markets": {
            "kuru": "MON_USDC",
            "coinbase": "MON-USD",
        },
        "kuru": {
            "states": kuru_books,
        },
        "coinbase": {
            "MON-USD": coinbase,
        },
        "gate": {
            "all_kuru_states_ok": all_kuru_ok,
            "coinbase_ok": coinbase_ok,
            "overall": (
                "PASS"
                if all_kuru_ok and coinbase_ok
                else "REVIEW"
            ),
        },
    }


def write_capture(capture: dict) -> tuple[Path, Path]:
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    json_path = output_dir / f"capture_cycle_{timestamp}.json"
    hash_path = output_dir / f"capture_cycle_{timestamp}.sha256"

    encoded = (
        json.dumps(
            capture,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    json_path.write_bytes(encoded)

    digest = hashlib.sha256(encoded).hexdigest()

    hash_path.write_text(
        f"{digest}  {json_path.name}\n",
        encoding="utf-8",
    )

    return json_path, hash_path


def print_summary(capture: dict) -> None:
    print(
        "cycle_started:",
        capture["capture_cycle_started_utc"],
    )
    print(
        "cycle_completed:",
        capture["capture_cycle_completed_utc"],
    )
    print("gate:", capture["gate"])

    for state in KURU_STATES:
        response = capture["kuru"]["states"][state]

        if not response.get("ok"):
            print(
                state,
                "ERROR:",
                response.get("error"),
            )
            continue

        data = response["data"]

        print(
            state,
            "block=",
            data.get("lastUpdateId"),
            "E=",
            data.get("E"),
            "T=",
            data.get("T"),
            "best_bid=",
            data.get("bids", [[None]])[0][0]
            if data.get("bids")
            else None,
            "best_ask=",
            data.get("asks", [[None]])[0][0]
            if data.get("asks")
            else None,
        )

    cb = capture["coinbase"]["MON-USD"]

    if cb.get("ok"):
        data = cb["data"]

        print(
            "coinbase",
            "sequence=",
            data.get("sequence"),
            "best_bid=",
            data.get("bids", [[None]])[0][0]
            if data.get("bids")
            else None,
            "best_ask=",
            data.get("asks", [[None]])[0][0]
            if data.get("asks")
            else None,
        )
    else:
        print(
            "coinbase ERROR:",
            cb.get("error"),
        )


def main() -> int:
    capture = capture_cycle()
    json_path, hash_path = write_capture(capture)

    print_summary(capture)

    print("raw_json:", json_path)
    print("sha256_file:", hash_path)

    return 0 if capture["gate"]["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
