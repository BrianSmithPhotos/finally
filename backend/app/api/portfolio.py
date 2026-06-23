"""Portfolio routes: positions, trade execution, value history."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db import Database, get_portfolio_snapshots

from .dependencies import get_db, get_price_cache
from .portfolio_service import build_portfolio_response
from .schemas import PortfolioResponse, PortfolioSnapshotView, TradeRequest
from .trading import TradeError, execute_trade

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(
    db: Database = Depends(get_db),
    price_cache=Depends(get_price_cache),
) -> PortfolioResponse:
    """Current positions, cash balance, total value, and unrealized P&L."""
    return build_portfolio_response(db, price_cache)


@router.post("/trade", response_model=PortfolioResponse)
async def trade(
    request: TradeRequest,
    db: Database = Depends(get_db),
    price_cache=Depends(get_price_cache),
) -> PortfolioResponse:
    """Execute a market order: instant fill at the current cache price."""
    try:
        execute_trade(db, price_cache, request.ticker, request.side, request.quantity)
    except TradeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_portfolio_response(db, price_cache)


@router.get("/history", response_model=list[PortfolioSnapshotView])
async def get_history(db: Database = Depends(get_db)) -> list[PortfolioSnapshotView]:
    """Portfolio value snapshots over time, for the P&L chart."""
    snapshots = get_portfolio_snapshots(db)
    return [
        PortfolioSnapshotView(total_value=s.total_value, recorded_at=s.recorded_at)
        for s in snapshots
    ]
