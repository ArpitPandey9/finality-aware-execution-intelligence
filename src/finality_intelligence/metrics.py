from __future__ import annotations

from decimal import Decimal


BPS_SCALE = Decimal("10000")


def _to_decimal(value: str | int | Decimal) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid market values.")

    if isinstance(value, float):
        raise TypeError(
            "Float values are not accepted; use Decimal, string, or integer."
        )

    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, str):
        try:
            result = Decimal(value)
        except Exception as exc:
            raise ValueError(
                f"Invalid decimal value: {value!r}"
            ) from exc
    else:
        raise TypeError(
            "Market value must be Decimal, string, or integer."
        )

    if not result.is_finite():
        raise ValueError("Market value must be finite.")

    if result < 0:
        raise ValueError("Market value must be non-negative.")

    return result


def midpoint(
    bid: str | int | Decimal,
    ask: str | int | Decimal,
) -> Decimal:
    bid_value = _to_decimal(bid)
    ask_value = _to_decimal(ask)

    if ask_value < bid_value:
        raise ValueError("Ask must not be below bid.")

    return (bid_value + ask_value) / Decimal("2")


def spread(
    bid: str | int | Decimal,
    ask: str | int | Decimal,
) -> Decimal:
    bid_value = _to_decimal(bid)
    ask_value = _to_decimal(ask)

    if ask_value < bid_value:
        raise ValueError("Ask must not be below bid.")

    return ask_value - bid_value


def spread_bps(
    bid: str | int | Decimal,
    ask: str | int | Decimal,
) -> Decimal:
    mid = midpoint(bid, ask)

    if mid == 0:
        raise ValueError(
            "Cannot calculate spread bps with zero midpoint."
        )

    return spread(bid, ask) / mid * BPS_SCALE


def reference_mid_difference(
    venue_mid: str | int | Decimal,
    reference_mid: str | int | Decimal,
) -> Decimal:
    return (
        _to_decimal(venue_mid)
        - _to_decimal(reference_mid)
    )


def reference_mid_difference_bps(
    venue_mid: str | int | Decimal,
    reference_mid: str | int | Decimal,
) -> Decimal:
    venue_value = _to_decimal(venue_mid)
    reference_value = _to_decimal(reference_mid)

    if reference_value == 0:
        raise ValueError(
            "Reference midpoint must be greater than zero."
        )

    return (
        (venue_value - reference_value)
        / reference_value
        * BPS_SCALE
    )
