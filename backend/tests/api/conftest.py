"""Fixtures for API route tests.

Builds a FastAPI app with the real routers but fake/injected state: an
isolated tmp_path Database, a fresh PriceCache pre-seeded with prices, and a
no-op MarketDataSource stand-in so tests never touch the real simulator or
network. Routes pull these out of app.state via the same dependency
functions used in production (app.api.dependencies), so the wiring under
test matches main.py exactly.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import chat_router, health_router, portfolio_router, watchlist_router
from app.db.connection import Database
from app.market import PriceCache


class FakeMarketDataSource:
    """No-op MarketDataSource stand-in; records calls for assertions."""

    def __init__(self) -> None:
        self.added: list[str] = []
        self.removed: list[str] = []
        self._tickers: list[str] = []

    async def start(self, tickers: list[str]) -> None:
        self._tickers = list(tickers)

    async def stop(self) -> None:
        pass

    async def add_ticker(self, ticker: str) -> None:
        self.added.append(ticker)
        if ticker not in self._tickers:
            self._tickers.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self.removed.append(ticker)
        if ticker in self._tickers:
            self._tickers.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)


def build_test_app(db: Database, price_cache: PriceCache, market_source) -> FastAPI:
    app = FastAPI()
    app.state.db = db
    app.state.price_cache = price_cache
    app.state.market_source = market_source

    app.include_router(portfolio_router)
    app.include_router(watchlist_router)
    app.include_router(chat_router)
    app.include_router(health_router)
    return app


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture
def price_cache():
    cache = PriceCache()
    cache.update("AAPL", 190.00)
    cache.update("GOOGL", 175.00)
    cache.update("MSFT", 420.00)
    return cache


@pytest.fixture
def market_source():
    return FakeMarketDataSource()


@pytest.fixture
def client(db, price_cache, market_source):
    app = build_test_app(db, price_cache, market_source)
    return TestClient(app)
