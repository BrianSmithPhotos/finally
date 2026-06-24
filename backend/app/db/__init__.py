"""FinAlly persistence layer (SQLite).

Public API for downstream agents (Backend API, LLM engineer):

    from app.db import (
        Database,
        get_database,
        DEFAULT_USER_ID,
        DEFAULT_TICKERS,
    )

`get_database()` returns a lazily-initialized, process-wide `Database`
singleton bound to the project-root `db/finally.db` file. All data access
goes through the `Database` repository class.
"""

from app.db.database import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_TICKERS,
    DEFAULT_USER_ID,
    Database,
    get_database,
    reset_database,
)

__all__ = [
    "Database",
    "get_database",
    "reset_database",
    "DEFAULT_USER_ID",
    "DEFAULT_CASH_BALANCE",
    "DEFAULT_TICKERS",
]
