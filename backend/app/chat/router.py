"""Chat REST endpoint (PLAN.md Section 9): ``POST /api/chat``."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.chat.schemas import ChatRequest, ChatResponse
from app.chat.service import handle_chat
from app.db import Database
from app.dependencies import get_cache, get_db, get_market_source
from app.market import MarketDataSource, PriceCache

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
    source: MarketDataSource = Depends(get_market_source),
) -> ChatResponse:
    """Send a user message; receive the assistant reply plus executed actions.

    Auto-executes any trades / watchlist changes the assistant returns. Trade
    validation failures are surfaced inline (per-action ``error``) rather than
    failing the request, so the assistant can explain them to the user.
    """
    return await handle_chat(
        db,
        cache,
        source.add_ticker,
        source.remove_ticker,
        body.message,
    )
