"""REST API routers for FinAlly (PLAN.md Section 8).

Routers:
    portfolio_router  - /api/portfolio[...]
    watchlist_router  - /api/watchlist[...]
    system_router     - /api/health

The chat router (/api/chat) is owned by the LLM Engineer and registered
separately in main.py.
"""

from app.api.portfolio import router as portfolio_router
from app.api.system import router as system_router
from app.api.watchlist import router as watchlist_router

__all__ = ["portfolio_router", "watchlist_router", "system_router"]
