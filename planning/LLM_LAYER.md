# LLM / Chat Layer — Contract for Downstream Agents

The chat subsystem (`backend/app/chat/`) implements PLAN.md Section 9: the
`POST /api/chat` endpoint. It builds portfolio/watchlist context, calls the LLM
(LiteLLM → OpenRouter, Cerebras inference, model `openrouter/openai/gpt-oss-120b`,
Structured Outputs), auto-executes any returned trades / watchlist changes
through the shared `app.services` seam, persists the conversation, and returns a
structured response enriched with per-action status for inline UI confirmations.

It does **not** modify `app/market/`, `app/db/`, `app/services/`, or the existing
`app/api/` routers. The only edit to `main.py` is registering `chat_router`.

## Module map

| Module | Responsibility |
|---|---|
| `app/chat/router.py` | `POST /api/chat` route (`chat_router`) |
| `app/chat/service.py` | Request orchestration (`handle_chat`) |
| `app/chat/llm.py` | LiteLLM→OpenRouter/Cerebras call + parsing + fallback |
| `app/chat/mock.py` | Deterministic mock for `LLM_MOCK=true` |
| `app/chat/schemas.py` | Pydantic models (LLM contract + HTTP request/response) |

## Endpoint

| Method | Path | Body | Response |
|---|---|---|---|
| POST | `/api/chat` | `{ "message": "<text>" }` | `ChatResponse` (200) / 422 on blank message |

### Request

```json
{ "message": "buy 5 AAPL" }
```

`message` is required and must be non-blank (whitespace-only → 422).

### Response (`ChatResponse`)

Top-level shape is faithful to PLAN.md §9 (`message` / `trades` /
`watchlist_changes`); each action item is enriched with a `status` (and
`error`/`price`/`executed_at`) so the UI can render inline confirmations.

```json
{
  "message": "Placing a buy order for 5 AAPL.",
  "trades": [
    {
      "ticker": "AAPL",
      "side": "buy",
      "quantity": 5.0,
      "status": "executed",        // "executed" | "error"
      "price": 190.03,             // fill price, null on error
      "executed_at": "2026-06-24T14:18:10.415014+00:00",  // null on error
      "error": null                // message string when status == "error"
    }
  ],
  "watchlist_changes": [
    {
      "ticker": "PYPL",
      "action": "add",             // "add" | "remove"
      "status": "added",           // "added" | "removed" | "noop" | "error"
      "error": null
    }
  ]
}
```

Per-action status values:

- **trades** `status`: `executed` (then `price` + `executed_at` set) or `error`
  (then `error` holds the `TradeError` message, e.g. insufficient cash/shares,
  no live price). A failing trade is surfaced inline — the endpoint never 500s on
  a trade validation failure.
- **watchlist_changes** `status`: `added`, `removed`, `noop` (remove of a ticker
  not on the watchlist), or `error`.

Empty `trades` / `watchlist_changes` arrays mean the assistant took no actions.

## LLM structured-output schema

The model is asked to return JSON matching `LLMResponse` (Structured Outputs):

```json
{
  "message": "string (required)",
  "trades": [ { "ticker": "AAPL", "side": "buy|sell", "quantity": 10 } ],
  "watchlist_changes": [ { "ticker": "PYPL", "action": "add|remove" } ]
}
```

`trades` and `watchlist_changes` default to empty arrays. The system prompt
identifies the assistant as "FinAlly, an AI trading assistant" and instructs it
to analyze portfolio/risk/P&L, suggest and execute trades, manage the watchlist,
be concise/data-driven, and only trade tickers with a live price.

## Request flow (`handle_chat`)

1. Persist the user message (`insert_chat_message("user", message)`).
2. Build context: `build_portfolio`, `build_watchlist`, last 20 messages
   (`list_chat_messages(limit=20)`).
3. Generate the LLM response — mock when `LLM_MOCK=true`, else the real call.
4. Auto-execute trades via `execute_trade(...)` (each validated; `TradeError`
   captured as `status:"error"`); apply watchlist changes to the DB
   (`add_/remove_watchlist_ticker`) **and** the market source
   (`await source.add_ticker/remove_ticker`).
5. Persist the assistant message with an `actions` JSON blob:
   `{"trades": [...], "watchlist_changes": [...]}` (the enriched results).
6. Return `ChatResponse`.

## Graceful degradation

- Network failure, empty output, or non-schema output never crashes the
  endpoint. `call_llm` catches all exceptions and returns a safe fallback
  message. Malformed-but-nonempty text is surfaced as the conversational
  `message` (no trades). The endpoint always returns 200 with a valid body.

## LLM_MOCK deterministic behavior (for the Integration Tester)

When `LLM_MOCK=true` **no network call is made** and `app/chat/mock.py` produces
a fixed-shape response from the user message via regex. Behavior contract:

- **Trade intent** — message matching `(buy|sell) <qty> [shares [of]] <TICKER>`
  emits exactly one trade `{ticker, side, quantity}`. `<TICKER>` is 1–5 letters
  (uppercased); `<qty>` is an integer or decimal. First match wins.
  - `"buy 5 AAPL"` → one buy of 5 AAPL.
  - `"sell 2.5 shares of TSLA"` → one sell of 2.5 TSLA.
  - `"please buy 10 shares NVDA now"` → one buy of 10 NVDA.
  - The trade still runs through the real `execute_trade`, so an invalid trade
    (e.g. `"buy 1000 NFLX"` with only $10k cash, or selling unowned shares)
    comes back as `status:"error"` with the validation message — not a 500.
- **Watchlist intent** — `(add|watch) <TICKER>` → one `add`;
  `(remove|unwatch|drop) <TICKER>` → one `remove`. A `remove` of a ticker not on
  the watchlist returns `status:"noop"`.
- **Otherwise** — no trades/changes; an echo-style message of the form
  `[mock] You said: '<message>'. You have $<cash> in cash across <n> position(s).`
  (quotes the live cash balance and position count from context).
- Common filler words (THE, ME, OF, SHARES, …) are rejected as tickers.
- The mock is pure/deterministic: identical input → identical output.

Suggested E2E assertions: send `"buy 5 AAPL"`, assert `trades[0].status ==
"executed"`, `ticker == "AAPL"`, `quantity == 5`, and that cash decreased; send a
plain greeting and assert `trades == []` and the `[mock]` prefix in `message`.

## Tests

`backend/tests/chat/` (pytest + FastAPI `TestClient`). `conftest.py` injects a
temp-file `Database`, a pre-seeded `PriceCache` (default 10 tickers + PYPL), and
a fake async market source onto `app.state`; an autouse fixture sets
`LLM_MOCK=true`. 24 tests:

- `test_endpoint.py` (9) — plain message, buy executes + cash decrements,
  sell-more-than-owned and insufficient-cash surfaced as errors (not 500),
  watchlist add/remove via chat (DB + source), remove-noop, blank→422,
  assistant `actions` persisted as JSON.
- `test_mock.py` (8) — trade/watchlist intent parsing, echo fallback, determinism.
- `test_llm_parsing.py` (7) — valid/empty/None/malformed parsing, `call_llm`
  exception fallback, structured-output parse, message assembly.

Run: `cd backend && uv run --extra dev pytest tests/chat -v` (or the full suite —
151 tests: 18 api + 73 market + 36 db + 24 chat).
