from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import time
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from finality_intelligence.dual_ws import (
    write_dual_capture,
)
from scripts.capture_dual_ws import (
    collect_dual,
)


SERIES_SCHEMA_VERSION = (
    "phase3.confirmatory_capture_series.v1"
)

CAPTURE_SCHEMA_VERSION = (
    "phase0.dual_ws_capture.v1"
)

CONTRACT_PATH = Path(
    "research/phase3/"
    "MARKET_INSTABILITY_CONTRACT.md"
)

EXPECTED_CONTRACT_SHA256 = (
    "1e3857d3d872d47a9b6e8056cec3cf62"
    "15eb1b2ad65c79eccce98ef492813419"
)

PREREGISTRATION_COMMIT = (
    "a834e149e309fcae0e90ce3b213d5318"
    "aabf5e7c"
)

EXPECTED_KURU_STREAM = (
    "mon_usdc@monadDepth"
)

EXPECTED_KURU_MARKET = "MON_USDC"
EXPECTED_COINBASE_MARKET = "MON-USD"
EXPECTED_COINBASE_CHANNEL = "level2"


@dataclass(frozen=True)
class CollectionPolicy:
    duration_seconds: int
    timeout_seconds: int
    interval_seconds: int
    target_qualifying_captures: int


FROZEN_POLICY = CollectionPolicy(
    duration_seconds=120,
    timeout_seconds=20,
    interval_seconds=900,
    target_qualifying_captures=10,
)


def utc_now() -> datetime:
    return datetime.now(
        timezone.utc
    )


def utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError(
            "UTC datetime must be timezone-aware."
        )

    return (
        value.astimezone(
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(
            "UTC timestamp must be a string."
        )

    parsed = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )

    if parsed.tzinfo is None:
        raise ValueError(
            "UTC timestamp must be timezone-aware."
        )

    return parsed.astimezone(
        timezone.utc
    )


def timestamp_slug(
    value: datetime,
) -> str:
    return value.astimezone(
        timezone.utc
    ).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )


def sha256_file(
    path: Path,
) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def canonical_json_bytes(
    value: dict,
) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode(
        "utf-8"
    )


def write_json_with_sha256(
    value: dict,
    path: Path,
) -> tuple[Path, Path]:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    encoded = canonical_json_bytes(
        value
    )

    path.write_bytes(
        encoded
    )

    digest = hashlib.sha256(
        encoded
    ).hexdigest()

    hash_path = path.with_suffix(
        ".sha256"
    )

    hash_path.write_text(
        f"{digest}  {path.name}\n",
        encoding="utf-8",
    )

    return path, hash_path


def verify_sidecar(
    raw_path: Path,
    hash_path: Path,
) -> bool:
    if (
        not raw_path.is_file()
        or not hash_path.is_file()
    ):
        return False

    parts = (
        hash_path.read_text(
            encoding="utf-8"
        )
        .strip()
        .split(
            maxsplit=1
        )
    )

    if len(parts) != 2:
        return False

    expected_digest = parts[0]
    expected_name = parts[1].strip()

    return (
        expected_digest
        == sha256_file(
            raw_path
        )
        and expected_name
        == raw_path.name
    )


def dataset_fingerprint(
    hashes: list[str],
) -> str:
    payload = "".join(
        f"{digest}\n"
        for digest in hashes
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        payload
    ).hexdigest()


def technical_acceptance_failures(
    capture: dict,
    *,
    raw_path: Path,
    hash_path: Path,
    policy: CollectionPolicy,
) -> list[str]:
    failures: list[str] = []

    if (
        capture.get(
            "schema_version"
        )
        != CAPTURE_SCHEMA_VERSION
    ):
        failures.append(
            "CAPTURE_SCHEMA_MISMATCH"
        )

    if (
        capture.get(
            "requested_duration_seconds"
        )
        != policy.duration_seconds
    ):
        failures.append(
            "DURATION_MISMATCH"
        )

    if not isinstance(
        capture.get(
            "session_started_utc"
        ),
        str,
    ):
        failures.append(
            "SESSION_START_MISSING"
        )

    if not isinstance(
        capture.get(
            "session_completed_utc"
        ),
        str,
    ):
        failures.append(
            "SESSION_COMPLETION_MISSING"
        )

    sources = capture.get(
        "sources"
    )

    if not isinstance(
        sources,
        dict,
    ):
        failures.append(
            "SOURCES_MISSING"
        )
        sources = {}

    kuru = sources.get(
        "kuru",
        {}
    )

    coinbase = sources.get(
        "coinbase",
        {}
    )

    if (
        kuru.get(
            "stream"
        )
        != EXPECTED_KURU_STREAM
    ):
        failures.append(
            "KURU_STREAM_MISMATCH"
        )

    if (
        kuru.get(
            "market"
        )
        != EXPECTED_KURU_MARKET
    ):
        failures.append(
            "KURU_MARKET_MISMATCH"
        )

    if (
        coinbase.get(
            "market"
        )
        != EXPECTED_COINBASE_MARKET
    ):
        failures.append(
            "COINBASE_MARKET_MISMATCH"
        )

    if (
        coinbase.get(
            "channel"
        )
        != EXPECTED_COINBASE_CHANNEL
    ):
        failures.append(
            "COINBASE_CHANNEL_MISMATCH"
        )

    gate = capture.get(
        "gate"
    )

    if not isinstance(
        gate,
        dict,
    ):
        failures.append(
            "GATE_MISSING"
        )
        gate = {}

    expected_gate_components = (
        "kuru",
        "coinbase",
        "temporal_overlap",
        "overall",
    )

    for component in (
        expected_gate_components
    ):
        if (
            gate.get(
                component
            )
            != "PASS"
        ):
            failures.append(
                (
                    "GATE_NOT_PASS:"
                    f"{component}"
                )
            )

    if not verify_sidecar(
        raw_path,
        hash_path,
    ):
        failures.append(
            "CAPTURE_SHA256_VERIFICATION_FAILED"
        )

    return failures


def git_output(
    repo_root: Path,
    *args: str,
) -> str:
    result = subprocess.run(
        [
            "git",
            *args,
        ],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return result.stdout.strip()


def ensure_clean_collection_runtime(
    repo_root: Path,
) -> None:
    status = git_output(
        repo_root,
        "status",
        "--porcelain",
        "--untracked-files=all",
    )

    if status:
        raise RuntimeError(
            "Phase 3 collection requires a clean "
            "Git worktree so acquisition code is "
            "bound to the recorded commit."
        )


def verify_preregistration(
    repo_root: Path,
) -> str:
    contract = (
        repo_root
        / CONTRACT_PATH
    )

    if (
        sha256_file(
            contract
        )
        != EXPECTED_CONTRACT_SHA256
    ):
        raise RuntimeError(
            "Current Phase 3 contract SHA256 "
            "does not match preregistration."
        )

    committed_text = git_output(
        repo_root,
        "show",
        (
            f"{PREREGISTRATION_COMMIT}:"
            f"{CONTRACT_PATH.as_posix()}"
        ),
    )

    committed_digest = hashlib.sha256(
        (
            committed_text
            + "\n"
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    if (
        committed_digest
        != EXPECTED_CONTRACT_SHA256
    ):
        raise RuntimeError(
            "Preregistered contract content "
            "does not match expected SHA256."
        )

    subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            PREREGISTRATION_COMMIT,
            "HEAD",
        ],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return git_output(
        repo_root,
        "rev-parse",
        "HEAD",
    )


def new_manifest(
    *,
    series_started_utc: str,
    collection_code_commit: str,
    policy: CollectionPolicy,
) -> dict:
    return {
        "schema_version":
            SERIES_SCHEMA_VERSION,
        "methodology": {
            "contract_path":
                CONTRACT_PATH.as_posix(),
            "contract_sha256":
                EXPECTED_CONTRACT_SHA256,
            "preregistration_commit":
                PREREGISTRATION_COMMIT,
        },
        "collection_code_commit":
            collection_code_commit,
        "policy":
            asdict(
                policy
            ),
        "series_started_utc":
            series_started_utc,
        "series_completed_utc":
            None,
        "attempt_count":
            0,
        "qualifying_capture_count":
            0,
        "non_qualifying_attempt_count":
            0,
        "attempts":
            [],
        "qualifying_capture_files":
            [],
        "qualifying_capture_sha256":
            [],
        "dataset_fingerprint":
            None,
        "dataset_fingerprint_definition": (
            "sha256 of ordered qualifying "
            "capture sha256 values, one value "
            "per line with a trailing newline"
        ),
    }


def refresh_manifest(
    manifest: dict,
    *,
    policy: CollectionPolicy,
) -> None:
    attempts = manifest[
        "attempts"
    ]

    qualifying = [
        attempt
        for attempt in attempts
        if attempt[
            "qualifies"
        ]
    ]

    manifest[
        "attempt_count"
    ] = len(
        attempts
    )

    manifest[
        "qualifying_capture_count"
    ] = len(
        qualifying
    )

    manifest[
        "non_qualifying_attempt_count"
    ] = (
        len(
            attempts
        )
        - len(
            qualifying
        )
    )

    manifest[
        "qualifying_capture_files"
    ] = [
        attempt[
            "raw_capture_file"
        ]
        for attempt in qualifying
    ]

    hashes = [
        attempt[
            "capture_sha256"
        ]
        for attempt in qualifying
    ]

    manifest[
        "qualifying_capture_sha256"
    ] = hashes

    if (
        len(
            qualifying
        )
        == policy.target_qualifying_captures
    ):
        manifest[
            "dataset_fingerprint"
        ] = dataset_fingerprint(
            hashes
        )
    else:
        manifest[
            "dataset_fingerprint"
        ] = None


def validate_manifest(
    manifest: dict,
    *,
    policy: CollectionPolicy,
) -> None:
    if (
        manifest.get(
            "schema_version"
        )
        != SERIES_SCHEMA_VERSION
    ):
        raise RuntimeError(
            "Phase 3 series schema mismatch."
        )

    methodology = manifest.get(
        "methodology",
        {}
    )

    if (
        methodology.get(
            "contract_sha256"
        )
        != EXPECTED_CONTRACT_SHA256
    ):
        raise RuntimeError(
            "Manifest contract SHA mismatch."
        )

    if (
        methodology.get(
            "preregistration_commit"
        )
        != PREREGISTRATION_COMMIT
    ):
        raise RuntimeError(
            "Manifest preregistration "
            "commit mismatch."
        )

    if (
        manifest.get(
            "policy"
        )
        != asdict(
            policy
        )
    ):
        raise RuntimeError(
            "Manifest collection policy mismatch."
        )

    attempts = manifest.get(
        "attempts"
    )

    if not isinstance(
        attempts,
        list,
    ):
        raise RuntimeError(
            "Manifest attempts missing."
        )

    for expected_index, attempt in enumerate(
        attempts,
        start=1,
    ):
        if (
            attempt.get(
                "attempt_index"
            )
            != expected_index
        ):
            raise RuntimeError(
                "Manifest attempt ordering invalid."
            )

    refreshed = json.loads(
        json.dumps(
            manifest
        )
    )

    refresh_manifest(
        refreshed,
        policy=policy,
    )

    for key in (
        "attempt_count",
        "qualifying_capture_count",
        "non_qualifying_attempt_count",
        "qualifying_capture_files",
        "qualifying_capture_sha256",
        "dataset_fingerprint",
    ):
        if (
            refreshed[
                key
            ]
            != manifest.get(
                key
            )
        ):
            raise RuntimeError(
                f"Manifest derived field mismatch: {key}"
            )


def write_manifest(
    manifest: dict,
    path: Path,
) -> tuple[Path, Path]:
    validate_manifest(
        manifest,
        policy=CollectionPolicy(
            **manifest[
                "policy"
            ]
        ),
    )

    return write_json_with_sha256(
        manifest,
        path,
    )


def load_manifest(
    path: Path,
    *,
    policy: CollectionPolicy,
) -> dict:
    hash_path = path.with_suffix(
        ".sha256"
    )

    if not verify_sidecar(
        path,
        hash_path,
    ):
        raise RuntimeError(
            "Manifest SHA256 verification failed."
        )

    manifest = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    validate_manifest(
        manifest,
        policy=policy,
    )

    return manifest


def technical_status_line(
    attempt: dict,
    *,
    qualifying_count: int,
    target_count: int,
) -> str:
    gate = attempt[
        "gate"
    ]

    return (
        f"attempt={attempt['attempt_index']} "
        f"overall={gate['overall']} "
        f"kuru={gate['kuru']} "
        f"coinbase={gate['coinbase']} "
        f"overlap={gate['temporal_overlap']} "
        f"qualifies={str(attempt['qualifies']).lower()} "
        f"qualifying={qualifying_count}/{target_count} "
        f"capture={attempt['raw_capture_file']} "
        f"sha256={attempt['capture_sha256']}"
    )


def run_series(
    *,
    output_dir: Path,
    manifest_path: Path,
    capture_once: Callable[
        [int, int],
        dict,
    ],
    collection_code_commit: str,
    policy: CollectionPolicy = FROZEN_POLICY,
    now_fn: Callable[
        [],
        datetime,
    ] = utc_now,
    sleep_fn: Callable[
        [float],
        None,
    ] = time.sleep,
    status_fn: Callable[
        [str],
        None,
    ] = print,
    attempt_limit: int | None = None,
) -> dict:
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if manifest_path.exists():
        manifest = load_manifest(
            manifest_path,
            policy=policy,
        )

        if (
            manifest[
                "collection_code_commit"
            ]
            != collection_code_commit
        ):
            raise RuntimeError(
                "Resume requires the same "
                "collection-code commit."
            )
    else:
        manifest = new_manifest(
            series_started_utc=utc_text(
                now_fn()
            ),
            collection_code_commit=(
                collection_code_commit
            ),
            policy=policy,
        )

        write_manifest(
            manifest,
            manifest_path,
        )

    if (
        manifest[
            "qualifying_capture_count"
        ]
        >= policy.target_qualifying_captures
    ):
        return manifest

    attempts_this_run = 0

    while (
        manifest[
            "qualifying_capture_count"
        ]
        < policy.target_qualifying_captures
    ):
        if (
            attempt_limit is not None
            and attempts_this_run
            >= attempt_limit
        ):
            break

        if manifest[
            "attempts"
        ]:
            previous_start = parse_utc(
                manifest[
                    "attempts"
                ][-1][
                    "attempt_started_utc"
                ]
            )

            target_start = (
                previous_start
                + timedelta(
                    seconds=(
                        policy.interval_seconds
                    )
                )
            )

            now = now_fn()

            remaining = (
                target_start
                - now
            ).total_seconds()

            if remaining > 0:
                sleep_fn(
                    remaining
                )

        attempt_started = now_fn()

        attempt_index = (
            len(
                manifest[
                    "attempts"
                ]
            )
            + 1
        )

        raw_path = (
            output_dir
            / (
                "dual_ws_"
                f"{timestamp_slug(attempt_started)}"
                ".json"
            )
        )

        capture = capture_once(
            policy.duration_seconds,
            policy.timeout_seconds,
        )

        raw_path, hash_path = (
            write_dual_capture(
                capture,
                raw_path,
            )
        )

        digest = sha256_file(
            raw_path
        )

        failures = (
            technical_acceptance_failures(
                capture,
                raw_path=raw_path,
                hash_path=hash_path,
                policy=policy,
            )
        )

        gate = capture.get(
            "gate",
            {}
        )

        attempt = {
            "attempt_index":
                attempt_index,
            "attempt_started_utc":
                utc_text(
                    attempt_started
                ),
            "attempt_completed_utc":
                utc_text(
                    now_fn()
                ),
            "capture_session_started_utc":
                capture.get(
                    "session_started_utc"
                ),
            "capture_session_completed_utc":
                capture.get(
                    "session_completed_utc"
                ),
            "raw_capture_file":
                raw_path.name,
            "sha256_file":
                hash_path.name,
            "capture_sha256":
                digest,
            "gate": {
                "kuru":
                    gate.get(
                        "kuru"
                    ),
                "coinbase":
                    gate.get(
                        "coinbase"
                    ),
                "temporal_overlap":
                    gate.get(
                        "temporal_overlap"
                    ),
                "overall":
                    gate.get(
                        "overall"
                    ),
            },
            "technical_acceptance_failures":
                failures,
            "qualifies":
                not failures,
        }

        manifest[
            "attempts"
        ].append(
            attempt
        )

        refresh_manifest(
            manifest,
            policy=policy,
        )

        attempts_this_run += 1

        if (
            manifest[
                "qualifying_capture_count"
            ]
            == policy.target_qualifying_captures
        ):
            manifest[
                "series_completed_utc"
            ] = utc_text(
                now_fn()
            )

        write_manifest(
            manifest,
            manifest_path,
        )

        status_fn(
            technical_status_line(
                attempt,
                qualifying_count=(
                    manifest[
                        "qualifying_capture_count"
                    ]
                ),
                target_count=(
                    policy.target_qualifying_captures
                ),
            )
        )

    return manifest


def collect_dual_silently(
    *,
    duration_seconds: int,
    timeout_seconds: int,
) -> dict:
    with open(
        os.devnull,
        "w",
        encoding="utf-8",
    ) as sink:
        with (
            redirect_stdout(sink),
            redirect_stderr(sink),
        ):
            return asyncio.run(
                collect_dual(
                    duration_seconds=(
                        duration_seconds
                    ),
                    timeout_seconds=(
                        timeout_seconds
                    ),
                )
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the preregistered Phase 3 "
            "confirmatory dual-WebSocket "
            "capture series."
        )
    )

    parser.add_argument(
        "--output-dir",
        default=(
            "data/raw/"
            "phase3_confirmatory"
        ),
    )

    parser.add_argument(
        "--resume-manifest",
        default=None,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    repo_root = Path(
        __file__
    ).resolve().parents[1]

    ensure_clean_collection_runtime(
        repo_root
    )

    collection_code_commit = (
        verify_preregistration(
            repo_root
        )
    )

    if args.resume_manifest:
        manifest_path = Path(
            args.resume_manifest
        )

        output_dir = (
            manifest_path.parent
        )
    else:
        output_dir = Path(
            args.output_dir
        )

        started = utc_now()

        manifest_path = (
            output_dir
            / (
                "phase3_confirmatory_"
                f"{timestamp_slug(started)}"
                ".manifest.json"
            )
        )

    print(
        "phase3_collection_schema:",
        SERIES_SCHEMA_VERSION,
    )

    print(
        "preregistration_commit:",
        PREREGISTRATION_COMMIT,
    )

    print(
        "contract_sha256:",
        EXPECTED_CONTRACT_SHA256,
    )

    print(
        "collection_code_commit:",
        collection_code_commit,
    )

    print(
        "duration_seconds:",
        FROZEN_POLICY.duration_seconds,
    )

    print(
        "timeout_seconds:",
        FROZEN_POLICY.timeout_seconds,
    )

    print(
        "start_interval_seconds:",
        FROZEN_POLICY.interval_seconds,
    )

    print(
        "target_qualifying_captures:",
        (
            FROZEN_POLICY
            .target_qualifying_captures
        ),
    )

    print(
        "manifest:",
        manifest_path,
    )

    def capture_once(
        duration_seconds: int,
        timeout_seconds: int,
    ) -> dict:
        return collect_dual_silently(
            duration_seconds=(
                duration_seconds
            ),
            timeout_seconds=(
                timeout_seconds
            ),
        )

    manifest = run_series(
        output_dir=output_dir,
        manifest_path=manifest_path,
        capture_once=capture_once,
        collection_code_commit=(
            collection_code_commit
        ),
    )

    print(
        "qualifying_capture_count:",
        manifest[
            "qualifying_capture_count"
        ],
    )

    print(
        "attempt_count:",
        manifest[
            "attempt_count"
        ],
    )

    print(
        "dataset_fingerprint:",
        manifest[
            "dataset_fingerprint"
        ],
    )

    print(
        "manifest_sha256_file:",
        manifest_path.with_suffix(
            ".sha256"
        ),
    )

    return (
        0
        if manifest[
            "qualifying_capture_count"
        ]
        == (
            FROZEN_POLICY
            .target_qualifying_captures
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
