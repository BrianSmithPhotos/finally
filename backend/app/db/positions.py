"""CRUD for the positions table.

P&L calculation (using live prices) is the Backend API Engineer's concern.
This module only persists quantity/avg_cost and provides the weighted-average
cost-basis math for applying a buy or sell, since that's pure bookkeeping
rather than business logic (validation, cash checks, etc. stay upstream).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .connection import Database
from .models import Position

DEFAULT_USER_ID = "default"


def _row_to_position(row) -> Position:
    return Position(
        id=row["id"],
        user_id=row["user_id"],
        ticker=row["ticker"],
        quantity=row["quantity"],
        avg_cost=row["avg_cost"],
        updated_at=row["updated_at"],
    )


def get_positions(db: Database, user_id: str = DEFAULT_USER_ID) -> list[Position]:
    """Return all open positions for the user."""
    rows = db.query(
        "SELECT * FROM positions WHERE user_id = ? ORDER BY ticker ASC", (user_id,)
    )
    return [_row_to_position(row) for row in rows]


def get_position(db: Database, ticker: str, user_id: str = DEFAULT_USER_ID) -> Position | None:
    """Return the user's position in a single ticker, or None if not held."""
    row = db.query_one(
        "SELECT * FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    return _row_to_position(row) if row else None


def upsert_position(
    db: Database, ticker: str, quantity: float, avg_cost: float, user_id: str = DEFAULT_USER_ID
) -> Position:
    """Set a position's quantity/avg_cost directly (insert or replace).

    Callers that need buy/sell bookkeeping should use `apply_buy` / `apply_sell`
    instead; this is for direct writes (e.g. tests, corrections).
    """
    updated_at = datetime.now(UTC).isoformat()
    existing = get_position(db, ticker, user_id)
    if existing:
        db.execute(
            "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
            "WHERE user_id = ? AND ticker = ?",
            (quantity, avg_cost, updated_at, user_id, ticker),
        )
        return Position(
            id=existing.id,
            user_id=user_id,
            ticker=ticker,
            quantity=quantity,
            avg_cost=avg_cost,
            updated_at=updated_at,
        )
    position_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (position_id, user_id, ticker, quantity, avg_cost, updated_at),
    )
    return Position(
        id=position_id,
        user_id=user_id,
        ticker=ticker,
        quantity=quantity,
        avg_cost=avg_cost,
        updated_at=updated_at,
    )


def delete_position(db: Database, ticker: str, user_id: str = DEFAULT_USER_ID) -> bool:
    """Delete a position outright (e.g. once quantity reaches zero). Returns True if deleted."""
    cur = db.execute(
        "DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    return cur.rowcount > 0


def apply_buy(
    db: Database, ticker: str, quantity: float, price: float, user_id: str = DEFAULT_USER_ID
) -> Position:
    """Apply a buy to the position, updating quantity and weighted-average cost basis.

    Creates the position if it doesn't exist yet. Validation (sufficient cash,
    quantity > 0, etc.) is the caller's responsibility.
    """
    existing = get_position(db, ticker, user_id)
    if existing is None:
        return upsert_position(db, ticker, quantity, price, user_id)
    new_quantity = existing.quantity + quantity
    new_avg_cost = (
        (existing.quantity * existing.avg_cost) + (quantity * price)
    ) / new_quantity
    return upsert_position(db, ticker, new_quantity, new_avg_cost, user_id)


def apply_sell(
    db: Database, ticker: str, quantity: float, user_id: str = DEFAULT_USER_ID
) -> Position | None:
    """Apply a sell to the position, reducing quantity. Cost basis is unchanged on a sell.

    If the resulting quantity is zero (within floating-point tolerance) or
    negative, the position row is deleted and None is returned. Validation
    (sufficient shares to sell, etc.) is the caller's responsibility.
    """
    existing = get_position(db, ticker, user_id)
    if existing is None:
        return None
    remaining = existing.quantity - quantity
    if remaining <= 1e-9:
        delete_position(db, ticker, user_id)
        return None
    return upsert_position(db, ticker, remaining, existing.avg_cost, user_id)
