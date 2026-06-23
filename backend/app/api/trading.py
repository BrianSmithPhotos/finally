"""Trade execution: validation, position/cash bookkeeping, and trade logging."""

from __future__ import annotations

from dataclasses import dataclass

from app.db import (
    Database,
    adjust_cash_balance,
    apply_buy,
    apply_sell,
    get_position,
    get_user_profile,
    insert_portfolio_snapshot,
    insert_trade,
)
from app.market import PriceCache

from .portfolio_service import build_portfolio_response

SIDES = {"buy", "sell"}


class TradeError(Exception):
    """Raised when a trade fails validation. Maps to a 4xx response."""


@dataclass(frozen=True, slots=True)
class TradeResult:
    ticker: str
    side: str
    quantity: float
    price: float


def execute_trade(
    db: Database,
    price_cache: PriceCache,
    ticker: str,
    side: str,
    quantity: float,
) -> TradeResult:
    """Validate and execute a market order at the current cache price.

    Raises TradeError on any validation failure (unknown ticker, non-positive
    quantity, insufficient cash, insufficient shares). On success: updates the
    position, adjusts cash, logs the trade, and records a portfolio snapshot.
    """
    ticker = ticker.upper()
    if side not in SIDES:
        raise TradeError(f"Invalid side '{side}'; must be 'buy' or 'sell'")
    if quantity <= 0:
        raise TradeError("Quantity must be positive")

    price = price_cache.get_price(ticker)
    if price is None:
        raise TradeError(f"No live price available for '{ticker}'")

    if side == "buy":
        profile = get_user_profile(db)
        cash_balance = profile.cash_balance if profile else 0.0
        cost = quantity * price
        if cost > cash_balance:
            raise TradeError(
                f"Insufficient cash: need {cost:.2f}, have {cash_balance:.2f}"
            )
        apply_buy(db, ticker, quantity, price)
        adjust_cash_balance(db, -cost)
    else:
        position = get_position(db, ticker)
        held = position.quantity if position else 0.0
        if quantity > held:
            raise TradeError(
                f"Insufficient shares: trying to sell {quantity}, hold {held}"
            )
        apply_sell(db, ticker, quantity)
        adjust_cash_balance(db, quantity * price)

    insert_trade(db, ticker, side, quantity, price)
    snapshot_total = build_portfolio_response(db, price_cache).total_value
    insert_portfolio_snapshot(db, snapshot_total)

    return TradeResult(ticker=ticker, side=side, quantity=quantity, price=price)
