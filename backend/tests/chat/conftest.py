"""Fixtures for chat-layer tests.

Mirrors tests/api/conftest.py: a temp-file Database, a pre-seeded PriceCache,
and a fake async market source injected onto app.state (no real lifespan).
Tests run with LLM_MOCK=true so no network call is made.
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

    async def start(self, tickers: list[str]) -> None:  # pragma: no cover
        pass

    async def stop(self) -> None:  # pragma: no cover
        pass

    async def add_ticker(self, ticker: str) -> None:
        self.added.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self.removed.append(ticker)
        self.cache.remove(ticker)


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch):
    """Force deterministic mock LLM mode for all chat tests."""
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.fixture
def db(tmp_path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture
def cache() -> PriceCache:
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
        "PYPL": 70.0,
    }
    for ticker, price in seed.items():
        c.update(ticker, price)
    return c


@pytest.fixture
def source(cache) -> FakeMarketSource:
    return FakeMarketSource(cache)


@pytest.fixture
def app(db, cache, source):
    application = create_app()
    application.state.db = db
    application.state.price_cache = cache
    application.state.market_source = source
    return application


@pytest.fixture
def client(app):
    return TestClient(app)
