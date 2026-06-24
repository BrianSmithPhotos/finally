"""Tests for the SQLite persistence layer."""

import json
import sqlite3

import pytest

from app.db import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_TICKERS,
    DEFAULT_USER_ID,
    Database,
)


@pytest.fixture
def db(tmp_path):
    """A fresh, initialized Database backed by a temp file."""
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


# ---------------------------------------------------------------------------
# Lazy init + seeding
# ---------------------------------------------------------------------------


class TestInitialization:
    def test_db_file_created(self, tmp_path):
        path = tmp_path / "sub" / "test.db"
        database = Database(path)
        assert path.exists()
        database.close()

    def test_all_tables_created(self, db):
        rows = db._query_all(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
        names = {r["name"] for r in rows}
        for table in (
            "users_profile",
            "watchlist",
            "positions",
            "trades",
            "portfolio_snapshots",
            "chat_messages",
        ):
            assert table in names

    def test_default_user_seeded(self, db):
        user = db.get_user()
        assert user is not None
        assert user["id"] == DEFAULT_USER_ID
        assert user["cash_balance"] == DEFAULT_CASH_BALANCE
        assert user["created_at"]

    def test_default_watchlist_seeded(self, db):
        tickers = db.list_watchlist_tickers()
        assert set(tickers) == set(DEFAULT_TICKERS)
        assert len(tickers) == 10

    def test_initialize_is_idempotent(self, tmp_path):
        path = tmp_path / "test.db"
        database = Database(path)
        database.add_watchlist_ticker("PYPL")
        database.set_cash_balance(500.0)
        # Re-initialize should not duplicate seed rows or reset state.
        database.initialize()
        database.initialize()
        assert database.get_cash_balance() == 500.0
        assert database.list_watchlist_tickers().count("AAPL") == 1
        assert "PYPL" in database.list_watchlist_tickers()
        database.close()

    def test_reopen_existing_db_preserves_data(self, tmp_path):
        path = tmp_path / "test.db"
        d1 = Database(path)
        d1.set_cash_balance(1234.5)
        d1.add_watchlist_ticker("SHOP")
        d1.close()

        d2 = Database(path)
        assert d2.get_cash_balance() == 1234.5
        assert "SHOP" in d2.list_watchlist_tickers()
        # Still exactly one default user, no duplicate seeding.
        users = d2._query_all("SELECT id FROM users_profile")
        assert len(users) == 1
        d2.close()


# ---------------------------------------------------------------------------
# Cash balance
# ---------------------------------------------------------------------------


class TestCashBalance:
    def test_get_default_balance(self, db):
        assert db.get_cash_balance() == DEFAULT_CASH_BALANCE

    def test_set_balance(self, db):
        assert db.set_cash_balance(2500.0) == 2500.0
        assert db.get_cash_balance() == 2500.0

    def test_adjust_balance(self, db):
        db.set_cash_balance(1000.0)
        assert db.adjust_cash_balance(-250.5) == 749.5
        assert db.adjust_cash_balance(0.5) == 750.0

    def test_get_balance_missing_user_raises(self, db):
        with pytest.raises(KeyError):
            db.get_cash_balance("nobody")


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------


class TestWatchlist:
    def test_add_ticker(self, db):
        row = db.add_watchlist_ticker("pypl")
        assert row["ticker"] == "PYPL"  # normalized to uppercase
        assert "PYPL" in db.list_watchlist_tickers()

    def test_add_ticker_idempotent(self, db):
        first = db.add_watchlist_ticker("AAPL")  # already seeded
        again = db.add_watchlist_ticker("AAPL")
        assert first["id"] == again["id"]
        assert db.list_watchlist_tickers().count("AAPL") == 1

    def test_unique_constraint_enforced(self, db):
        # Direct duplicate insert (bypassing the idempotent helper) must fail.
        from app.db.database import _new_id, _now_iso

        with pytest.raises(sqlite3.IntegrityError):
            db._execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) "
                "VALUES (?, ?, ?, ?)",
                (_new_id(), DEFAULT_USER_ID, "AAPL", _now_iso()),
            )

    def test_remove_ticker(self, db):
        assert db.remove_watchlist_ticker("AAPL") is True
        assert "AAPL" not in db.list_watchlist_tickers()

    def test_remove_missing_ticker(self, db):
        assert db.remove_watchlist_ticker("ZZZZ") is False

    def test_empty_ticker_rejected(self, db):
        with pytest.raises(ValueError):
            db.add_watchlist_ticker("   ")


# ---------------------------------------------------------------------------
# Positions
# ---------------------------------------------------------------------------


class TestPositions:
    def test_no_positions_initially(self, db):
        assert db.list_positions() == []
        assert db.get_position("AAPL") is None

    def test_upsert_inserts(self, db):
        pos = db.upsert_position("AAPL", 10.5, 190.0)
        assert pos["ticker"] == "AAPL"
        assert pos["quantity"] == 10.5  # fractional shares
        assert pos["avg_cost"] == 190.0
        assert db.get_position("AAPL") is not None

    def test_upsert_updates_existing(self, db):
        db.upsert_position("AAPL", 10, 190.0)
        updated = db.upsert_position("AAPL", 15, 192.5)
        assert updated["quantity"] == 15
        assert updated["avg_cost"] == 192.5
        # Still a single row (UNIQUE on user_id, ticker).
        assert len(db.list_positions()) == 1

    def test_delete_position(self, db):
        db.upsert_position("AAPL", 10, 190.0)
        assert db.delete_position("AAPL") is True
        assert db.get_position("AAPL") is None

    def test_delete_missing_position(self, db):
        assert db.delete_position("AAPL") is False

    def test_position_ticker_normalized(self, db):
        db.upsert_position("nvda", 1, 100.0)
        assert db.get_position("NVDA") is not None


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------


class TestTrades:
    def test_insert_trade(self, db):
        trade = db.insert_trade("AAPL", "buy", 5.0, 190.0)
        assert trade["side"] == "buy"
        assert trade["ticker"] == "AAPL"
        assert trade["id"]

    def test_invalid_side_rejected(self, db):
        with pytest.raises(ValueError):
            db.insert_trade("AAPL", "hold", 1, 1.0)

    def test_check_constraint_on_side(self, db):
        from app.db.database import _new_id, _now_iso

        with pytest.raises(sqlite3.IntegrityError):
            db._execute(
                "INSERT INTO trades "
                "(id, user_id, ticker, side, quantity, price, executed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (_new_id(), DEFAULT_USER_ID, "AAPL", "hold", 1, 1.0, _now_iso()),
            )

    def test_list_trades_newest_first(self, db):
        db.insert_trade("AAPL", "buy", 1, 1.0, executed_at="2026-01-01T00:00:00+00:00")
        db.insert_trade("AAPL", "sell", 1, 2.0, executed_at="2026-01-02T00:00:00+00:00")
        trades = db.list_trades()
        assert trades[0]["price"] == 2.0
        assert trades[1]["price"] == 1.0

    def test_list_trades_filter_by_ticker(self, db):
        db.insert_trade("AAPL", "buy", 1, 1.0)
        db.insert_trade("MSFT", "buy", 1, 1.0)
        assert len(db.list_trades(ticker="AAPL")) == 1

    def test_list_trades_limit(self, db):
        for i in range(5):
            db.insert_trade("AAPL", "buy", 1, float(i))
        assert len(db.list_trades(limit=3)) == 3


# ---------------------------------------------------------------------------
# Portfolio snapshots
# ---------------------------------------------------------------------------


class TestSnapshots:
    def test_insert_and_list_chronological(self, db):
        db.insert_snapshot(10000.0, recorded_at="2026-01-02T00:00:00+00:00")
        db.insert_snapshot(9000.0, recorded_at="2026-01-01T00:00:00+00:00")
        snaps = db.list_snapshots()
        assert [s["total_value"] for s in snaps] == [9000.0, 10000.0]

    def test_list_snapshots_limit_returns_recent_chronological(self, db):
        for i in range(5):
            db.insert_snapshot(
                float(i), recorded_at=f"2026-01-0{i + 1}T00:00:00+00:00"
            )
        snaps = db.list_snapshots(limit=2)
        # Two most recent, oldest-first.
        assert [s["total_value"] for s in snaps] == [3.0, 4.0]


# ---------------------------------------------------------------------------
# Chat messages
# ---------------------------------------------------------------------------


class TestChatMessages:
    def test_insert_user_message(self, db):
        msg = db.insert_chat_message("user", "hello")
        assert msg["role"] == "user"
        assert msg["actions"] is None

    def test_insert_assistant_message_with_actions(self, db):
        actions = json.dumps({"trades": [{"ticker": "AAPL", "side": "buy"}]})
        msg = db.insert_chat_message("assistant", "Bought AAPL", actions=actions)
        assert json.loads(msg["actions"])["trades"][0]["ticker"] == "AAPL"

    def test_invalid_role_rejected(self, db):
        with pytest.raises(ValueError):
            db.insert_chat_message("system", "nope")

    def test_list_messages_chronological(self, db):
        db.insert_chat_message(
            "user", "first", created_at="2026-01-01T00:00:00+00:00"
        )
        db.insert_chat_message(
            "assistant", "second", created_at="2026-01-02T00:00:00+00:00"
        )
        msgs = db.list_chat_messages()
        assert [m["content"] for m in msgs] == ["first", "second"]

    def test_list_messages_limit_recent_chronological(self, db):
        for i in range(5):
            db.insert_chat_message(
                "user", f"m{i}", created_at=f"2026-01-0{i + 1}T00:00:00+00:00"
            )
        msgs = db.list_chat_messages(limit=2)
        assert [m["content"] for m in msgs] == ["m3", "m4"]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_get_database_returns_same_instance(self, tmp_path):
        from app.db import get_database, reset_database

        reset_database()
        try:
            d1 = get_database(tmp_path / "singleton.db")
            d2 = get_database()
            assert d1 is d2
        finally:
            reset_database()
