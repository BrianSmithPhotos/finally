"""Structured output schema for LLM chat responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class TradeAction(BaseModel):
    """A single trade the LLM wants to auto-execute."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class WatchlistChange(BaseModel):
    """A single watchlist add/remove the LLM wants to apply."""

    ticker: str
    action: Literal["add", "remove"]


class ChatResponse(BaseModel):
    """Structured response returned by get_chat_response.

    `message` is always present. `trades` and `watchlist_changes` default to
    empty lists when the LLM has nothing to execute, or when a response could
    not be parsed and a fallback message-only response is returned instead.
    """

    message: str
    trades: list[TradeAction] = []
    watchlist_changes: list[WatchlistChange] = []
