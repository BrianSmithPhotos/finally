"""Watchlist REST endpoints (PLAN.md Section 8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import WatchlistAddRequest, WatchlistResponse
from app.db import Database
from app.dependencies import get_cache, get_db, get_market_source
from app.market import MarketDataSource, PriceCache
from app.services import build_watchlist

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=WatchlistResponse)
def get_watchlist(
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
) -> WatchlistResponse:
    """Watchlist tickers with their latest cached price/change."""
    return WatchlistResponse(watchlist=build_watchlist(db, cache))


@router.post("", response_model=WatchlistResponse, status_code=201)
async def add_watchlist(
    body: WatchlistAddRequest,
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
    source: MarketDataSource = Depends(get_market_source),
) -> WatchlistResponse:
    """Add a ticker to the watchlist and start tracking its price."""
    ticker = body.ticker
    db.add_watchlist_ticker(ticker)  # idempotent
    await source.add_ticker(ticker)
    return WatchlistResponse(watchlist=build_watchlist(db, cache))


@router.delete("/{ticker}", response_model=WatchlistResponse)
async def delete_watchlist(
    ticker: str,
    db: Database = Depends(get_db),
    cache: PriceCache = Depends(get_cache),
    source: MarketDataSource = Depends(get_market_source),
) -> WatchlistResponse:
    """Remove a ticker from the watchlist and stop tracking it."""
    normalized = ticker.strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="Ticker must be a non-empty symbol.")
    removed = db.remove_watchlist_ticker(normalized)
    if not removed:
        raise HTTPException(
            status_code=404, detail=f"{normalized} is not in the watchlist."
        )
    await source.remove_ticker(normalized)
    return WatchlistResponse(watchlist=build_watchlist(db, cache))
