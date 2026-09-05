from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone


HEADERS = {
    "User-Agent": "finality-aware-execution-intelligence/0.1"
}


def get_json(url: str):
    req = urllib.request.Request(url, headers=HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return {
                "ok": True,
                "http_status": response.status,
                "data": json.load(response),
            }

    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


result = {
    "audit": "phase0_data_feasibility",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "writes_to_external_systems": False,
    "private_keys_used": False,
    "kuru": {},
    "coinbase": {},
}


# Kuru health
result["kuru"]["health"] = get_json(
    "https://exchange.kuru.io/health"
)


# Kuru MON/USDC order book across Monad consensus states
states = [
    "proposed",
    "voted",
    "finalized",
    "committed",
]

books = {}

for state in states:
    url = (
        "https://exchange.kuru.io/api/v3/depth"
        f"?symbol=MON_USDC&limit=20&state={state}"
    )

    response = get_json(url)

    if response["ok"]:
        data = response["data"]

        books[state] = {
            "ok": True,
            "http_status": response["http_status"],
            "lastUpdateId": data.get("lastUpdateId"),
            "event_time_ms": data.get("E"),
            "block_time_s": data.get("T"),
            "bid_levels": len(data.get("bids", [])),
            "ask_levels": len(data.get("asks", [])),
            "best_bid": (
                data.get("bids", [[None]])[0][0]
                if data.get("bids")
                else None
            ),
            "best_ask": (
                data.get("asks", [[None]])[0][0]
                if data.get("asks")
                else None
            ),
        }

    else:
        books[state] = response


result["kuru"]["MON_USDC_books"] = books


# Kuru 24-hour ticker
result["kuru"]["ticker"] = get_json(
    "https://exchange.kuru.io/api/v3/ticker/24hr?symbol=MON_USDC"
)


# Coinbase MON/USD Level-2 order book
coinbase = get_json(
    "https://api.exchange.coinbase.com/products/MON-USD/book?level=2"
)

if coinbase["ok"]:
    data = coinbase["data"]

    result["coinbase"]["MON-USD"] = {
        "ok": True,
        "http_status": coinbase["http_status"],
        "sequence": data.get("sequence"),
        "bid_levels": len(data.get("bids", [])),
        "ask_levels": len(data.get("asks", [])),
        "best_bid": (
            data.get("bids", [[None]])[0][0]
            if data.get("bids")
            else None
        ),
        "best_ask": (
            data.get("asks", [[None]])[0][0]
            if data.get("asks")
            else None
        ),
    }

else:
    result["coinbase"]["MON-USD"] = coinbase


# Phase-0 feasibility gate
kuru_health_ok = (
    result["kuru"]["health"].get("ok") is True
)

all_states_ok = all(
    books[state].get("ok") is True
    for state in states
)

coinbase_ok = (
    result["coinbase"]["MON-USD"].get("ok") is True
)


result["gate"] = {
    "kuru_health": kuru_health_ok,
    "kuru_MON_USDC_all_four_states": all_states_ok,
    "coinbase_MON_USD_l2": coinbase_ok,
    "overall": (
        "PASS"
        if kuru_health_ok
        and all_states_ok
        and coinbase_ok
        else "REVIEW"
    ),
}


print(json.dumps(result, indent=2))
