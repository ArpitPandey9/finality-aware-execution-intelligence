from __future__ import annotations

from collections import Counter
from decimal import Decimal

from finality_intelligence.alignment import (
    ALIGNED,
    INSUFFICIENT_SOURCE_EVIDENCE,
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
    align_dual_capture,
)
from finality_intelligence.coinbase_l2_reconstruction import (
    CoinbaseL2Reconstructor,
)
from finality_intelligence.depth_execution import (
    BUY,
    SELL,
    DEPTH_BANDS_BPS,
    SIDES,
    TARGET_BASE_QUANTITIES,
    FULLY_FILLED_IN_CAPTURED_BOOK,
    depth_within_bps,
    sweep_base_quantity,
    validate_and_normalize_book,
)


SCHEMA_VERSION = (
    "phase1.cross_venue_execution.v1"
)

STATE_ORDER = (
    "proposed",
    "voted",
    "finalized",
    "committed",
)

BOTH_FULL = "BOTH_FULL"
KURU_ONLY_FULL = "KURU_ONLY_FULL"
COINBASE_ONLY_FULL = "COINBASE_ONLY_FULL"
NEITHER_FULL = "NEITHER_FULL"

FILLABILITY_TRANSITIONS = (
    BOTH_FULL,
    KURU_ONLY_FULL,
    COINBASE_ONLY_FULL,
    NEITHER_FULL,
)

INVALID_KURU_PANEL = "INVALID_KURU_PANEL"
INVALID_COINBASE_RECONSTRUCTION = (
    "INVALID_COINBASE_RECONSTRUCTION"
)

ECONOMICALLY_ELIGIBLE = (
    "ECONOMICALLY_ELIGIBLE"
)

ELIGIBILITY_OUTCOMES = (
    ALIGNED,
    NO_PRIOR_REFERENCE,
    STALE_REFERENCE,
    INSUFFICIENT_SOURCE_EVIDENCE,
    INVALID_KURU_PANEL,
    INVALID_COINBASE_RECONSTRUCTION,
)

CLAIM_BOUNDARIES = (
    "Kuru MON_USDC and Coinbase MON-USD have a common MON "
    "base asset but different quote assets.",
    "USD/USDC basis risk is not removed by point-in-time alignment.",
    "Static captured-book fillability is not realized execution "
    "or execution probability.",
    "Cross-venue slippage gaps are descriptive static-book "
    "differences, not trading edge or profit.",
    "Cross-quote VWAP differences mix venue price, quote basis, "
    "book shape, and reference age.",
    "The four Kuru state views use the same selected Coinbase "
    "reference book for one Kuru observation.",
    "State-conditioned differences are observational and do not "
    "establish a causal finality effect.",
)


def _serialize_decimal(
    value: Decimal | None,
) -> str | None:
    if value is None:
        return None

    if not isinstance(value, Decimal):
        raise TypeError(
            "Expected Decimal for serialization."
        )

    return str(value)


def _coinbase_book_to_execution_book(
    current_book: dict,
) -> dict:
    if not isinstance(current_book, dict):
        raise TypeError(
            "Coinbase current_book must be a mapping."
        )

    bid_pairs = current_book.get("bids")
    offer_pairs = current_book.get("offers")

    if not isinstance(
        bid_pairs,
        tuple,
    ):
        raise ValueError(
            "Coinbase bids must be an ordered tuple."
        )

    if not isinstance(
        offer_pairs,
        tuple,
    ):
        raise ValueError(
            "Coinbase offers must be an ordered tuple."
        )

    if not bid_pairs or not offer_pairs:
        raise ValueError(
            "Coinbase book must be two-sided."
        )

    bids = []
    asks = []

    for pair in bid_pairs:
        if (
            not isinstance(pair, tuple)
            or len(pair) != 2
        ):
            raise ValueError(
                "Invalid Coinbase bid level."
            )

        price, quantity = pair

        if (
            not isinstance(price, Decimal)
            or not isinstance(quantity, Decimal)
        ):
            raise TypeError(
                "Coinbase book levels must use Decimal."
            )

        if price <= 0 or quantity <= 0:
            raise ValueError(
                "Coinbase bid price and quantity "
                "must be positive."
            )

        bids.append(
            {
                "price": price,
                "quantity": quantity,
            }
        )

    for pair in offer_pairs:
        if (
            not isinstance(pair, tuple)
            or len(pair) != 2
        ):
            raise ValueError(
                "Invalid Coinbase offer level."
            )

        price, quantity = pair

        if (
            not isinstance(price, Decimal)
            or not isinstance(quantity, Decimal)
        ):
            raise TypeError(
                "Coinbase book levels must use Decimal."
            )

        if price <= 0 or quantity <= 0:
            raise ValueError(
                "Coinbase offer price and quantity "
                "must be positive."
            )

        asks.append(
            {
                "price": price,
                "quantity": quantity,
            }
        )

    for previous, current in zip(
        bids,
        bids[1:],
    ):
        if (
            current["price"]
            > previous["price"]
        ):
            raise ValueError(
                "Coinbase bids must be "
                "non-increasing."
            )

    for previous, current in zip(
        asks,
        asks[1:],
    ):
        if (
            current["price"]
            < previous["price"]
        ):
            raise ValueError(
                "Coinbase asks must be "
                "non-decreasing."
            )

    best_bid = bids[0]["price"]
    best_ask = asks[0]["price"]

    if best_ask < best_bid:
        raise ValueError(
            "Coinbase reconstructed book "
            "must not be crossed."
        )

    return {
        "bids": bids,
        "asks": asks,
        "best_bid": best_bid,
        "best_ask": best_ask,
    }


def reconstruct_coinbase_books_at_indices(
    records: list[dict],
    *,
    record_indices: set[int],
) -> dict[int, dict]:
    if not isinstance(records, list):
        raise TypeError(
            "Coinbase records must be a list."
        )

    if not records:
        raise ValueError(
            "Coinbase records must not be empty."
        )

    if not isinstance(
        record_indices,
        set,
    ):
        raise TypeError(
            "record_indices must be a set."
        )

    for index in record_indices:
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
        ):
            raise TypeError(
                "Coinbase record index must be int."
            )

        if (
            index < 0
            or index >= len(records)
        ):
            raise ValueError(
                "Coinbase record index out of range."
            )

    reconstructor = (
        CoinbaseL2Reconstructor()
    )

    books: dict[int, dict] = {}

    for index, record in enumerate(records):
        reconstructor.verify_stored_record(
            record
        )

        if index in record_indices:
            books[index] = (
                _coinbase_book_to_execution_book(
                    reconstructor.current_book()
                )
            )

    if (
        set(books)
        != record_indices
    ):
        raise ValueError(
            "Failed to reconstruct all "
            "requested Coinbase books."
        )

    return books


def _fillability_transition(
    kuru_status: str,
    coinbase_status: str,
) -> str:
    kuru_full = (
        kuru_status
        == FULLY_FILLED_IN_CAPTURED_BOOK
    )

    coinbase_full = (
        coinbase_status
        == FULLY_FILLED_IN_CAPTURED_BOOK
    )

    if kuru_full and coinbase_full:
        return BOTH_FULL

    if kuru_full:
        return KURU_ONLY_FULL

    if coinbase_full:
        return COINBASE_ONLY_FULL

    return NEITHER_FULL


def _cross_venue_metrics(
    *,
    kuru_sweep: dict,
    coinbase_sweep: dict,
) -> dict:
    transition = _fillability_transition(
        kuru_sweep["fillability_status"],
        coinbase_sweep[
            "fillability_status"
        ],
    )

    slippage_gap_bps = None
    vwap_difference_bps = None

    if transition == BOTH_FULL:
        kuru_slippage = kuru_sweep[
            "slippage_bps"
        ]
        coinbase_slippage = (
            coinbase_sweep[
                "slippage_bps"
            ]
        )

        kuru_vwap = kuru_sweep["vwap"]
        coinbase_vwap = (
            coinbase_sweep["vwap"]
        )

        if (
            not isinstance(
                kuru_slippage,
                Decimal,
            )
            or not isinstance(
                coinbase_slippage,
                Decimal,
            )
            or not isinstance(
                kuru_vwap,
                Decimal,
            )
            or not isinstance(
                coinbase_vwap,
                Decimal,
            )
        ):
            raise TypeError(
                "Both-full sweeps must expose "
                "Decimal slippage and VWAP."
            )

        if coinbase_vwap <= 0:
            raise ValueError(
                "Coinbase VWAP must be positive."
            )

        slippage_gap_bps = (
            kuru_slippage
            - coinbase_slippage
        )

        vwap_difference_bps = (
            (
                kuru_vwap
                - coinbase_vwap
            )
            / coinbase_vwap
            * Decimal("10000")
        )

    return {
        "fillability_transition":
            transition,
        "slippage_gap_bps":
            slippage_gap_bps,
        "vwap_difference_bps":
            vwap_difference_bps,
    }


def analyze_cross_venue_capture(
    capture: dict,
    *,
    capture_id: str,
    max_age_ms,
) -> dict:
    alignment = align_dual_capture(
        capture,
        capture_id=capture_id,
        max_age_ms=max_age_ms,
    )

    rows = alignment["rows"]

    eligible_rows = [
        row
        for row in rows
        if row["status"] == ALIGNED
    ]

    requested_indices = {
        row[
            "coinbase_reference"
        ]["record_index"]
        for row in eligible_rows
    }

    alignment_status_counts = Counter(
        row["status"]
        for row in rows
    )

    economic_eligibility_counts = Counter()

    economic_rows: list[dict] = []
    depth_rows: list[dict] = []

    if requested_indices:
        try:
            coinbase_records = (
                capture[
                    "sources"
                ]["coinbase"]["records"]
            )

            coinbase_books = (
                reconstruct_coinbase_books_at_indices(
                    coinbase_records,
                    record_indices=requested_indices,
                )
            )

        except (
            ArithmeticError,
            KeyError,
            TypeError,
            ValueError,
        ):
            economic_eligibility_counts[
                INVALID_COINBASE_RECONSTRUCTION
            ] += len(eligible_rows)

            eligible_rows = []
            coinbase_books = {}

    for aligned_row in eligible_rows:
        try:
            kuru_index = (
                aligned_row[
                    "kuru"
                ][
                    "record_index"
                ]
            )

            kuru_records = (
                capture[
                    "sources"
                ][
                    "kuru"
                ][
                    "records"
                ]
            )

            if (
                not isinstance(
                    kuru_records,
                    list,
                )
                or kuru_index < 0
                or kuru_index
                >= len(kuru_records)
            ):
                raise ValueError(
                    "Kuru source record index "
                    "is invalid."
                )

            kuru_record = (
                kuru_records[
                    kuru_index
                ]
            )

            if not isinstance(
                kuru_record,
                dict,
            ):
                raise ValueError(
                    "Kuru source record "
                    "must be a mapping."
                )

            raw_message = (
                kuru_record.get(
                    "raw_message"
                )
            )

            if not isinstance(
                raw_message,
                dict,
            ):
                raise ValueError(
                    "Kuru raw_message "
                    "missing or invalid."
                )

            raw_states = (
                raw_message.get(
                    "states"
                )
            )

            if not isinstance(
                raw_states,
                dict,
            ):
                raise ValueError(
                    "Kuru raw states "
                    "missing or invalid."
                )

            normalized_kuru = {}

            for state in STATE_ORDER:
                raw_book = (
                    raw_states.get(
                        state
                    )
                )

                if not isinstance(
                    raw_book,
                    dict,
                ):
                    raise ValueError(
                        "Missing or invalid "
                        f"Kuru raw state: {state}"
                    )

                normalized_kuru[
                    state
                ] = (
                    validate_and_normalize_book(
                        raw_book
                    )
                )

        except (
            ArithmeticError,
            KeyError,
            TypeError,
            ValueError,
        ):
            economic_eligibility_counts[
                INVALID_KURU_PANEL
            ] += 1
            continue

        economic_eligibility_counts[
            ECONOMICALLY_ELIGIBLE
        ] += 1

        coinbase_reference = (
            aligned_row[
                "coinbase_reference"
            ]
        )

        coinbase_index = (
            coinbase_reference[
                "record_index"
            ]
        )

        coinbase_book = (
            coinbase_books[
                coinbase_index
            ]
        )

        for state in STATE_ORDER:
            kuru_book = (
                normalized_kuru[state]
            )

            for side in SIDES:
                for band_bps in DEPTH_BANDS_BPS:
                    kuru_depth = (
                        depth_within_bps(
                            kuru_book,
                            side=side,
                            band_bps=band_bps,
                        )
                    )

                    coinbase_depth = (
                        depth_within_bps(
                            coinbase_book,
                            side=side,
                            band_bps=band_bps,
                        )
                    )

                    depth_rows.append(
                        {
                            "capture_id":
                                capture_id,
                            "freshness_threshold_ms":
                                alignment[
                                    "max_age_ms"
                                ],
                            "kuru_record_index":
                                aligned_row[
                                    "kuru"
                                ][
                                    "record_index"
                                ],
                            "U":
                                aligned_row[
                                    "kuru"
                                ]["U"],
                            "state":
                                state,
                            "side":
                                side,
                            "band_bps":
                                _serialize_decimal(
                                    band_bps
                                ),
                            "coinbase_record_index":
                                coinbase_index,
                            "coinbase_sequence_num":
                                coinbase_reference[
                                    "sequence_num"
                                ],
                            "reference_age_ms":
                                aligned_row[
                                    "reference_age_ms"
                                ],
                            "kuru_depth_MON":
                                _serialize_decimal(
                                    kuru_depth
                                ),
                            "coinbase_depth_MON":
                                _serialize_decimal(
                                    coinbase_depth
                                ),
                            "depth_gap_MON":
                                _serialize_decimal(
                                    kuru_depth
                                    - coinbase_depth
                                ),
                        }
                    )

                for target_base in (
                    TARGET_BASE_QUANTITIES
                ):
                    kuru_sweep = (
                        sweep_base_quantity(
                            kuru_book,
                            side=side,
                            target_base=target_base,
                        )
                    )

                    coinbase_sweep = (
                        sweep_base_quantity(
                            coinbase_book,
                            side=side,
                            target_base=target_base,
                        )
                    )

                    cross = (
                        _cross_venue_metrics(
                            kuru_sweep=kuru_sweep,
                            coinbase_sweep=(
                                coinbase_sweep
                            ),
                        )
                    )

                    economic_rows.append(
                        {
                            "capture_id":
                                capture_id,
                            "freshness_threshold_ms":
                                alignment[
                                    "max_age_ms"
                                ],
                            "kuru_record_index":
                                aligned_row[
                                    "kuru"
                                ][
                                    "record_index"
                                ],
                            "kuru_received_at_utc":
                                aligned_row[
                                    "kuru"
                                ][
                                    "received_at_utc"
                                ],
                            "kuru_received_monotonic_ns":
                                aligned_row[
                                    "kuru"
                                ][
                                    "received_monotonic_ns"
                                ],
                            "U":
                                aligned_row[
                                    "kuru"
                                ]["U"],
                            "state":
                                state,
                            "side":
                                side,
                            "target_base_MON":
                                _serialize_decimal(
                                    target_base
                                ),
                            "coinbase_record_index":
                                coinbase_index,
                            "coinbase_sequence_num":
                                coinbase_reference[
                                    "sequence_num"
                                ],
                            "coinbase_received_at_utc":
                                coinbase_reference[
                                    "received_at_utc"
                                ],
                            "coinbase_received_monotonic_ns":
                                coinbase_reference[
                                    "received_monotonic_ns"
                                ],
                            "reference_age_ms":
                                aligned_row[
                                    "reference_age_ms"
                                ],
                            "alignment_status":
                                ALIGNED,
                            "kuru_best_price":
                                _serialize_decimal(
                                    kuru_sweep[
                                        "best_price"
                                    ]
                                ),
                            "coinbase_best_price":
                                _serialize_decimal(
                                    coinbase_sweep[
                                        "best_price"
                                    ]
                                ),
                            "kuru_fillability_status":
                                kuru_sweep[
                                    "fillability_status"
                                ],
                            "coinbase_fillability_status":
                                coinbase_sweep[
                                    "fillability_status"
                                ],
                            "fillability_transition":
                                cross[
                                    "fillability_transition"
                                ],
                            "kuru_filled_base_MON":
                                _serialize_decimal(
                                    kuru_sweep[
                                        "filled_base"
                                    ]
                                ),
                            "coinbase_filled_base_MON":
                                _serialize_decimal(
                                    coinbase_sweep[
                                        "filled_base"
                                    ]
                                ),
                            "kuru_total_captured_depth_MON":
                                _serialize_decimal(
                                    kuru_sweep[
                                        "total_captured_base_depth"
                                    ]
                                ),
                            "coinbase_total_captured_depth_MON":
                                _serialize_decimal(
                                    coinbase_sweep[
                                        "total_captured_base_depth"
                                    ]
                                ),
                            "kuru_levels_touched":
                                kuru_sweep[
                                    "levels_touched"
                                ],
                            "coinbase_levels_touched":
                                coinbase_sweep[
                                    "levels_touched"
                                ],
                            "kuru_vwap_USDC_per_MON":
                                _serialize_decimal(
                                    kuru_sweep[
                                        "vwap"
                                    ]
                                ),
                            "coinbase_vwap_USD_per_MON":
                                _serialize_decimal(
                                    coinbase_sweep[
                                        "vwap"
                                    ]
                                ),
                            "kuru_slippage_bps":
                                _serialize_decimal(
                                    kuru_sweep[
                                        "slippage_bps"
                                    ]
                                ),
                            "coinbase_slippage_bps":
                                _serialize_decimal(
                                    coinbase_sweep[
                                        "slippage_bps"
                                    ]
                                ),
                            "slippage_gap_bps":
                                _serialize_decimal(
                                    cross[
                                        "slippage_gap_bps"
                                    ]
                                ),
                            "cross_quote_vwap_difference_bps":
                                _serialize_decimal(
                                    cross[
                                        "vwap_difference_bps"
                                    ]
                                ),
                        }
                    )

    return {
        "schema_version": SCHEMA_VERSION,
        "capture_id": capture_id,
        "source_capture_schema_version":
            alignment[
                "source_capture_schema_version"
            ],
        "freshness_threshold_ms":
            alignment[
                "max_age_ms"
            ],
        "source_evidence_reasons":
            alignment[
                "source_evidence_reasons"
            ],
        "claim_boundaries":
            list(CLAIM_BOUNDARIES),
        "summary": {
            "kuru_observations":
                alignment[
                    "summary"
                ][
                    "kuru_observations"
                ],
            "alignment_status_counts":
                dict(
                    sorted(
                        alignment_status_counts.items()
                    )
                ),
            "economic_eligibility_counts":
                dict(
                    sorted(
                        economic_eligibility_counts.items()
                    )
                ),
            "execution_rows":
                len(economic_rows),
            "depth_rows":
                len(depth_rows),
        },
        "rows": economic_rows,
        "depth_rows": depth_rows,
    }
