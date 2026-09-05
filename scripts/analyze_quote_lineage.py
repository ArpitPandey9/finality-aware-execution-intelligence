from __future__ import annotations

import argparse
import json
import statistics

from finality_intelligence.quote_lineage import (
    analyze_quote_lineage,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze same-U top-quote "
            "state-view lineage."
        )
    )

    parser.add_argument(
        "--capture",
        required=True,
    )

    return parser.parse_args()


def latency_values(
    rows: list[dict],
    state: str,
) -> list[float]:
    key = f"{state}_delta_ms"

    return [
        row[key]
        for row in rows
        if (
            row["evaluable"]
            and row[
                "observed_later_progression"
            ]
            and row[key] is not None
        )
    ]

def print_analysis(
    analysis: dict,
) -> None:
    summary = analysis[
        "summary"
    ]

    rows = analysis["rows"]

    print()
    print(
        "identity_mode:",
        summary["identity_mode"],
    )

    for key, value in (
        summary.items()
    ):
        if key == "identity_mode":
            continue

        print(
            f"{key}:",
            value,
        )

    print()
    print(
        "===== LATER-PROGRESSION FIRST-SEEN LATENCIES ====="
    )

    for state in (
        "voted",
        "finalized",
        "committed",
    ):
        values = latency_values(
            rows,
            state,
        )

        print(
            state,
            "matches=",
            len(values),
        )

        if values:
            print(
                "  min_ms=",
                round(
                    min(values),
                    3,
                ),
            )

            print(
                "  median_ms=",
                round(
                    statistics.median(
                        values
                    ),
                    3,
                ),
            )

            print(
                "  max_ms=",
                round(
                    max(values),
                    3,
                ),
            )

    print()
    print(
        "===== EVALUABLE LATER PROGRESSION EXAMPLES ====="
    )

    examples = [
        row
        for row in rows
        if (
            row["evaluable"]
            and row[
                "observed_later_progression"
            ]
        )
    ][:10]

    for row in examples:
        print()

        print(
            "U=",
            row["U"],
            "side=",
            row["side"],
            "identity=",
            row["identity"],
        )

        print(
            "episode=",
            row["episode_number"],
            "proposed_records=",
            (
                row["episode_start_record"],
                row["episode_end_record"],
            ),
        )

        for state in (
            "voted",
            "finalized",
            "committed",
        ):
            item = row[state]

            print(
                state,
                "record=",
                (
                    item["record_index"]
                    if item
                    else None
                ),
                "delta_ms=",
                (
                    round(
                        row[
                            f"{state}_delta_ms"
                        ],
                        3,
                    )
                    if row[
                        f"{state}_delta_ms"
                    ]
                    is not None
                    else None
                ),
            )


def main() -> int:
    args = parse_args()

    with open(
        args.capture,
        encoding="utf-8",
    ) as f:
        capture = json.load(f)

    if (
        capture.get(
            "schema_version"
        )
        != "phase0.kuru_monad_depth_ws.v2"
    ):
        raise ValueError(
            "Expected "
            "phase0.kuru_monad_depth_ws.v2"
        )

    print(
        "capture:",
        args.capture,
    )

    print(
        "captured_messages:",
        len(capture["records"]),
    )

    print(
        "\n===== EXACT PRICE + QUANTITY ====="
    )

    exact = analyze_quote_lineage(
        capture["records"],
        identity_mode=(
            "price_quantity"
        ),
        capture_end_utc=(
            capture[
                "connection_completed_utc"
            ]
        ),
    )

    print_analysis(
        exact
    )

    print(
        "\n===== PRICE LEVEL ONLY ====="
    )

    price = analyze_quote_lineage(
        capture["records"],
        identity_mode="price",
        capture_end_utc=(
            capture[
                "connection_completed_utc"
            ]
        ),
    )

    print_analysis(
        price
    )

    print()
    print(
        "===== CLAIM BOUNDARY ====="
    )

    print(
        "U is only an observed stream "
        "grouping field."
    )

    print(
        "Quote identity does not establish "
        "order identity or ownership."
    )

    print(
        "Exact quote means identical top-level "
        "price and quantity."
    )

    print(
        "Price-only survival allows quantity "
        "to change."
    )

    print(
        "Re-entry keys are preserved but excluded "
        "from evaluable lineage statistics because "
        "episode attribution is ambiguous."
    )

    print(
        "Not observed in later states is not "
        "classified as execution or finality "
        "failure."
    )

    print(
        "Latencies are client-observed "
        "first-seen differences."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
