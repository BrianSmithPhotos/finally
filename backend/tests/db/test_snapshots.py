"""Tests for portfolio_snapshots CRUD."""

from __future__ import annotations

import time

from app.db.snapshots import get_portfolio_snapshots, insert_portfolio_snapshot


class TestSnapshots:
    def test_no_snapshots_initially(self, db):
        assert get_portfolio_snapshots(db) == []

    def test_insert_snapshot(self, db):
        snap = insert_portfolio_snapshot(db, 10500.0)
        assert snap.total_value == 10500.0

    def test_get_snapshots_chronological_order(self, db):
        insert_portfolio_snapshot(db, 10000.0)
        time.sleep(0.01)
        insert_portfolio_snapshot(db, 10500.0)
        snaps = get_portfolio_snapshots(db)
        assert len(snaps) == 2
        assert snaps[0].total_value == 10000.0
        assert snaps[1].total_value == 10500.0

    def test_get_snapshots_limit_keeps_chronological_order(self, db):
        for i in range(5):
            insert_portfolio_snapshot(db, 10000.0 + i)
            time.sleep(0.005)
        snaps = get_portfolio_snapshots(db, limit=2)
        assert len(snaps) == 2
        assert snaps[0].total_value == 10003.0
        assert snaps[1].total_value == 10004.0

    def test_snapshots_scoped_per_user(self, db):
        insert_portfolio_snapshot(db, 10000.0, user_id="other")
        assert get_portfolio_snapshots(db, user_id="default") == []
        assert len(get_portfolio_snapshots(db, user_id="other")) == 1
