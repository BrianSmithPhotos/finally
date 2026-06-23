"""Tests for watchlist CRUD."""

from __future__ import annotations

from app.db.watchlist import add_watchlist_ticker, get_watchlist, remove_watchlist_ticker


class TestWatchlist:
    def test_default_seed_has_ten_tickers(self, db):
        entries = get_watchlist(db)
        assert len(entries) == 10

    def test_add_ticker(self, db):
        entry = add_watchlist_ticker(db, "PYPL")
        assert entry is not None
        assert entry.ticker == "PYPL"
        assert entry.user_id == "default"
        tickers = {e.ticker for e in get_watchlist(db)}
        assert "PYPL" in tickers

    def test_add_duplicate_ticker_returns_none(self, db):
        result = add_watchlist_ticker(db, "AAPL")
        assert result is None
        tickers = [e.ticker for e in get_watchlist(db) if e.ticker == "AAPL"]
        assert len(tickers) == 1

    def test_remove_ticker(self, db):
        assert remove_watchlist_ticker(db, "AAPL") is True
        tickers = {e.ticker for e in get_watchlist(db)}
        assert "AAPL" not in tickers

    def test_remove_nonexistent_ticker_returns_false(self, db):
        assert remove_watchlist_ticker(db, "NOPE") is False

    def test_watchlist_scoped_per_user(self, db):
        add_watchlist_ticker(db, "AAPL", user_id="other")
        assert len(get_watchlist(db, user_id="other")) == 1
        assert len(get_watchlist(db, user_id="default")) == 10
