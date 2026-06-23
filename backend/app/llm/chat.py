"""Placeholder for the LLM Engineer's chat module.

This stub exists only so app.api.chat has a real module to import against
before the LLM Engineer's worktree merges. It will be overwritten with the
real implementation (LiteLLM -> OpenRouter -> Cerebras, structured outputs)
per PLAN.md §9. Do not build out chat logic here — this file is owned by the
LLM Engineer.
"""

from __future__ import annotations

from pydantic import BaseModel


class TradeAction(BaseModel):
    ticker: str
    side: str
    quantity: float


class WatchlistChange(BaseModel):
    ticker: str
    action: str


class ChatResponse(BaseModel):
    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistChange] = []


async def get_chat_response(
    message: str, portfolio_context: dict, history: list[dict]
) -> ChatResponse:
    raise NotImplementedError(
        "app.llm.chat.get_chat_response is a placeholder; the real "
        "implementation is owned by the LLM Engineer."
    )
