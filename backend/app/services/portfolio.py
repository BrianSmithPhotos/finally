"""Portfolio service: trade execution, valuation, and P&L math.

This module is the single source of truth for portfolio business logic. It is
deliberately framework-agnostic — it takes a `Database` and a `PriceCache` and
returns/raises plain Python values — so it can be reused by the portfolio REST
router and by the LLM chat router without duplicating trade rules.

Shared seam for the LLM Engineer
--------------------------------
    from app.services import (
        TradeError,
        execute_trade,
        build_portfolio,
        build_watchlist,
        record_snapshot,
    )

    # Execute a validated market order (raises TradeError on bad input /
    # insufficient funds / insufficient shares / missing price):
    result = execute_trade(db, cache, ticker="AAPL", quantity=10, side="buy")
    # result -> {"trade": {...}, "portfolio": {...}}

    # Build the full portfolio snapshot dict (positions enriched with live
    # price + unrealized P&L, cash, total value):
    portfolio = build_portfolio(db, cache)

All money/quantity values are floats. Tickers are uppercased here as a
convenience, but the DB layer also normalizes on write/read.
"""

from __future__ import annotations

from app.db import Database
from app.market import PriceCache

# A position quantity at or below this magnitude is treated as fully closed.
_ZERO_QTY_EPSILON = 1e-9


class TradeError(Exception):
    """Raised when a trade fails validation (bad input, funds, shares, price).

    Carries a human-readable `message` suitable for returning to the client
    (HTTP 4xx) or surfacing to the LLM so it can inform the user.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def normalize_ticker(ticker: str) -> str:
    """Uppercase + strip a ticker symbol. Raises TradeError if empty."""
    cleaned = (ticker or "").strip().upper()
    if not cleaned:
        raise TradeError("Ticker must be a non-empty symbol.")
    return cleaned


def _position_market_value(quantity: float, price: float | None) -> float | None:
    if price is None:
        return None
    return quantity * price


def build_position_view(position: dict, cache: PriceCache) -> dict:
    """Enrich a stored position row with live price, market value, and P&L.

    `price`, `market_value`, `unrealized_pnl`, and `change_percent` are None
    when the ticker has no price in the cache yet.
    """
    ticker = position["ticker"]
    quantity = float(position["quantity"])
    avg_cost = float(position["avg_cost"])
    price = cache.get_price(ticker)

    cost_basis = quantity * avg_cost
    market_value = _position_market_value(quantity, price)
    if market_value is None:
        unrealized_pnl: float | None = None
        change_percent: float | None = None
    else:
        unrealized_pnl = market_value - cost_basis
        change_percent = (unrealized_pnl / cost_basis * 100) if cost_basis != 0 else 0.0

    return {
        "ticker": ticker,
        "quantity": quantity,
        "avg_cost": avg_cost,
        "current_price": price,
        "cost_basis": cost_basis,
        "market_value": market_value,
        "unrealized_pnl": unrealized_pnl,
        "change_percent": change_percent,
    }


def build_portfolio(db: Database, cache: PriceCache) -> dict:
    """Return the full portfolio snapshot.

    Shape:
        {
          "cash_balance": float,
          "positions": [position_view, ...],
          "positions_value": float,   # market value of priced positions
          "total_value": float,       # cash + positions_value
          "total_unrealized_pnl": float,
        }

    Positions with no cached price contribute their cost basis to
    `positions_value` (best available estimate) so totals stay sensible before
    the first price tick.
    """
    cash = db.get_cash_balance()
    positions = [build_position_view(p, cache) for p in db.list_positions()]

    positions_value = 0.0
    total_unrealized_pnl = 0.0
    for view in positions:
        if view["market_value"] is not None:
            positions_value += view["market_value"]
            total_unrealized_pnl += view["unrealized_pnl"]
        else:
            # No live price yet — fall back to cost basis for valuation.
            positions_value += view["cost_basis"]

    return {
        "cash_balance": cash,
        "positions": positions,
        "positions_value": positions_value,
        "total_value": cash + positions_value,
        "total_unrealized_pnl": total_unrealized_pnl,
    }


def record_snapshot(db: Database, cache: PriceCache) -> dict:
    """Compute the current total portfolio value and persist a snapshot row."""
    total_value = build_portfolio(db, cache)["total_value"]
    return db.insert_snapshot(total_value=total_value)


def execute_trade(
    db: Database,
    cache: PriceCache,
    *,
    ticker: str,
    quantity: float,
    side: str,
) -> dict:
    """Execute a market order at the current cached price (instant fill).

    Validates input, sufficient cash (buys) / sufficient shares (sells), applies
    weighted-average-cost on buys, reduces quantity on sells (deleting the
    position when it hits ~0), adjusts cash, appends a trade row, and records a
    portfolio snapshot immediately.

    Returns ``{"trade": <trade row>, "portfolio": <portfolio snapshot>}``.
    Raises ``TradeError`` (no state mutated) on any validation failure.
    """
    ticker = normalize_ticker(ticker)

    side = (side or "").strip().lower()
    if side not in ("buy", "sell"):
        raise TradeError("Side must be 'buy' or 'sell'.")

    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise TradeError("Quantity must be a number.") from None
    if quantity <= 0:
        raise TradeError("Quantity must be greater than zero.")

    price = cache.get_price(ticker)
    if price is None:
        raise TradeError(
            f"No live price available for {ticker}. "
            "Add it to the watchlist and wait for a price tick before trading."
        )

    cost = quantity * price
    existing = db.get_position(ticker)

    if side == "buy":
        cash = db.get_cash_balance()
        if cost > cash + _ZERO_QTY_EPSILON:
            raise TradeError(
                f"Insufficient cash: need ${cost:,.2f} but only ${cash:,.2f} available."
            )
        if existing is None:
            new_qty = quantity
            new_avg_cost = price
        else:
            old_qty = float(existing["quantity"])
            old_avg = float(existing["avg_cost"])
            new_qty = old_qty + quantity
            # Weighted-average cost across old basis + new fill.
            new_avg_cost = (old_qty * old_avg + quantity * price) / new_qty
        db.adjust_cash_balance(-cost)
        db.upsert_position(ticker, quantity=new_qty, avg_cost=new_avg_cost)
    else:  # sell
        if existing is None:
            raise TradeError(f"No position in {ticker} to sell.")
        held = float(existing["quantity"])
        if quantity > held + _ZERO_QTY_EPSILON:
            raise TradeError(
                f"Insufficient shares: trying to sell {quantity:g} "
                f"but only {held:g} held."
            )
        db.adjust_cash_balance(cost)
        remaining = held - quantity
        if remaining <= _ZERO_QTY_EPSILON:
            db.delete_position(ticker)
        else:
            # avg_cost is unchanged on a partial sell.
            db.upsert_position(
                ticker, quantity=remaining, avg_cost=float(existing["avg_cost"])
            )

    trade = db.insert_trade(ticker, side, quantity=quantity, price=price)
    portfolio = build_portfolio(db, cache)
    db.insert_snapshot(total_value=portfolio["total_value"])

    return {"trade": trade, "portfolio": portfolio}


def build_watchlist(db: Database, cache: PriceCache) -> list[dict]:
    """Return watchlist tickers enriched with the latest cached price/change.

    Price-derived fields are None when the ticker is not yet in the cache.
    """
    items: list[dict] = []
    for ticker in db.list_watchlist_tickers():
        update = cache.get(ticker)
        if update is None:
            items.append(
                {
                    "ticker": ticker,
                    "price": None,
                    "previous_price": None,
                    "change": None,
                    "change_percent": None,
                    "direction": "flat",
                }
            )
        else:
            items.append(
                {
                    "ticker": ticker,
                    "price": update.price,
                    "previous_price": update.previous_price,
                    "change": update.change,
                    "change_percent": update.change_percent,
                    "direction": update.direction,
                }
            )
    return items
