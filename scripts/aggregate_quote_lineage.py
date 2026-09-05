from __future__ import annotations

import argparse
import json
from pathlib import Path

from finality_intelligence.lineage_aggregation import (
    aggregate_captures,
    verify_capture_hash,
)


EXPECTED_SCHEMA = (
    "phase0.kuru_monad_depth_ws.v2"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate episode-aware quote "
            "lineage across Kuru WS captures."
        )
    )

    parser.add_argument(
        "--captures",
        nargs="+",
        required=True,
    )

    parser.add_argument(
        "--minimum-followup-ms",
        type=float,
        default=1000.0,
    )

    return parser.parse_args()


def pct(
    value: float | None,
) -> str:
    if value is None:
        return "N/A"

    return (
        f"{value * 100:.2f}%"
    )


def show_distribution(
    label: str,
    values: dict,
    *,
    percentage: bool = False,
) -> None:
    print(label)

    if values["count"] == 0:
        print("  count: 0")
        return

    print(
        "  count:",
        values["count"],
    )

    for key in (
        "min",
        "median",
        "mean",
        "max",
    ):
        value = values[key]

        if percentage:
            shown = pct(
                value
            )
        else:
            shown = round(
                value,
                3,
            )

        print(
            f"  {key}:",
            shown,
        )


def main() -> int:
    args = parse_args()

    loaded = []

    print(
        "===== HASH VERIFICATION ====="
    )

    for raw_path in args.captures:
        path = Path(
            raw_path
        )

        digest = (
            verify_capture_hash(
                path
            )
        )

        with path.open(
            encoding="utf-8"
        ) as f:
            capture = json.load(
                f
            )

        if (
            capture.get(
                "schema_version"
            )
            != EXPECTED_SCHEMA
        ):
            raise ValueError(
                f"{path}: expected "
                f"{EXPECTED_SCHEMA}"
            )

        if (
            capture.get(
                "gate",
                {},
            ).get(
                "overall"
            )
            != "PASS"
        ):
            raise ValueError(
                f"{path}: capture gate "
                "is not PASS"
            )

        loaded.append(
            (
                path.name,
                capture,
            )
        )

        print(
            path.name,
            "OK",
            digest[:16],
        )

    result = aggregate_captures(
        loaded,
        minimum_followup_ms=(
            args.minimum_followup_ms
        ),
    )

    print()
    print(
        "===== AGGREGATION SUMMARY ====="
    )

    print(
        "capture_count:",
        result["capture_count"],
    )

    print(
        "captured_messages_total:",
        result[
            "captured_messages_total"
        ],
    )

    print(
        "sum_unique_U_within_captures:",
        result[
            "sum_unique_U_within_captures"
        ],
    )

    for capture in (
        result["per_capture"]
    ):
        print()
        print(
            "===== CAPTURE ====="
        )

        print(
            "name:",
            capture["capture"],
        )

        print(
            "messages:",
            capture[
                "captured_messages"
            ],
        )

        print(
            "unique_U_within_capture:",
            capture[
                "unique_U_within_capture"
            ],
        )

        for mode, summary in (
            capture["modes"].items()
        ):
            print()
            print(
                "mode:",
                mode,
            )

            print(
                "proposed_episodes:",
                summary[
                    "proposed_episodes"
                ],
            )

            print(
                "reentry_ambiguous_episodes:",
                summary[
                    "reentry_ambiguous_episodes"
                ],
            )

            print(
                "evaluable_episodes:",
                summary[
                    "evaluable_episodes"
                ],
            )

            print(
                "evaluable_ordered:",
                summary[
                    "evaluable_ordered"
                ],
            )

            print(
                "ordered_rate:",
                pct(
                    summary[
                        "ordered_rate"
                    ]
                ),
            )

            print(
                "evaluable_later_progressions:",
                summary[
                    "evaluable_later_progressions"
                ],
            )

            print(
                "later_progression_rate:",
                pct(
                    summary[
                        "later_progression_rate"
                    ]
                ),
            )

    print()
    print(
        "===== CROSS-CAPTURE DESCRIPTIVE SUMMARY ====="
    )

    for mode, summary in (
        result[
            "cross_capture"
        ].items()
    ):
        print()
        print(
            "===== MODE:",
            mode,
            "====="
        )

        totals = summary[
            "descriptive_pooled_totals"
        ]

        print(
            "pooled_evaluable_episodes:",
            totals[
                "evaluable_episodes"
            ],
        )

        print(
            "pooled_evaluable_ordered:",
            totals[
                "evaluable_ordered"
            ],
        )

        print(
            "pooled_ordered_rate_descriptive_only:",
            pct(
                totals[
                    "ordered_rate"
                ]
            ),
        )

        print(
            "pooled_evaluable_later_progressions:",
            totals[
                "evaluable_later_progressions"
            ],
        )

        print(
            "pooled_later_progression_rate_descriptive_only:",
            pct(
                totals[
                    "later_progression_rate"
                ]
            ),
        )

        print()

        show_distribution(
            "capture_level_ordered_rate:",
            summary[
                "capture_level_ordered_rate"
            ],
            percentage=True,
        )

        print()

        show_distribution(
            "capture_level_later_progression_rate:",
            summary[
                "capture_level_later_progression_rate"
            ],
            percentage=True,
        )

        print()

        for state, values in (
            summary[
                "descriptive_pooled_latency_ms"
            ].items()
        ):
            show_distribution(
                (
                    "pooled_"
                    f"{state}_latency_ms:"
                ),
                values,
            )

    print()
    print(
        "===== CLAIM BOUNDARY ====="
    )

    print(
        "Captures are separate observation "
        "windows, not assumed statistically "
        "independent."
    )

    print(
        "Pooled episode rates are descriptive "
        "only and are not inferential survival "
        "estimates."
    )

    print(
        "U remains an observed stream grouping "
        "field only."
    )

    print(
        "Latency values remain client-observed "
        "first-seen differences."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
