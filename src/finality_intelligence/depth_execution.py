from __future__ import annotations

from decimal import Decimal

from finality_intelligence.normalization import (
    normalize_kuru_level,
)


BUY = "BUY"
SELL = "SELL"

SIDES = (
    BUY,
    SELL,
)

FULLY_FILLED_IN_CAPTURED_BOOK = (
    "FULLY_FILLED_IN_CAPTURED_BOOK"
)
INSUFFICIENT_CAPTURED_DEPTH = (
    "INSUFFICIENT_CAPTURED_DEPTH"
)

DEPTH_BANDS_BPS = (
    Decimal("5"),
    Decimal("10"),
    Decimal("25"),
    Decimal("50"),
)

TARGET_BASE_QUANTITIES = (
    Decimal("200"),
    Decimal("2000"),
    Decimal("20000"),
    Decimal("200000"),
)


def _require_decimal(
    value,
    *,
    name: str,
) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(
            f"{name} must be a Decimal."
        )

    if not isinstance(value, Decimal):
        raise TypeError(
            f"{name} must be a Decimal."
        )

    if not value.is_finite():
        raise ValueError(
            f"{name} must be finite."
        )

    return value


def _normalize_side(
    levels,
    *,
    side_name: str,
) -> list[dict]:
    if not isinstance(levels, list):
        raise ValueError(
            f"{side_name} levels must be a list."
        )

    if not levels:
        raise ValueError(
            f"{side_name} levels must not be empty."
        )

    normalized = []

    for source_index, raw_level in enumerate(
        levels
    ):
        if (
            not isinstance(
                raw_level,
                (list, tuple),
            )
            or len(raw_level) != 2
        ):
            raise ValueError(
                "Each Kuru level must contain "
                "exactly price and quantity."
            )

        price, quantity = normalize_kuru_level(
            raw_level
        )

        if price <= 0:
            raise ValueError(
                "Kuru economic price must be "
                "strictly positive."
            )

        if quantity <= 0:
            raise ValueError(
                "Kuru economic quantity must be "
                "strictly positive."
            )

        normalized.append(
            {
                "source_index": source_index,
                "raw_price": str(
                    raw_level[0]
                ),
                "raw_quantity": str(
                    raw_level[1]
                ),
                "price": price,
                "quantity": quantity,
            }
        )

    return normalized


def validate_and_normalize_book(
    raw_book: dict,
) -> dict:
    if not isinstance(raw_book, dict):
        raise ValueError(
            "Kuru state book must be a mapping."
        )

    bids = _normalize_side(
        raw_book.get("b"),
        side_name="bid",
    )

    asks = _normalize_side(
        raw_book.get("a"),
        side_name="ask",
    )

    for previous, current in zip(
        bids,
        bids[1:],
    ):
        if current["price"] > previous["price"]:
            raise ValueError(
                "Bid prices must be "
                "non-increasing in source order."
            )

    for previous, current in zip(
        asks,
        asks[1:],
    ):
        if current["price"] < previous["price"]:
            raise ValueError(
                "Ask prices must be "
                "non-decreasing in source order."
            )

    best_bid = bids[0]["price"]
    best_ask = asks[0]["price"]

    if best_ask < best_bid:
        raise ValueError(
            "Kuru state book must not be crossed."
        )

    return {
        "bids": bids,
        "asks": asks,
        "best_bid": best_bid,
        "best_ask": best_ask,
    }


def _require_side(side: str) -> None:
    if side not in SIDES:
        raise ValueError(
            f"Unsupported side: {side}"
        )


def _require_band(
    band_bps: Decimal,
) -> Decimal:
    band_bps = _require_decimal(
        band_bps,
        name="band_bps",
    )

    if band_bps not in DEPTH_BANDS_BPS:
        raise ValueError(
            "Depth band is not part of the "
            "frozen methodology."
        )

    return band_bps


def _require_target(
    target_base: Decimal,
) -> Decimal:
    target_base = _require_decimal(
        target_base,
        name="target_base",
    )

    if (
        target_base
        not in TARGET_BASE_QUANTITIES
    ):
        raise ValueError(
            "Target base quantity is not part "
            "of the frozen methodology."
        )

    return target_base


def depth_within_bps(
    book: dict,
    *,
    side: str,
    band_bps: Decimal,
) -> Decimal:
    _require_side(side)
    band_bps = _require_band(
        band_bps
    )

    fraction = (
        band_bps
        / Decimal("10000")
    )

    if side == BUY:
        best_price = book["best_ask"]
        limit_price = (
            best_price
            * (
                Decimal("1")
                + fraction
            )
        )
        levels = book["asks"]

        eligible = (
            level
            for level in levels
            if level["price"] <= limit_price
        )

    else:
        best_price = book["best_bid"]
        limit_price = (
            best_price
            * (
                Decimal("1")
                - fraction
            )
        )
        levels = book["bids"]

        eligible = (
            level
            for level in levels
            if level["price"] >= limit_price
        )

    return sum(
        (
            level["quantity"]
            for level in eligible
        ),
        Decimal("0"),
    )


def total_captured_depth(
    book: dict,
    *,
    side: str,
) -> Decimal:
    _require_side(side)

    levels = (
        book["asks"]
        if side == BUY
        else book["bids"]
    )

    return sum(
        (
            level["quantity"]
            for level in levels
        ),
        Decimal("0"),
    )


def sweep_base_quantity(
    book: dict,
    *,
    side: str,
    target_base: Decimal,
) -> dict:
    _require_side(side)
    target_base = _require_target(
        target_base
    )

    levels = (
        book["asks"]
        if side == BUY
        else book["bids"]
    )

    best_price = (
        book["best_ask"]
        if side == BUY
        else book["best_bid"]
    )

    remaining = target_base
    filled_base = Decimal("0")
    quote_amount = Decimal("0")
    levels_touched = 0
    final_level_partially_consumed = False

    for level in levels:
        if remaining == 0:
            break

        available = level["quantity"]
        fill = min(
            remaining,
            available,
        )

        if fill <= 0:
            raise ValueError(
                "Sweep encountered a "
                "non-positive level quantity."
            )

        levels_touched += 1

        filled_base += fill
        quote_amount += (
            fill
            * level["price"]
        )

        remaining -= fill

        if (
            fill < available
            and remaining == 0
        ):
            final_level_partially_consumed = (
                True
            )

    if filled_base == target_base:
        status = (
            FULLY_FILLED_IN_CAPTURED_BOOK
        )

        vwap = (
            quote_amount
            / target_base
        )

        if side == BUY:
            slippage_bps = (
                (
                    vwap
                    / best_price
                )
                - Decimal("1")
            ) * Decimal("10000")

        else:
            slippage_bps = (
                Decimal("1")
                - (
                    vwap
                    / best_price
                )
            ) * Decimal("10000")

        if slippage_bps < 0:
            raise ValueError(
                "Side-normalized slippage "
                "must not be negative."
            )

    else:
        status = (
            INSUFFICIENT_CAPTURED_DEPTH
        )
        vwap = None
        slippage_bps = None

    return {
        "side": side,
        "target_base": target_base,
        "best_price": best_price,
        "captured_level_count": len(
            levels
        ),
        "total_captured_base_depth":
            total_captured_depth(
                book,
                side=side,
            ),
        "fillability_status": status,
        "filled_base": filled_base,
        "unfilled_base": (
            target_base
            - filled_base
        ),
        "levels_touched": levels_touched,
        "final_level_partially_consumed":
            final_level_partially_consumed,
        "quote_amount": quote_amount,
        "vwap": vwap,
        "slippage_bps": slippage_bps,
    }
