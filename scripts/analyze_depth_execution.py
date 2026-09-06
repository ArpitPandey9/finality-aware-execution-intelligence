from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.analyze_staleness import (
    load_verified_capture,
)
from finality_intelligence.depth_aggregation import (
    aggregate_depth_panels,
)
from finality_intelligence.depth_execution import (
    DEPTH_BANDS_BPS,
    SIDES,
    TARGET_BASE_QUANTITIES,
)
from finality_intelligence.depth_panel import (
    EXPECTED_KURU_MARKET,
    STATE_ORDER,
    analyze_capture_depth_panels,
)


SCHEMA_VERSION = (
    "phase1.state_conditioned_depth_execution_report.v1"
)

REPORT_CLAIM_BOUNDARIES = (
    "The dataset fingerprint binds the ordered source "
    "capture identifiers and verified SHA256 hashes; "
    "it is not a hash of the derived result.",
    "This initial depth layer is Kuru-only and does not "
    "apply Coinbase reference-age freshness thresholds.",
    "Simulated sweeps describe captured displayed book "
    "levels and are not actual order executions.",
    "State-view contrasts compare simultaneously observed "
    "views and do not establish causal finality effects.",
)


def _canonical_hash(
    value,
) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def _fingerprint_input(
    provenance: list[dict],
) -> list[dict]:
    return [
        {
            "capture_id":
                source["capture_id"],
            "sha256":
                source["sha256"],
        }
        for source in provenance
    ]


def build_report(
    paths,
) -> dict:
    paths = [
        Path(path)
        for path in paths
    ]

    if not paths:
        raise ValueError(
            "At least one capture path is required."
        )

    provenance = []
    analyses = []
    capture_ids = []

    for path in paths:
        capture, source = (
            load_verified_capture(
                path
            )
        )

        capture_id = (
            source["capture_id"]
        )

        provenance.append(
            source
        )
        capture_ids.append(
            capture_id
        )

        analysis = (
            analyze_capture_depth_panels(
                capture,
                capture_id=capture_id,
            )
        )

        if analysis[
            "source_evidence_reasons"
        ]:
            raise ValueError(
                "Insufficient Kuru source evidence "
                f"for {capture_id}: "
                f"{analysis['source_evidence_reasons']}"
            )

        analyses.append(
            analysis
        )

    if (
        len(set(capture_ids))
        != len(capture_ids)
    ):
        raise ValueError(
            "Capture identifiers must be unique."
        )

    result = aggregate_depth_panels(
        analyses
    )

    fingerprint_input = (
        _fingerprint_input(
            provenance
        )
    )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "dataset_fingerprint":
            _canonical_hash(
                fingerprint_input
            ),
        "source_captures":
            provenance,
        "methodology": {
            "market":
                EXPECTED_KURU_MARKET,
            "states":
                list(STATE_ORDER),
            "sides":
                list(SIDES),
            "depth_bands_bps": [
                str(value)
                for value
                in DEPTH_BANDS_BPS
            ],
            "target_base_quantities": [
                str(value)
                for value
                in TARGET_BASE_QUANTITIES
            ],
            "coinbase_reference_age_thresholds_applied":
                False,
        },
        "result":
            result,
        "claim_boundaries": list(
            REPORT_CLAIM_BOUNDARIES
        ),
    }


def render_report(
    report: dict,
) -> str:
    return (
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def write_report(
    report: dict,
    path: Path,
) -> None:
    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        render_report(
            report
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a provenance-bound Phase 1 "
            "state-conditioned Kuru depth and "
            "simulated-execution report."
        )
    )

    parser.add_argument(
        "captures",
        nargs="+",
        type=Path,
        help=(
            "Dual-WebSocket capture JSON files "
            "with matching SHA256 sidecars."
        ),
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help=(
            "Destination JSON report path."
        ),
    )

    args = parser.parse_args()

    report = build_report(
        args.captures
    )

    write_report(
        report,
        args.output,
    )

    print(
        "dataset_fingerprint:",
        report[
            "dataset_fingerprint"
        ],
    )
    print(
        "source_capture_count:",
        len(
            report[
                "source_captures"
            ]
        ),
    )
    print(
        "eligible_panel_count:",
        report["result"][
            "eligible_panel_count"
        ],
    )
    print(
        "json:",
        args.output,
    )


if __name__ == "__main__":
    main()
