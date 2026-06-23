"""CRUD for the portfolio_snapshots table (P&L chart data)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from .connection import Database
from .models import PortfolioSnapshot

DEFAULT_USER_ID = "default"


def _row_to_snapshot(row) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        id=row["id"],
        user_id=row["user_id"],
        total_value=row["total_value"],
        recorded_at=row["recorded_at"],
    )


def insert_portfolio_snapshot(
    db: Database, total_value: float, user_id: str = DEFAULT_USER_ID
) -> PortfolioSnapshot:
    """Record the portfolio's total value at the current moment."""
    snapshot_id = str(uuid.uuid4())
    recorded_at = datetime.now(UTC).isoformat()
    db.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
        "VALUES (?, ?, ?, ?)",
        (snapshot_id, user_id, total_value, recorded_at),
    )
    return PortfolioSnapshot(
        id=snapshot_id, user_id=user_id, total_value=total_value, recorded_at=recorded_at
    )


def get_portfolio_snapshots(
    db: Database, user_id: str = DEFAULT_USER_ID, limit: int | None = None
) -> list[PortfolioSnapshot]:
    """Return snapshots ordered oldest-to-newest (chart-ready). Optionally capped to the
    most recent `limit` snapshots, still returned in chronological order."""
    if limit is not None:
        rows = db.query(
            "SELECT * FROM (SELECT * FROM portfolio_snapshots WHERE user_id = ? "
            "ORDER BY recorded_at DESC LIMIT ?) ORDER BY recorded_at ASC",
            (user_id, limit),
        )
    else:
        rows = db.query(
            "SELECT * FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at ASC",
            (user_id,),
        )
    return [_row_to_snapshot(row) for row in rows]
