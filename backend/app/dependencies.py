"""FastAPI dependencies exposing shared app state to routers.

Shared singletons (the `Database`, the `PriceCache`, and the running
`MarketDataSource`) are created once in `main.py`'s lifespan and stored on
`app.state`. Routers depend on the small accessors below rather than reaching
for module-level globals, which keeps them testable and lets `main.py` own
construction/teardown.

The LLM chat router can use the same accessors (`get_db`, `get_cache`) to reach
the database and price cache, then call into `app.services`.
"""

from __future__ import annotations

from fastapi import Request

from app.db import Database
from app.market import MarketDataSource, PriceCache


def get_db(request: Request) -> Database:
    """Return the shared Database instance."""
    return request.app.state.db


def get_cache(request: Request) -> PriceCache:
    """Return the shared PriceCache instance."""
    return request.app.state.price_cache


def get_market_source(request: Request) -> MarketDataSource:
    """Return the running MarketDataSource (for watchlist add/remove)."""
    return request.app.state.market_source
