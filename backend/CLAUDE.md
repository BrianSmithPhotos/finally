# Backend — Developer Guide

## Project Setup

```bash
cd backend
uv sync --extra dev   # Install all dependencies including test/lint tools
```

## Market Data API

The market data subsystem lives in `app/market/`. Use these imports:

```python
from app.market import PriceCache, PriceUpdate, MarketDataSource, create_market_data_source
```

### Core Types

- **`PriceUpdate`** — Immutable dataclass: `ticker`, `price`, `previous_price`, `timestamp`, plus properties `change`, `change_percent`, `direction` ("up"/"down"/"flat"), and `to_dict()` for JSON serialization.

- **`PriceCache`** — Thread-safe in-memory store. Key methods:
  - `update(ticker, price, timestamp=None) -> PriceUpdate`
  - `get(ticker) -> PriceUpdate | None`
  - `get_price(ticker) -> float | None`
  - `get_all() -> dict[str, PriceUpdate]`
  - `remove(ticker)`
  - `version` property — monotonic counter, increments on every update (for SSE change detection)

- **`MarketDataSource`** — Abstract interface implemented by `SimulatorDataSource` and `MassiveDataSource`. Lifecycle: `start(tickers)` -> `add_ticker()` / `remove_ticker()` -> `stop()`.

- **`create_market_data_source(cache)`** — Factory. Returns `MassiveDataSource` if `MASSIVE_API_KEY` is set, otherwise `SimulatorDataSource`.

### SSE Streaming

```python
from app.market import create_stream_router

router = create_stream_router(price_cache)  # Returns FastAPI APIRouter
# Endpoint: GET /api/stream/prices (text/event-stream)
```

### Seed Data

Default tickers: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX. Seed prices and per-ticker volatility/drift params are in `app/market/seed_prices.py`.

## Database API

The database layer lives in `app/db/`. SQLite (stdlib `sqlite3`, no ORM), single file,
lazily initialized — schema is created and seed data inserted automatically on first
connection. Use these imports:

```python
from app.db import (
    get_database, Database,
    UserProfile, WatchlistEntry, Position, Trade, PortfolioSnapshot, ChatMessage,
    get_user_profile, update_cash_balance, adjust_cash_balance,
    get_watchlist, add_watchlist_ticker, remove_watchlist_ticker,
    get_positions, get_position, upsert_position, apply_buy, apply_sell, delete_position,
    insert_trade, get_trades,
    insert_portfolio_snapshot, get_portfolio_snapshots,
    insert_chat_message, get_chat_messages,
)
```

### Getting a connection

- **`get_database() -> Database`** — process-wide singleton; call this in route handlers
  and other app code rather than constructing `Database()` directly, so the whole app
  shares one underlying sqlite3 connection.
- **`Database(db_path=None)`** — construct directly only for tests/scripts that need an
  isolated file (e.g. `Database(tmp_path / "test.db")`). Thread-safe: wraps a single
  `sqlite3` connection (`check_same_thread=False`) behind an internal lock.
- DB file path resolution: `DB_PATH` env var if set and non-blank, else
  `<repo_root>/db/finally.db` (the Docker volume mount target per PLAN.md §4).

Every CRUD function below takes the `Database` instance as its first positional arg and
an optional `user_id: str = "default"` keyword (this is a single-user app; the column
exists for future multi-user support).

### Schema (see PLAN.md §7 for the authoritative spec)

`users_profile(id, cash_balance, created_at)` ·
`watchlist(id, user_id, ticker, added_at)` UNIQUE(user_id, ticker) ·
`positions(id, user_id, ticker, quantity, avg_cost, updated_at)` UNIQUE(user_id, ticker) ·
`trades(id, user_id, ticker, side, quantity, price, executed_at)` ·
`portfolio_snapshots(id, user_id, total_value, recorded_at)` ·
`chat_messages(id, user_id, role, content, actions, created_at)`

Seed data: one profile (`id="default"`, `cash_balance=10000.0`) and watchlist entries
for AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX.

### Return types

Frozen dataclasses, one per table: `UserProfile`, `WatchlistEntry`, `Position`, `Trade`,
`PortfolioSnapshot`, `ChatMessage` (field names match the schema columns exactly). No ORM
models — plain `sqlite3.Row` mapped to dataclasses internally.

### Functions

- **Users**: `get_user_profile(db, user_id=...) -> UserProfile | None` ·
  `update_cash_balance(db, cash_balance, user_id=...) -> UserProfile | None` (sets an
  absolute value) · `adjust_cash_balance(db, delta, user_id=...) -> UserProfile | None`
  (adds/subtracts a delta — use this for trade settlement)

- **Watchlist**: `get_watchlist(db, user_id=...) -> list[WatchlistEntry]` ·
  `add_watchlist_ticker(db, ticker, user_id=...) -> WatchlistEntry | None` (returns
  `None` on a duplicate, does not raise) ·
  `remove_watchlist_ticker(db, ticker, user_id=...) -> bool`

- **Positions**: `get_positions(db, user_id=...) -> list[Position]` ·
  `get_position(db, ticker, user_id=...) -> Position | None` ·
  `upsert_position(db, ticker, quantity, avg_cost, user_id=...) -> Position` (direct
  write, no math — use for corrections/tests) ·
  `apply_buy(db, ticker, quantity, price, user_id=...) -> Position` (weighted-average
  cost-basis bookkeeping for a buy; creates the position if new) ·
  `apply_sell(db, ticker, quantity, user_id=...) -> Position | None` (reduces quantity,
  cost basis unchanged; deletes the row and returns `None` once quantity hits ~0) ·
  `delete_position(db, ticker, user_id=...) -> bool`

  Note: `apply_buy`/`apply_sell` only do bookkeeping math — they do **not** validate
  cash balance or share count. Callers (API routes / LLM trade execution) must validate
  before calling, and should pair a buy/sell with `adjust_cash_balance` and `insert_trade`.

- **Trades**: `insert_trade(db, ticker, side, quantity, price, user_id=...) -> Trade`
  (`side` is `"buy"` or `"sell"`) ·
  `get_trades(db, user_id=..., limit=None) -> list[Trade]` (most-recent-first)

- **Snapshots**: `insert_portfolio_snapshot(db, total_value, user_id=...) -> PortfolioSnapshot` ·
  `get_portfolio_snapshots(db, user_id=..., limit=None) -> list[PortfolioSnapshot]`
  (chronological order; `limit` keeps the most recent N, still chronological — ready to
  feed straight into a chart)

- **Chat**: `insert_chat_message(db, role, content, actions=None, user_id=...) -> ChatMessage`
  (`role` is `"user"` or `"assistant"`; `actions` is a JSON string or `None`) ·
  `get_chat_messages(db, user_id=..., limit=None) -> list[ChatMessage]` (chronological,
  same `limit` semantics as snapshots)

### Tests

Unit tests in `tests/db/` use a `db` fixture (see `tests/db/conftest.py`) that builds a
`Database` against a `tmp_path` file per test — no shared state, no real filesystem
pollution of the repo's `db/` directory.

## Running Tests

```bash
uv run --extra dev pytest -v              # All tests
uv run --extra dev pytest --cov=app       # With coverage
uv run --extra dev ruff check app/ tests/ # Lint
```

## Demo

```bash
uv run market_data_demo.py   # Live terminal dashboard with simulated prices
```
