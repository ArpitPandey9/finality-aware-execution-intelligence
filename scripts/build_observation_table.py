from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from finality_intelligence.metrics import (
    midpoint,
    reference_mid_difference,
    reference_mid_difference_bps,
    spread,
    spread_bps,
)
from finality_intelligence.normalization import (
    normalize_kuru_price,
    normalize_kuru_size,
)


KURU_STATES = (
    "proposed",
    "voted",
    "finalized",
    "committed",
)


def decimal_text(value) -> str:
    return format(value, "f")


def verify_sha256(
    json_path: Path,
    hash_path: Path,
) -> None:
    if not json_path.exists():
        raise FileNotFoundError(
            f"Raw capture not found: {json_path}"
        )

    if not hash_path.exists():
        raise FileNotFoundError(
            f"SHA256 file not found: {hash_path}"
        )

    line = hash_path.read_text(
        encoding="utf-8"
    ).strip()

    try:
        expected_hash, expected_name = line.split(
            "  ",
            1,
        )
    except ValueError as exc:
        raise ValueError(
            f"Invalid SHA256 file format: {hash_path}"
        ) from exc

    if expected_name != json_path.name:
        raise ValueError(
            "SHA256 filename does not match raw capture."
        )

    actual_hash = hashlib.sha256(
        json_path.read_bytes()
    ).hexdigest()

    if actual_hash != expected_hash:
        raise ValueError(
            f"SHA256 mismatch: {json_path}"
        )


def first_level(
    payload: dict,
    side: str,
) -> tuple[str | None, str | None]:
    levels = payload.get(side, [])

    if not levels:
        return None, None

    level = levels[0]

    if len(level) < 2:
        return None, None

    return str(level[0]), str(level[1])


def add_kuru_state(
    row: dict,
    *,
    state: str,
    response: dict,
) -> None:
    prefix = f"kuru_{state}"

    row[f"{prefix}_ok"] = response.get("ok") is True
    row[f"{prefix}_request_started_utc"] = response.get(
        "request_started_utc"
    )
    row[f"{prefix}_request_completed_utc"] = response.get(
        "request_completed_utc"
    )

    if not response.get("ok"):
        row[f"{prefix}_error"] = response.get("error")
        return

    data = response["data"]

    bid_raw, bid_qty_raw = first_level(
        data,
        "bids",
    )
    ask_raw, ask_qty_raw = first_level(
        data,
        "asks",
    )

    row[f"{prefix}_block"] = data.get("lastUpdateId")
    row[f"{prefix}_event_time_ms"] = data.get("E")
    row[f"{prefix}_block_time_s"] = data.get("T")

    row[f"{prefix}_best_bid_raw"] = bid_raw
    row[f"{prefix}_best_ask_raw"] = ask_raw
    row[f"{prefix}_best_bid_qty_raw"] = bid_qty_raw
    row[f"{prefix}_best_ask_qty_raw"] = ask_qty_raw

    if bid_raw is not None:
        row[f"{prefix}_best_bid"] = decimal_text(
            normalize_kuru_price(bid_raw)
        )

    if ask_raw is not None:
        row[f"{prefix}_best_ask"] = decimal_text(
            normalize_kuru_price(ask_raw)
        )

    if bid_qty_raw is not None:
        row[f"{prefix}_best_bid_size"] = decimal_text(
            normalize_kuru_size(bid_qty_raw)
        )

    if ask_qty_raw is not None:
        row[f"{prefix}_best_ask_size"] = decimal_text(
            normalize_kuru_size(ask_qty_raw)
        )


def add_coinbase(
    row: dict,
    response: dict,
) -> None:
    row["coinbase_ok"] = response.get("ok") is True
    row["coinbase_request_started_utc"] = response.get(
        "request_started_utc"
    )
    row["coinbase_request_completed_utc"] = response.get(
        "request_completed_utc"
    )

    if not response.get("ok"):
        row["coinbase_error"] = response.get("error")
        return

    data = response["data"]

    bid, bid_qty = first_level(
        data,
        "bids",
    )
    ask, ask_qty = first_level(
        data,
        "asks",
    )

    row["coinbase_sequence"] = data.get("sequence")
    row["coinbase_best_bid"] = bid
    row["coinbase_best_ask"] = ask
    row["coinbase_best_bid_size"] = bid_qty
    row["coinbase_best_ask_size"] = ask_qty


def add_market_metrics(row: dict) -> None:
    for state in KURU_STATES:
        prefix = f"kuru_{state}"

        bid = row.get(
            f"{prefix}_best_bid"
        )
        ask = row.get(
            f"{prefix}_best_ask"
        )

        if bid is None or ask is None:
            continue

        market_mid = midpoint(
            bid,
            ask,
        )

        row[f"{prefix}_mid"] = decimal_text(
            market_mid
        )
        row[f"{prefix}_spread"] = decimal_text(
            spread(
                bid,
                ask,
            )
        )
        row[f"{prefix}_spread_bps"] = decimal_text(
            spread_bps(
                bid,
                ask,
            )
        )

    coinbase_bid = row.get(
        "coinbase_best_bid"
    )
    coinbase_ask = row.get(
        "coinbase_best_ask"
    )

    if (
        coinbase_bid is None
        or coinbase_ask is None
    ):
        return

    coinbase_mid = midpoint(
        coinbase_bid,
        coinbase_ask,
    )

    row["coinbase_mid"] = decimal_text(
        coinbase_mid
    )
    row["coinbase_spread"] = decimal_text(
        spread(
            coinbase_bid,
            coinbase_ask,
        )
    )
    row["coinbase_spread_bps"] = decimal_text(
        spread_bps(
            coinbase_bid,
            coinbase_ask,
        )
    )

    for state in KURU_STATES:
        kuru_mid = row.get(
            f"kuru_{state}_mid"
        )

        if kuru_mid is None:
            continue

        prefix = (
            f"kuru_{state}_vs_coinbase_reference"
        )

        row[f"{prefix}_mid_diff"] = decimal_text(
            reference_mid_difference(
                kuru_mid,
                coinbase_mid,
            )
        )

        row[f"{prefix}_mid_diff_bps"] = decimal_text(
            reference_mid_difference_bps(
                kuru_mid,
                coinbase_mid,
            )
        )


def build_row(observation: dict) -> dict:
    json_path = Path(observation["raw_json"])
    hash_path = Path(observation["sha256_file"])

    verify_sha256(
        json_path,
        hash_path,
    )

    capture = json.loads(
        json_path.read_text(
            encoding="utf-8"
        )
    )

    row = {
        "cycle_index": observation["index"],
        "cycle_gate": observation["gate"]["overall"],
        "capture_cycle_started_utc": capture[
            "capture_cycle_started_utc"
        ],
        "capture_cycle_completed_utc": capture[
            "capture_cycle_completed_utc"
        ],
        "raw_json": str(json_path),
        "sha256_file": str(hash_path),
    }

    for state in KURU_STATES:
        add_kuru_state(
            row,
            state=state,
            response=capture["kuru"]["states"][state],
        )

    add_coinbase(
        row,
        capture["coinbase"]["MON-USD"],
    )

    add_market_metrics(row)

    blocks = [
        row.get(f"kuru_{state}_block")
        for state in KURU_STATES
        if row.get(f"kuru_{state}_block") is not None
    ]

    if blocks:
        row["kuru_block_min"] = min(blocks)
        row["kuru_block_max"] = max(blocks)
        row["kuru_block_span"] = (
            row["kuru_block_max"]
            - row["kuru_block_min"]
        )
        row["kuru_all_states_same_block"] = (
            len(set(blocks)) == 1
        )

    top_books = []

    for state in KURU_STATES:
        bid = row.get(
            f"kuru_{state}_best_bid"
        )
        ask = row.get(
            f"kuru_{state}_best_ask"
        )

        if bid is not None and ask is not None:
            top_books.append((bid, ask))

    if top_books:
        row["kuru_all_states_same_top_of_book"] = (
            len(set(top_books)) == 1
        )

    return row


def build_rows(
    manifest_path: Path,
) -> list[dict]:
    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if (
        manifest.get("schema_version")
        != "phase0.capture_series.v1"
    ):
        raise ValueError(
            "Unsupported capture-series schema."
        )

    observations = manifest.get(
        "observations",
        [],
    )

    if (
        manifest.get("completed_cycles")
        != len(observations)
    ):
        raise ValueError(
            "Manifest completed_cycles does not match observations."
        )

    return [
        build_row(observation)
        for observation in observations
    ]


def write_csv(
    rows: list[dict],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = []

    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def default_output_path(
    manifest_path: Path,
) -> Path:
    name = manifest_path.name

    if name.endswith(".manifest.json"):
        name = name[: -len(".manifest.json")]

    return (
        Path("data/derived")
        / f"{name}.observations.csv"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a verified observation table "
            "from a capture-series manifest."
        )
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    rows = build_rows(args.manifest)

    if not rows:
        raise SystemExit(
            "No observations found in manifest."
        )

    output_path = (
        args.output
        if args.output is not None
        else default_output_path(
            args.manifest
        )
    )

    write_csv(
        rows,
        output_path,
    )

    print("observations:", len(rows))
    print("output:", output_path)

    for row in rows:
        print(
            "cycle",
            row["cycle_index"],
            "gate=",
            row["cycle_gate"],
            "block_span=",
            row.get("kuru_block_span"),
            "same_block=",
            row.get(
                "kuru_all_states_same_block"
            ),
            "same_top=",
            row.get(
                "kuru_all_states_same_top_of_book"
            ),
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
