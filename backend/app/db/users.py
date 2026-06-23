"""CRUD for the users_profile table."""

from __future__ import annotations

from .connection import Database
from .models import UserProfile

DEFAULT_USER_ID = "default"


def _row_to_profile(row) -> UserProfile:
    return UserProfile(id=row["id"], cash_balance=row["cash_balance"], created_at=row["created_at"])


def get_user_profile(db: Database, user_id: str = DEFAULT_USER_ID) -> UserProfile | None:
    """Fetch the user's profile (cash balance), or None if it doesn't exist."""
    row = db.query_one("SELECT * FROM users_profile WHERE id = ?", (user_id,))
    return _row_to_profile(row) if row else None


def update_cash_balance(
    db: Database, cash_balance: float, user_id: str = DEFAULT_USER_ID
) -> UserProfile | None:
    """Set the user's cash balance to an absolute value. Returns the updated profile."""
    db.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
        (cash_balance, user_id),
    )
    return get_user_profile(db, user_id)


def adjust_cash_balance(
    db: Database, delta: float, user_id: str = DEFAULT_USER_ID
) -> UserProfile | None:
    """Add `delta` (negative for a debit) to the user's cash balance."""
    db.execute(
        "UPDATE users_profile SET cash_balance = cash_balance + ? WHERE id = ?",
        (delta, user_id),
    )
    return get_user_profile(db, user_id)
