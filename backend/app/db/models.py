"""Data models for the database layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserProfile:
    """A user's account state (single-user app; id is always 'default')."""

    id: str
    cash_balance: float
    created_at: str


@dataclass(frozen=True, slots=True)
class WatchlistEntry:
    """A ticker the user is watching."""

    id: str
    user_id: str
    ticker: str
    added_at: str


@dataclass(frozen=True, slots=True)
class Position:
    """A current holding (one row per ticker per user)."""

    id: str
    user_id: str
    ticker: str
    quantity: float
    avg_cost: float
    updated_at: str


@dataclass(frozen=True, slots=True)
class Trade:
    """A single executed trade (append-only log entry)."""

    id: str
    user_id: str
    ticker: str
    side: str  # "buy" or "sell"
    quantity: float
    price: float
    executed_at: str


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    """Total portfolio value at a point in time, for the P&L chart."""

    id: str
    user_id: str
    total_value: float
    recorded_at: str


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """A single message in the conversation history with the LLM."""

    id: str
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    actions: str | None  # JSON string of executed actions, or None
    created_at: str
