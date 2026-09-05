from __future__ import annotations

import argparse
from pathlib import Path

from finality_intelligence.lineage_evidence import (
    build_empirical_evidence,
    write_capture_csv,
    write_json,
    write_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a provenance-bound empirical "
            "quote-lineage evidence bundle."
        )
    )

    parser.add_argument(
        "--captures",
        nargs="+",
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "research/phase0/"
            "quote_lineage_evidence"
        ),
    )

    parser.add_argument(
        "--minimum-followup-ms",
        type=float,
        default=1000.0,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    capture_paths = [
        Path(value)
        for value in args.captures
    ]

    evidence = (
        build_empirical_evidence(
            capture_paths,
            minimum_followup_ms=(
                args.minimum_followup_ms
            ),
        )
    )

    output_dir = Path(
        args.output_dir
    )

    json_path = (
        output_dir
        / "QUOTE_LINEAGE_EMPIRICAL_RESULT.json"
    )

    csv_path = (
        output_dir
        / "QUOTE_LINEAGE_EMPIRICAL_RESULT.csv"
    )

    markdown_path = (
        output_dir
        / "QUOTE_LINEAGE_EMPIRICAL_RESULT.md"
    )

    write_json(
        evidence,
        json_path,
    )

    write_capture_csv(
        evidence,
        csv_path,
    )

    write_markdown(
        evidence,
        markdown_path,
    )

    print(
        "dataset_fingerprint_sha256:",
        evidence[
            "dataset_fingerprint_sha256"
        ],
    )

    print(
        "capture_count:",
        evidence[
            "aggregation"
        ][
            "capture_count"
        ],
    )

    print(
        "captured_messages_total:",
        evidence[
            "aggregation"
        ][
            "captured_messages_total"
        ],
    )

    print(
        "json:",
        json_path,
    )

    print(
        "csv:",
        csv_path,
    )

    print(
        "markdown:",
        markdown_path,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
