"""Pydantic request/response models for the REST API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------
class PositionView(BaseModel):
    """A single holding enriched with live price and unrealized P&L."""

    ticker: str
    quantity: float
    avg_cost: float
    current_price: float | None = None
    cost_basis: float
    market_value: float | None = None
    unrealized_pnl: float | None = None
    change_percent: float | None = None


class PortfolioResponse(BaseModel):
    cash_balance: float
    positions: list[PositionView]
    positions_value: float
    total_value: float
    total_unrealized_pnl: float


class TradeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, description="Ticker symbol, e.g. AAPL")
    quantity: float = Field(..., gt=0, description="Number of shares (fractional allowed)")
    side: Literal["buy", "sell"]

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("ticker must be a non-empty symbol")
        return cleaned


class TradeView(BaseModel):
    id: str
    ticker: str
    side: str
    quantity: float
    price: float
    executed_at: str


class TradeResponse(BaseModel):
    trade: TradeView
    portfolio: PortfolioResponse


class SnapshotView(BaseModel):
    id: str
    total_value: float
    recorded_at: str


class HistoryResponse(BaseModel):
    snapshots: list[SnapshotView]


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------
class WatchlistItem(BaseModel):
    ticker: str
    price: float | None = None
    previous_price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    direction: str = "flat"


class WatchlistResponse(BaseModel):
    watchlist: list[WatchlistItem]


class WatchlistAddRequest(BaseModel):
    ticker: str = Field(..., min_length=1)

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("ticker must be a non-empty symbol")
        return cleaned


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = "ok"
