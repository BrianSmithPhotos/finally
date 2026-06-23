"""Tests for users_profile CRUD."""

from __future__ import annotations

from app.db.users import adjust_cash_balance, get_user_profile, update_cash_balance


class TestUsers:
    def test_get_default_user_profile(self, db):
        profile = get_user_profile(db)
        assert profile is not None
        assert profile.id == "default"
        assert profile.cash_balance == 10000.0

    def test_get_unknown_user_returns_none(self, db):
        assert get_user_profile(db, user_id="nope") is None

    def test_update_cash_balance(self, db):
        profile = update_cash_balance(db, 1234.5)
        assert profile.cash_balance == 1234.5
        assert get_user_profile(db).cash_balance == 1234.5

    def test_adjust_cash_balance_positive(self, db):
        profile = adjust_cash_balance(db, 500.0)
        assert profile.cash_balance == 10500.0

    def test_adjust_cash_balance_negative(self, db):
        profile = adjust_cash_balance(db, -2500.0)
        assert profile.cash_balance == 7500.0
