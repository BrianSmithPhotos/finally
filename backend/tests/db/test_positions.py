"""Tests for positions CRUD and buy/sell bookkeeping."""

from __future__ import annotations

from app.db.positions import (
    apply_buy,
    apply_sell,
    delete_position,
    get_position,
    get_positions,
    upsert_position,
)


class TestPositions:
    def test_no_positions_initially(self, db):
        assert get_positions(db) == []
        assert get_position(db, "AAPL") is None

    def test_upsert_creates_position(self, db):
        pos = upsert_position(db, "AAPL", 10.0, 190.0)
        assert pos.ticker == "AAPL"
        assert pos.quantity == 10.0
        assert pos.avg_cost == 190.0
        assert get_position(db, "AAPL").quantity == 10.0

    def test_upsert_overwrites_existing(self, db):
        upsert_position(db, "AAPL", 10.0, 190.0)
        upsert_position(db, "AAPL", 5.0, 200.0)
        pos = get_position(db, "AAPL")
        assert pos.quantity == 5.0
        assert pos.avg_cost == 200.0
        assert len(get_positions(db)) == 1

    def test_delete_position(self, db):
        upsert_position(db, "AAPL", 10.0, 190.0)
        assert delete_position(db, "AAPL") is True
        assert get_position(db, "AAPL") is None

    def test_delete_nonexistent_position(self, db):
        assert delete_position(db, "AAPL") is False

    def test_apply_buy_new_position(self, db):
        pos = apply_buy(db, "AAPL", 10.0, 100.0)
        assert pos.quantity == 10.0
        assert pos.avg_cost == 100.0

    def test_apply_buy_averages_cost(self, db):
        apply_buy(db, "AAPL", 10.0, 100.0)
        pos = apply_buy(db, "AAPL", 10.0, 200.0)
        assert pos.quantity == 20.0
        assert pos.avg_cost == 150.0

    def test_apply_sell_partial(self, db):
        apply_buy(db, "AAPL", 10.0, 100.0)
        pos = apply_sell(db, "AAPL", 4.0)
        assert pos.quantity == 6.0
        assert pos.avg_cost == 100.0  # cost basis unchanged on sell

    def test_apply_sell_full_deletes_position(self, db):
        apply_buy(db, "AAPL", 10.0, 100.0)
        result = apply_sell(db, "AAPL", 10.0)
        assert result is None
        assert get_position(db, "AAPL") is None

    def test_apply_sell_nonexistent_position_returns_none(self, db):
        assert apply_sell(db, "AAPL", 5.0) is None

    def test_positions_scoped_per_user(self, db):
        apply_buy(db, "AAPL", 10.0, 100.0, user_id="other")
        assert get_positions(db, user_id="default") == []
        assert len(get_positions(db, user_id="other")) == 1
