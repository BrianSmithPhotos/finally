# Market Data Interface Design

Unified Python interface for market data in FinAlly. Two implementations — simulator and Massive API — behind one abstract interface, selected by environment variable. All downstream code (SSE streaming, price cache, portfolio valuation, trade execution) is source-agnostic: it only ever talks to the `PriceCache`, never to a `MarketDataSource` implementation directly after startup.

See [MASSIVE_API.md](MASSIVE_API.md) for verified Massive API details and [MARKET_SIMULATOR.md](MARKET_SIMULATOR.md) for the simulator's internals.

## Core Data Model

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PriceUpdate:
    """A single price update for one ticker."""
    ticker: str
    price: float
    previous_price: float
    timestamp: float          # Unix seconds
    change: float             # price - previous_price
    direction: str            # "up", "down", or "flat"
```

This is the only data structure that leaves the market data layer. Everything downstream — SSE payloads, portfolio valuation, trade fills — works with `PriceUpdate` objects, not raw Massive snapshots or simulator internals.

## Abstract Interface

```python
from abc import ABC, abstractmethod

class MarketDataSource(ABC):
    """Abstract interface for market data providers."""

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates for the given tickers."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop producing price updates and clean up."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the active set."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of active tickers."""
```

Both implementations write to a shared `PriceCache` on their own schedule — the interface has no method that returns a price directly. This keeps `MassiveDataSource` (synchronous-client-in-a-thread, slow polling) and `SimulatorDataSource` (in-process, fast ticking) interchangeable despite very different internal timing.

## Price Cache

Shared in-memory store that both data sources write to and the SSE streamer / portfolio code reads from.

```python
import time
from threading import Lock

class PriceCache:
    """Thread-safe cache of latest prices per ticker."""

    def __init__(self):
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        with self._lock:
            ts = timestamp if timestamp is not None else time.time()
            previous = self._prices.get(ticker)
            previous_price = previous.price if previous else price

            if price > previous_price:
                direction = "up"
            elif price < previous_price:
                direction = "down"
            else:
                direction = "flat"

            update = PriceUpdate(
                ticker=ticker,
                price=price,
                previous_price=previous_price,
                timestamp=ts,
                change=price - previous_price,
                direction=direction,
            )
            self._prices[ticker] = update
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        with self._lock:
            return self._prices.get(ticker)

    def get_all(self) -> dict[str, PriceUpdate]:
        with self._lock:
            return dict(self._prices)

    def remove(self, ticker: str) -> None:
        with self._lock:
            self._prices.pop(ticker, None)
```

`Lock` (not `asyncio.Lock`) is deliberate: `MassiveDataSource` updates the cache from a thread-pool worker (via `asyncio.to_thread`), so the cache must be safe across real threads, not just coroutines.

## Factory Function

Select the data source at startup based on environment — this is the only place that branches on `MASSIVE_API_KEY`:

```python
import os

def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        from .massive_client import MassiveDataSource
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        from .simulator import SimulatorDataSource
        return SimulatorDataSource(price_cache=price_cache)
```

## Massive Implementation Sketch

```python
import asyncio
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

class MassiveDataSource(MarketDataSource):
    def __init__(self, api_key: str, price_cache: PriceCache, poll_interval: float = 15.0):
        self._client = RESTClient(api_key=api_key)
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._tickers = list(tickers)
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self._tickers:
            self._tickers.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _poll_loop(self) -> None:
        while True:
            await self._poll_once()
            await asyncio.sleep(self._interval)

    async def _poll_once(self) -> None:
        if not self._tickers:
            return
        # massive's RESTClient is synchronous; offload to a thread
        snapshots = await asyncio.to_thread(
            self._client.get_snapshot_all,
            market_type=SnapshotMarketType.STOCKS,
            tickers=self._tickers,
        )
        for snap in snapshots:
            if snap.last_trade is None or snap.last_trade.price is None:
                continue
            self._cache.update(ticker=snap.ticker, price=snap.last_trade.price)
```

Poll interval defaults to 15s to respect the free tier's 5 req/min limit (one request per poll regardless of watchlist size, since `get_snapshot_all` batches all tickers).

## Simulator Implementation Sketch

```python
import asyncio

class SimulatorDataSource(MarketDataSource):
    def __init__(self, price_cache: PriceCache, update_interval: float = 0.5):
        self._cache = price_cache
        self._interval = update_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._sim: GBMSimulator | None = None  # see MARKET_SIMULATOR.md

    async def start(self, tickers: list[str]) -> None:
        self._tickers = list(tickers)
        self._sim = GBMSimulator(tickers=self._tickers)
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            self._sim.add_ticker(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self._tickers = [t for t in self._tickers if t != ticker]
        self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _run_loop(self) -> None:
        while True:
            prices = self._sim.step()  # dict[str, float]
            for ticker, price in prices.items():
                self._cache.update(ticker=ticker, price=price)
            await asyncio.sleep(self._interval)
```

## Integration with SSE

The SSE endpoint reads from the `PriceCache` and pushes to connected clients:

```python
import json

async def price_stream(price_cache: PriceCache):
    while True:
        prices = price_cache.get_all()
        data = {
            ticker: {
                "ticker": p.ticker,
                "price": p.price,
                "previous_price": p.previous_price,
                "change": p.change,
                "direction": p.direction,
                "timestamp": p.timestamp,
            }
            for ticker, p in prices.items()
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(0.5)
```

## File Structure

```
backend/
  app/
    market/
      __init__.py
      models.py             # PriceUpdate dataclass
      interface.py           # MarketDataSource ABC, PriceCache
      factory.py             # create_market_data_source()
      massive_client.py      # MassiveDataSource
      simulator.py           # SimulatorDataSource + GBMSimulator
      seed_prices.py         # Default ticker seed prices
```

## Lifecycle

1. **App startup**: Create `PriceCache`, call `create_market_data_source(price_cache)`, then `await source.start(initial_tickers)`
2. **Watchlist changes**: Call `source.add_ticker()` / `source.remove_ticker()`
3. **SSE streaming**: Reads from `PriceCache.get_all()` every ~500ms
4. **Trade execution**: Reads current price from `PriceCache.get(ticker)`
5. **App shutdown**: `await source.stop()`

## Why This Split

- **Strategy pattern** keeps the Massive integration's polling cadence and threading concerns fully isolated from the simulator's tight in-process loop — neither implementation needs to know the other exists.
- **`PriceCache` as the single point of truth** decouples producers from consumers; the SSE layer, portfolio valuation, and trade execution never import `massive` or the simulator directly.
- Switching providers is a pure environment-variable change (`MASSIVE_API_KEY` set or unset) — no code change, no redeploy logic branching elsewhere in the app.
