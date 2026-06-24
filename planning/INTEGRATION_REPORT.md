# FinAlly — Integration Test Report

**Date:** 2026-06-24
**Tester:** Integration Tester agent
**Suite:** `test/` Playwright project (`@playwright/test`, TypeScript)
**App under test:** FastAPI (`app.main:app`) serving the Next.js static export
from `backend/static`, single origin, port 8000.

---

## ✅ ROUND 2 RE-VERIFICATION (after Frontend fixes) — 15/15 PASS

**Status: ALL GREEN. No outstanding issues. No bugs remain.**

The Frontend Engineer fixed BUG-1, BUG-2, and BUG-3 (plus two bonus field-name
mismatches: portfolio `total_unrealized_pnl` and per-position `change_percent`)
via: `api.ts` unwrapping `.watchlist` (GET+POST) and `.portfolio`/`.trade` from
the trade response, a top-level React **error boundary**, chat status enums
aligned to `executed`/`error`, and a `normalizePortfolio` helper.

Re-ran the full suite against a freshly rebuilt frontend export served by the
backend (fresh seeded `$10,000` DB, `LLM_MOCK=true`):

| # | Scenario | Round 1 | Round 2 |
|---|---|---|---|
| API 0–7 | health, portfolio, watchlist, trade, chat, SSE shapes | PASS | **PASS** |
| 1 | Fresh start: 10 tickers, seeded cash, prices streaming | FAIL | **PASS** |
| 2 | Add / remove ticker via UI | FAIL | **PASS** |
| 3 | Buy: cash↓, position appears promptly | FAIL | **PASS** |
| 4 | Sell: cash↑, position updates/disappears | FAIL | **PASS** |
| 5 | Portfolio viz: heatmap + P&L chart render | FAIL | **PASS** |
| 6 | AI chat (mock) "buy 5 NVDA": inline confirm + portfolio update | FAIL | **PASS** |
| 7 | SSE resilience: prices keep updating live (dot `connected`) | FAIL | **PASS** |

**Result: 15/15 (8 API contract + 7 UI), green on two consecutive full runs.**

Confirmed working end-to-end in the browser:
- App **mounts cleanly** — no "Application error" screen (the only console error
  is a harmless `favicon.ico` 404). Screenshot: `test/artifacts/app-working-after-fix.png`
  (compare to the Round-1 crash: `test/artifacts/app-crash-onload.png`).
- **BUG-1 fixed:** watchlist renders the 10 default tickers; add/remove work and
  reflect immediately.
- **BUG-2 fixed:** a manual Buy decrements header cash and adds the position to
  the positions table promptly (no longer corrupts portfolio state); Sell
  reverses it.
- **BUG-3 fixed:** chat `buy 5 NVDA` renders the inline ✓ trade confirmation and
  the NVDA position + cash drop appear in the portfolio.
- Heatmap labels positions; the P&L chart renders an SVG with snapshot data.
- SSE: connection dot reaches `data-status="connected"`; AAPL price updates
  through multiple distinct values live.

### Test-suite adjustments made during re-verification (test-only, no product impact)

Three UI tests initially failed on Round 2 due to **test brittleness, not
product bugs** — fixed in `test/tests/ui-scenarios.spec.ts`:
1. Header cash / buy precision were hardcoded to exactly `$10,000`. Because the
   single-user backend shares one portfolio across tests and GBM price drift
   means buy→sell round-trips don't restore cash to *exactly* $10k, these now
   assert FE cash == live `/api/portfolio` cash within a sensible band, and
   buy/sell use **relative** (decrease/increase) assertions.
2. The connection-dot check keyed off `aria-label`/text; the dot exposes status
   via `data-status` (label is "LIVE"). Switched to `data-status="connected"`.

No frontend/backend code was touched. The suite is now idempotent across runs.

---

## How the app was run

Fast path (no Docker churn), per PLAN.md / launch notes:

1. `cd frontend && npm run build` → static export in `frontend/out`.
2. `cp -R frontend/out backend/static` (gitignored build artifact).
3. `cd backend && LLM_MOCK=true FINALLY_DB_PATH=$TMPDIR/finally-e2e.db MASSIVE_API_KEY="" .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`.
   Health check `GET /api/health` → `{"status":"ok"}`.
4. Drove the app at `http://127.0.0.1:8000` with Playwright (Chromium) and the
   Playwright MCP browser for interactive investigation.

A `test/docker-compose.test.yml` is also provided (app container + Playwright
runner image, wired to `LLM_MOCK=true`, ephemeral DB) for CI without browser
deps in the prod image. It was authored to spec; not executed in this sandbox
(Docker networking constrained) but is documented in `test/README.md`.

## Headline result

**The integrated app is currently unusable in the browser.** The SPA throws an
unhandled exception on initial load and React renders only Next.js's
"Application error: a client-side exception has occurred" screen — no header, no
watchlist, no trade bar, no chat. Root cause is the **watchlist response-shape
mismatch** (suspected mismatch #2), which is therefore a **real, severity-1
bug**. The **trade response-shape mismatch** (suspected mismatch #1) is also
**real** and confirmed by API probing + code; it would break the portfolio even
after the watchlist crash is fixed.

The backend REST/SSE API itself is healthy: every API-contract test passes, SSE
streams a correct ticker-keyed map with live price changes, and the LLM mock
behaves to contract.

## Per-scenario results

| # | Scenario (PLAN §12) | Result | Owner of failure |
|---|---|---|---|
| API-0 | `GET /api/health` | PASS | — |
| API-1 | `GET /api/portfolio` bare shape | PASS | — |
| API-2 | `GET /api/watchlist` shape | PASS* | — (documents mismatch) |
| API-3 | `POST /api/portfolio/trade` shape | PASS* | — (documents mismatch) |
| API-4 | `POST /api/watchlist` shape | PASS* | — (documents mismatch) |
| API-5 | `POST /api/chat` buy 5 NVDA (mock) | PASS | — |
| API-6 | `POST /api/chat` insufficient funds → inline error | PASS | — |
| API-7 | `GET /api/stream/prices` SSE map | PASS | — |
| 1 | Fresh start: 10 tickers, $10k, prices streaming | **FAIL** | Frontend (root cause: BUG-1) |
| 2 | Add / remove ticker via UI | **FAIL** | Frontend (root cause: BUG-1) |
| 3 | Buy shares: cash↓, position appears | **FAIL** | Frontend (BUG-1 blocks; BUG-2 underlying) |
| 4 | Sell shares: cash↑, position updates/disappears | **FAIL** | Frontend (BUG-1 blocks; BUG-2 underlying) |
| 5 | Portfolio viz: heatmap + P&L chart | **FAIL** | Frontend (root cause: BUG-1) |
| 6 | AI chat (mock): inline confirm + portfolio update | **FAIL** | Frontend (BUG-1 blocks; BUG-2 underlying) |
| 7 | SSE resilience: prices keep updating live | **FAIL** | Frontend (root cause: BUG-1) |

\* API-2/3/4 assert the backend's *actual* (nested) shapes and pass; their
purpose is to be the machine-checked evidence for BUG-1/BUG-2, not to enforce the
frontend's assumption.

All 7 UI scenarios fail at the same point: `expectAppMounted()` detects the
client-side exception screen. They are written to assert correct behavior and
will pass once the shapes are reconciled.

**Run summary:** API-contract spec — 8/8 pass. UI scenarios — 0/7 pass (all
blocked by BUG-1).

---

## Bug reports (routed to owning engineer)

### BUG-1 — [SEV-1] Watchlist response is nested `{watchlist:[...]}`; frontend expects a bare array → whole app crashes on load
**Owner: Frontend (primary) — see "Resolution options" for the Backend alternative.**

- **Symptom:** On loading `http://localhost:8000/`, the page shows only
  *"Application error: a client-side exception has occurred."* Nothing else
  renders. Console error:
  `TypeError: e.map is not a function` (minified `page-*.js`).
- **Evidence:**
  - Screenshot: `test/artifacts/app-crash-onload.png` and
    `test/artifacts/ui-fresh-start-failure.png`.
  - Live API: `GET /api/watchlist` →
    `{"watchlist":[{"ticker":"AAPL",...}, ...]}` (object, not array).
  - Code: `frontend/src/lib/api.ts` types `getWatchlist`/`addWatchlist` as
    `request<WatchlistEntry[]>` (a **bare array**), and
    `frontend/src/hooks/useTerminal.tsx` does `setWatchlist(wl)` then
    `frontend/src/components/Watchlist.tsx` calls `watchlist.map(...)`.
    `wl` is actually `{watchlist:[...]}`, so `.map` is undefined → unhandled
    throw → React tree unmounts (no error boundary).
  - Backend: `backend/app/api/watchlist.py` returns
    `WatchlistResponse(watchlist=...)` on GET, POST (201) and DELETE; schema in
    `backend/app/api/schemas.py` (`WatchlistResponse`).
- **Root-cause hypothesis:** Frontend↔backend contract drift. `FRONTEND.md`
  §"GET /api/watchlist" documents a bare array; `API_LAYER.md` documents
  `WatchlistResponse = {watchlist:[...]}`. They disagree. The backend shipped
  the nested envelope; the frontend coded against the bare array.
- **Resolution options (pick one, project-wide):**
  - **Frontend fix (recommended, smallest blast radius):** in `api.ts`, unwrap
    `.watchlist` from the GET/POST responses (and handle DELETE returning the
    nested object too). Also add an error boundary so a future shape drift
    degrades gracefully instead of white-screening.
  - **Backend fix:** return a bare array for watchlist endpoints (breaks
    `API_LAYER.md` and the 18 backend API unit tests that assert the envelope).
- **Recommendation:** Frontend unwraps. The backend envelope is consistent with
  its other responses and is unit-tested; changing the FE client is the cheaper,
  lower-risk fix. **Whoever owns the canonical contract should also reconcile
  `FRONTEND.md` vs `API_LAYER.md`.**

---

### BUG-2 — [SEV-1] Trade response is nested `{trade, portfolio}`; frontend treats it as a bare Portfolio → portfolio state corrupts after a manual trade
**Owner: Frontend (primary) — Backend alternative noted.**

- **Symptom:** Cannot be observed in the UI yet because BUG-1 prevents the app
  from mounting, but is confirmed by code + live API probing. After a manual
  Buy/Sell, the frontend would set `portfolio` to `{trade, portfolio}` (lacking
  top-level `cash_balance`/`positions`), so the header cash goes blank and the
  next render of `liveTotalValue` (`portfolio.positions.reduce(...)`) would throw
  on `positions` being `undefined`.
- **Evidence:**
  - Live API (in-browser fetch reproduction): `POST /api/portfolio/trade`
    `{ticker:"MSFT",quantity:1,side:"buy"}` →
    top-level keys `["trade","portfolio"]`; `body.cash_balance === undefined`;
    `body.portfolio.cash_balance === 9200.77`.
  - Code: `frontend/src/lib/api.ts` `trade()` is typed `request<Portfolio>`
    (bare); `useTerminal.executeTrade` does `setPortfolio(p)` and `sendChat`
    relies on a follow-up `refreshPortfolio()` (the `GET /api/portfolio` shape is
    fine, so chat-driven trades partially self-heal via the resync — but the
    manual TradeBar path uses the POST body directly).
  - Backend: `backend/app/api/portfolio.py` returns `TradeResponse(**result)` =
    `{trade: TradeView, portfolio: PortfolioResponse}` (`schemas.py`).
- **Root-cause hypothesis:** Same contract drift. `FRONTEND.md`
  §"POST /api/portfolio/trade" expects "the updated Portfolio object";
  `API_LAYER.md` defines `TradeResponse = {trade, portfolio}`. The backend
  shipped the nested envelope.
- **Resolution options:**
  - **Frontend fix (recommended):** in `api.ts` `trade()`, return
    `response.portfolio` (and optionally surface `response.trade` for a richer
    toast).
  - **Backend fix:** return the bare portfolio (breaks `API_LAYER.md` + backend
    API unit tests).
- **Recommendation:** Frontend unwraps `.portfolio`.

---

### BUG-3 — [SEV-3 / cosmetic] Chat trade `status` enum mismatch (`executed`/`error` vs `filled`/`rejected`)
**Owner: Contract owner (LLM ↔ Frontend) — confirm intended enum.**

- **Symptom:** No functional break today, but the FE and backend use different
  enum strings, which is fragile.
- **Evidence:**
  - Backend (`LLM_LAYER.md`, live `POST /api/chat`): trade `status` is
    `"executed"` | `"error"`; watchlist `status` is `"added"|"removed"|"noop"|"error"`.
  - Frontend (`frontend/src/lib/types.ts`, `ChatPanel.tsx`): `ExecutedTrade.status`
    typed `"filled"|"rejected"`; `TradeConfirm` computes `failed =
    status === 'rejected' || !!trade.error`.
  - Net effect: a successful trade (`status:"executed"`, `error:null`) → `failed`
    is false → renders ✓ (correct by luck). A failed trade (`status:"error"`,
    `error:"..."`) → `failed` true via `!!error` → renders ✕ (correct by luck).
    So it works **only because the FE also checks `!!error`**. If the backend ever
    omits `error` on a rejected trade, it would render as success.
- **Root-cause hypothesis:** Enum naming never unified between LLM_LAYER and
  FRONTEND docs.
- **Recommendation:** Align on one enum (LLM_LAYER's `executed/error` is the live
  contract). FE: update `types.ts` + `TradeConfirm`/`WatchConfirm` to key off
  `status === 'error'`. Low priority — works today.

---

### Non-issues confirmed (suspected mismatch #3 and others)

- **SSE frame shape — CORRECT.** `GET /api/stream/prices` emits a JSON **map
  keyed by ticker** per `message` event, each value
  `{ticker, price, previous_price, timestamp, change, change_percent, direction}`.
  Matches `FRONTEND.md` and `usePriceStream`. Verified live (2+ frames, fields
  present) via API-7 and in-browser EventSource. Streaming is continuous and
  prices change tick-to-tick. (The UI flash can't be observed yet due to BUG-1,
  but the data feeding it is correct.)
- **`GET /api/portfolio` shape — CORRECT.** Bare `PortfolioResponse`; matches FE.
- **LLM mock — CORRECT.** `buy 5 NVDA` → exactly one executed trade, cash
  decremented; over-buy → inline `status:"error"` (no 500); echo fallback shape
  per contract.
- **Health & static serving — CORRECT.** `/api/health` 200; `/` serves the SPA
  HTML (200, text/html).

---

## Are the two suspected mismatches real bugs?

**Yes, both are real.**

1. **Trade nesting (`{trade, portfolio}`)** — REAL (BUG-2). Confirmed by live API
   probe (`cash_balance` undefined at top level) and FE code (`api.trade` typed
   bare, `setPortfolio` consumes it directly). Currently masked only because
   BUG-1 stops the app from running.
2. **Watchlist nesting (`{watchlist:[...]}`)** — REAL and worse than suspected
   (BUG-1). It doesn't merely delay a UI update — it throws `e.map is not a
   function` and crashes the entire SPA on load.

Both stem from the same root cause: `FRONTEND.md` and `API_LAYER.md` describe
the trade/watchlist responses differently, and the two sides shipped to different
docs. Recommend fixing on the **frontend** (unwrap `.watchlist` / `.portfolio`),
adding a React **error boundary**, and reconciling the two contract docs so they
no longer disagree.

## Prioritized fix list

1. **BUG-1** (SEV-1, Frontend) — unwrap watchlist envelope + add error boundary.
   Unblocks all 7 UI scenarios.
2. **BUG-2** (SEV-1, Frontend) — unwrap trade `.portfolio`. Required for manual
   Buy/Sell to update the portfolio.
3. **BUG-3** (SEV-3, LLM/Frontend contract) — unify trade/watchlist `status`
   enums. Cosmetic today.
4. **Docs** — reconcile `FRONTEND.md` ↔ `API_LAYER.md` on the trade/watchlist
   response envelopes (prevents recurrence).

## Re-test instructions

After BUG-1/BUG-2 are fixed: rebuild the frontend export → `backend/static`,
restart the backend with a fresh `FINALLY_DB_PATH`, then
`cd test && BASE_URL=http://127.0.0.1:8000 npx playwright test`. Expect 15/15
green (8 API + 7 UI).
