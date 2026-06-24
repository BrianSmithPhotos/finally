"""SQLite persistence layer for FinAlly.

This module owns connection management, lazy schema initialization + seeding,
and a clean data-access API (the `Database` repository class) covering
everything the API and LLM layers need.

Design notes:
- Uses the stdlib `sqlite3` module (no ORM).
- One connection per `Database` instance, shared across threads
  (`check_same_thread=False`) and guarded by an internal lock, which is
  appropriate for a single-process FastAPI app plus its background tasks.
- WAL journal mode for better read/write concurrency.
- `row_factory = sqlite3.Row` so rows behave dict-like; all public methods
  return plain `dict`s (or lists of dicts) for easy JSON serialization.
- Money and share quantities are stored as REAL (float) per the spec;
  fractional shares are supported.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants / seed configuration
# ---------------------------------------------------------------------------

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0
DEFAULT_TICKERS: list[str] = [
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
]

# backend/app/db/database.py -> project root is three parents up from app/db.
_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "db" / "schema.sql"
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DB_PATH = _PROJECT_ROOT / "db" / "finally.db"

_ALL_TABLES = (
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
)


def _now_iso() -> str:
    """Current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Generate a new UUID4 string id."""
    return str(uuid.uuid4())


def _resolve_db_path(db_path: str | os.PathLike[str] | None) -> str:
    """Resolve the effective DB path.

    Priority: explicit arg > FINALLY_DB_PATH env var > project-root default.
    The special value ":memory:" is passed through unchanged.
    """
    if db_path is None:
        db_path = os.environ.get("FINALLY_DB_PATH") or _DEFAULT_DB_PATH
    if str(db_path) == ":memory:":
        return ":memory:"
    return str(Path(db_path))


class Database:
    """Repository over the FinAlly SQLite database.

    Construct directly for tests (pass a `tmp_path` file or ":memory:") or use
    the module-level `get_database()` singleton in application code.
    """

    def __init__(
        self,
        db_path: str | os.PathLike[str] | None = None,
        *,
        auto_init: bool = True,
    ) -> None:
        self.path = _resolve_db_path(db_path)
        self._lock = threading.RLock()
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._initialized = False
        if auto_init:
            self.initialize()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Lazily create the schema and seed default data.

        Idempotent: creating tables uses ``IF NOT EXISTS`` and seeding only
        inserts rows that are missing. Safe to call repeatedly and from
        multiple call sites at startup.
        """
        with self._lock:
            if self._initialized:
                return
            schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
            self._conn.executescript(schema_sql)
            self._seed()
            self._conn.commit()
            self._initialized = True

    def _seed(self) -> None:
        """Insert default seed data if absent. Idempotent."""
        now = _now_iso()
        # Default user profile.
        self._conn.execute(
            "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) "
            "VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
        )
        # Default watchlist tickers (UNIQUE(user_id, ticker) makes this idempotent).
        for ticker in DEFAULT_TICKERS:
            self._conn.execute(
                "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) "
                "VALUES (?, ?, ?, ?)",
                (_new_id(), DEFAULT_USER_ID, ticker, now),
            )

    def close(self) -> None:
        """Close the underlying connection."""
        with self._lock:
            self._conn.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def _query_all(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def _query_one(self, sql: str, params: tuple = ()) -> dict | None:
        with self._lock:
            cur = self._conn.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row is not None else None

    # ------------------------------------------------------------------
    # Users / cash balance
    # ------------------------------------------------------------------

    def get_user(self, user_id: str = DEFAULT_USER_ID) -> dict | None:
        """Return the user profile row as a dict, or None if not found."""
        return self._query_one(
            "SELECT id, cash_balance, created_at FROM users_profile WHERE id = ?",
            (user_id,),
        )

    def get_cash_balance(self, user_id: str = DEFAULT_USER_ID) -> float:
        """Return the user's current cash balance."""
        row = self._query_one(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        )
        if row is None:
            raise KeyError(f"No user profile for user_id={user_id!r}")
        return float(row["cash_balance"])

    def set_cash_balance(
        self, cash_balance: float, user_id: str = DEFAULT_USER_ID
    ) -> float:
        """Set the user's cash balance to an absolute value. Returns new balance."""
        self._execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (float(cash_balance), user_id),
        )
        return self.get_cash_balance(user_id)

    def adjust_cash_balance(
        self, delta: float, user_id: str = DEFAULT_USER_ID
    ) -> float:
        """Add `delta` (may be negative) to the cash balance. Returns new balance."""
        with self._lock:
            self._conn.execute(
                "UPDATE users_profile SET cash_balance = cash_balance + ? WHERE id = ?",
                (float(delta), user_id),
            )
            self._conn.commit()
        return self.get_cash_balance(user_id)

    # ------------------------------------------------------------------
    # Watchlist
    # ------------------------------------------------------------------

    def list_watchlist(self, user_id: str = DEFAULT_USER_ID) -> list[dict]:
        """Return watchlist rows ordered by added_at (oldest first)."""
        return self._query_all(
            "SELECT id, user_id, ticker, added_at FROM watchlist "
            "WHERE user_id = ? ORDER BY added_at ASC, ticker ASC",
            (user_id,),
        )

    def list_watchlist_tickers(self, user_id: str = DEFAULT_USER_ID) -> list[str]:
        """Return just the ticker symbols on the watchlist."""
        return [row["ticker"] for row in self.list_watchlist(user_id)]

    def add_watchlist_ticker(
        self, ticker: str, user_id: str = DEFAULT_USER_ID
    ) -> dict:
        """Add a ticker to the watchlist (idempotent). Returns the row.

        Ticker symbols are normalized to uppercase.
        """
        ticker = ticker.strip().upper()
        if not ticker:
            raise ValueError("ticker must be a non-empty string")
        existing = self._query_one(
            "SELECT id, user_id, ticker, added_at FROM watchlist "
            "WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        if existing is not None:
            return existing
        row_id = _new_id()
        now = _now_iso()
        self._execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (row_id, user_id, ticker, now),
        )
        return {
            "id": row_id,
            "user_id": user_id,
            "ticker": ticker,
            "added_at": now,
        }

    def remove_watchlist_ticker(
        self, ticker: str, user_id: str = DEFAULT_USER_ID
    ) -> bool:
        """Remove a ticker from the watchlist. Returns True if a row was removed."""
        ticker = ticker.strip().upper()
        cur = self._execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def list_positions(self, user_id: str = DEFAULT_USER_ID) -> list[dict]:
        """Return all position rows for the user, ordered by ticker."""
        return self._query_all(
            "SELECT id, user_id, ticker, quantity, avg_cost, updated_at FROM positions "
            "WHERE user_id = ? ORDER BY ticker ASC",
            (user_id,),
        )

    def get_position(
        self, ticker: str, user_id: str = DEFAULT_USER_ID
    ) -> dict | None:
        """Return the position row for a ticker, or None if not held."""
        ticker = ticker.strip().upper()
        return self._query_one(
            "SELECT id, user_id, ticker, quantity, avg_cost, updated_at FROM positions "
            "WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )

    def upsert_position(
        self,
        ticker: str,
        quantity: float,
        avg_cost: float,
        user_id: str = DEFAULT_USER_ID,
    ) -> dict:
        """Insert or update a position to the given absolute quantity / avg_cost.

        Returns the resulting position row. (Trade math, e.g. weighted average
        cost on a buy, is the responsibility of the caller / API layer; this
        method simply persists the supplied values.)
        """
        ticker = ticker.strip().upper()
        now = _now_iso()
        with self._lock:
            existing = self._conn.execute(
                "SELECT id FROM positions WHERE user_id = ? AND ticker = ?",
                (user_id, ticker),
            ).fetchone()
            if existing is None:
                row_id = _new_id()
                self._conn.execute(
                    "INSERT INTO positions "
                    "(id, user_id, ticker, quantity, avg_cost, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (row_id, user_id, ticker, float(quantity), float(avg_cost), now),
                )
            else:
                self._conn.execute(
                    "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
                    "WHERE user_id = ? AND ticker = ?",
                    (float(quantity), float(avg_cost), now, user_id, ticker),
                )
            self._conn.commit()
        return self.get_position(ticker, user_id)  # type: ignore[return-value]

    def delete_position(
        self, ticker: str, user_id: str = DEFAULT_USER_ID
    ) -> bool:
        """Delete a position (e.g. when fully sold). Returns True if removed."""
        ticker = ticker.strip().upper()
        cur = self._execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Trades
    # ------------------------------------------------------------------

    def insert_trade(
        self,
        ticker: str,
        side: str,
        quantity: float,
        price: float,
        user_id: str = DEFAULT_USER_ID,
        executed_at: str | None = None,
    ) -> dict:
        """Append a trade to the log. Returns the inserted row."""
        ticker = ticker.strip().upper()
        side = side.strip().lower()
        if side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
        row_id = _new_id()
        executed_at = executed_at or _now_iso()
        self._execute(
            "INSERT INTO trades "
            "(id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (row_id, user_id, ticker, side, float(quantity), float(price), executed_at),
        )
        return {
            "id": row_id,
            "user_id": user_id,
            "ticker": ticker,
            "side": side,
            "quantity": float(quantity),
            "price": float(price),
            "executed_at": executed_at,
        }

    def list_trades(
        self,
        user_id: str = DEFAULT_USER_ID,
        ticker: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Return trades newest-first, optionally filtered by ticker / limited."""
        sql = (
            "SELECT id, user_id, ticker, side, quantity, price, executed_at "
            "FROM trades WHERE user_id = ?"
        )
        params: list = [user_id]
        if ticker is not None:
            sql += " AND ticker = ?"
            params.append(ticker.strip().upper())
        sql += " ORDER BY executed_at DESC, id DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        return self._query_all(sql, tuple(params))

    # ------------------------------------------------------------------
    # Portfolio snapshots
    # ------------------------------------------------------------------

    def insert_snapshot(
        self,
        total_value: float,
        user_id: str = DEFAULT_USER_ID,
        recorded_at: str | None = None,
    ) -> dict:
        """Record a portfolio total-value snapshot. Returns the inserted row."""
        row_id = _new_id()
        recorded_at = recorded_at or _now_iso()
        self._execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (row_id, user_id, float(total_value), recorded_at),
        )
        return {
            "id": row_id,
            "user_id": user_id,
            "total_value": float(total_value),
            "recorded_at": recorded_at,
        }

    def list_snapshots(
        self,
        user_id: str = DEFAULT_USER_ID,
        limit: int | None = None,
    ) -> list[dict]:
        """Return snapshots in chronological order (oldest first) for charting.

        When `limit` is given, the most recent `limit` snapshots are returned,
        still in chronological order.
        """
        if limit is not None:
            rows = self._query_all(
                "SELECT id, user_id, total_value, recorded_at FROM portfolio_snapshots "
                "WHERE user_id = ? ORDER BY recorded_at DESC, id DESC LIMIT ?",
                (user_id, int(limit)),
            )
            rows.reverse()
            return rows
        return self._query_all(
            "SELECT id, user_id, total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? ORDER BY recorded_at ASC, id ASC",
            (user_id,),
        )

    # ------------------------------------------------------------------
    # Chat messages
    # ------------------------------------------------------------------

    def insert_chat_message(
        self,
        role: str,
        content: str,
        actions: str | None = None,
        user_id: str = DEFAULT_USER_ID,
        created_at: str | None = None,
    ) -> dict:
        """Append a chat message. `actions` is a JSON string (or None).

        The caller is responsible for JSON-encoding the `actions` payload.
        """
        role = role.strip().lower()
        if role not in ("user", "assistant"):
            raise ValueError(f"role must be 'user' or 'assistant', got {role!r}")
        row_id = _new_id()
        created_at = created_at or _now_iso()
        self._execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (row_id, user_id, role, content, actions, created_at),
        )
        return {
            "id": row_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "actions": actions,
            "created_at": created_at,
        }

    def list_chat_messages(
        self,
        user_id: str = DEFAULT_USER_ID,
        limit: int | None = None,
    ) -> list[dict]:
        """Return chat messages in chronological order (oldest first).

        When `limit` is given, the most recent `limit` messages are returned,
        still in chronological order (useful for building LLM context).
        """
        if limit is not None:
            rows = self._query_all(
                "SELECT id, user_id, role, content, actions, created_at "
                "FROM chat_messages WHERE user_id = ? "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (user_id, int(limit)),
            )
            rows.reverse()
            return rows
        return self._query_all(
            "SELECT id, user_id, role, content, actions, created_at "
            "FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC, id ASC",
            (user_id,),
        )


# ---------------------------------------------------------------------------
# Process-wide singleton
# ---------------------------------------------------------------------------

_db_singleton: Database | None = None
_singleton_lock = threading.Lock()


def get_database(db_path: str | os.PathLike[str] | None = None) -> Database:
    """Return the lazily-initialized, process-wide `Database` singleton.

    The first call constructs the instance (creating + seeding the schema as
    needed). Subsequent calls return the same instance; `db_path` is honored
    only on the first call. Use this in application code; tests should
    construct `Database(tmp_path)` directly.
    """
    global _db_singleton
    if _db_singleton is None:
        with _singleton_lock:
            if _db_singleton is None:
                _db_singleton = Database(db_path)
    return _db_singleton


def reset_database() -> None:
    """Drop the cached singleton (closing it). Primarily for tests."""
    global _db_singleton
    with _singleton_lock:
        if _db_singleton is not None:
            _db_singleton.close()
            _db_singleton = None
