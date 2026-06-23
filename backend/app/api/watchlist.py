"""Watchlist routes: list with live prices, add, remove.

Add/remove also drive the running MarketDataSource so the in-process
simulator/poller starts (or stops) streaming the affected ticker, per
PLAN.md §8.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.db import Database, add_watchlist_ticker, get_watchlist, remove_watchlist_ticker
from app.market import MarketDataSource, PriceCache

from .dependencies import get_db, get_market_source, get_price_cache
from .schemas import WatchlistRequest, WatchlistTickerView

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def _ticker_view(price_cache: PriceCache, ticker: str) -> WatchlistTickerView:
    update = price_cache.get(ticker)
    if update is None:
        return WatchlistTickerView(
            ticker=ticker,
            price=None,
            previous_price=None,
            change=None,
            change_percent=None,
            direction=None,
        )
    return WatchlistTickerView(
        ticker=ticker,
        price=update.price,
        previous_price=update.previous_price,
        change=update.change,
        change_percent=update.change_percent,
        direction=update.direction,
    )


@router.get("", response_model=list[WatchlistTickerView])
async def list_watchlist(
    db: Database = Depends(get_db),
    price_cache: PriceCache = Depends(get_price_cache),
) -> list[WatchlistTickerView]:
    """Current watchlist tickers with their latest prices from the market cache."""
    entries = get_watchlist(db)
    return [_ticker_view(price_cache, entry.ticker) for entry in entries]


@router.post("", response_model=WatchlistTickerView, status_code=201)
async def add_to_watchlist(
    request: WatchlistRequest,
    db: Database = Depends(get_db),
    price_cache: PriceCache = Depends(get_price_cache),
    market_source: MarketDataSource = Depends(get_market_source),
) -> WatchlistTickerView:
    """Add a ticker to the watchlist and start streaming it."""
    ticker = request.ticker.upper()
    entry = add_watchlist_ticker(db, ticker)
    if entry is None:
        raise HTTPException(status_code=409, detail=f"'{ticker}' is already on the watchlist")
    await market_source.add_ticker(ticker)
    return _ticker_view(price_cache, ticker)


@router.delete("/{ticker}", status_code=204)
async def remove_from_watchlist(
    ticker: str,
    db: Database = Depends(get_db),
    market_source: MarketDataSource = Depends(get_market_source),
) -> None:
    """Remove a ticker from the watchlist and stop streaming it."""
    ticker = ticker.upper()
    removed = remove_watchlist_ticker(db, ticker)
    if not removed:
        raise HTTPException(status_code=404, detail=f"'{ticker}' is not on the watchlist")
    await market_source.remove_ticker(ticker)
