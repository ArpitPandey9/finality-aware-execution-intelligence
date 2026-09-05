from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts import capture_cycle


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run repeated cross-venue capture cycles."
    )

    parser.add_argument(
        "--cycles",
        type=int,
        default=3,
        help="Number of capture cycles to run.",
    )

    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=5.0,
        help="Target delay between cycle starts.",
    )

    args = parser.parse_args()

    if args.cycles <= 0:
        parser.error("--cycles must be greater than zero")

    if args.interval_seconds < 0:
        parser.error("--interval-seconds must be non-negative")

    return args


def run_series(
    *,
    cycles: int,
    interval_seconds: float,
) -> dict:
    if cycles <= 0:
        raise ValueError("cycles must be greater than zero.")

    if interval_seconds < 0:
        raise ValueError(
            "interval_seconds must be non-negative."
        )

    series_started = utc_now()
    observations = []

    for index in range(cycles):
        cycle_started_monotonic = time.monotonic()

        capture = capture_cycle.capture_cycle()
        json_path, hash_path = capture_cycle.write_capture(
            capture
        )

        observations.append(
            {
                "index": index + 1,
                "capture_cycle_started_utc": capture[
                    "capture_cycle_started_utc"
                ],
                "capture_cycle_completed_utc": capture[
                    "capture_cycle_completed_utc"
                ],
                "gate": capture["gate"],
                "raw_json": str(json_path),
                "sha256_file": str(hash_path),
            }
        )

        if index < cycles - 1:
            elapsed = (
                time.monotonic()
                - cycle_started_monotonic
            )

            remaining = max(
                0.0,
                interval_seconds - elapsed,
            )

            if remaining > 0:
                time.sleep(remaining)

    series_completed = utc_now()

    passed = sum(
        observation["gate"]["overall"] == "PASS"
        for observation in observations
    )

    reviewed = len(observations) - passed

    return {
        "schema_version": "phase0.capture_series.v1",
        "series_started_utc": series_started,
        "series_completed_utc": series_completed,
        "requested_cycles": cycles,
        "interval_seconds": interval_seconds,
        "completed_cycles": len(observations),
        "pass_cycles": passed,
        "review_cycles": reviewed,
        "observations": observations,
    }


def write_manifest(series: dict) -> tuple[Path, Path]:
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )

    manifest_path = (
        output_dir
        / f"capture_series_{timestamp}.manifest.json"
    )

    hash_path = (
        output_dir
        / f"capture_series_{timestamp}.manifest.sha256"
    )

    encoded = (
        json.dumps(
            series,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    manifest_path.write_bytes(encoded)

    digest = hashlib.sha256(encoded).hexdigest()

    hash_path.write_text(
        f"{digest}  {manifest_path.name}\n",
        encoding="utf-8",
    )

    return manifest_path, hash_path


def print_summary(series: dict) -> None:
    print("series_started:", series["series_started_utc"])
    print(
        "series_completed:",
        series["series_completed_utc"],
    )
    print(
        "completed_cycles:",
        series["completed_cycles"],
    )
    print(
        "pass_cycles:",
        series["pass_cycles"],
    )
    print(
        "review_cycles:",
        series["review_cycles"],
    )

    for observation in series["observations"]:
        print(
            "cycle",
            observation["index"],
            "gate=",
            observation["gate"]["overall"],
            "raw_json=",
            observation["raw_json"],
        )


def main() -> int:
    args = parse_args()

    series = run_series(
        cycles=args.cycles,
        interval_seconds=args.interval_seconds,
    )

    manifest_path, hash_path = write_manifest(series)

    print_summary(series)

    print("manifest:", manifest_path)
    print("manifest_sha256:", hash_path)

    return 0 if series["review_cycles"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
