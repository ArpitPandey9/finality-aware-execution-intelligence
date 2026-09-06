from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts.analyze_staleness import (
    load_verified_capture,
)

from finality_intelligence.alignment import (
    EXPECTED_COINBASE_CHANNEL,
    EXPECTED_COINBASE_MARKET,
    EXPECTED_KURU_MARKET,
)
from finality_intelligence.temporal_aggregation import (
    FROZEN_FRESHNESS_THRESHOLDS_MS,
    aggregate_temporal_outcomes,
)
from finality_intelligence.temporal_outcome import (
    EXTENDED_HORIZON_MS,
    FROZEN_HORIZONS_MS,
    PRIMARY_HORIZONS_MS,
    analyze_temporal_capture,
)


SCHEMA_VERSION = (
    "phase2.temporal_outcome_report.v1"
)


PRIMARY_BASELINE_FRESHNESS_THRESHOLD_MS = (
    "250"
)

EXCLUDED_INITIAL_HORIZON_MS = (
    "30000"
)


REPORT_CLAIM_BOUNDARIES = (
    "The Phase 2 temporal analysis is descriptive market-state "
    "evidence, not prediction, not alpha, and not arbitrage.",
    "Directional concordance is not causal evidence and does not "
    "establish that Kuru leads Coinbase.",
    "Directional-concordance sign counts are not a win rate, hit "
    "rate, execution probability, or trading-performance statistic.",
    "A future Coinbase midpoint change is not realized trading PnL "
    "or a realizable strategy return.",
    "The 250 ms, 500 ms, and 1000 ms baseline freshness populations "
    "are nested sensitivity bands and are not independent samples.",
    "Overlapping future windows are not independent observations.",
    "The deterministic non-overlapping sensitivity reduces horizon "
    "overlap but is not statistically independent.",
    "Simultaneous Kuru state views are not temporal protocol-state "
    "transitions, finality-latency observations, or causal finality "
    "effects.",
)


def _canonical_hash(
    value,
) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


def _fingerprint_input(
    provenance: list[dict],
) -> list[dict]:
    return [
        {
            "capture_id":
                source[
                    "capture_id"
                ],
            "sha256":
                source[
                    "sha256"
                ],
        }
        for source
        in provenance
    ]


def build_report(
    paths,
) -> dict:
    paths = [
        Path(
            path
        )
        for path in paths
    ]

    if not paths:
        raise ValueError(
            "At least one capture path is required."
        )

    provenance = []
    loaded = []
    capture_ids = []

    for path in paths:
        capture, source = (
            load_verified_capture(
                path
            )
        )

        capture_id = source[
            "capture_id"
        ]

        provenance.append(
            source
        )

        loaded.append(
            (
                capture_id,
                capture,
            )
        )

        capture_ids.append(
            capture_id
        )

    if (
        len(
            set(
                capture_ids
            )
        )
        != len(
            capture_ids
        )
    ):
        raise ValueError(
            "Capture identifiers must be unique."
        )

    threshold_results = {}

    for threshold in (
        FROZEN_FRESHNESS_THRESHOLDS_MS
    ):
        horizon_results = {}

        for horizon in (
            FROZEN_HORIZONS_MS
        ):
            analyses = []

            for (
                capture_id,
                capture,
            ) in loaded:
                analysis = (
                    analyze_temporal_capture(
                        capture,
                        capture_id=
                            capture_id,
                        max_age_ms=
                            threshold,
                        horizon_ms=
                            horizon,
                    )
                )

                if analysis[
                    "source_evidence_reasons"
                ]:
                    raise ValueError(
                        "Insufficient source evidence "
                        f"for {capture_id}: "
                        f"{analysis['source_evidence_reasons']}"
                    )

                analyses.append(
                    analysis
                )

            horizon_results[
                str(
                    horizon
                )
            ] = (
                aggregate_temporal_outcomes(
                    analyses
                )
            )

        threshold_results[
            str(
                threshold
            )
        ] = horizon_results

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
            "kuru_market":
                EXPECTED_KURU_MARKET,
            "coinbase_market":
                EXPECTED_COINBASE_MARKET,
            "coinbase_channel":
                EXPECTED_COINBASE_CHANNEL,
            "common_base_asset":
                "MON",
            "kuru_quote_asset":
                "USDC",
            "coinbase_quote_asset":
                "USD",
            "primary_outcome_market":
                "Coinbase MON-USD",
            "unit_of_observation":
                "one Kuru four-state panel",
            "baseline_time_anchor":
                "Kuru received_monotonic_ns",
            "baseline_reference_selection":
                "latest eligible Coinbase target Level2 "
                "state at or before Kuru receive time",
            "future_state_selection":
                "latest eligible Coinbase target Level2 "
                "state at or before t0 plus frozen horizon",
            "future_price_interpolation":
                False,
            "cross_capture_stitching":
                False,
            "capture_end_right_censoring":
                True,
            "future_asof_age_is_diagnostic":
                True,
            "baseline_freshness_thresholds_ms": [
                str(
                    value
                )
                for value
                in FROZEN_FRESHNESS_THRESHOLDS_MS
            ],
            "primary_baseline_freshness_threshold_ms":
                PRIMARY_BASELINE_FRESHNESS_THRESHOLD_MS,
            "future_horizons_ms": [
                str(
                    value
                )
                for value
                in FROZEN_HORIZONS_MS
            ],
            "primary_future_horizons_ms": [
                str(
                    value
                )
                for value
                in PRIMARY_HORIZONS_MS
            ],
            "extended_future_horizon_ms":
                str(
                    EXTENDED_HORIZON_MS
                ),
            "excluded_initial_horizon_ms":
                EXCLUDED_INITIAL_HORIZON_MS,
            "primary_state_contrast":
                "Kuru proposed midpoint versus finalized midpoint",
            "future_outcome":
                "Coinbase forward midpoint return in basis points",
            "directional_concordance_is_predictive_claim":
                False,
            "realized_execution_claim":
                False,
            "causal_finality_claim":
                False,
        },
        "threshold_results":
            threshold_results,
        "claim_boundaries":
            list(
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
    path = Path(
        path
    )

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
            "Build a provenance-bound Phase 2 "
            "state-conditioned temporal market-response report."
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
        "json:",
        args.output,
    )


if __name__ == "__main__":
    main()
