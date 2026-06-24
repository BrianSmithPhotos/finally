"""Service layer: business logic shared across API routers.

The portfolio service owns trade-execution, weighted-average-cost, and
portfolio-valuation/P&L math. Both the portfolio router and (later) the chat
router import from here so trade behavior stays identical across entry points.
"""

from app.services.portfolio import (
    TradeError,
    build_portfolio,
    build_watchlist,
    execute_trade,
    record_snapshot,
)

__all__ = [
    "TradeError",
    "execute_trade",
    "build_portfolio",
    "build_watchlist",
    "record_snapshot",
]
