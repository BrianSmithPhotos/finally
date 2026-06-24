"""Chat orchestration: the request flow from PLAN.md §9.

`handle_chat` ties together the DB, services seam, and LLM client:

  1. Persist the user message.
  2. Build context (portfolio, watchlist, recent history).
  3. Call the LLM (or the deterministic mock when ``LLM_MOCK=true``).
  4. Auto-execute returned trades (validated via ``execute_trade``; failures are
     captured, not raised) and apply watchlist changes (DB + market source).
  5. Persist the assistant message with an ``actions`` JSON blob.
  6. Return a :class:`~app.chat.schemas.ChatResponse` enriched with per-action
     status for inline UI confirmations.

The watchlist/source apply step is async (the market source is async), so this
function is a coroutine; trade execution and DB work are sync and run inline.
"""

from __future__ import annotations

import json
import os
from typing import Awaitable, Callable

from app.chat.llm import call_llm
from app.chat.mock import mock_llm_response
from app.chat.schemas import (
    ChatResponse,
    LLMResponse,
    LLMTrade,
    LLMWatchlistChange,
    TradeResult,
    WatchlistResult,
)
from app.db import Database
from app.market import PriceCache
from app.services import TradeError, build_portfolio, build_watchlist, execute_trade

# How many prior messages to include as LLM context.
HISTORY_LIMIT = 20


def _llm_mock_enabled() -> bool:
    return os.environ.get("LLM_MOCK", "").strip().lower() == "true"


def _generate_llm_response(
    user_message: str,
    portfolio: dict,
    watchlist: list[dict],
    history: list[dict],
) -> LLMResponse:
    """Mock-or-real LLM response. Read at call time so env changes take effect."""
    if _llm_mock_enabled():
        return mock_llm_response(user_message, portfolio)
    return call_llm(portfolio, watchlist, history, user_message)


def _apply_trade(db: Database, cache: PriceCache, trade: LLMTrade) -> TradeResult:
    """Execute one LLM-requested trade, capturing validation errors."""
    try:
        result = execute_trade(
            db, cache, ticker=trade.ticker, quantity=trade.quantity, side=trade.side
        )
        row = result["trade"]
        return TradeResult(
            ticker=row["ticker"],
            side=row["side"],
            quantity=row["quantity"],
            status="executed",
            price=row["price"],
            executed_at=row["executed_at"],
        )
    except TradeError as exc:
        return TradeResult(
            ticker=(trade.ticker or "").strip().upper(),
            side=trade.side,
            quantity=trade.quantity,
            status="error",
            error=exc.message,
        )


async def _apply_watchlist_change(
    db: Database,
    add_ticker: Callable[[str], Awaitable[None]],
    remove_ticker: Callable[[str], Awaitable[None]],
    change: LLMWatchlistChange,
) -> WatchlistResult:
    """Apply one watchlist change to the DB and the market source."""
    ticker = (change.ticker or "").strip().upper()
    if not ticker:
        return WatchlistResult(
            ticker=change.ticker, action=change.action, status="error",
            error="Ticker must be a non-empty symbol.",
        )
    try:
        if change.action == "add":
            db.add_watchlist_ticker(ticker)  # idempotent
            await add_ticker(ticker)
            return WatchlistResult(ticker=ticker, action="add", status="added")
        else:  # remove
            removed = db.remove_watchlist_ticker(ticker)
            if removed:
                await remove_ticker(ticker)
                return WatchlistResult(ticker=ticker, action="remove", status="removed")
            return WatchlistResult(ticker=ticker, action="remove", status="noop")
    except Exception as exc:  # pragma: no cover - defensive
        return WatchlistResult(
            ticker=ticker, action=change.action, status="error", error=str(exc)
        )


async def handle_chat(
    db: Database,
    cache: PriceCache,
    add_ticker: Callable[[str], Awaitable[None]],
    remove_ticker: Callable[[str], Awaitable[None]],
    user_message: str,
) -> ChatResponse:
    """Run the full chat request flow and return the enriched response."""
    # 1. Persist user message.
    db.insert_chat_message("user", user_message)

    # 2. Build context.
    portfolio = build_portfolio(db, cache)
    watchlist = build_watchlist(db, cache)
    history = db.list_chat_messages(limit=HISTORY_LIMIT)

    # 3. Generate the LLM (or mock) response.
    llm = _generate_llm_response(user_message, portfolio, watchlist, history)

    # 4. Auto-execute trades, then apply watchlist changes.
    trade_results = [_apply_trade(db, cache, t) for t in llm.trades]
    watchlist_results = [
        await _apply_watchlist_change(db, add_ticker, remove_ticker, c)
        for c in llm.watchlist_changes
    ]

    # 5. Persist assistant message with an actions JSON blob.
    actions = {
        "trades": [r.model_dump() for r in trade_results],
        "watchlist_changes": [r.model_dump() for r in watchlist_results],
    }
    db.insert_chat_message("assistant", llm.message, actions=json.dumps(actions))

    # 6. Return the enriched response.
    return ChatResponse(
        message=llm.message,
        trades=trade_results,
        watchlist_changes=watchlist_results,
    )
