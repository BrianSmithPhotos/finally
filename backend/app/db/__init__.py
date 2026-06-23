"""Database layer for FinAlly.

SQLite, single file, lazily initialized (schema + seed data created on first
connection). No ORM — plain sqlite3 with frozen dataclasses for return types.

Public API:
    Database          - Connection wrapper (thread-safe via internal lock)
    get_database()     - Process-wide singleton; use this in app code
    get_db_path()       - Resolves the DB file path (DB_PATH env var or default)

    UserProfile, WatchlistEntry, Position, Trade, PortfolioSnapshot, ChatMessage
        - Frozen dataclasses returned by the query functions below

    get_user_profile, update_cash_balance, adjust_cash_balance
    get_watchlist, add_watchlist_ticker, remove_watchlist_ticker
    get_positions, get_position, upsert_position, apply_buy, apply_sell, delete_position
    insert_trade, get_trades
    insert_portfolio_snapshot, get_portfolio_snapshots
    insert_chat_message, get_chat_messages

Every function takes a `Database` instance as its first argument and an
optional `user_id` (default "default" — this is a single-user app).

Typical usage:
    from app.db import get_database, get_watchlist, add_watchlist_ticker

    db = get_database()
    entries = get_watchlist(db)
    add_watchlist_ticker(db, "PYPL")
"""

from .chat import get_chat_messages, insert_chat_message
from .connection import Database, get_database, get_db_path, reset_database
from .models import (
    ChatMessage,
    PortfolioSnapshot,
    Position,
    Trade,
    UserProfile,
    WatchlistEntry,
)
from .positions import (
    apply_buy,
    apply_sell,
    delete_position,
    get_position,
    get_positions,
    upsert_position,
)
from .snapshots import get_portfolio_snapshots, insert_portfolio_snapshot
from .trades import get_trades, insert_trade
from .users import adjust_cash_balance, get_user_profile, update_cash_balance
from .watchlist import add_watchlist_ticker, get_watchlist, remove_watchlist_ticker

__all__ = [
    "Database",
    "get_database",
    "get_db_path",
    "reset_database",
    "UserProfile",
    "WatchlistEntry",
    "Position",
    "Trade",
    "PortfolioSnapshot",
    "ChatMessage",
    "get_user_profile",
    "update_cash_balance",
    "adjust_cash_balance",
    "get_watchlist",
    "add_watchlist_ticker",
    "remove_watchlist_ticker",
    "get_positions",
    "get_position",
    "upsert_position",
    "apply_buy",
    "apply_sell",
    "delete_position",
    "insert_trade",
    "get_trades",
    "insert_portfolio_snapshot",
    "get_portfolio_snapshots",
    "insert_chat_message",
    "get_chat_messages",
]
