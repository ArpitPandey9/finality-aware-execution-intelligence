from __future__ import annotations

from decimal import Decimal


KURU_REST_PRICE_SCALE = Decimal("1000000000000000000")  # 1e18
MON_USDC_SIZE_PRECISION = Decimal("10000000000")  # 1e10


def _parse_raw_integer(value: str | int) -> Decimal:
    """
    Parse a raw non-negative integer value without using binary floating point.
    """

    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid raw numeric values.")

    if isinstance(value, int):
        if value < 0:
            raise ValueError("Raw numeric value must be non-negative.")
        return Decimal(value)

    if not isinstance(value, str):
        raise TypeError("Raw numeric value must be a string or integer.")

    if not value or not value.isdigit():
        raise ValueError(
            "Raw numeric string must contain only non-negative integer digits."
        )

    return Decimal(value)


def normalize_kuru_price(raw_price: str | int) -> Decimal:
    """
    Convert Kuru REST MON-USDC raw price representation to human price.

    Verified Phase-0 relationship:
        human_price = REST_price_raw / 1e18
    """

    raw = _parse_raw_integer(raw_price)
    return raw / KURU_REST_PRICE_SCALE


def normalize_kuru_size(
    raw_size: str | int,
    *,
    size_precision: Decimal = MON_USDC_SIZE_PRECISION,
) -> Decimal:
    """
    Convert Kuru REST raw quantity to human base-asset size.

    Verified Phase-0 relationship:
        human_base_size = REST_quantity_raw / sizePrecision
    """

    raw = _parse_raw_integer(raw_size)

    if size_precision <= 0:
        raise ValueError("size_precision must be greater than zero.")

    return raw / size_precision


def normalize_kuru_level(
    raw_level: list[str] | tuple[str, str],
    *,
    size_precision: Decimal = MON_USDC_SIZE_PRECISION,
) -> tuple[Decimal, Decimal]:
    """
    Normalize one Kuru [price, quantity] order-book level.
    """

    if len(raw_level) != 2:
        raise ValueError("Kuru order-book level must contain price and quantity.")

    raw_price, raw_size = raw_level

    return (
        normalize_kuru_price(raw_price),
        normalize_kuru_size(
            raw_size,
            size_precision=size_precision,
        ),
    )
