# API Layer — Contract for Downstream Agents

The REST/API layer (`backend/app/api/`, `backend/app/services/`,
`backend/app/main.py`) implements PLAN.md Section 8 (except chat) and owns all
portfolio/trade business logic. The chat endpoint (`/api/chat`) is owned by the
LLM Engineer and reuses the shared services seam documented below.

## Module map

| Module | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, lifespan wiring, static serving |
| `app/dependencies.py` | FastAPI deps exposing shared `app.state` (db, cache, source) |
| `app/services/portfolio.py` | Trade execution, valuation, P&L — the shared seam |
| `app/api/schemas.py` | Pydantic request/response models |
| `app/api/portfolio.py` | `/api/portfolio[...]` routes |
| `app/api/watchlist.py` | `/api/watchlist[...]` routes |
| `app/api/system.py` | `/api/health` |

## Routes

### Portfolio
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/portfolio` | — | `PortfolioResponse` |
| POST | `/api/portfolio/trade` | `{ticker, quantity, side}` | `TradeResponse` (200) / `{detail}` (400) |
| GET | `/api/portfolio/history?limit=` | — | `HistoryResponse` |

### Watchlist
| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/watchlist` | — | `WatchlistResponse` |
| POST | `/api/watchlist` | `{ticker}` | `WatchlistResponse` (201) |
| DELETE | `/api/watchlist/{ticker}` | — | `WatchlistResponse` (200) / 404 |

### System / Streaming (streaming owned by market subsystem)
| Method | Path | Response |
|---|---|---|
| GET | `/api/health` | `{status: "ok"}` |
| GET | `/api/stream/prices` | SSE (`text/event-stream`) |

## Response schemas (Pydantic, `app/api/schemas.py`)

```python
PositionView      = {ticker, quantity, avg_cost, current_price|None,
                     cost_basis, market_value|None, unrealized_pnl|None,
                     change_percent|None}
PortfolioResponse = {cash_balance, positions: [PositionView],
                     positions_value, total_value, total_unrealized_pnl}
TradeView         = {id, ticker, side, quantity, price, executed_at}
TradeResponse     = {trade: TradeView, portfolio: PortfolioResponse}
SnapshotView      = {id, total_value, recorded_at}
HistoryResponse   = {snapshots: [SnapshotView]}   # oldest-first
WatchlistItem     = {ticker, price|None, previous_price|None, change|None,
                     change_percent|None, direction}
WatchlistResponse = {watchlist: [WatchlistItem]}
```

Price-derived fields are `None` until the ticker has a price in the cache.
Positions with no live price fall back to cost basis in the valuation totals.

## Shared services seam (for the LLM Engineer)

Import the trade/portfolio logic so chat-initiated trades behave identically to
REST trades:

```python
from app.services import (
    TradeError,        # raised on bad input / funds / shares / missing price
    execute_trade,     # validated market order; persists trade + snapshot
    build_portfolio,   # full portfolio dict (positions + P&L + totals)
    build_watchlist,   # watchlist tickers enriched with live price
    record_snapshot,   # compute + persist a portfolio_snapshots row
)
```

Signatures:

```python
execute_trade(db: Database, cache: PriceCache, *,
              ticker: str, quantity: float, side: str) -> dict
    # side in {"buy","sell"}; returns {"trade": <row>, "portfolio": <dict>}
    # raises TradeError(message=str) on any failure (no state mutated).
    # Weighted-avg-cost on buys; deletes the position on sell-to-zero.

build_portfolio(db: Database, cache: PriceCache) -> dict
    # {cash_balance, positions:[...], positions_value, total_value,
    #  total_unrealized_pnl}

build_watchlist(db: Database, cache: PriceCache) -> list[dict]

record_snapshot(db: Database, cache: PriceCache) -> dict   # inserts a snapshot

# also exported: TradeError, normalize_ticker, build_position_view
```

### Reaching shared state from a router

Use the dependency accessors; do not create your own DB/cache:

```python
from fastapi import Depends
from app.dependencies import get_db, get_cache
from app.db import Database
from app.market import PriceCache
from app.services import execute_trade, build_portfolio, TradeError

@chat_router.post("/api/chat")
def chat(body, db: Database = Depends(get_db), cache: PriceCache = Depends(get_cache)):
    portfolio = build_portfolio(db, cache)        # context for the LLM prompt
    try:
        execute_trade(db, cache, ticker="AAPL", quantity=10, side="buy")
    except TradeError as e:
        ...  # include e.message in the chat reply
```

The shared singletons live on `app.state` (`db`, `price_cache`,
`market_source`), created in `main.py`'s lifespan.

## Registering the chat router

In `app/main.py`, `create_app()` registers API routers BEFORE the static
catch-all mount. Add the chat router at the marked spot:

```python
# app/main.py, inside create_app(), before _mount_static(app):
from app.chat import chat_router
app.include_router(chat_router)
```

Keep the prefix `/api/...` so it is matched before the SPA fallback.

## main.py startup wiring (summary)

Lifespan startup:
1. `get_database()` — lazy init + seed.
2. Create one shared `PriceCache` → `app.state.price_cache`.
3. `create_market_data_source(cache)` → `app.state.market_source`; `start()`
   with `db.list_watchlist_tickers()`.
4. SSE stream router mounted via `create_stream_router(...)`.
5. Background task records a `portfolio_snapshots` row every 30s
   (`SNAPSHOT_INTERVAL_SECONDS`).

Shutdown: cancel the snapshot task, `await source.stop()`.

Static serving: files from `backend/static/` served at `/` with SPA fallback to
`index.html` for non-`/api` 404s. If `static/` is absent, it is skipped so the
API runs standalone in dev. API routers are always registered before the static
mount.

## Tests

`backend/tests/api/` (pytest + FastAPI `TestClient`). `conftest.py` injects a
temp-file `Database`, a pre-seeded `PriceCache`, and a `FakeMarketSource` onto
`app.state` (no real lifespan). 18 tests cover buy/sell happy paths, insufficient
cash/shares, weighted-avg-cost, sell-to-zero removal, totals/P&L, watchlist
add/remove, and health.
