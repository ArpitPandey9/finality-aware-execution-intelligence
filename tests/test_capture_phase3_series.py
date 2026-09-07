from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import capture_phase3_series as phase3
from finality_intelligence.dual_ws import (
    write_dual_capture,
)


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(
            2026,
            9,
            7,
            12,
            0,
            0,
            tzinfo=timezone.utc,
        )
        self.sleeps: list[float] = []

    def now(self) -> datetime:
        return self.current

    def advance(
        self,
        seconds: float,
    ) -> None:
        self.current += timedelta(
            seconds=seconds
        )

    def sleep(
        self,
        seconds: float,
    ) -> None:
        self.sleeps.append(
            seconds
        )
        self.advance(
            seconds
        )


def synthetic_capture(
    *,
    overall: str = "PASS",
    requested_duration_seconds: int = 120,
) -> dict:
    source_status = (
        "PASS"
        if overall == "PASS"
        else "REVIEW"
    )

    return {
        "schema_version":
            phase3.CAPTURE_SCHEMA_VERSION,
        "requested_duration_seconds":
            requested_duration_seconds,
        "session_started_utc":
            "2026-09-07T12:00:00Z",
        "session_completed_utc":
            "2026-09-07T12:02:00Z",
        "sources": {
            "kuru": {
                "stream":
                    phase3.EXPECTED_KURU_STREAM,
                "market":
                    phase3.EXPECTED_KURU_MARKET,
                "records": [],
            },
            "coinbase": {
                "channel":
                    phase3.EXPECTED_COINBASE_CHANNEL,
                "market":
                    phase3.EXPECTED_COINBASE_MARKET,
                "records": [],
            },
        },
        "temporal_overlap": {},
        "gate": {
            "kuru": "PASS",
            "coinbase": source_status,
            "temporal_overlap": "PASS",
            "overall": overall,
        },
        "claim_boundary": {},
    }


class TestPhase3ConfirmatoryCaptureSeries(
    unittest.TestCase
):
    def test_frozen_policy(self) -> None:
        self.assertEqual(
            phase3.FROZEN_POLICY.duration_seconds,
            120,
        )
        self.assertEqual(
            phase3.FROZEN_POLICY.timeout_seconds,
            20,
        )
        self.assertEqual(
            phase3.FROZEN_POLICY.interval_seconds,
            900,
        )
        self.assertEqual(
            (
                phase3.FROZEN_POLICY
                .target_qualifying_captures
            ),
            10,
        )

    def test_pass_capture_qualifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = (
                Path(tmp)
                / "capture.json"
            )

            capture = synthetic_capture()

            raw, sidecar = write_dual_capture(
                capture,
                raw,
            )

            failures = (
                phase3
                .technical_acceptance_failures(
                    capture,
                    raw_path=raw,
                    hash_path=sidecar,
                    policy=phase3.FROZEN_POLICY,
                )
            )

            self.assertEqual(
                failures,
                [],
            )

    def test_review_capture_does_not_qualify(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = (
                Path(tmp)
                / "capture.json"
            )

            capture = synthetic_capture(
                overall="REVIEW"
            )

            raw, sidecar = write_dual_capture(
                capture,
                raw,
            )

            failures = (
                phase3
                .technical_acceptance_failures(
                    capture,
                    raw_path=raw,
                    hash_path=sidecar,
                    policy=phase3.FROZEN_POLICY,
                )
            )

            self.assertIn(
                "GATE_NOT_PASS:coinbase",
                failures,
            )
            self.assertIn(
                "GATE_NOT_PASS:overall",
                failures,
            )

    def test_tampered_capture_fails_sha(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = (
                Path(tmp)
                / "capture.json"
            )

            capture = synthetic_capture()

            raw, sidecar = write_dual_capture(
                capture,
                raw,
            )

            raw.write_bytes(
                raw.read_bytes()
                + b" "
            )

            failures = (
                phase3
                .technical_acceptance_failures(
                    capture,
                    raw_path=raw,
                    hash_path=sidecar,
                    policy=phase3.FROZEN_POLICY,
                )
            )

            self.assertIn(
                (
                    "CAPTURE_SHA256_"
                    "VERIFICATION_FAILED"
                ),
                failures,
            )

    def test_first_ten_qualifying_rule_and_cadence(
        self,
    ) -> None:
        clock = FakeClock()

        statuses = [
            "PASS",
            "REVIEW",
            "PASS",
            "PASS",
            "REVIEW",
            "PASS",
            "PASS",
            "PASS",
            "PASS",
            "PASS",
            "PASS",
            "PASS",
        ]

        calls = 0
        technical_lines: list[str] = []

        def capture_once(
            duration_seconds: int,
            timeout_seconds: int,
        ) -> dict:
            nonlocal calls

            self.assertEqual(
                duration_seconds,
                120,
            )
            self.assertEqual(
                timeout_seconds,
                20,
            )

            status = statuses[calls]
            calls += 1

            clock.advance(
                120
            )

            return synthetic_capture(
                overall=status
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            manifest = phase3.run_series(
                output_dir=root,
                manifest_path=(
                    root
                    / "series.manifest.json"
                ),
                capture_once=capture_once,
                collection_code_commit=(
                    "collection-code-commit"
                ),
                now_fn=clock.now,
                sleep_fn=clock.sleep,
                status_fn=technical_lines.append,
            )

            self.assertEqual(
                manifest[
                    "attempt_count"
                ],
                12,
            )

            self.assertEqual(
                manifest[
                    "qualifying_capture_count"
                ],
                10,
            )

            self.assertEqual(
                manifest[
                    "non_qualifying_attempt_count"
                ],
                2,
            )

            self.assertEqual(
                len(
                    manifest[
                        "qualifying_capture_files"
                    ]
                ),
                10,
            )

            self.assertIsNotNone(
                manifest[
                    "dataset_fingerprint"
                ]
            )

            self.assertEqual(
                manifest[
                    "dataset_fingerprint"
                ],
                phase3.dataset_fingerprint(
                    manifest[
                        "qualifying_capture_sha256"
                    ]
                ),
            )

            self.assertEqual(
                len(clock.sleeps),
                11,
            )

            self.assertTrue(
                all(
                    sleep == 780
                    for sleep in clock.sleeps
                )
            )

            starts = [
                phase3.parse_utc(
                    attempt[
                        "attempt_started_utc"
                    ]
                )
                for attempt
                in manifest[
                    "attempts"
                ]
            ]

            deltas = [
                (
                    later
                    - earlier
                ).total_seconds()
                for earlier, later
                in zip(
                    starts,
                    starts[1:],
                )
            ]

            self.assertEqual(
                deltas,
                [900.0] * 11,
            )

            self.assertEqual(
                len(technical_lines),
                12,
            )

    def test_resume_preserves_attempt_history(
        self,
    ) -> None:
        clock = FakeClock()

        first_statuses = [
            "PASS",
            "REVIEW",
            "PASS",
        ]

        first_calls = 0

        def first_capture(
            duration_seconds: int,
            timeout_seconds: int,
        ) -> dict:
            nonlocal first_calls

            status = (
                first_statuses[
                    first_calls
                ]
            )

            first_calls += 1
            clock.advance(120)

            return synthetic_capture(
                overall=status
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = (
                root
                / "series.manifest.json"
            )

            first = phase3.run_series(
                output_dir=root,
                manifest_path=manifest_path,
                capture_once=first_capture,
                collection_code_commit=(
                    "same-code-commit"
                ),
                now_fn=clock.now,
                sleep_fn=clock.sleep,
                status_fn=lambda _: None,
                attempt_limit=3,
            )

            self.assertEqual(
                first[
                    "attempt_count"
                ],
                3,
            )
            self.assertEqual(
                first[
                    "qualifying_capture_count"
                ],
                2,
            )

            def resumed_capture(
                duration_seconds: int,
                timeout_seconds: int,
            ) -> dict:
                clock.advance(120)
                return synthetic_capture()

            resumed = phase3.run_series(
                output_dir=root,
                manifest_path=manifest_path,
                capture_once=resumed_capture,
                collection_code_commit=(
                    "same-code-commit"
                ),
                now_fn=clock.now,
                sleep_fn=clock.sleep,
                status_fn=lambda _: None,
            )

            self.assertEqual(
                resumed[
                    "qualifying_capture_count"
                ],
                10,
            )

            self.assertEqual(
                resumed[
                    "attempt_count"
                ],
                11,
            )

            self.assertEqual(
                [
                    item[
                        "attempt_index"
                    ]
                    for item
                    in resumed[
                        "attempts"
                    ]
                ],
                list(
                    range(
                        1,
                        12,
                    )
                ),
            )

    def test_resume_rejects_different_code_commit(
        self,
    ) -> None:
        clock = FakeClock()

        def capture_once(
            duration_seconds: int,
            timeout_seconds: int,
        ) -> dict:
            clock.advance(120)
            return synthetic_capture()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = (
                root
                / "series.manifest.json"
            )

            phase3.run_series(
                output_dir=root,
                manifest_path=manifest_path,
                capture_once=capture_once,
                collection_code_commit="commit-a",
                now_fn=clock.now,
                sleep_fn=clock.sleep,
                status_fn=lambda _: None,
                attempt_limit=1,
            )

            with self.assertRaises(
                RuntimeError
            ):
                phase3.run_series(
                    output_dir=root,
                    manifest_path=manifest_path,
                    capture_once=capture_once,
                    collection_code_commit="commit-b",
                    now_fn=clock.now,
                    sleep_fn=clock.sleep,
                    status_fn=lambda _: None,
                    attempt_limit=1,
                )

    def test_manifest_serialization_is_deterministic(
        self,
    ) -> None:
        manifest = phase3.new_manifest(
            series_started_utc=(
                "2026-09-07T12:00:00Z"
            ),
            collection_code_commit=(
                "collection-code-commit"
            ),
            policy=phase3.FROZEN_POLICY,
        )

        first = phase3.canonical_json_bytes(
            manifest
        )

        second = phase3.canonical_json_bytes(
            manifest
        )

        self.assertEqual(
            first,
            second,
        )

    def test_real_collector_output_is_suppressed(
        self,
    ) -> None:
        async def fake_collect_dual(
            *,
            duration_seconds: int,
            timeout_seconds: int,
        ) -> dict:
            print(
                "coinbase top=123.45"
            )
            print(
                "economic stderr marker",
                file=sys.stderr,
            )

            return {
                "ok": True,
            }

        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch.object(
            phase3,
            "collect_dual",
            fake_collect_dual,
        ):
            with (
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                result = (
                    phase3
                    .collect_dual_silently(
                        duration_seconds=120,
                        timeout_seconds=20,
                    )
                )

        self.assertEqual(
            result,
            {"ok": True},
        )

        self.assertEqual(
            stdout.getvalue(),
            "",
        )

        self.assertEqual(
            stderr.getvalue(),
            "",
        )

    def test_operator_status_contains_only_technical_fields(
        self,
    ) -> None:
        attempt = {
            "attempt_index": 1,
            "raw_capture_file":
                "dual_ws_example.json",
            "capture_sha256":
                "abc123",
            "qualifies":
                True,
            "gate": {
                "overall": "PASS",
                "kuru": "PASS",
                "coinbase": "PASS",
                "temporal_overlap": "PASS",
            },
        }

        line = phase3.technical_status_line(
            attempt,
            qualifying_count=1,
            target_count=10,
        )

        for forbidden in (
            "price",
            "best_bid",
            "best_offer",
            "midpoint",
            "spread",
            "return",
            "volatility",
            "correlation",
            "slippage",
            "alpha",
        ):
            self.assertNotIn(
                forbidden,
                line.lower(),
            )

    def test_dirty_runtime_is_rejected(
        self,
    ) -> None:
        with patch.object(
            phase3,
            "git_output",
            return_value=(
                "?? uncommitted.py"
            ),
        ):
            with self.assertRaises(
                RuntimeError
            ):
                (
                    phase3
                    .ensure_clean_collection_runtime(
                        Path(".")
                    )
                )

        with patch.object(
            phase3,
            "git_output",
            return_value="",
        ):
            (
                phase3
                .ensure_clean_collection_runtime(
                    Path(".")
                )
            )


if __name__ == "__main__":
    unittest.main()
