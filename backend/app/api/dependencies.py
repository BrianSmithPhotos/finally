"""FastAPI dependency accessors for shared app state.

main.py attaches the PriceCache, MarketDataSource, and Database singleton to
`app.state` on startup. Route modules pull them out through these dependency
functions rather than importing globals, so routes stay testable in
isolation (tests can override these dependencies on a fresh app instance).
"""

from __future__ import annotations

from fastapi import Request

from app.db import Database, get_database
from app.market import MarketDataSource, PriceCache


def get_price_cache(request: Request) -> PriceCache:
    return request.app.state.price_cache


def get_market_source(request: Request) -> MarketDataSource:
    return request.app.state.market_source


def get_db(request: Request) -> Database:
    db: Database | None = getattr(request.app.state, "db", None)
    return db if db is not None else get_database()
