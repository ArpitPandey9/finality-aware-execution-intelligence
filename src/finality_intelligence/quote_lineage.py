from __future__ import annotations

from collections import defaultdict
from datetime import datetime


STATES = (
    "proposed",
    "voted",
    "finalized",
    "committed",
)

SIDES = (
    "bid",
    "ask",
)

IDENTITY_MODES = (
    "price_quantity",
    "price",
)


def _received_at(record: dict) -> datetime:
    return datetime.fromisoformat(
        record["received_at_utc"]
    )


def _quote_identity(
    record: dict,
    *,
    state: str,
    side: str,
    identity_mode: str,
) -> tuple[str, ...] | None:
    if state not in STATES:
        raise ValueError(
            f"Unsupported state: {state}"
        )

    if side not in SIDES:
        raise ValueError(
            f"Unsupported side: {side}"
        )

    if identity_mode not in IDENTITY_MODES:
        raise ValueError(
            "identity_mode must be "
            "'price_quantity' or 'price'"
        )

    book = (
        record.get("states", {})
        .get(state, {})
    )

    if side == "bid":
        price = book.get(
            "best_bid_raw"
        )
        quantity = book.get(
            "best_bid_quantity_raw"
        )
    else:
        price = book.get(
            "best_ask_raw"
        )
        quantity = book.get(
            "best_ask_quantity_raw"
        )

    if price is None:
        return None

    if identity_mode == "price":
        return (
            str(price),
        )

    if quantity is None:
        return None

    return (
        str(price),
        str(quantity),
    )


def _first_at_or_after(
    items: list[dict],
    *,
    minimum_index: int,
) -> dict | None:
    for item in items:
        if (
            item["record_index"]
            >= minimum_index
        ):
            return item

    return None


def _segment_episodes(
    items: list[dict],
) -> list[dict]:
    if not items:
        return []

    episodes = []

    current = [
        items[0]
    ]

    for item in items[1:]:
        if (
            item["record_index"]
            == current[-1][
                "record_index"
            ]
            + 1
        ):
            current.append(
                item
            )
            continue

        episodes.append(
            {
                "start": current[0],
                "end": current[-1],
                "message_count": (
                    len(current)
                ),
            }
        )

        current = [
            item
        ]

    episodes.append(
        {
            "start": current[0],
            "end": current[-1],
            "message_count": (
                len(current)
            ),
        }
    )

    return episodes


def analyze_quote_lineage(
    records: list[dict],
    *,
    identity_mode: str,
    capture_end_utc: str | None = None,
    minimum_followup_ms: float = 1000.0,
) -> dict:
    if identity_mode not in IDENTITY_MODES:
        raise ValueError(
            "identity_mode must be "
            "'price_quantity' or 'price'"
        )

    if minimum_followup_ms < 0:
        raise ValueError(
            "minimum_followup_ms must be "
            "non-negative"
        )

    capture_end = (
        datetime.fromisoformat(
            capture_end_utc
        )
        if capture_end_utc
        else None
    )

    occurrences = {
        state: defaultdict(list)
        for state in STATES
    }

    records_missing_u = 0

    for record_index, record in enumerate(
        records,
        start=1,
    ):
        u = record.get("U")

        if u is None:
            records_missing_u += 1
            continue

        received = _received_at(
            record
        )

        for state in STATES:
            for side in SIDES:
                identity = _quote_identity(
                    record,
                    state=state,
                    side=side,
                    identity_mode=(
                        identity_mode
                    ),
                )

                if identity is None:
                    continue

                key = (
                    u,
                    side,
                    *identity,
                )

                occurrences[state][
                    key
                ].append(
                    {
                        "record_index": (
                            record_index
                        ),
                        "received_at": (
                            received
                        ),
                        "received_at_utc": (
                            record[
                                "received_at_utc"
                            ]
                        ),
                        "U": u,
                        "side": side,
                        "identity": (
                            identity
                        ),
                    }
                )

    proposed_episodes = {
        key: _segment_episodes(
            items
        )
        for key, items in (
            occurrences[
                "proposed"
            ].items()
        )
    }

    rows = []

    for key, episodes in (
        proposed_episodes.items()
    ):
        reentry_ambiguous = (
            len(episodes) > 1
        )

        for episode_number, episode in enumerate(
            episodes,
            start=1,
        ):
            proposed = episode[
                "start"
            ]

            proposed_index = (
                proposed[
                    "record_index"
                ]
            )

            proposed_end_index = (
                episode[
                    "end"
                ][
                    "record_index"
                ]
            )

            preexisting_later_states = []

            for state in (
                "voted",
                "finalized",
                "committed",
            ):
                if any(
                    item[
                        "record_index"
                    ]
                    < proposed_index
                    for item in (
                        occurrences[
                            state
                        ].get(
                            key,
                            []
                        )
                    )
                ):
                    preexisting_later_states.append(
                        state
                    )

            matches = {}

            previous_index = (
                proposed_index
            )

            for state in (
                "voted",
                "finalized",
                "committed",
            ):
                match = _first_at_or_after(
                    occurrences[
                        state
                    ].get(
                        key,
                        []
                    ),
                    minimum_index=(
                        previous_index
                    ),
                )

                matches[state] = match

                if match is not None:
                    previous_index = (
                        match[
                            "record_index"
                        ]
                    )

            all_later_observed = all(
                matches[state]
                is not None
                for state in (
                    "voted",
                    "finalized",
                    "committed",
                )
            )

            ordered = (
                not preexisting_later_states
                and all_later_observed
                and proposed_index
                <= matches["voted"][
                    "record_index"
                ]
                <= matches[
                    "finalized"
                ][
                    "record_index"
                ]
                <= matches[
                    "committed"
                ][
                    "record_index"
                ]
            )

            already_aligned = (
                ordered
                and all(
                    matches[state][
                        "record_index"
                    ]
                    == proposed_index
                    for state in (
                        "voted",
                        "finalized",
                        "committed",
                    )
                )
            )

            later_progression = (
                ordered
                and not already_aligned
            )

            remaining_capture_ms = (
                (
                    capture_end
                    - proposed[
                        "received_at"
                    ]
                ).total_seconds()
                * 1000
                if capture_end
                is not None
                else None
            )

            capture_start_candidate = (
                proposed_index == 1
            )

            right_censored = (
                not ordered
                and remaining_capture_ms
                is not None
                and remaining_capture_ms
                < minimum_followup_ms
            )

            evaluable = (
                not reentry_ambiguous
                and not preexisting_later_states
                and not capture_start_candidate
                and not right_censored
            )

            row = {
                "U": proposed["U"],
                "side": proposed["side"],
                "identity": (
                    proposed["identity"]
                ),
                "episode_number": (
                    episode_number
                ),
                "episode_start_record": (
                    proposed_index
                ),
                "episode_end_record": (
                    proposed_end_index
                ),
                "episode_message_count": (
                    episode[
                        "message_count"
                    ]
                ),
                "reentry_ambiguous": (
                    reentry_ambiguous
                ),
                "proposed": proposed,
                "voted": matches[
                    "voted"
                ],
                "finalized": matches[
                    "finalized"
                ],
                "committed": matches[
                    "committed"
                ],
                "preexisting_later_states": (
                    preexisting_later_states
                ),
                "capture_start_candidate": (
                    capture_start_candidate
                ),
                "right_censored": (
                    right_censored
                ),
                "evaluable": (
                    evaluable
                ),
                "observed_ordered_all_states": (
                    ordered
                ),
                "already_aligned_same_record": (
                    already_aligned
                ),
                "observed_later_progression": (
                    later_progression
                ),
                "remaining_capture_ms": (
                    remaining_capture_ms
                ),
            }

            for state in (
                "voted",
                "finalized",
                "committed",
            ):
                item = matches[
                    state
                ]

                row[
                    f"{state}_delta_ms"
                ] = (
                    (
                        item[
                            "received_at"
                        ]
                        - proposed[
                            "received_at"
                        ]
                    ).total_seconds()
                    * 1000
                    if item is not None
                    else None
                )

            rows.append(
                row
            )

    keys_with_reentry = sum(
        len(episodes) > 1
        for episodes in (
            proposed_episodes.values()
        )
    )

    additional_reentry_episodes = sum(
        max(
            0,
            len(episodes) - 1,
        )
        for episodes in (
            proposed_episodes.values()
        )
    )

    summary = {
        "identity_mode": (
            identity_mode
        ),
        "minimum_followup_ms": (
            minimum_followup_ms
        ),
        "records": len(records),
        "records_missing_U": (
            records_missing_u
        ),

        "unique_proposed_keys": (
            len(proposed_episodes)
        ),
        "proposed_episodes": (
            len(rows)
        ),
        "keys_with_reentry": (
            keys_with_reentry
        ),
        "additional_reentry_episodes": (
            additional_reentry_episodes
        ),
        "reentry_ambiguous_episodes": sum(
            row[
                "reentry_ambiguous"
            ]
            for row in rows
        ),

        "observed_in_voted_episodes": sum(
            row["voted"] is not None
            and row["voted"][
                "record_index"
            ]
            >= row[
                "episode_start_record"
            ]
            for row in rows
        ),
        "observed_in_finalized_episodes": sum(
            row["finalized"] is not None
            and row["finalized"][
                "record_index"
            ]
            >= row[
                "episode_start_record"
            ]
            for row in rows
        ),
        "observed_in_committed_episodes": sum(
            row["committed"] is not None
            and row["committed"][
                "record_index"
            ]
            >= row[
                "episode_start_record"
            ]
            for row in rows
        ),
        "observed_ordered_all_states_episodes": sum(
            row[
                "observed_ordered_all_states"
            ]
            for row in rows
        ),
        "already_aligned_same_record_episodes": sum(
            row[
                "already_aligned_same_record"
            ]
            for row in rows
        ),
        "observed_later_progression_episodes": sum(
            row[
                "observed_later_progression"
            ]
            for row in rows
        ),

        "preexisting_later_state_episodes": sum(
            bool(
                row[
                    "preexisting_later_states"
                ]
            )
            for row in rows
        ),
        "capture_start_episodes": sum(
            row[
                "capture_start_candidate"
            ]
            for row in rows
        ),
        "right_censored_unmatched_episodes": sum(
            row[
                "right_censored"
            ]
            for row in rows
        ),

        "evaluable_episodes": sum(
            row[
                "evaluable"
            ]
            for row in rows
        ),
        "evaluable_observed_ordered_all_states": sum(
            row[
                "evaluable"
            ]
            and row[
                "observed_ordered_all_states"
            ]
            for row in rows
        ),
        "evaluable_observed_later_progressions": sum(
            row[
                "evaluable"
            ]
            and row[
                "observed_later_progression"
            ]
            for row in rows
        ),
        "evaluable_not_observed_ordered_all_states": sum(
            row[
                "evaluable"
            ]
            and not row[
                "observed_ordered_all_states"
            ]
            for row in rows
        ),

        # Compatibility aliases retained while
        # the research interface is stabilizing.
        "proposed_candidates": (
            len(rows)
        ),
        "observed_in_voted": sum(
            row["voted"] is not None
            and row["voted"][
                "record_index"
            ]
            >= row[
                "episode_start_record"
            ]
            for row in rows
        ),
        "observed_in_finalized": sum(
            row["finalized"] is not None
            and row["finalized"][
                "record_index"
            ]
            >= row[
                "episode_start_record"
            ]
            for row in rows
        ),
        "observed_in_committed": sum(
            row["committed"] is not None
            and row["committed"][
                "record_index"
            ]
            >= row[
                "episode_start_record"
            ]
            for row in rows
        ),
        "observed_ordered_all_states": sum(
            row[
                "observed_ordered_all_states"
            ]
            for row in rows
        ),
        "already_aligned_same_record": sum(
            row[
                "already_aligned_same_record"
            ]
            for row in rows
        ),
        "observed_later_progressions": sum(
            row[
                "observed_later_progression"
            ]
            for row in rows
        ),
        "not_observed_ordered_all_states": sum(
            not row[
                "observed_ordered_all_states"
            ]
            for row in rows
        ),
        "preexisting_later_state_candidates": sum(
            bool(
                row[
                    "preexisting_later_states"
                ]
            )
            for row in rows
        ),
        "capture_start_candidates": sum(
            row[
                "capture_start_candidate"
            ]
            for row in rows
        ),
        "right_censored_candidates": sum(
            row[
                "right_censored"
            ]
            for row in rows
        ),
        "evaluable_candidates": sum(
            row[
                "evaluable"
            ]
            for row in rows
        ),
    }

    return {
        "summary": summary,
        "rows": rows,
    }
