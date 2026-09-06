from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from finality_intelligence.staleness import (
    CORE_THRESHOLDS_MS,
    aggregate_staleness,
    analyze_capture_staleness,
)


SCHEMA_VERSION = "phase1.staleness_sensitivity.v1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_hash(value) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return _sha256(encoded)


def load_verified_capture(path: Path) -> tuple[dict, dict]:
    path = Path(path)
    sidecar = path.with_suffix(".sha256")

    if not path.is_file():
        raise ValueError(f"Capture file not found: {path}")

    if not sidecar.is_file():
        raise ValueError(f"SHA256 sidecar not found: {sidecar}")

    raw = path.read_bytes()
    actual = _sha256(raw)
    expected = sidecar.read_text(encoding="utf-8").strip().split()[0]

    if actual != expected:
        raise ValueError(f"SHA256 mismatch: {path}")

    capture = json.loads(raw)

    if capture.get("gate", {}).get("overall") != "PASS":
        raise ValueError(f"Source capture gate not PASS: {path}")

    provenance = {
        "capture_id": path.name,
        "source_path": str(path),
        "sha256": actual,
    }

    return capture, provenance


def build_report(paths) -> dict:
    paths = [Path(path) for path in paths]

    if not paths:
        raise ValueError("At least one capture path is required.")

    analyses = []
    provenance = []

    for path in paths:
        capture, source = load_verified_capture(path)

        analysis = analyze_capture_staleness(
            capture,
            capture_id=source["capture_id"],
        )

        if analysis["source_evidence_reasons"]:
            raise ValueError(
                f"Insufficient source evidence for {path}: "
                f"{analysis['source_evidence_reasons']}"
            )

        analyses.append(analysis)
        provenance.append(source)

    aggregate = aggregate_staleness(analyses)

    fingerprint_input = [
        {
            "capture_id": item["capture_id"],
            "sha256": item["sha256"],
        }
        for item in provenance
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "core_thresholds_ms": [
            str(value) for value in CORE_THRESHOLDS_MS
        ],
        "dataset_fingerprint": _canonical_hash(fingerprint_input),
        "source_captures": provenance,
        "result": aggregate,
        "claim_boundaries": [
            "Monotonic receive timestamps are compared only within each capture process.",
            "Pooled values combine derived within-capture durations and are descriptive only.",
            "The 250 ms, 500 ms, and 1000 ms bands are analysis sensitivities, not venue or protocol constants.",
            "Reference age is not exchange-clock latency, network latency, execution latency, consensus latency, or protocol-finality latency.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze provenance-verified Phase 1 reference staleness."
    )
    parser.add_argument(
        "captures",
        nargs="+",
        type=Path,
        help="Dual-WebSocket capture JSON files with matching .sha256 sidecars.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path.",
    )
    args = parser.parse_args()

    report = build_report(args.captures)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
