"""Tests for schema creation, seeding, and connection management."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from app.db.connection import Database, get_database, get_db_path, reset_database
from app.db.schema import DEFAULT_CASH_BALANCE, DEFAULT_WATCHLIST_TICKERS


class TestSchemaAndSeed:
    def test_tables_created(self, db):
        tables = {
            row["name"]
            for row in db.query("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        expected = {
            "users_profile",
            "watchlist",
            "positions",
            "trades",
            "portfolio_snapshots",
            "chat_messages",
        }
        assert expected.issubset(tables)

    def test_default_user_seeded(self, db):
        row = db.query_one("SELECT * FROM users_profile WHERE id = 'default'")
        assert row is not None
        assert row["cash_balance"] == DEFAULT_CASH_BALANCE

    def test_default_watchlist_seeded(self, db):
        rows = db.query("SELECT ticker FROM watchlist WHERE user_id = 'default'")
        tickers = {row["ticker"] for row in rows}
        assert tickers == set(DEFAULT_WATCHLIST_TICKERS)

    def test_reopen_does_not_duplicate_seed(self, tmp_path):
        path = tmp_path / "reopen.db"
        db1 = Database(path)
        db1.close()
        db2 = Database(path)
        rows = db2.query("SELECT * FROM watchlist WHERE user_id = 'default'")
        assert len(rows) == len(DEFAULT_WATCHLIST_TICKERS)
        db2.close()

    def test_reopen_preserves_existing_data(self, tmp_path):
        path = tmp_path / "preserve.db"
        db1 = Database(path)
        db1.execute("UPDATE users_profile SET cash_balance = 5000.0 WHERE id = 'default'")
        db1.close()

        db2 = Database(path)
        row = db2.query_one("SELECT cash_balance FROM users_profile WHERE id = 'default'")
        assert row["cash_balance"] == 5000.0
        db2.close()


class TestDbPath:
    def test_default_path_is_repo_root_db_finally_db(self):
        with patch.dict(os.environ, {}, clear=True):
            path = get_db_path()
        assert path.name == "finally.db"
        assert path.parent.name == "db"

    def test_db_path_env_override(self):
        with patch.dict(os.environ, {"DB_PATH": "/tmp/custom/path.db"}, clear=True):
            path = get_db_path()
        assert path == Path("/tmp/custom/path.db")

    def test_db_path_env_blank_falls_back_to_default(self):
        with patch.dict(os.environ, {"DB_PATH": "   "}, clear=True):
            path = get_db_path()
        assert path.name == "finally.db"


class TestSingleton:
    def test_get_database_returns_same_instance(self, tmp_path):
        with patch.dict(os.environ, {"DB_PATH": str(tmp_path / "singleton.db")}, clear=True):
            reset_database()
            try:
                db1 = get_database()
                db2 = get_database()
                assert db1 is db2
            finally:
                reset_database()
