"""Fixtures for API-layer tests.

We build a FastAPI app whose shared state (db, price cache, market source) is
injected directly rather than going through the real lifespan startup. This
keeps tests fast and deterministic: a temp-file Database, an in-memory
PriceCache pre-populated with prices, and a fake async market source that just
records add/remove calls.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import Database
from app.main import create_app
from app.market import PriceCache


class FakeMarketSource:
    """Minimal async MarketDataSource stand-in for tests."""

    def __init__(self, cache: PriceCache) -> None:
        self.cache = cache
        self.added: list[str] = []
        self.removed: list[str] = []
        self.started = False
        self.stopped = False

    async def start(self, tickers: list[str]) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def add_ticker(self, ticker: str) -> None:
        self.added.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self.removed.append(ticker)
        self.cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self.cache.get_all().keys())


@pytest.fixture
def db(tmp_path) -> Database:
    """A fresh temp-file Database (lazy-inits + seeds on construction)."""
    return Database(tmp_path / "test.db")


@pytest.fixture
def cache() -> PriceCache:
    """PriceCache seeded with prices for the default watchlist tickers."""
    c = PriceCache()
    seed = {
        "AAPL": 190.0,
        "GOOGL": 175.0,
        "MSFT": 420.0,
        "AMZN": 185.0,
        "TSLA": 250.0,
        "NVDA": 120.0,
        "META": 500.0,
        "JPM": 200.0,
        "V": 280.0,
        "NFLX": 650.0,
    }
    for ticker, price in seed.items():
        c.update(ticker, price)
    return c


@pytest.fixture
def app(db, cache):
    """App with shared state injected (no real lifespan / market task)."""
    application = create_app()
    application.state.db = db
    application.state.price_cache = cache
    application.state.market_source = FakeMarketSource(cache)
    return application


@pytest.fixture
def client(app):
    # Do not enter lifespan: we inject state manually above.
    return TestClient(app)
