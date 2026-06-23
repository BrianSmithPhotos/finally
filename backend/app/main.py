"""FastAPI app entrypoint: wires market data, database, routes, and static files."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import chat_router, health_router, portfolio_router, watchlist_router
from app.api.portfolio_service import build_portfolio_response
from app.db import get_database, get_watchlist, insert_portfolio_snapshot
from app.market import PriceCache, create_market_data_source, create_stream_router

logger = logging.getLogger(__name__)

SNAPSHOT_INTERVAL_SECONDS = 30
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


async def _snapshot_loop(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)
        try:
            db = app.state.db
            price_cache = app.state.price_cache
            total_value = build_portfolio_response(db, price_cache).total_value
            insert_portfolio_snapshot(db, total_value)
        except Exception:
            logger.exception("Failed to record periodic portfolio snapshot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_database()
    app.state.db = db

    tickers = [entry.ticker for entry in get_watchlist(db)]
    market_source = create_market_data_source(app.state.price_cache)
    await market_source.start(tickers)
    app.state.market_source = market_source

    snapshot_task = asyncio.create_task(_snapshot_loop(app), name="portfolio-snapshot-loop")

    try:
        yield
    finally:
        snapshot_task.cancel()
        try:
            await snapshot_task
        except asyncio.CancelledError:
            pass
        await market_source.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.state.price_cache = PriceCache()

    app.include_router(create_stream_router(app.state.price_cache))
    app.include_router(portfolio_router)
    app.include_router(watchlist_router)
    app.include_router(chat_router)
    app.include_router(health_router)

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


app = create_app()
