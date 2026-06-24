"""Schemas for the chat endpoint and the LLM structured output (PLAN.md §9).

Two layers of models:

* ``LLMResponse`` / ``LLMTrade`` / ``LLMWatchlistChange`` — the *structured
  output* contract handed to the model. Kept deliberately small and matching
  the §9 schema exactly so the model can reliably populate it.
* ``ChatRequest`` / ``ChatResponse`` plus the enriched ``TradeResult`` /
  ``WatchlistResult`` — the HTTP request/response shape returned to the
  frontend, where each action carries an execution status the UI can render.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# LLM structured-output contract (what the model fills in)
# ---------------------------------------------------------------------------
class LLMTrade(BaseModel):
    """A trade the assistant wants to execute."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float


class LLMWatchlistChange(BaseModel):
    """A watchlist modification the assistant wants to apply."""

    ticker: str
    action: Literal["add", "remove"]


class LLMResponse(BaseModel):
    """Structured output the LLM must return (PLAN.md §9 schema)."""

    message: str = Field(..., description="Conversational response shown to the user")
    trades: list[LLMTrade] = Field(default_factory=list)
    watchlist_changes: list[LLMWatchlistChange] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# HTTP request / response (what the frontend sends and receives)
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User chat message")

    @field_validator("message")
    @classmethod
    def _non_blank(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("message must not be blank")
        return cleaned


class TradeResult(BaseModel):
    """A trade the assistant requested, enriched with execution status."""

    ticker: str
    side: str
    quantity: float
    status: Literal["executed", "error"]
    price: float | None = None
    executed_at: str | None = None
    error: str | None = None


class WatchlistResult(BaseModel):
    """A watchlist change the assistant requested, enriched with status."""

    ticker: str
    action: str
    status: Literal["added", "removed", "noop", "error"]
    error: str | None = None


class ChatResponse(BaseModel):
    """Response returned to the frontend.

    Top-level shape stays faithful to §9 (``message`` / ``trades`` /
    ``watchlist_changes``); each action item additionally carries a status so
    the UI can render inline confirmations.
    """

    message: str
    trades: list[TradeResult] = Field(default_factory=list)
    watchlist_changes: list[WatchlistResult] = Field(default_factory=list)
