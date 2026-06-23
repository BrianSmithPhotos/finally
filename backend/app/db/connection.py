"""Connection management and lazy schema initialization.

Single SQLite file, shared across the process via one connection guarded by a
lock. This is a single-user app with light load, so a connection pool would be
over-engineering; check_same_thread=False + a lock is sufficient and simple.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from .schema import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    DEFAULT_WATCHLIST_TICKERS,
    SCHEMA_SQL,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DB_PATH = _REPO_ROOT / "db" / "finally.db"


def get_db_path() -> Path:
    """Resolve the SQLite file path from the DB_PATH env var, or the default.

    Default: <repo_root>/db/finally.db (the Docker volume mount target).
    """
    override = os.environ.get("DB_PATH", "").strip()
    return Path(override) if override else _DEFAULT_DB_PATH


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _seed(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, _now()),
    )
    for ticker in DEFAULT_WATCHLIST_TICKERS:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), DEFAULT_USER_ID, ticker, _now()),
        )
    conn.commit()


def _connect_raw(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    _seed(conn)
    return conn


class Database:
    """Owns a single sqlite3 connection and a lock for thread-safe access.

    Use the module-level `get_database()` singleton in application code.
    Construct a `Database(path)` directly in tests for isolation (e.g. a temp
    file or ':memory:').
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.path = Path(db_path) if db_path is not None else get_db_path()
        self._conn = _connect_raw(self.path)
        self._lock = Lock()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Run a single statement and commit. Thread-safe."""
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Run a SELECT and return all rows. Thread-safe."""
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    def query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Run a SELECT and return the first row, or None. Thread-safe."""
        with self._lock:
            return self._conn.execute(sql, params).fetchone()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


_db: Database | None = None
_db_lock = Lock()


def get_database() -> Database:
    """Process-wide singleton Database, lazily created on first call.

    Downstream code (API routes, LLM tooling) should call this rather than
    constructing Database directly, so the whole app shares one connection.
    """
    global _db
    with _db_lock:
        if _db is None:
            _db = Database()
        return _db


def reset_database() -> None:
    """Close and clear the singleton. Test-only; not used by app code."""
    global _db
    with _db_lock:
        if _db is not None:
            _db.close()
            _db = None
