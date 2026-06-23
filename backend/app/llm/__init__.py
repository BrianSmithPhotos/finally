"""LLM chat subsystem for FinAlly.

Public API:
    get_chat_response  - Async entry point: (message, portfolio_context, history) -> ChatResponse
    ChatResponse        - Structured response: message, trades, watchlist_changes
    TradeAction         - A single trade to auto-execute
    WatchlistChange     - A single watchlist add/remove to apply
"""

from .chat import get_chat_response
from .schemas import ChatResponse, TradeAction, WatchlistChange

__all__ = [
    "get_chat_response",
    "ChatResponse",
    "TradeAction",
    "WatchlistChange",
]
