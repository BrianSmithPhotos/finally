"""Deterministic mock responses for LLM_MOCK=true.

Used by E2E tests (PLAN.md §12) so they run without network calls, fast and
reproducibly. Behavior is intentionally simple, not clever:

- A message containing "buy" followed by a ticker-like token (2-5 uppercase
  letters) returns a mock buy trade for 1 share of that ticker.
- A message containing "sell" followed by a ticker-like token returns a mock
  sell trade for 1 share of that ticker.
- A message containing "watch" or "add" followed by a ticker-like token adds
  it to the watchlist.
- Anything else returns a canned analytical message with no actions.
"""

from __future__ import annotations

import re

from .schemas import ChatResponse, TradeAction, WatchlistChange

_TICKER_RE = re.compile(r"\b[A-Z]{2,5}\b")


def _find_ticker(message: str) -> str | None:
    """Find an all-caps, ticker-like token (2-5 letters) in the original text.

    Case matters here: only words already written in uppercase in the user's
    message are treated as tickers, so ordinary lowercase words like "buy" or
    "how" never match.
    """
    match = _TICKER_RE.search(message)
    return match.group(0) if match else None


def get_mock_response(message: str) -> ChatResponse:
    """Return a deterministic ChatResponse for the given user message."""
    lowered = message.lower()
    ticker = _find_ticker(message)

    if "buy" in lowered and ticker:
        return ChatResponse(
            message=f"Mock mode: executing a buy order for 1 share of {ticker}.",
            trades=[TradeAction(ticker=ticker, side="buy", quantity=1)],
        )

    if "sell" in lowered and ticker:
        return ChatResponse(
            message=f"Mock mode: executing a sell order for 1 share of {ticker}.",
            trades=[TradeAction(ticker=ticker, side="sell", quantity=1)],
        )

    if ("watch" in lowered or "add" in lowered) and ticker:
        return ChatResponse(
            message=f"Mock mode: adding {ticker} to the watchlist.",
            watchlist_changes=[WatchlistChange(ticker=ticker, action="add")],
        )

    return ChatResponse(
        message=(
            "Mock mode: your portfolio looks balanced. No trades or watchlist "
            "changes suggested right now."
        ),
    )
