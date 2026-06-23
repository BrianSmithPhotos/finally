"""REST API routes for FinAlly.

Public API:
    portfolio_router  - GET/POST /api/portfolio, /api/portfolio/trade, /api/portfolio/history
    watchlist_router   - GET/POST /api/watchlist, DELETE /api/watchlist/{ticker}
    chat_router        - POST /api/chat
    health_router      - GET /api/health
"""

from .chat import router as chat_router
from .health import router as health_router
from .portfolio import router as portfolio_router
from .watchlist import router as watchlist_router

__all__ = [
    "portfolio_router",
    "watchlist_router",
    "chat_router",
    "health_router",
]
