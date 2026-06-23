"""Pydantic request/response models for the API layer."""

from __future__ import annotations

from pydantic import BaseModel


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: str  # "buy" or "sell"


class PositionView(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float


class PortfolioResponse(BaseModel):
    cash_balance: float
    positions: list[PositionView]
    total_value: float
    total_unrealized_pnl: float


class PortfolioSnapshotView(BaseModel):
    total_value: float
    recorded_at: str


class WatchlistTickerView(BaseModel):
    ticker: str
    price: float | None
    previous_price: float | None
    change: float | None
    change_percent: float | None
    direction: str | None


class WatchlistRequest(BaseModel):
    ticker: str


class ChatRequest(BaseModel):
    message: str


class TradeActionResult(BaseModel):
    ticker: str
    side: str
    quantity: float
    price: float | None = None
    error: str | None = None


class WatchlistActionResult(BaseModel):
    ticker: str
    action: str
    error: str | None = None


class ChatResponseView(BaseModel):
    message: str
    trades: list[TradeActionResult]
    watchlist_changes: list[WatchlistActionResult]
