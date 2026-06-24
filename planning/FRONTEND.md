# FinAlly Frontend — Engineer Notes

The `frontend/` directory is a self-contained Next.js 14 (App Router) + TypeScript
project, built as a **static export** (`output: 'export'`). FastAPI serves the
resulting `out/` directory as static files on the same origin (port 8000), so the
frontend talks to the backend purely via same-origin `/api/*` REST endpoints and
the `/api/stream/prices` SSE stream — no CORS, no base URL.

This doc records the exact request/response shapes the frontend was coded
against so the Backend and LLM engineers can confirm alignment.

---

## Dev / Build / Test

```bash
cd frontend
npm install          # install deps
npm run dev          # dev server on :3000, proxies /api/* -> :8000 (see below)
npm run build        # static export -> frontend/out/
npm test             # vitest unit tests (run once)
npm run test:watch   # vitest watch mode
npm run lint         # next lint (eslint-config-next)
```

**Definition of done is green:** `npm run build` emits `out/index.html` with no
errors/warnings, `npm test` passes (24 tests), `npm run lint` is clean.

### Sandboxed/offline environments (note for CI & Docker)

- Fonts are **self-hosted** via `@fontsource/inter` and
  `@fontsource/jetbrains-mono` (bundled woff2). We deliberately do **not** use
  `next/font/google`, because it fetches from `fonts.gstatic.com` at build time,
  which fails in offline/sandboxed builds (including the Docker image build).
- If `npm install` fails with `EPERM` on `~/.npm/_cacache` in a restricted
  sandbox, point npm at a writable cache for that shell:
  `npm install --cache "$TMPDIR/npmcache" ...`. This is environment-specific and
  is **not** committed (`.npmrc` is gitignored).

### Local dev proxy

`next.config.mjs` adds a dev-only rewrite: in `development` it proxies
`/api/:path*` to `http://localhost:8000` (override with `BACKEND_ORIGIN`). This
lets the Next dev server (:3000) reach the FastAPI backend (:8000) while keeping
all client code same-origin. `output: 'export'` is incompatible with rewrites,
so export is applied only for production builds and the rewrite only for dev.

---

## Project structure

```
frontend/
├── next.config.mjs        # output:'export' (prod), dev-only /api proxy, images.unoptimized
├── tailwind.config.ts     # custom dark "phosphor-amber" terminal theme
├── vitest.config.ts       # jsdom + RTL test runner
├── src/
│   ├── app/
│   │   ├── layout.tsx      # fonts + globals
│   │   ├── globals.css     # theme tokens, flash keyframes, panel chrome
│   │   └── page.tsx        # single-page dense terminal grid
│   ├── lib/
│   │   ├── types.ts        # ALL backend contract types (authoritative on FE side)
│   │   ├── api.ts          # typed same-origin API client (fetch)
│   │   ├── format.ts       # USD / %, tabular display helpers
│   │   └── treemap.ts      # squarified treemap layout (heatmap)
│   ├── hooks/
│   │   ├── usePriceStream.ts  # EventSource SSE + reconnect + sparkline history
│   │   └── useTerminal.tsx    # app store/provider (portfolio, watchlist, chat, trades)
│   └── components/
│       ├── Header.tsx, ConnectionDot.tsx
│       ├── Watchlist.tsx, WatchlistRow.tsx   # price-flash lives here
│       ├── MainChart.tsx, PnlChart.tsx        # Recharts
│       ├── Heatmap.tsx                         # custom canvas-free treemap
│       ├── PositionsTable.tsx, TradeBar.tsx
│       ├── ChatPanel.tsx                       # collapsible AI sidebar
│       ├── Sparkline.tsx                       # canvas sparkline
│       └── Toast.tsx
└── *.test.tsx / *.test.ts  # colocated unit tests
```

### Key dependencies

| Purpose | Choice |
|---|---|
| Framework | Next.js 14 (App Router), static export |
| Charts (line/area) | Recharts 2 |
| Heatmap treemap | custom squarified layout (`src/lib/treemap.ts`) — full control over P&L color + labels |
| Sparklines | hand-rolled `<canvas>` (cheap re-renders at ~500ms tick rate) |
| Styling | Tailwind CSS 3, custom dark theme |
| Fonts | self-hosted JetBrains Mono (numeric/data) + Inter (UI) |
| Tests | Vitest 2 + React Testing Library + jsdom |

---

## How SSE + flash + sparklines work

- **SSE** (`usePriceStream`): native `EventSource` on `/api/stream/prices`.
  Connection state is mirrored to the header dot: `connecting` / `connected` /
  `reconnecting` / `disconnected`. EventSource auto-reconnects; we surface that
  as `reconnecting` (yellow) once a connection has previously succeeded.
- **Sparkline accumulation**: every SSE frame appends each ticker's latest
  price to a per-ticker array kept in the hook (bounded to 240 points). Charts
  and sparklines fill in progressively from page load — no historical fetch.
- **Price flash**: `WatchlistRow` tracks the previous price; on change it toggles
  a `flash-up` / `flash-down` CSS class (green/red background highlight that
  fades over ~500ms via a keyframe), then clears it. Unit-tested in isolation.

### Resilience to an unavailable backend

If `/api/*` calls fail (backend not up yet), the UI does not crash: the watchlist
falls back to the documented default seed (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA,
META, JPM, V, NFLX), charts show "accumulating…" empty states, and a banner
notes the backend is unreachable. Portfolio/history are polled every 15s and
recover automatically.

---

## API contract the frontend codes against (VERIFIED against backend code)

All paths are same-origin under `/api`. Request bodies are JSON. These shapes
are verified against the backend pydantic schemas (`app/api/schemas.py`,
`app/chat/schemas.py`), not just PLAN.md.

> **Envelopes:** several endpoints wrap their payload in a named key. The API
> client (`src/lib/api.ts`) unwraps/normalizes them so the rest of the app sees
> flat data. Endpoints that wrap: `GET/POST /api/watchlist` (`{watchlist}`),
> `POST /api/portfolio/trade` (`{trade, portfolio}`). `GET /api/portfolio` and
> `/history` are flat but use the field names below.

### SSE — `GET /api/stream/prices`

Authoritative shape taken from the backend's `PriceUpdate.to_dict()` and
`stream.py`. **Each SSE `message` event's `data` is a JSON MAP** keyed by ticker
(not one event per ticker):

```jsonc
data: {
  "AAPL": {
    "ticker": "AAPL",
    "price": 190.50,
    "previous_price": 190.10,
    "timestamp": 1719200000.123,   // unix seconds (float)
    "change": 0.40,
    "change_percent": 0.21,
    "direction": "up"              // "up" | "down" | "flat"
  },
  "GOOGL": { ... }
}
```

The client also tolerates a single-object frame (`{ticker, price, ...}`) just in
case, but the map form is the contract.

### `GET /api/portfolio`  (flat — `PortfolioResponse`)

```jsonc
{
  "cash_balance": 5000.0,
  "positions_value": 6000.0,
  "total_value": 11000.0,
  "total_unrealized_pnl": 200.0,        // NOTE: this name, not "unrealized_pnl"
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": 10,                   // fractional allowed
      "avg_cost": 180.0,
      "cost_basis": 1800.0,
      "current_price": 200.0,           // nullable until price cache is warm
      "market_value": 2000.0,           // nullable
      "unrealized_pnl": 200.0,          // nullable
      "change_percent": 11.1            // NOTE: this name, not "pnl_percent"
    }
  ]
}
```
> The client (`normalizePortfolio`) maps this onto the UI's `Portfolio`
> (`total_unrealized_pnl → unrealized_pnl`, `change_percent → pnl_percent`,
> nulls filled from cost basis). The UI then recomputes `current_price` /
> `unrealized_pnl` / `pnl_percent` live from SSE prices, so server price fields
> are a fallback only; `quantity` / `avg_cost` / `cash_balance` are authoritative.

### `POST /api/portfolio/trade`  (**nested** — `TradeResponse`)

Request: `{ "ticker": "AAPL", "quantity": 10, "side": "buy" }` (`side`: `"buy"|"sell"`).

Response nests the updated portfolio under `portfolio` alongside the executed
`trade` record:

```jsonc
{
  "trade": {
    "id": "uuid", "ticker": "AAPL", "side": "buy",
    "quantity": 10, "price": 200.0, "executed_at": "2026-06-24T12:00:00Z"
  },
  "portfolio": { /* same shape as GET /api/portfolio above */ }
}
```
The client returns `{ trade, portfolio: <normalized> }`; the UI sets the
portfolio from `.portfolio` and uses `.trade` for the toast confirmation. On
validation failure the backend returns a non-2xx `{"detail": "<reason>"}` — the
FE shows that text in a toast.

### `GET /api/portfolio/history`  (flat — `HistoryResponse`)

```jsonc
{
  "snapshots": [
    { "id": "uuid", "total_value": 10000.0, "recorded_at": "2026-06-24T12:00:00Z" },
    { "id": "uuid", "total_value": 10120.5, "recorded_at": "2026-06-24T12:00:30Z" }
  ]
}
```

### `GET /api/watchlist`  (**nested** — `WatchlistResponse`)

Wrapped in a `watchlist` key (NOT a bare array — the client unwraps it):

```jsonc
{
  "watchlist": [
    {
      "ticker": "AAPL", "price": 190.5, "previous_price": 190.1,
      "change": 0.4, "change_percent": 0.21, "direction": "up"
    },
    { "ticker": "GOOGL", "price": null, "direction": "flat" }
  ]
}
```

### `POST /api/watchlist`  (**nested** — `WatchlistResponse`)

Request: `{ "ticker": "PYPL" }`. Response: the **same `{watchlist: [...]}`
envelope** as GET (HTTP 201). The FE uppercases tickers before sending and the
client unwraps `.watchlist`.

### `DELETE /api/watchlist/{ticker}`

Path param ticker (uppercased by FE). Any 2xx (incl. `204`) is treated as
success; the FE removes optimistically and restores on failure. (Backend returns
404 `{"detail": ...}` if the ticker is not present.)

### `POST /api/chat`  (flat — `ChatResponse`)

Request: `{ "message": "buy 5 nvda" }`.

Response (faithful to §9 top-level shape; each action item carries a status so
the UI can render inline confirmations):

```jsonc
{
  "message": "Bought 5 NVDA at $120.50.",
  "trades": [
    {
      "ticker": "NVDA", "side": "buy", "quantity": 5,
      "status": "executed",       // "executed" | "error"
      "price": 120.50,            // nullable
      "executed_at": "2026-06-24T12:00:00Z",  // nullable
      "error": null               // shown in red when status == "error"
    }
  ],
  "watchlist_changes": [
    {
      "ticker": "PYPL", "action": "add",
      "status": "added",          // "added" | "removed" | "noop" | "error"
      "error": null
    }
  ]
}
```

`trades` / `watchlist_changes` default to `[]`. `message` is required. After a
chat response the FE re-fetches portfolio/history (if trades present) and
watchlist (if watchlist_changes present) to resync.

### `GET /api/health`

`{ "status": "ok" }` (used only for an optional liveness check).

---

## Contract notes (verified against backend)

1. **SSE frame is a MAP of all tickers per event** (not one event per ticker).
   ✅ confirmed against `backend/app/market/stream.py`. `timestamp` is unix
   seconds (float); SSE/positions use `change_percent` / `change`.
2. **Watchlist endpoints (GET + POST) return `{watchlist: [...]}`**, not a bare
   array. The client unwraps `.watchlist`. *(Was BUG-1: a bare-array assumption
   crashed `Watchlist.map`. Fixed + a top-level `ErrorBoundary` now prevents any
   single bad payload from unmounting the whole UI.)*
3. **`POST /api/portfolio/trade` nests the portfolio** under `.portfolio`
   (with `.trade`). The client reads `.portfolio`. *(Was BUG-2: `setPortfolio(body)`
   left `cash_balance` undefined and threw in `liveTotalValue`.)*
4. **Portfolio field names**: `total_unrealized_pnl` (not `unrealized_pnl`) and
   per-position `change_percent` (not `pnl_percent`); `current_price` /
   `market_value` / `unrealized_pnl` are nullable. The client normalizes these.
5. **Chat status enums** (verified `app/chat/schemas.py`): trades are
   `"executed" | "error"`; watchlist changes are
   `"added" | "removed" | "noop" | "error"`. The FE treats `"error"` as the
   failure state. *(Was BUG-3: FE checked `filled`/`rejected`.)*
6. **Trade `side`** is `"buy" | "sell"`; LLM watchlist `action` is `"add" |
   "remove"`.
7. **Error bodies**: the FE reads `detail` then `message` from a non-2xx JSON
   body for toast text. FastAPI's default `{"detail": ...}` works as-is.
8. **Session P&L baseline**: the header's "Session P&L" is computed FE-side as
   `total_value − $10,000` (the seed cash). No endpoint needed.
