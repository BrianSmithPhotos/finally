# Massive API Reference (formerly Polygon.io)

Verified reference documentation for the Massive REST API, for use in FinAlly's market data layer. Massive is the May 2026 client/branding successor to Polygon.io — Polygon.io rebranded to Massive on 2025-10-30. Existing Polygon.io API keys and accounts continue to work unchanged.

Sources: [massive-com/client-python](https://github.com/massive-com/client-python), [massive.com/docs](https://massive.com/docs/rest/stocks/overview), [Polygon.io is Now Massive](https://massive.com/blog/polygon-is-now-massive).

## Overview

- **Base URL**: `https://api.massive.com` (legacy `https://api.polygon.io` still works, planned for eventual deprecation)
- **Python package**: `massive` — install via `pip install -U massive` / `uv add massive`
- **Auth**: API key passed to `RESTClient(api_key=...)`, or read automatically from the `POLYGON_API_KEY` / `MASSIVE_API_KEY` environment variable depending on client version — pass it explicitly to avoid ambiguity
- **Auth header**: `Authorization: Bearer <API_KEY>` (handled by the client)

## Rate Limits

| Tier | Limit |
|------|-------|
| Free | 5 requests/minute |
| Paid (all tiers) | Unlimited; recommended to stay under 100 req/s to avoid throttling |

For FinAlly, we poll on a timer. Free tier: poll every 15s. Paid: poll every 2-5s.

## Client Initialization

```python
from massive import RESTClient

client = RESTClient(api_key="your_key_here")
```

## Endpoints Used in FinAlly

### 1. Full Market Snapshot — Multiple Tickers (Primary Endpoint)

Gets current market data for multiple tickers in a **single API call**. This is the endpoint we poll on a timer.

**REST**: `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,MSFT`

Query parameters:
- `tickers` — case-sensitive comma-separated ticker list (e.g. `AAPL,TSLA,GOOG`). Omit to get the whole market (10,000+ tickers) — always pass an explicit list for FinAlly's small watchlist.
- `include_otc` — include OTC securities, default `false`.

Snapshot data is cleared once per day (early morning ET) and repopulates as exchanges report new data.

**Python client**:
```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient(api_key="...")

snapshots = client.get_snapshot_all(
    market_type=SnapshotMarketType.STOCKS,   # "stocks" | "forex" | "crypto" | "indices"
    tickers=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
)

for snap in snapshots:
    print(f"{snap.ticker}: ${snap.last_trade.price}")
    print(f"  Today's change: {snap.todays_change} ({snap.todays_change_percent}%)")
    print(f"  Day OHLC: O={snap.day.open} H={snap.day.high} L={snap.day.low} C={snap.day.close}")
    print(f"  Prev close: {snap.prev_day.close}")
```

`get_snapshot_all` returns `List[TickerSnapshot]` (or raw `HTTPResponse` if `raw=True`).

**`TickerSnapshot` fields** (Python attribute names, snake_case — note the wire format is camelCase, e.g. `lastTrade`/`prevDay`, but the client deserializes to snake_case):

| Attribute | Type | Notes |
|---|---|---|
| `ticker` | `str` | Symbol |
| `day` | `Agg` | Current day's aggregate bar |
| `prev_day` | `Agg` | Previous trading day's aggregate bar |
| `min` | `MinuteSnapshot` | Most recent minute bar |
| `last_trade` | `LastTrade` | Most recent trade (plan-dependent) |
| `last_quote` | `LastQuote` | Most recent NBBO quote (plan-dependent) |
| `todays_change` | `float` | Absolute change vs previous close |
| `todays_change_percent` | `float` | Percent change vs previous close |
| `updated` | `int` | Last-updated timestamp (ns) |
| `fair_market_value` | `float` | Business-plan tier only |

**`Agg` fields** (used for both `day` and `prev_day`): `open`, `high`, `low`, `close`, `volume`, `vwap`, `timestamp` (Unix ms), `transactions`, `otc`.

**`LastTrade` fields** (subset we use): `price`, `size`, `exchange` (int exchange code), `sip_timestamp`, `participant_timestamp`.

Important correction vs. older internal notes: there is **no `previous_close` field nested inside `day`** — the previous close lives in the separate `prev_day` aggregate, and the day-over-day change is `todays_change` / `todays_change_percent` on the snapshot itself, not on `day`.

### 2. Single Ticker Snapshot

For detailed data on one ticker (e.g., the detail chart view when a user clicks a ticker).

**REST**: `GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}`

**Python client**:
```python
snapshot = client.get_snapshot_ticker(
    market_type=SnapshotMarketType.STOCKS,
    ticker="AAPL",
)

print(f"Price: ${snapshot.last_trade.price}")
print(f"Bid/Ask: ${snapshot.last_quote.bid_price} / ${snapshot.last_quote.ask_price}")
print(f"Day range: ${snapshot.day.low} - ${snapshot.day.high}")
```

Returns a single `TickerSnapshot` (not a list).

### 3. Previous Close

Gets the previous trading day's OHLC for a single ticker. Useful for seeding initial prices or computing baseline change when a fresh snapshot lacks `prev_day`.

**REST**: `GET /v2/aggs/ticker/{ticker}/prev`

**Python client**:
```python
prev = client.get_previous_close_agg(ticker="AAPL", adjusted=True)

print(f"Previous close: ${prev.close}")
print(f"OHLC: O={prev.open} H={prev.high} L={prev.low} C={prev.close}")
print(f"Volume: {prev.volume}")
```

`get_previous_close_agg` returns a **single `PreviousCloseAgg` object**, not a list — this differs from `list_aggs`/`get_snapshot_all`, which return iterables. Fields: `ticker`, `open`, `high`, `low`, `close`, `volume`, `vwap`, `timestamp`.

### 4. Aggregates (Bars)

Historical OHLCV bars over a date range. Not needed for live polling but useful for historical chart backfill.

**REST**: `GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}`

**Python client**:
```python
aggs = client.get_aggs(
    "AAPL",
    1,
    "day",
    "2024-01-01",
    "2024-01-31",
    limit=50000,
)

for a in aggs:
    print(f"t={a.timestamp} O={a.open} H={a.high} L={a.low} C={a.close} V={a.volume}")
```

`get_aggs` returns a paginated iterator of `Agg` objects (auto-paginates under the hood). `list_aggs` is the explicitly-paginated variant if you need direct control over pagination.

### 5. Last Trade / Last Quote

Individual endpoints for the most recent trade or NBBO quote on a single ticker — rarely needed once snapshots are in use, since snapshots already embed both.

```python
trade = client.get_last_trade(ticker="AAPL")
print(f"Last trade: ${trade.price} x {trade.size}")

quote = client.get_last_quote(ticker="AAPL")
print(f"Bid: ${quote.bid_price} x {quote.bid_size}")
print(f"Ask: ${quote.ask_price} x {quote.ask_size}")
```

## How FinAlly Uses the API

The Massive poller runs as a background asyncio task:

1. Collects all tickers from the watchlist
2. Calls `get_snapshot_all()` with those tickers (one API call covers the whole watchlist)
3. Extracts `last_trade.price` and `prev_day.close` from each snapshot
4. Writes to the shared in-memory price cache
5. Sleeps for the poll interval, then repeats

```python
import asyncio
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

async def poll_massive(api_key: str, get_tickers, price_cache, interval: float = 15.0):
    """Poll Massive API and update the price cache."""
    client = RESTClient(api_key=api_key)

    while True:
        tickers = get_tickers()
        if tickers:
            # client is synchronous; run in a thread so we don't block the event loop
            snapshots = await asyncio.to_thread(
                client.get_snapshot_all,
                market_type=SnapshotMarketType.STOCKS,
                tickers=tickers,
            )
            for snap in snapshots:
                if snap.last_trade is None:
                    continue
                price_cache.update(
                    ticker=snap.ticker,
                    price=snap.last_trade.price,
                    timestamp=snap.last_trade.sip_timestamp / 1e9 if snap.last_trade.sip_timestamp else None,
                )

        await asyncio.sleep(interval)
```

Note `sip_timestamp` is Unix **nanoseconds**, not milliseconds — divide by `1e9` for seconds (the legacy `/v2` snapshot JSON's `last_trade.timestamp` was milliseconds; the Python client's `sip_timestamp` attribute on the deserialized model is nanoseconds — confirm against the actual response if precision matters).

## Error Handling

The client raises exceptions for HTTP errors:
- **401**: Invalid API key
- **403**: Insufficient permissions (plan doesn't include the endpoint, e.g. real-time quotes on Starter)
- **429**: Rate limit exceeded (free tier: 5 req/min)
- **5xx**: Server errors

## Notes

- The snapshot endpoint returns data for **all requested tickers in one call** — critical for staying within free-tier rate limits
- Data recency depends on plan tier: Starter/Developer plans get 15-minute-delayed data; Advanced/Business plans get real-time
- `last_trade` / `last_quote` are only populated if the current plan includes trades/quotes — always null-check before accessing
- During market-closed hours, `last_trade.price` reflects the last traded price (may include after-hours)
- `day` resets at the start of each session; outside market hours its values may lag until new data arrives
