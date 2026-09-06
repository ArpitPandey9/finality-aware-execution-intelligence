from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.analyze_staleness import load_verified_capture
from finality_intelligence.staleness import CORE_THRESHOLDS_MS
from finality_intelligence.top_of_book import (
    analyze_capture_top_of_book,
)
from finality_intelligence.top_of_book_aggregation import (
    aggregate_top_of_book,
)


SCHEMA_VERSION = "phase1.state_conditioned_top_of_book_report.v1"

REPORT_CLAIM_BOUNDARIES = (
    "The dataset fingerprint binds the ordered source capture identifiers and verified SHA256 hashes; it is not a hash of the derived result.",
    "The 250 ms, 500 ms, and 1000 ms results are overlapping freshness-sensitivity analyses, not independent samples.",
    "Pooled market summaries are descriptive and must be interpreted alongside capture-level variation.",
    "State-view contrasts do not establish temporal quote progression, causal finality effects, executable arbitrage, alpha, or profit.",
)


def _canonical_hash(value) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def _fingerprint_input(provenance: list[dict]) -> list[dict]:
    return [
        {
            "capture_id": source["capture_id"],
            "sha256": source["sha256"],
        }
        for source in provenance
    ]


def build_report(paths) -> dict:
    paths = [Path(path) for path in paths]

    if not paths:
        raise ValueError("At least one capture path is required.")

    verified = []
    provenance = []

    for path in paths:
        capture, source = load_verified_capture(path)
        verified.append((capture, source))
        provenance.append(source)

    capture_ids = [
        source["capture_id"]
        for source in provenance
    ]

    if len(set(capture_ids)) != len(capture_ids):
        raise ValueError("Capture identifiers must be unique.")

    threshold_results = {}

    for threshold in CORE_THRESHOLDS_MS:
        analyses = []

        for capture, source in verified:
            analysis = analyze_capture_top_of_book(
                capture,
                capture_id=source["capture_id"],
                max_age_ms=threshold,
            )

            if analysis["source_evidence_reasons"]:
                raise ValueError(
                    "Insufficient source evidence for "
                    f"{source['capture_id']}: "
                    f"{analysis['source_evidence_reasons']}"
                )

            analyses.append(analysis)

        threshold_results[str(threshold)] = (
            aggregate_top_of_book(analyses)
        )

    fingerprint_input = _fingerprint_input(provenance)

    return {
        "schema_version": SCHEMA_VERSION,
        "core_thresholds_ms": [
            str(value)
            for value in CORE_THRESHOLDS_MS
        ],
        "dataset_fingerprint": _canonical_hash(
            fingerprint_input
        ),
        "source_captures": provenance,
        "results_by_threshold_ms": threshold_results,
        "claim_boundaries": list(REPORT_CLAIM_BOUNDARIES),
    }


def render_report(report: dict) -> str:
    return json.dumps(
        report,
        indent=2,
        sort_keys=True,
    ) + "\n"


def write_report(report: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_report(report),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a provenance-bound Phase 1 "
            "state-conditioned top-of-book report."
        )
    )
    parser.add_argument(
        "captures",
        nargs="+",
        type=Path,
        help=(
            "Dual-WebSocket capture JSON files with "
            "matching SHA256 sidecars."
        ),
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination JSON report path.",
    )

    args = parser.parse_args()
    report = build_report(args.captures)
    write_report(report, args.output)

    print(
        "dataset_fingerprint:",
        report["dataset_fingerprint"],
    )
    print(
        "source_capture_count:",
        len(report["source_captures"]),
    )
    print(
        "thresholds_ms:",
        ",".join(report["core_thresholds_ms"]),
    )
    print("json:", args.output)


if __name__ == "__main__":
    main()
