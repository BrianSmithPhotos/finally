"""Tests for trades CRUD."""

from __future__ import annotations

from app.db.trades import get_trades, insert_trade


class TestTrades:
    def test_no_trades_initially(self, db):
        assert get_trades(db) == []

    def test_insert_trade(self, db):
        trade = insert_trade(db, "AAPL", "buy", 10.0, 190.0)
        assert trade.ticker == "AAPL"
        assert trade.side == "buy"
        assert trade.quantity == 10.0
        assert trade.price == 190.0

    def test_get_trades_most_recent_first(self, db):
        insert_trade(db, "AAPL", "buy", 10.0, 190.0)
        insert_trade(db, "GOOGL", "buy", 5.0, 175.0)
        trades = get_trades(db)
        assert len(trades) == 2
        assert trades[0].ticker == "GOOGL"
        assert trades[1].ticker == "AAPL"

    def test_get_trades_limit(self, db):
        for i in range(5):
            insert_trade(db, "AAPL", "buy", 1.0, 100.0 + i)
        trades = get_trades(db, limit=2)
        assert len(trades) == 2

    def test_trades_scoped_per_user(self, db):
        insert_trade(db, "AAPL", "buy", 10.0, 190.0, user_id="other")
        assert get_trades(db, user_id="default") == []
        assert len(get_trades(db, user_id="other")) == 1
