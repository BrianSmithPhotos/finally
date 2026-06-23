"""Chat route: send a message to the LLM assistant, auto-execute its actions.

Integrates against app.llm.chat.get_chat_response (owned by the LLM Engineer):

    async def get_chat_response(
        message: str, portfolio_context: dict, history: list[dict]
    ) -> ChatResponse

`ChatResponse` is a pydantic model with `message: str`, `trades: list[...]`,
`watchlist_changes: list[...]` per PLAN.md §9. Trades/watchlist changes are
auto-executed through the same validation as manual requests; failures are
reported back in the response rather than raising, so the LLM can relay the
failure to the user.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from app.db import (
    Database,
    add_watchlist_ticker,
    get_chat_messages,
    insert_chat_message,
    remove_watchlist_ticker,
)
from app.llm.chat import get_chat_response
from app.market import MarketDataSource, PriceCache

from .dependencies import get_db, get_market_source, get_price_cache
from .portfolio_service import portfolio_context_dict
from .schemas import ChatRequest, ChatResponseView, TradeActionResult, WatchlistActionResult
from .trading import TradeError, execute_trade

router = APIRouter(prefix="/api/chat", tags=["chat"])

HISTORY_LIMIT = 20


def _history_as_dicts(db: Database) -> list[dict]:
    messages = get_chat_messages(db, limit=HISTORY_LIMIT)
    return [{"role": m.role, "content": m.content} for m in messages]


async def _execute_trades(
    db: Database, price_cache: PriceCache, trades: list
) -> list[TradeActionResult]:
    results = []
    for t in trades:
        ticker = t.ticker if hasattr(t, "ticker") else t["ticker"]
        side = t.side if hasattr(t, "side") else t["side"]
        quantity = t.quantity if hasattr(t, "quantity") else t["quantity"]
        try:
            result = execute_trade(db, price_cache, ticker, side, quantity)
            results.append(
                TradeActionResult(
                    ticker=result.ticker,
                    side=result.side,
                    quantity=result.quantity,
                    price=result.price,
                )
            )
        except TradeError as exc:
            results.append(
                TradeActionResult(
                    ticker=ticker, side=side, quantity=quantity, error=str(exc)
                )
            )
    return results


async def _apply_watchlist_changes(
    db: Database, market_source: MarketDataSource, changes: list
) -> list[WatchlistActionResult]:
    results = []
    for c in changes:
        ticker = (c.ticker if hasattr(c, "ticker") else c["ticker"]).upper()
        action = c.action if hasattr(c, "action") else c["action"]
        if action == "add":
            entry = add_watchlist_ticker(db, ticker)
            if entry is None:
                results.append(
                    WatchlistActionResult(
                        ticker=ticker, action=action, error=f"'{ticker}' already on watchlist"
                    )
                )
                continue
            await market_source.add_ticker(ticker)
            results.append(WatchlistActionResult(ticker=ticker, action=action))
        elif action == "remove":
            removed = remove_watchlist_ticker(db, ticker)
            if not removed:
                results.append(
                    WatchlistActionResult(
                        ticker=ticker, action=action, error=f"'{ticker}' not on watchlist"
                    )
                )
                continue
            await market_source.remove_ticker(ticker)
            results.append(WatchlistActionResult(ticker=ticker, action=action))
        else:
            results.append(
                WatchlistActionResult(
                    ticker=ticker, action=action, error=f"Unknown action '{action}'"
                )
            )
    return results


@router.post("", response_model=ChatResponseView)
async def chat(
    request: ChatRequest,
    db: Database = Depends(get_db),
    price_cache: PriceCache = Depends(get_price_cache),
    market_source: MarketDataSource = Depends(get_market_source),
) -> ChatResponseView:
    """Send a message to the LLM assistant; auto-execute any returned actions."""
    portfolio_context = portfolio_context_dict(db, price_cache)
    history = _history_as_dicts(db)

    insert_chat_message(db, role="user", content=request.message)

    llm_response = await get_chat_response(
        message=request.message, portfolio_context=portfolio_context, history=history
    )

    trade_results = await _execute_trades(db, price_cache, llm_response.trades)
    watchlist_results = await _apply_watchlist_changes(
        db, market_source, llm_response.watchlist_changes
    )

    actions = {
        "trades": [r.model_dump() for r in trade_results],
        "watchlist_changes": [r.model_dump() for r in watchlist_results],
    }
    insert_chat_message(
        db,
        role="assistant",
        content=llm_response.message,
        actions=json.dumps(actions) if (trade_results or watchlist_results) else None,
    )

    return ChatResponseView(
        message=llm_response.message,
        trades=trade_results,
        watchlist_changes=watchlist_results,
    )
