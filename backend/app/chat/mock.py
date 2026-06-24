"""Deterministic mock LLM for ``LLM_MOCK=true`` (no network).

The E2E suite runs with ``LLM_MOCK=true`` so chat is fast, free, and
reproducible. This mock parses the user message with simple regex rules and
returns a fixed-shape :class:`~app.chat.schemas.LLMResponse`.

Deterministic behavior contract (also documented in planning/LLM_LAYER.md):

* Trade intent — a message matching ``(buy|sell) <qty> [shares of] <TICKER>``
  produces exactly one trade ``{ticker, side, quantity}``. ``<TICKER>`` is 1-5
  letters; ``<qty>`` may be an integer or decimal. Example: ``"buy 5 AAPL"`` ->
  one buy of 5 AAPL.
* Watchlist intent — ``(add|watch) <TICKER>`` -> add; ``(remove|unwatch|drop)
  <TICKER>`` -> remove. One change per match.
* Otherwise — no trades/changes; an echo-style analytical message that quotes
  the current cash balance and number of positions.

The mock applies at most one trade and one watchlist change per message
(first match wins) to keep assertions simple. The actual execution / validation
still runs through the real services seam, so an invalid mock trade (e.g.
insufficient cash) surfaces as an error exactly like a real one.
"""

from __future__ import annotations

import re

from app.chat.schemas import LLMResponse, LLMTrade, LLMWatchlistChange

# "buy 5 AAPL", "sell 2.5 shares of TSLA", "buy 10 shares NVDA"
_TRADE_RE = re.compile(
    r"\b(?P<side>buy|sell)\b\s+(?P<qty>\d+(?:\.\d+)?)\s+(?:shares?\s+(?:of\s+)?)?(?P<ticker>[A-Za-z]{1,5})\b",
    re.IGNORECASE,
)
_ADD_RE = re.compile(r"\b(?:add|watch)\s+(?P<ticker>[A-Za-z]{1,5})\b", re.IGNORECASE)
_REMOVE_RE = re.compile(
    r"\b(?:remove|unwatch|drop)\s+(?P<ticker>[A-Za-z]{1,5})\b", re.IGNORECASE
)

# Words that follow buy/sell/add but are not tickers — guards loose matches.
_STOPWORDS = {
    "ME", "THE", "A", "AN", "OF", "TO", "MY", "SOME", "ALL", "AND", "FOR",
    "SHARES", "SHARE", "STOCK", "STOCKS", "MORE", "IT",
}


def mock_llm_response(user_message: str, portfolio: dict) -> LLMResponse:
    """Produce a deterministic mock response from the user message."""
    trades: list[LLMTrade] = []
    watchlist_changes: list[LLMWatchlistChange] = []
    parts: list[str] = []

    trade_match = _TRADE_RE.search(user_message)
    if trade_match:
        ticker = trade_match.group("ticker").upper()
        if ticker not in _STOPWORDS:
            side = trade_match.group("side").lower()
            qty = float(trade_match.group("qty"))
            trades.append(LLMTrade(ticker=ticker, side=side, quantity=qty))
            parts.append(f"Placing a {side} order for {qty:g} {ticker}.")

    add_match = _ADD_RE.search(user_message)
    if add_match:
        ticker = add_match.group("ticker").upper()
        if ticker not in _STOPWORDS and not _is_trade_ticker(trades, ticker):
            watchlist_changes.append(LLMWatchlistChange(ticker=ticker, action="add"))
            parts.append(f"Adding {ticker} to your watchlist.")

    remove_match = _REMOVE_RE.search(user_message)
    if remove_match:
        ticker = remove_match.group("ticker").upper()
        if ticker not in _STOPWORDS:
            watchlist_changes.append(LLMWatchlistChange(ticker=ticker, action="remove"))
            parts.append(f"Removing {ticker} from your watchlist.")

    if not parts:
        cash = portfolio.get("cash_balance", 0.0)
        n_positions = len(portfolio.get("positions", []))
        parts.append(
            f"[mock] You said: {user_message!r}. You have ${cash:,.2f} in cash "
            f"across {n_positions} position(s)."
        )

    return LLMResponse(
        message=" ".join(parts),
        trades=trades,
        watchlist_changes=watchlist_changes,
    )


def _is_trade_ticker(trades: list[LLMTrade], ticker: str) -> bool:
    """True if `ticker` already appears as a trade (avoid double-matching 'add')."""
    return any(t.ticker == ticker for t in trades)
