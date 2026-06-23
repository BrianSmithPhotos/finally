"""CRUD for the trades table (append-only log)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .connection import Database
from .models import Trade

DEFAULT_USER_ID = "default"


def _row_to_trade(row) -> Trade:
    return Trade(
        id=row["id"],
        user_id=row["user_id"],
        ticker=row["ticker"],
        side=row["side"],
        quantity=row["quantity"],
        price=row["price"],
        executed_at=row["executed_at"],
    )


def insert_trade(
    db: Database,
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    user_id: str = DEFAULT_USER_ID,
) -> Trade:
    """Append a trade record. `side` must be "buy" or "sell"."""
    trade_id = str(uuid.uuid4())
    executed_at = datetime.now(UTC).isoformat()
    db.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (trade_id, user_id, ticker, side, quantity, price, executed_at),
    )
    return Trade(
        id=trade_id,
        user_id=user_id,
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        executed_at=executed_at,
    )


def get_trades(
    db: Database, user_id: str = DEFAULT_USER_ID, limit: int | None = None
) -> list[Trade]:
    """Return trade history, most recent first. Optionally capped at `limit` rows."""
    if limit is not None:
        rows = db.query(
            "SELECT * FROM trades WHERE user_id = ? ORDER BY executed_at DESC LIMIT ?",
            (user_id, limit),
        )
    else:
        rows = db.query(
            "SELECT * FROM trades WHERE user_id = ? ORDER BY executed_at DESC", (user_id,)
        )
    return [_row_to_trade(row) for row in rows]
