"""Portfolio REST endpoints (PLAN.md Section 8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    HistoryResponse,
    PortfolioResponse,
    TradeRequest,
    TradeResponse,
)
from app.db import Database
from app.dependencies import get_cache, get_db
from app.market import PriceCache
from app.services import TradeError, build_portfolio, execute_trade

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioResponse)
def get_portfolio(
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
) -> PortfolioResponse:
    """Current positions (with live price + P&L), cash, and total value."""
    return PortfolioResponse(**build_portfolio(db, cache))


@router.post("/trade", response_model=TradeResponse)
def post_trade(
    body: TradeRequest,
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
) -> TradeResponse:
    """Execute a market order at the current price. Instant fill, no fees."""
    try:
        result = execute_trade(
            db,
            cache,
            ticker=body.ticker,
            quantity=body.quantity,
            side=body.side,
        )
    except TradeError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc
    return TradeResponse(**result)


@router.get("/history", response_model=HistoryResponse)
def get_history(
    limit: int | None = None,
    db: Database = Depends(get_db),
) -> HistoryResponse:
    """Portfolio value snapshots over time (oldest-first) for the P&L chart."""
    snapshots = db.list_snapshots(limit=limit)
    return HistoryResponse(snapshots=snapshots)
