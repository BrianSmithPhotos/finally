"""CRUD for the watchlist table."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

from .connection import Database
from .models import WatchlistEntry

DEFAULT_USER_ID = "default"


def _row_to_entry(row) -> WatchlistEntry:
    return WatchlistEntry(
        id=row["id"], user_id=row["user_id"], ticker=row["ticker"], added_at=row["added_at"]
    )


def get_watchlist(db: Database, user_id: str = DEFAULT_USER_ID) -> list[WatchlistEntry]:
    """Return all watchlist entries for the user, ordered by when they were added."""
    rows = db.query(
        "SELECT * FROM watchlist WHERE user_id = ? ORDER BY added_at ASC", (user_id,)
    )
    return [_row_to_entry(row) for row in rows]


def add_watchlist_ticker(
    db: Database, ticker: str, user_id: str = DEFAULT_USER_ID
) -> WatchlistEntry | None:
    """Add a ticker to the watchlist. Returns None if it's already present (UNIQUE conflict)."""
    entry_id = str(uuid.uuid4())
    added_at = datetime.now(UTC).isoformat()
    try:
        db.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (entry_id, user_id, ticker, added_at),
        )
    except sqlite3.IntegrityError:
        return None
    return WatchlistEntry(id=entry_id, user_id=user_id, ticker=ticker, added_at=added_at)


def remove_watchlist_ticker(db: Database, ticker: str, user_id: str = DEFAULT_USER_ID) -> bool:
    """Remove a ticker from the watchlist. Returns True if a row was deleted."""
    cur = db.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    return cur.rowcount > 0
