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
from finality_intelligence.cross_venue_aggregation import (
    aggregate_cross_venue_execution,
)
from finality_intelligence.cross_venue_execution import (
    STATE_ORDER,
    analyze_cross_venue_capture,
)
from finality_intelligence.depth_execution import (
    DEPTH_BANDS_BPS,
    SIDES,
    TARGET_BASE_QUANTITIES,
)
from finality_intelligence.staleness import (
    CORE_THRESHOLDS_MS,
)


SCHEMA_VERSION = (
    "phase1.cross_venue_execution_report.v1"
)

REPORT_CLAIM_BOUNDARIES = (
    "The dataset fingerprint binds the ordered source "
    "capture identifiers and verified SHA256 hashes; "
    "it is not a hash of the derived result.",
    "The three Coinbase reference-age thresholds are "
    "nested sensitivity bands and are not independent "
    "samples.",
    "Kuru MON_USDC and Coinbase MON-USD share MON as "
    "the base asset but use different quote assets.",
    "USD/USDC parity is not assumed or normalized away.",
    "Displayed-book sweeps are deterministic static "
    "simulations and are not actual executions.",
    "Fillability counts are not execution probabilities.",
    "Fees, gas, MEV, queue position, cancellation risk, "
    "inclusion risk, latency reaction, and market impact "
    "are excluded.",
    "Cross-venue gaps are descriptive market-structure "
    "measurements, not arbitrage, alpha, profitability, "
    "or causal finality claims.",
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
        for source
        in provenance
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
        len(set(capture_ids))
        != len(capture_ids)
    ):
        raise ValueError(
            "Capture identifiers must be unique."
        )

    threshold_results = {}

    for threshold in (
        CORE_THRESHOLDS_MS
    ):
        analyses = []

        for capture_id, capture in loaded:
            analysis = (
                analyze_cross_venue_capture(
                    capture,
                    capture_id=capture_id,
                    max_age_ms=threshold,
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

        threshold_results[
            str(threshold)
        ] = (
            aggregate_cross_venue_execution(
                analyses
            )
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
            "quote_basis_normalized":
                False,
            "states":
                list(STATE_ORDER),
            "sides":
                list(SIDES),
            "target_base_quantities_MON": [
                str(value)
                for value
                in TARGET_BASE_QUANTITIES
            ],
            "depth_bands_bps": [
                str(value)
                for value
                in DEPTH_BANDS_BPS
            ],
            "coinbase_reference_age_thresholds_ms": [
                str(value)
                for value
                in CORE_THRESHOLDS_MS
            ],
            "reference_selection":
                "latest prior same-process "
                "monotonic-time Coinbase Level2 "
                "state; no future reference and "
                "no interpolation",
            "coinbase_reconstruction":
                "raw Level2 snapshot/update replay "
                "with stored-record parity checks",
            "same_coinbase_reference_for_four_states":
                True,
            "fees_included":
                False,
            "gas_included":
                False,
            "realized_execution_claim":
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
            "PIT-aligned cross-venue displayed-depth "
            "and simulated-execution report."
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

    for threshold in (
        CORE_THRESHOLDS_MS
    ):
        result = report[
            "threshold_results"
        ][
            str(threshold)
        ]

        print(
            "threshold_ms:",
            threshold,
            "economic_panel_count:",
            result[
                "economic_panel_count"
            ],
        )

    print(
        "json:",
        args.output,
    )


if __name__ == "__main__":
    main()
