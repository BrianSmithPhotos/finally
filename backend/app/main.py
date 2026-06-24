"""FinAlly FastAPI application.

Wiring (lifespan startup):
  1. Initialize the SQLite database (lazy init + seed on first use).
  2. Create one shared `PriceCache`.
  3. Create the market data source via `create_market_data_source(cache)` and
     `start()` it with the current watchlist tickers.
  4. Mount the SSE stream router (`create_stream_router(cache)`).
  5. Launch a background task that records a `portfolio_snapshots` row every
     30 seconds.

Shutdown: cancel the snapshot task and `stop()` the market data source.

Router registration order matters: all `/api/*` routers (including the SSE
stream and the future chat router) are registered BEFORE the catch-all static
mount, so API routes always win over the SPA fallback.

Extending for chat (LLM Engineer): import your router and add it next to the
other `app.include_router(...)` calls below, before `_mount_static`. Reach
shared state via `app.dependencies.get_db` / `get_cache` and the
`app.services` helpers.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import portfolio_router, system_router, watchlist_router
from app.chat import chat_router
from app.db import get_database
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.services import record_snapshot

logger = logging.getLogger(__name__)

# Interval between automatic portfolio value snapshots (seconds).
SNAPSHOT_INTERVAL_SECONDS = 30.0

# static/ lives alongside the backend package root (backend/static), populated
# from the Next.js export at Docker build time.
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


async def _snapshot_loop(app: FastAPI, interval: float) -> None:
    """Record a portfolio value snapshot every `interval` seconds."""
    db = app.state.db
    cache = app.state.price_cache
    while True:
        try:
            await asyncio.sleep(interval)
            await asyncio.to_thread(record_snapshot, db, cache)
        except asyncio.CancelledError:
            break
        except Exception:  # pragma: no cover - defensive; keep the loop alive
            logger.exception("Failed to record portfolio snapshot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Database (lazy init + seed).
    db = get_database()
    app.state.db = db

    # 2. Shared price cache.
    price_cache = PriceCache()
    app.state.price_cache = price_cache

    # 3. Market data source, started with the current watchlist.
    source = create_market_data_source(price_cache)
    app.state.market_source = source
    tickers = db.list_watchlist_tickers()
    await source.start(tickers)
    logger.info("Market data source started with %d tickers", len(tickers))

    # 5. Background snapshot task.
    snapshot_task = asyncio.create_task(_snapshot_loop(app, SNAPSHOT_INTERVAL_SECONDS))
    app.state.snapshot_task = snapshot_task

    try:
        yield
    finally:
        snapshot_task.cancel()
        try:
            await snapshot_task
        except asyncio.CancelledError:
            pass
        await source.stop()
        logger.info("Market data source stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="FinAlly", version="0.1.0", lifespan=lifespan)

    # --- API routers (registered BEFORE static catch-all) ---
    app.include_router(system_router)
    app.include_router(portfolio_router)
    app.include_router(watchlist_router)

    # SSE stream router. The cache is created in lifespan, so this router reads
    # app.state.price_cache lazily via a thin wrapper.
    _mount_stream_router(app)

    # Chat router (LLM-backed; auto-executes trades/watchlist changes).
    app.include_router(chat_router)

    # --- Static frontend (catch-all, registered LAST) ---
    _mount_static(app)

    return app


def _mount_stream_router(app: FastAPI) -> None:
    """Mount the SSE stream router.

    `create_stream_router` needs a concrete PriceCache, but the cache is built
    in lifespan startup. We give it a lightweight proxy that forwards to
    app.state.price_cache once it exists.
    """

    class _CacheProxy:
        def __getattr__(self, name: str):
            return getattr(app.state.price_cache, name)

    app.include_router(create_stream_router(_CacheProxy()))


def _mount_static(app: FastAPI) -> None:
    """Serve the Next.js static export with SPA fallback to index.html.

    Skips gracefully when `static/` is absent so the API runs standalone in dev.
    """
    if not _STATIC_DIR.is_dir():
        logger.info("No static/ directory at %s; serving API only", _STATIC_DIR)
        return

    index_file = _STATIC_DIR / "index.html"

    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request, exc: StarletteHTTPException):
        # For non-API 404s, serve index.html so client-side routing works.
        if exc.status_code == 404 and not request.url.path.startswith("/api"):
            if index_file.is_file():
                return FileResponse(index_file)
        raise exc

    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
    logger.info("Serving static frontend from %s", _STATIC_DIR)


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )
