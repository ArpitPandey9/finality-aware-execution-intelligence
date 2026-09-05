from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from finality_intelligence.lineage_aggregation import (
    aggregate_captures,
    verify_capture_hash,
)


EXPECTED_SCHEMA = (
    "phase0.kuru_monad_depth_ws.v2"
)

IDENTITY_MODES = (
    "price_quantity",
    "price",
)


def _canonical_json_bytes(
    value: object,
) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_empirical_evidence(
    capture_paths: list[Path],
    *,
    minimum_followup_ms: float = 1000.0,
) -> dict:
    if not capture_paths:
        raise ValueError(
            "At least one capture is required."
        )

    loaded = []
    sources = []

    for path in capture_paths:
        digest = verify_capture_hash(
            path
        )

        with path.open(
            encoding="utf-8",
        ) as f:
            capture = json.load(
                f
            )

        if (
            capture.get(
                "schema_version"
            )
            != EXPECTED_SCHEMA
        ):
            raise ValueError(
                f"{path}: expected schema "
                f"{EXPECTED_SCHEMA}"
            )

        if (
            capture.get(
                "gate",
                {},
            ).get(
                "overall"
            )
            != "PASS"
        ):
            raise ValueError(
                f"{path}: capture gate "
                "is not PASS"
            )

        loaded.append(
            (
                path.name,
                capture,
            )
        )

        sources.append(
            {
                "file": path.name,
                "sha256": digest,
                "captured_messages": len(
                    capture["records"]
                ),
                "unique_U_within_capture": (
                    capture.get(
                        "summary",
                        {},
                    ).get(
                        "unique_U"
                    )
                ),
            }
        )

    aggregate = aggregate_captures(
        loaded,
        minimum_followup_ms=(
            minimum_followup_ms
        ),
    )

    fingerprint_input = {
        "minimum_followup_ms": (
            minimum_followup_ms
        ),
        "sources": [
            {
                "file": source["file"],
                "sha256": source[
                    "sha256"
                ],
            }
            for source in sources
        ],
    }

    dataset_fingerprint = (
        hashlib.sha256(
            _canonical_json_bytes(
                fingerprint_input
            )
        ).hexdigest()
    )

    return {
        "schema_version": (
            "phase0.quote_lineage_empirical_evidence.v1"
        ),
        "methodology": {
            "minimum_followup_ms": (
                minimum_followup_ms
            ),
            "identity_modes": [
                "price_quantity",
                "price",
            ],
            "episode_aware": True,
            "reentry_ambiguous_excluded_from_evaluable": (
                True
            ),
            "capture_start_candidates_excluded_from_evaluable": (
                True
            ),
            "unresolved_short_followup_excluded": (
                True
            ),
        },
        "dataset_fingerprint_sha256": (
            dataset_fingerprint
        ),
        "sources": sources,
        "aggregation": aggregate,
        "claim_boundary": {
            "captures_not_assumed_statistically_independent": (
                True
            ),
            "pooled_rates_descriptive_only": (
                True
            ),
            "U_semantics_not_assumed": (
                True
            ),
            "quote_identity_not_order_identity": (
                True
            ),
            "not_observed_not_classified_as_failure": (
                True
            ),
            "latencies_are_client_observed_first_seen_differences": (
                True
            ),
            "no_trading_edge_claim": True,
            "no_finality_premium_claim": True,
            "no_protocol_finality_latency_claim": (
                True
            ),
            "raw_source_captures_required_for_reproduction": (
                True
            ),
            "raw_source_captures_not_embedded_in_bundle": (
                True
            ),
        },
    }


def write_json(
    evidence: dict,
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            evidence,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_capture_csv(
    evidence: dict,
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "capture",
        "captured_messages",
        "unique_U_within_capture",
        "identity_mode",
        "proposed_episodes",
        "reentry_ambiguous_episodes",
        "evaluable_episodes",
        "evaluable_ordered",
        "ordered_rate",
        "evaluable_later_progressions",
        "later_progression_rate",
        "voted_latency_count",
        "voted_latency_median_ms",
        "finalized_latency_count",
        "finalized_latency_median_ms",
        "committed_latency_count",
        "committed_latency_median_ms",
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            lineterminator="\n",
        )

        writer.writeheader()

        for capture in evidence[
            "aggregation"
        ][
            "per_capture"
        ]:
            for mode in IDENTITY_MODES:
                summary = capture[
                    "modes"
                ][mode]

                latency = summary[
                    "latency_ms"
                ]

                writer.writerow(
                    {
                        "capture": capture[
                            "capture"
                        ],
                        "captured_messages": (
                            capture[
                                "captured_messages"
                            ]
                        ),
                        "unique_U_within_capture": (
                            capture[
                                "unique_U_within_capture"
                            ]
                        ),
                        "identity_mode": (
                            mode
                        ),
                        "proposed_episodes": (
                            summary[
                                "proposed_episodes"
                            ]
                        ),
                        "reentry_ambiguous_episodes": (
                            summary[
                                "reentry_ambiguous_episodes"
                            ]
                        ),
                        "evaluable_episodes": (
                            summary[
                                "evaluable_episodes"
                            ]
                        ),
                        "evaluable_ordered": (
                            summary[
                                "evaluable_ordered"
                            ]
                        ),
                        "ordered_rate": (
                            summary[
                                "ordered_rate"
                            ]
                        ),
                        "evaluable_later_progressions": (
                            summary[
                                "evaluable_later_progressions"
                            ]
                        ),
                        "later_progression_rate": (
                            summary[
                                "later_progression_rate"
                            ]
                        ),
                        "voted_latency_count": (
                            latency[
                                "voted"
                            ][
                                "count"
                            ]
                        ),
                        "voted_latency_median_ms": (
                            latency[
                                "voted"
                            ][
                                "median"
                            ]
                        ),
                        "finalized_latency_count": (
                            latency[
                                "finalized"
                            ][
                                "count"
                            ]
                        ),
                        "finalized_latency_median_ms": (
                            latency[
                                "finalized"
                            ][
                                "median"
                            ]
                        ),
                        "committed_latency_count": (
                            latency[
                                "committed"
                            ][
                                "count"
                            ]
                        ),
                        "committed_latency_median_ms": (
                            latency[
                                "committed"
                            ][
                                "median"
                            ]
                        ),
                    }
                )


def _pct(
    value: float | None,
) -> str:
    if value is None:
        return "N/A"

    return (
        f"{value * 100:.2f}%"
    )


def _ms(
    value: float | None,
) -> str:
    if value is None:
        return "N/A"

    return (
        f"{value:.3f} ms"
    )


def render_markdown(
    evidence: dict,
) -> str:
    aggregation = evidence[
        "aggregation"
    ]

    exact = aggregation[
        "cross_capture"
    ][
        "price_quantity"
    ]

    price = aggregation[
        "cross_capture"
    ][
        "price"
    ]

    exact_total = exact[
        "descriptive_pooled_totals"
    ]

    price_total = price[
        "descriptive_pooled_totals"
    ]

    exact_ordered = exact[
        "capture_level_ordered_rate"
    ]

    price_ordered = price[
        "capture_level_ordered_rate"
    ]

    exact_latency = exact[
        "descriptive_pooled_latency_ms"
    ]

    price_latency = price[
        "descriptive_pooled_latency_ms"
    ]

    source_lines = "\n".join(
        (
            f"- `{source['file']}` — "
            f"SHA256 `{source['sha256']}`; "
            f"{source['captured_messages']} messages"
        )
        for source in evidence[
            "sources"
        ]
    )

    return f"""# Quote-Lineage Empirical Result

## Scope

This artifact summarizes five captured Kuru `mon_usdc@monadDepth` observation windows using the episode-aware quote-lineage methodology implemented in this repository.

Dataset fingerprint:

`{evidence["dataset_fingerprint_sha256"]}`

The analysis uses a minimum unresolved follow-up window of **{evidence["methodology"]["minimum_followup_ms"]:.0f} ms**.

## Evidence Base

- Capture windows: **{aggregation["capture_count"]}**
- Captured WebSocket messages: **{aggregation["captured_messages_total"]}**
- Sum of within-capture unique `U` counts: **{aggregation["sum_unique_U_within_captures"]}**

{source_lines}

Raw capture payloads are not embedded in this evidence bundle. Reproducing the calculations requires the listed source capture files to be available and to pass SHA256 verification against the hashes above.

## Exact Price + Quantity Identity

Across the five windows, **{exact_total["evaluable_episodes"]}** episodes remained evaluable after conservative ambiguity and censoring exclusions. **{exact_total["evaluable_ordered"]}** were observed in ordered proposed → voted → finalized → committed state views.

The pooled ordered proportion is **{_pct(exact_total["ordered_rate"])}**, but this value is **descriptive only**.

Across individual capture windows, the ordered proportion ranged from **{_pct(exact_ordered["min"])}** to **{_pct(exact_ordered["max"])}**, with a capture-level median of **{_pct(exact_ordered["median"])}**.

There were **{exact_total["evaluable_later_progressions"]}** evaluable later-observed progressions. For those observations, the pooled client-observed first-sighting median was **{_ms(exact_latency["voted"]["median"])}** for voted and **{_ms(exact_latency["finalized"]["median"])}** for finalized. Committed had the same pooled median of **{_ms(exact_latency["committed"]["median"])}** in this sample.

## Price-Level Identity

When quote identity is relaxed to price only, **{price_total["evaluable_episodes"]}** episodes remained evaluable and **{price_total["evaluable_ordered"]}** were observed in ordered state views.

The pooled ordered proportion is **{_pct(price_total["ordered_rate"])}**, again **descriptive only**.

Across individual capture windows, the ordered proportion ranged from **{_pct(price_ordered["min"])}** to **{_pct(price_ordered["max"])}**, with a capture-level median of **{_pct(price_ordered["median"])}**.

There were **{price_total["evaluable_later_progressions"]}** evaluable later-observed progressions. Their pooled client-observed first-sighting median was **{_ms(price_latency["voted"]["median"])}** for voted and **{_ms(price_latency["finalized"]["median"])}** for finalized. Committed had a pooled median of **{_ms(price_latency["committed"]["median"])}**.

## Interpretation

The captures demonstrate that state-specific top-of-book representations can be observed across Kuru's proposed, voted, finalized, and committed views, and that some conservatively evaluable quote episodes are observed in ordered progression across those views.

The capture-level variation is material, so a single pooled proportion should not be interpreted as a stable population survival probability. The observation windows are not assumed to be statistically independent.

## Claim Boundary

`U` is retained only as an observed stream grouping field; no block-number or undocumented protocol semantics are assigned to it.

Quote identity does not establish individual order identity, ownership, execution, or economic intent. Re-entry-ambiguous episodes are excluded from evaluable statistics.

A quote not observed in a later state is not classified as a finality failure or execution failure.

Reported latency values are client-observed first-sighting differences within the captured WebSocket stream. They are **not** measurements of Monad consensus latency or protocol finality latency.

These results do not establish a trading edge, arbitrage opportunity, finality premium, causal relationship, or profitability claim.
"""


def write_markdown(
    evidence: dict,
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        render_markdown(
            evidence
        ),
        encoding="utf-8",
    )
