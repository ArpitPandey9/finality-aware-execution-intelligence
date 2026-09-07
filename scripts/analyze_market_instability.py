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
from finality_intelligence.market_instability import (
    analyze_market_instability_capture,
)
from finality_intelligence.market_instability_aggregation import (
    FROZEN_FRESHNESS_THRESHOLDS_MS,
    REQUIRED_CONFIRMATORY_CAPTURE_COUNT,
    aggregate_market_instability,
)
from finality_intelligence.temporal_outcome import (
    EXTENDED_HORIZON_MS,
    FROZEN_HORIZONS_MS,
    PRIMARY_HORIZONS_MS,
)


SCHEMA_VERSION = (
    "phase3.market_instability_report.v1"
)

PRIMARY_BASELINE_FRESHNESS_THRESHOLD_MS = (
    "250"
)

CONFIRMATORY_DATASET_FINGERPRINT = (
    "ff29993a22743674edf13363957e7e538"
    "6b338d4e599027b4006089991f382e2"
)

CONFIRMATORY_CAPTURE_SHA256 = (
    "1039dc601f4142a80a484bac82ac4b449"
    "6f9dfea50f98bf92198354bd5c21d1f",
    "38bbaeccfe56d5857a74f0884705e3d7"
    "b244058bb1d1024e8cb19137b169b4fc",
    "4c85c427184213dec2cbdcb60d6d32c5"
    "d1359fe5195dd8ba35768cfc6d717bb5",
    "619c3d65d2b902c5b09d7fd71be35cd"
    "1adb9adebbe9ba2728e361f047e014677",
    "4d215697e54646660cae04a474a0174d"
    "1bd8ae3e6248651e5136e0d6b19d472c",
    "641324dd383f66857ffc1461d7caaca4"
    "1717e8fd51198d1f2cc889adc38b1532",
    "feae4de3ba4b2cbf67f884afd0e20d48"
    "b400a167f26f08cd5ec928365aa90955",
    "d5f4886e73da9d683e18cd92ecd74b27"
    "5ddfc7a7912c87c0e55935f4879d7d54",
    "e196db96d61bc791966c29630af1f023"
    "c721a1131ef1ad96b96c255aa40dc986",
    "e2d3190238803a2e4b0a9c8fd13e7be"
    "26a833a7edbc54043ec41a0017106a492",
)

PRIMARY_SUPPORT_NOT_ESTABLISHED = (
    "NOT ESTABLISHED"
)

PRIMARY_SUPPORT_OBSERVED = (
    "ROBUST DIRECTIONAL SUPPORT OBSERVED"
)


REPORT_CLAIM_BOUNDARIES = (
    "Phase 3 is a descriptive market-instability "
    "association study and does not establish "
    "prediction, alpha, arbitrage, or causality.",
    "A positive Spearman association does not establish "
    "that Kuru state disagreement causes or predicts "
    "future Coinbase movement.",
    "The Coinbase absolute forward midpoint movement is "
    "not realized PnL, execution, market impact, or "
    "adverse selection suffered by a trader.",
    "Simultaneous proposed and finalized Kuru views are "
    "not temporal protocol-state transitions or "
    "finality-latency measurements.",
    "The 250 ms, 500 ms, and 1000 ms freshness "
    "populations are nested sensitivity populations, "
    "not independent samples.",
    "Overlapping horizon observations are not "
    "statistically independent.",
    "The deterministic non-overlapping sensitivity "
    "reduces mechanical overlap but does not create "
    "statistical independence.",
    "The 10000 ms extended horizon cannot rescue the "
    "primary three-horizon conclusion.",
)


def dataset_fingerprint_from_hashes(
    hashes,
) -> str:
    hashes = list(
        hashes
    )

    if not hashes:
        raise ValueError(
            "At least one capture hash is required."
        )

    for value in hashes:
        if (
            not isinstance(
                value,
                str,
            )
            or len(value) != 64
        ):
            raise ValueError(
                "Invalid capture SHA256 value."
            )

    encoded = (
        "\n".join(
            hashes
        )
        + "\n"
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


def _classify_primary_support(
    threshold_results: dict,
) -> dict:
    primary = threshold_results.get(
        PRIMARY_BASELINE_FRESHNESS_THRESHOLD_MS
    )

    if not isinstance(
        primary,
        dict,
    ):
        raise ValueError(
            "Primary 250 ms freshness result missing."
        )

    supportive_horizons = []

    horizon_support = {}

    for horizon in (
        PRIMARY_HORIZONS_MS
    ):
        key = str(
            horizon
        )

        result = primary.get(
            key
        )

        if not isinstance(
            result,
            dict,
        ):
            raise ValueError(
                f"Primary horizon {key} ms missing."
            )

        support = bool(
            result.get(
                "descriptive_support",
                {},
            ).get(
                "directionally_supportive",
                False,
            )
        )

        horizon_support[
            key
        ] = support

        if support:
            supportive_horizons.append(
                key
            )

    extended_key = str(
        EXTENDED_HORIZON_MS
    )

    extended = primary.get(
        extended_key
    )

    if not isinstance(
        extended,
        dict,
    ):
        raise ValueError(
            "Extended 10000 ms result missing."
        )

    extended_support = bool(
        extended.get(
            "descriptive_support",
            {},
        ).get(
            "directionally_supportive",
            False,
        )
    )

    robust = (
        len(
            supportive_horizons
        )
        >= 2
    )

    return {
        "primary_baseline_freshness_threshold_ms":
            PRIMARY_BASELINE_FRESHNESS_THRESHOLD_MS,
        "primary_horizon_support":
            horizon_support,
        "supportive_primary_horizon_count":
            len(
                supportive_horizons
            ),
        "supportive_primary_horizons_ms":
            supportive_horizons,
        "primary_horizon_count_required":
            2,
        "primary_horizon_count_total":
            3,
        "extended_horizon_ms":
            extended_key,
        "extended_horizon_directionally_supportive":
            extended_support,
        "extended_horizon_counts_toward_primary":
            False,
        "robust_cross_horizon_support":
            robust,
        "primary_relationship_status":
            (
                PRIMARY_SUPPORT_OBSERVED
                if robust
                else PRIMARY_SUPPORT_NOT_ESTABLISHED
            ),
        "is_statistical_significance_test":
            False,
    }


def _validate_frozen_source_binding(
    provenance: list[dict],
) -> str:
    if len(
        provenance
    ) != REQUIRED_CONFIRMATORY_CAPTURE_COUNT:
        raise ValueError(
            "Phase 3 requires exactly ten frozen "
            "confirmatory captures."
        )

    observed_hashes = []

    for source in provenance:
        value = source.get(
            "sha256"
        )

        if not isinstance(
            value,
            str,
        ):
            raise ValueError(
                "Capture provenance missing SHA256."
            )

        observed_hashes.append(
            value
        )

    if tuple(
        observed_hashes
    ) != CONFIRMATORY_CAPTURE_SHA256:
        raise ValueError(
            "Source SHA256 sequence does not match "
            "the frozen Phase 3 confirmatory dataset."
        )

    fingerprint = (
        dataset_fingerprint_from_hashes(
            observed_hashes
        )
    )

    if (
        fingerprint
        != CONFIRMATORY_DATASET_FINGERPRINT
    ):
        raise ValueError(
            "Frozen Phase 3 dataset fingerprint "
            "mismatch."
        )

    return fingerprint


def build_report(
    paths,
) -> dict:
    paths = [
        Path(
            path
        )
        for path in paths
    ]

    if (
        len(
            paths
        )
        != REQUIRED_CONFIRMATORY_CAPTURE_COUNT
    ):
        raise ValueError(
            "Exactly ten Phase 3 confirmatory "
            "capture paths are required."
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

        capture_id = source.get(
            "capture_id"
        )

        if (
            not isinstance(
                capture_id,
                str,
            )
            or not capture_id.strip()
        ):
            raise ValueError(
                "Invalid capture identifier."
            )

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

    dataset_fingerprint = (
        _validate_frozen_source_binding(
            provenance
        )
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
                    analyze_market_instability_capture(
                        capture,
                        capture_id=
                            capture_id,
                        max_age_ms=
                            threshold,
                        horizon_ms=
                            horizon,
                    )
                )

                reasons = analysis.get(
                    "source_evidence_reasons",
                    [],
                )

                if reasons:
                    raise ValueError(
                        "Insufficient Phase 3 source "
                        f"evidence for {capture_id}: "
                        f"{reasons}"
                    )

                analyses.append(
                    analysis
                )

            horizon_results[
                str(
                    horizon
                )
            ] = (
                aggregate_market_instability(
                    analyses
                )
            )

        threshold_results[
            str(
                threshold
            )
        ] = horizon_results

    primary_support = (
        _classify_primary_support(
            threshold_results
        )
    )

    return {
        "schema_version":
            SCHEMA_VERSION,
        "dataset_fingerprint":
            dataset_fingerprint,
        "source_captures":
            provenance,
        "frozen_dataset_binding": {
            "required_capture_count":
                REQUIRED_CONFIRMATORY_CAPTURE_COUNT,
            "ordered_capture_sha256":
                list(
                    CONFIRMATORY_CAPTURE_SHA256
                ),
            "expected_dataset_fingerprint":
                CONFIRMATORY_DATASET_FINGERPRINT,
            "observed_dataset_fingerprint":
                dataset_fingerprint,
            "binding_status":
                "PASS",
        },
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
            "unit_of_observation":
                "one Kuru four-state panel",
            "primary_exposure":
                "absolute proposed-finalized "
                "Kuru midpoint gap in basis points",
            "primary_exposure_formula":
                "abs((proposed_mid / "
                "finalized_mid - 1) * 10000)",
            "primary_outcome":
                "absolute Coinbase forward "
                "midpoint movement in basis points",
            "primary_outcome_formula":
                "abs((future_mid / "
                "baseline_mid - 1) * 10000)",
            "association_statistic":
                "Spearman rank correlation",
            "tie_handling":
                "deterministic average ranks",
            "undefined_correlation_is_zero":
                False,
            "zero_exposure_panels_retained":
                True,
            "posthoc_exposure_threshold":
                False,
            "baseline_time_anchor":
                "Kuru received_monotonic_ns",
            "baseline_reference_selection":
                "latest eligible Coinbase target "
                "Level2 state at or before t0",
            "future_state_selection":
                "latest eligible Coinbase target "
                "Level2 state at or before "
                "t0 plus frozen horizon",
            "future_interpolation":
                False,
            "cross_capture_stitching":
                False,
            "capture_end_right_censoring":
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
            "confirmatory_capture_count":
                REQUIRED_CONFIRMATORY_CAPTURE_COUNT,
            "minimum_defined_capture_correlations":
                6,
            "cross_horizon_support_rule":
                "at least two of three primary "
                "horizons directionally supportive",
            "p_values_used":
                False,
            "confidence_intervals_used":
                False,
            "regression_used":
                False,
        },
        "threshold_results":
            threshold_results,
        "primary_support":
            primary_support,
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
            ensure_ascii=False,
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


def sha256_file(
    path: Path,
) -> str:
    return hashlib.sha256(
        Path(
            path
        ).read_bytes()
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen Phase 3 confirmatory "
            "market-instability analysis."
        )
    )

    parser.add_argument(
        "captures",
        nargs="+",
        help=(
            "The ten frozen qualifying "
            "Phase 3 capture JSON files, "
            "in chronological order."
        ),
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON report path.",
    )

    args = parser.parse_args()

    report = build_report(
        args.captures
    )

    output = Path(
        args.output
    )

    write_report(
        report,
        output,
    )

    print(
        "report:",
        output,
    )

    print(
        "report_sha256:",
        sha256_file(
            output
        ),
    )

    print(
        "dataset_fingerprint:",
        report[
            "dataset_fingerprint"
        ],
    )

    print(
        "primary_relationship_status:",
        report[
            "primary_support"
        ][
            "primary_relationship_status"
        ],
    )


if __name__ == "__main__":
    main()
