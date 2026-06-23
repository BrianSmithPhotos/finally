"""Tests for /api/watchlist routes: list, add, remove.

The `db` fixture is a freshly created Database, which is auto-seeded with the
ten default watchlist tickers per app/db/schema.py — tests account for that
seed data rather than assuming an empty watchlist.
"""

from __future__ import annotations

from app.db.watchlist import add_watchlist_ticker, remove_watchlist_ticker


class TestListWatchlist:
    def test_seeded_watchlist_has_ten_tickers(self, client):
        resp = client.get("/api/watchlist")
        assert resp.status_code == 200
        assert len(resp.json()) == 10

    def test_seeded_ticker_with_cached_price(self, client):
        resp = client.get("/api/watchlist")
        body = {entry["ticker"]: entry for entry in resp.json()}
        assert body["AAPL"]["price"] == 190.00
        assert body["AAPL"]["direction"] == "flat"

    def test_ticker_without_cached_price_yet(self, client, db):
        add_watchlist_ticker(db, "ZZZZ")
        resp = client.get("/api/watchlist")
        body = {entry["ticker"]: entry for entry in resp.json()}
        assert body["ZZZZ"]["price"] is None

    def test_empty_watchlist_after_removing_all(self, client, db):
        for ticker in ("AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"):
            remove_watchlist_ticker(db, ticker)
        resp = client.get("/api/watchlist")
        assert resp.json() == []


class TestAddTicker:
    def test_add_ticker_succeeds(self, client, market_source):
        resp = client.post("/api/watchlist", json={"ticker": "pypl"})
        assert resp.status_code == 201
        assert resp.json()["ticker"] == "PYPL"
        assert market_source.added == ["PYPL"]

    def test_add_duplicate_ticker_returns_409(self, client):
        resp = client.post("/api/watchlist", json={"ticker": "AAPL"})
        assert resp.status_code == 409


class TestRemoveTicker:
    def test_remove_existing_ticker(self, client, market_source):
        resp = client.delete("/api/watchlist/AAPL")
        assert resp.status_code == 204
        assert market_source.removed == ["AAPL"]

    def test_remove_missing_ticker_returns_404(self, client):
        resp = client.delete("/api/watchlist/ZZZZ")
        assert resp.status_code == 404
