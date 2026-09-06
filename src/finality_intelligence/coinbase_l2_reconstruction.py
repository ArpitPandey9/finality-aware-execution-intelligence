from __future__ import annotations

from decimal import Decimal, InvalidOperation


EXPECTED_PRODUCT_ID = "MON-USD"
EXPECTED_RAW_CHANNEL = "l2_data"

TARGET_EVENT_TYPES = (
    "snapshot",
    "update",
)


def _exact_decimal(
    value,
    *,
    name: str,
) -> Decimal:
    if (
        isinstance(value, bool)
        or isinstance(value, float)
    ):
        raise TypeError(
            f"{name} must use exact non-float input."
        )

    try:
        parsed = Decimal(
            str(value)
        )
    except (
        InvalidOperation,
        ValueError,
    ):
        raise ValueError(
            f"{name} is not a valid Decimal."
        ) from None

    if not parsed.is_finite():
        raise ValueError(
            f"{name} must be finite."
        )

    return parsed


def _sequence(
    value,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
    ):
        raise ValueError(
            "sequence_num must be a "
            "non-negative integer."
        )

    return value


def _stored_decimal_equal(
    observed,
    expected: Decimal,
    *,
    name: str,
) -> None:
    parsed = _exact_decimal(
        observed,
        name=name,
    )

    if parsed != expected:
        raise ValueError(
            f"{name} mismatch: "
            f"stored={parsed} "
            f"reconstructed={expected}"
        )


class CoinbaseL2Reconstructor:
    def __init__(
        self,
        *,
        product_id: str = EXPECTED_PRODUCT_ID,
    ) -> None:
        if (
            not isinstance(product_id, str)
            or not product_id
        ):
            raise ValueError(
                "product_id must be a "
                "non-empty string."
            )

        self.product_id = product_id

        self.bids: dict[
            Decimal,
            Decimal,
        ] = {}

        self.offers: dict[
            Decimal,
            Decimal,
        ] = {}

        self.initialized = False
        self.last_sequence_num: int | None = None

    def _validate_sequence(
        self,
        sequence_num,
    ) -> int:
        current = _sequence(
            sequence_num
        )

        if (
            self.last_sequence_num
            is not None
            and current
            != self.last_sequence_num + 1
        ):
            raise ValueError(
                "Coinbase wrapper sequence "
                "is not contiguous."
            )

        self.last_sequence_num = (
            current
        )

        return current

    def _apply_level(
        self,
        update: dict,
    ) -> bool:
        if not isinstance(update, dict):
            raise ValueError(
                "Level2 update must be a mapping."
            )

        side = update.get(
            "side"
        )

        if side not in {
            "bid",
            "offer",
        }:
            raise ValueError(
                "Unknown Coinbase Level2 side."
            )

        price = _exact_decimal(
            update.get(
                "price_level"
            ),
            name="price_level",
        )

        quantity = _exact_decimal(
            update.get(
                "new_quantity"
            ),
            name="new_quantity",
        )

        if price <= 0:
            raise ValueError(
                "price_level must be positive."
            )

        if quantity < 0:
            raise ValueError(
                "new_quantity must be non-negative."
            )

        book = (
            self.bids
            if side == "bid"
            else self.offers
        )

        zero_delete = (
            quantity == 0
        )

        if zero_delete:
            book.pop(
                price,
                None,
            )
        else:
            book[
                price
            ] = quantity

        return zero_delete

    def _top(
        self,
    ) -> dict:
        if not self.initialized:
            raise ValueError(
                "Book has not been initialized."
            )

        if (
            not self.bids
            or not self.offers
        ):
            raise ValueError(
                "Initialized Coinbase book "
                "must be two-sided."
            )

        best_bid = max(
            self.bids
        )

        best_offer = min(
            self.offers
        )

        if best_offer < best_bid:
            raise ValueError(
                "Reconstructed Coinbase "
                "book is crossed."
            )

        return {
            "best_bid":
                best_bid,
            "best_bid_quantity":
                self.bids[
                    best_bid
                ],
            "best_offer":
                best_offer,
            "best_offer_quantity":
                self.offers[
                    best_offer
                ],
            "spread":
                best_offer
                - best_bid,
        }

    def current_top(
        self,
    ) -> dict:
        return dict(
            self._top()
        )

    def current_book(
        self,
    ) -> dict:
        if not self.initialized:
            raise ValueError(
                "Book has not been initialized."
            )

        return {
            "bids": tuple(
                (
                    price,
                    self.bids[
                        price
                    ],
                )
                for price in sorted(
                    self.bids,
                    reverse=True,
                )
            ),
            "offers": tuple(
                (
                    price,
                    self.offers[
                        price
                    ],
                )
                for price in sorted(
                    self.offers
                )
            ),
        }

    def apply_message(
        self,
        message: dict,
    ) -> dict:
        if not isinstance(message, dict):
            raise TypeError(
                "Coinbase message must "
                "be a mapping."
            )

        sequence_num = (
            self._validate_sequence(
                message.get(
                    "sequence_num"
                )
            )
        )

        channel = message.get(
            "channel"
        )

        if not isinstance(
            channel,
            str,
        ):
            raise ValueError(
                "Coinbase channel must "
                "be a string."
            )

        events = message.get(
            "events"
        )

        if events is None:
            events = []

        if not isinstance(
            events,
            list,
        ):
            raise ValueError(
                "Coinbase events must "
                "be a list."
            )

        snapshot_events = 0
        update_events = 0
        target_updates = 0
        zero_quantity_updates = 0
        target_event_types = []

        target_record = False

        for event in events:
            if not isinstance(
                event,
                dict,
            ):
                raise ValueError(
                    "Coinbase event must "
                    "be a mapping."
                )

            if (
                event.get(
                    "product_id"
                )
                != self.product_id
            ):
                continue

            if channel != EXPECTED_RAW_CHANNEL:
                raise ValueError(
                    "Target product event "
                    "must be on l2_data."
                )

            event_type = event.get(
                "type"
            )

            if (
                event_type
                not in TARGET_EVENT_TYPES
            ):
                raise ValueError(
                    "Unsupported target "
                    "Level2 event type."
                )

            target_record = True

            target_event_types.append(
                event_type
            )

            if event_type == "snapshot":
                snapshot_events += 1

                self.bids = {}
                self.offers = {}
                self.initialized = True

            else:
                update_events += 1

                if not self.initialized:
                    raise ValueError(
                        "Coinbase Level2 update "
                        "observed before snapshot."
                    )

            updates = event.get(
                "updates"
            )

            if not isinstance(
                updates,
                list,
            ):
                raise ValueError(
                    "Target Level2 updates "
                    "must be a list."
                )

            for update in updates:
                zero_delete = (
                    self._apply_level(
                        update
                    )
                )

                target_updates += 1

                if zero_delete:
                    zero_quantity_updates += 1

        top = None

        if self.initialized:
            top = self._top()

        return {
            "sequence_num":
                sequence_num,
            "channel":
                channel,
            "target_record":
                target_record,
            "target_event_types":
                target_event_types,
            "snapshot_events":
                snapshot_events,
            "update_events":
                update_events,
            "target_updates":
                target_updates,
            "zero_quantity_updates":
                zero_quantity_updates,
            "bid_levels_after":
                (
                    len(self.bids)
                    if self.initialized
                    else None
                ),
            "offer_levels_after":
                (
                    len(self.offers)
                    if self.initialized
                    else None
                ),
            "book_top_after":
                top,
        }

    def verify_stored_record(
        self,
        record: dict,
    ) -> dict:
        if not isinstance(record, dict):
            raise TypeError(
                "Stored Coinbase record "
                "must be a mapping."
            )

        raw_message = record.get(
            "raw_message"
        )

        if not isinstance(
            raw_message,
            dict,
        ):
            raise ValueError(
                "Stored Coinbase record "
                "has no raw_message."
            )

        result = self.apply_message(
            raw_message
        )

        if (
            record.get(
                "sequence_num"
            )
            != result[
                "sequence_num"
            ]
        ):
            raise ValueError(
                "Stored/raw sequence mismatch."
            )

        if (
            record.get("channel")
            != result["channel"]
        ):
            raise ValueError(
                "Stored/raw channel mismatch."
            )

        optional_exact_fields = (
            "target_event_types",
            "snapshot_events",
            "update_events",
            "target_updates",
            "zero_quantity_updates",
        )

        for field in optional_exact_fields:
            if field in record:
                if (
                    record[field]
                    != result[field]
                ):
                    raise ValueError(
                        f"Stored {field} mismatch."
                    )

        if self.initialized:
            stored_top = record.get(
                "book_top_after"
            )

            if not isinstance(
                stored_top,
                dict,
            ):
                raise ValueError(
                    "Stored book_top_after missing."
                )

            reconstructed_top = result[
                "book_top_after"
            ]

            for field in (
                "best_bid",
                "best_bid_quantity",
                "best_offer",
                "best_offer_quantity",
                "spread",
            ):
                _stored_decimal_equal(
                    stored_top.get(
                        field
                    ),
                    reconstructed_top[
                        field
                    ],
                    name=field,
                )

            stored_bid_count = (
                record.get(
                    "bid_levels_after"
                )
            )

            stored_offer_count = (
                record.get(
                    "offer_levels_after"
                )
            )

            if (
                isinstance(
                    stored_bid_count,
                    bool,
                )
                or not isinstance(
                    stored_bid_count,
                    int,
                )
            ):
                raise ValueError(
                    "Stored bid-level count invalid."
                )

            if (
                isinstance(
                    stored_offer_count,
                    bool,
                )
                or not isinstance(
                    stored_offer_count,
                    int,
                )
            ):
                raise ValueError(
                    "Stored offer-level count invalid."
                )

            if (
                stored_bid_count
                != result[
                    "bid_levels_after"
                ]
            ):
                raise ValueError(
                    "Stored bid-level count mismatch."
                )

            if (
                stored_offer_count
                != result[
                    "offer_levels_after"
                ]
            ):
                raise ValueError(
                    "Stored offer-level count mismatch."
                )

        return result


def verify_capture_records(
    records: list[dict],
    *,
    product_id: str = EXPECTED_PRODUCT_ID,
) -> dict:
    if not isinstance(records, list):
        raise TypeError(
            "records must be a list."
        )

    if not records:
        raise ValueError(
            "records must not be empty."
        )

    book = CoinbaseL2Reconstructor(
        product_id=product_id
    )

    summary = {
        "records": 0,
        "target_l2_records": 0,
        "snapshots": 0,
        "updates": 0,
        "price_level_mutations": 0,
        "zero_quantity_deletes": 0,
        "top_checks": 0,
        "bid_count_checks": 0,
        "offer_count_checks": 0,
    }

    for record in records:
        result = (
            book.verify_stored_record(
                record
            )
        )

        summary["records"] += 1

        if result[
            "target_record"
        ]:
            summary[
                "target_l2_records"
            ] += 1

        summary["snapshots"] += (
            result[
                "snapshot_events"
            ]
        )

        summary["updates"] += (
            result[
                "update_events"
            ]
        )

        summary[
            "price_level_mutations"
        ] += result[
            "target_updates"
        ]

        summary[
            "zero_quantity_deletes"
        ] += result[
            "zero_quantity_updates"
        ]

        if book.initialized:
            summary[
                "top_checks"
            ] += 1
            summary[
                "bid_count_checks"
            ] += 1
            summary[
                "offer_count_checks"
            ] += 1

    if not book.initialized:
        raise ValueError(
            "No target snapshot initialized "
            "the reconstructed book."
        )

    return summary
