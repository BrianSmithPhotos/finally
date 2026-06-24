"""Tests for the watchlist router."""

from __future__ import annotations


class TestWatchlistRead:
    def test_default_watchlist_with_prices(self, client):
        resp = client.get("/api/watchlist")
        assert resp.status_code == 200
        items = resp.json()["watchlist"]
        tickers = [i["ticker"] for i in items]
        assert "AAPL" in tickers
        assert len(items) == 10
        aapl = next(i for i in items if i["ticker"] == "AAPL")
        assert aapl["price"] == 190.0
        assert aapl["direction"] in ("up", "down", "flat")


class TestWatchlistAdd:
    def test_add_ticker(self, client, app, cache):
        cache.update("PYPL", 70.0)
        resp = client.post("/api/watchlist", json={"ticker": "pypl"})
        assert resp.status_code == 201
        tickers = [i["ticker"] for i in resp.json()["watchlist"]]
        assert "PYPL" in tickers
        # source.add_ticker was called
        assert "PYPL" in app.state.market_source.added

    def test_add_is_idempotent(self, client):
        client.post("/api/watchlist", json={"ticker": "AAPL"})
        resp = client.post("/api/watchlist", json={"ticker": "AAPL"})
        assert resp.status_code == 201
        tickers = [i["ticker"] for i in resp.json()["watchlist"]]
        assert tickers.count("AAPL") == 1


class TestWatchlistDelete:
    def test_remove_ticker(self, client, app):
        resp = client.delete("/api/watchlist/AAPL")
        assert resp.status_code == 200
        tickers = [i["ticker"] for i in resp.json()["watchlist"]]
        assert "AAPL" not in tickers
        assert "AAPL" in app.state.market_source.removed

    def test_remove_missing_ticker_404(self, client):
        resp = client.delete("/api/watchlist/ZZZZ")
        assert resp.status_code == 404
