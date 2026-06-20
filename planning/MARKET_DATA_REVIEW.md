# Market Data Backend — Code Review

**Scope:** `backend/app/market/` (9 modules) and `backend/tests/market/` (6 test modules), reviewed against `planning/PLAN.md` and `planning/MARKET_DATA_DESIGN.md`.

**Verdict: Approved.** The implementation matches the design doc, the abstraction is clean, and the test suite is strong. Two minor inconsistencies and one real test gap are noted below — none block merging, but the gap should be closed before this code is relied on in production.

> **Update:** Both action items from §5 have been resolved. `stream.py` now has 100% test coverage (`tests/market/test_stream.py`), and ticker normalization (`strip().upper()`) is now applied consistently at the `PriceCache` boundary and inside `GBMSimulator`, matching `MassiveDataSource`'s existing behavior. The full suite is 90/90 passing at 98% coverage. See the bottom of this document for the verification run.

---

## 1. Test Run

```
cd backend
uv sync --extra dev
uv run pytest tests/market -v --cov=app.market --cov-report=term-missing
```

**Result: 73 passed, 0 failed, 0 skipped, 2.98s.**

```
Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
app/market/__init__.py             6      0   100%
app/market/cache.py               39      0   100%
app/market/factory.py             15      0   100%
app/market/interface.py           13      0   100%
app/market/massive_client.py      67      4    94%   85-87, 125
app/market/models.py              26      0   100%
app/market/seed_prices.py          8      0   100%
app/market/simulator.py          139      3    98%   149, 268-269
app/market/stream.py              36     24    33%   26-48, 62-87
------------------------------------------------------------
TOTAL                            349     31    91%
```

Lint: `uv run ruff check app/market tests/market` — **all checks passed**, no warnings.

---

## 2. Coverage Gaps

### 2.1 `stream.py` — 33% coverage (the one real gap)

**There are no tests for the SSE streaming module at all.** The 33% shown is just the module/router-factory definitions being imported; the actual route handler (`stream_prices`) and the event generator (`_generate_events`) — including the version-based change-detection loop, the disconnect check, and the `retry:` directive — are never exercised by a test.

This is the most important finding in this review. Every other module in the subsystem has full or near-full coverage; `stream.py` has none of its logic under test. Recommend adding, before this is considered production-ready:

- A test that drives `_generate_events()` as an async generator against a `PriceCache`, asserting:
  - the first yielded chunk is `retry: 1000\n\n`
  - a `data:` event is yielded after `cache.update(...)` bumps the version
  - no event is yielded on a tick where the version hasn't changed (proves the version-counter optimization actually works)
  - the generator returns when a mock `Request.is_disconnected()` returns `True`
- A `TestClient`-based test hitting `GET /api/stream/prices` (via `create_stream_router`) to confirm headers (`Cache-Control`, `Connection`, `X-Accel-Buffering`) and that the response is parseable SSE.

This requires an async test double for `Request` (mock `.is_disconnected()` and `.client.host`) — straightforward with `unittest.mock.AsyncMock`.

### 2.2 `massive_client.py` lines 85–87 (`_poll_loop`)

The infinite `while True: sleep; poll` loop body is never executed in tests — every test calls `_poll_once()` directly instead of going through `start()` and letting the background task run. This is a reasonable simplification (a real wait-based test would be slow/flaky), but it means a regression in the loop itself (e.g. wrong sleep placement, swallowed exception) wouldn't be caught. Low risk: the loop body is two lines and trivial to eyeball-verify. Not blocking.

### 2.3 `massive_client.py` line 125 (`_fetch_snapshots`)

The real synchronous call to `self._client.get_snapshot_all(...)` is never invoked — every test patches `_fetch_snapshots` itself. This is correct practice (no network calls in unit tests) but means the actual Massive SDK call signature (`market_type=SnapshotMarketType.STOCKS, tickers=...`) is unverified against the real `massive` package. Recommend a manual smoke test against a real (or sandbox) API key before relying on the Massive path in production, since this is the one place where a third-party API contract could silently drift.

### 2.4 `simulator.py` lines 149, 268–269

- Line 149: the early-return guard in `_add_ticker_internal` when a ticker is already present. Harmless dead branch in tests since `add_ticker()` already guards against duplicates before calling it — the internal guard is just defensive redundancy.
- Lines 268–269: the `except Exception: logger.exception(...)` branch in `SimulatorDataSource._run_loop`. Not exercised because nothing in the GBM step path actually raises in tests. Acceptable — this is a defensive catch-all and forcing it to fire would require injecting a fault into `numpy`/dict access, which isn't worth the complexity for a logging statement.

None of 2.2–2.4 need action. **2.1 does.**

---

## 3. Design & Correctness Review

### 3.1 Architecture

The Strategy pattern (`MarketDataSource` ABC with `SimulatorDataSource` / `MassiveDataSource` implementations) is implemented exactly as specified in `planning/MARKET_DATA_DESIGN.md`. The factory (`create_market_data_source`) correctly branches on `MASSIVE_API_KEY` being non-empty after `.strip()`, covered by `test_factory.py` including the whitespace-only-key edge case.

The `PriceCache` is the single point of contention between producers (one data source) and consumers (SSE, future portfolio code), exactly matching the "push model" described in the design doc. Good separation of concerns — `stream.py` has no knowledge of which data source is active.

### 3.2 `PriceCache` (`cache.py`)

- `threading.Lock` (not `asyncio.Lock`) is the right choice given `MassiveDataSource` runs its fetch in `asyncio.to_thread()` — a real OS thread that an `asyncio.Lock` would not protect against. Correctly reasoned in the design doc and correctly implemented.
- The version counter is a clean, low-overhead way to let SSE skip redundant sends. Verified by `test_version_increments`.
- `update()` always re-rounds `previous_price` even when it's unchanged from a prior update — harmless (rounding is idempotent on already-rounded values) but technically one redundant `round()` call per tick. Not worth changing.
- No ticker normalization (case/whitespace) happens here — see §3.5.

### 3.3 `PriceUpdate` (`models.py`)

`frozen=True, slots=True` dataclass with derived properties (`change`, `change_percent`, `direction`) is a sound design — there is no way for `direction` to disagree with `price`/`previous_price` because it's computed, not stored. `change_percent` correctly guards the `previous_price == 0` division case. `to_dict()` is the single serialization boundary, used consistently by `stream.py`. No issues.

### 3.4 `GBMSimulator` (`simulator.py`)

- The GBM math (`exp((mu - 0.5*sigma²)*dt + sigma*sqrt(dt)*Z)`) is the standard correct formulation; prices are provably positive since `exp()` never returns ≤0, and this is explicitly tested (`test_prices_are_positive`, 10,000 iterations).
- The Cholesky-based correlation model is reasonable for "looks realistic" purposes: tech stocks at 0.6, finance at 0.5, TSLA and cross-sector at 0.3. `_rebuild_cholesky()` is correctly called on every `add_ticker`/`remove_ticker`, and the `n <= 1` guard avoids a degenerate 1x1 Cholesky decomposition (tested: `test_cholesky_none_with_one_ticker`).
- `_pairwise_correlation` checks `TSLA` membership before tech/finance — correct, since `TSLA` is also a member of the `tech` correlation group set but is meant to behave independently. This ordering matters and is correctly tested (`test_pairwise_correlation_tsla`).
- Random "event" shocks (~0.1%/tick) are a nice touch for demo drama and don't affect correctness — they can never drive a price negative since they're multiplicative.
- `DEFAULT_DT` is derived from a real trading-calendar calculation (252 days × 6.5h × 3600s) rather than a magic number — good, self-documenting, and tested for sanity (`test_default_dt_is_reasonable`).
- `SimulatorDataSource.start()` seeds the cache synchronously before the background task begins, so the very first SSE read after `await source.start(...)` always has data — this matches the design doc's stated goal of avoiding a blank first paint, and is tested (`test_start_populates_cache`).
- `stop()` cancels and awaits the task, swallowing `CancelledError` — proper async cleanup, tested for idempotency (`test_stop_is_clean`, double-stop).

No correctness issues found here. This is the most thoroughly tested module in the subsystem (17 simulator tests + 9 source tests) and it shows.

### 3.5 Ticker normalization inconsistency (minor)

`MassiveDataSource.add_ticker`/`remove_ticker` normalize input with `ticker.upper().strip()`. `SimulatorDataSource`/`GBMSimulator` do not — they use whatever string is passed in verbatim. This means:

- Adding `"aapl"` and `"AAPL"` would be treated as two different tickers by the simulator but collapse to one by Massive.
- A caller passing un-normalized input would get different behavior depending on which data source is active — a violation of the "downstream code is source-agnostic" goal stated in the design doc.

**Recommendation:** normalize tickers (`upper().strip()`) once at the API boundary (the future watchlist route) rather than duplicating it in each data source, or push the normalization into the shared `MarketDataSource` interface contract / `PriceCache.update()`. Either fix is cheap; just pick one place and do it consistently. Not a blocker since no caller exists yet (the watchlist API isn't built), but should be resolved before that API ships.

### 3.6 `MassiveDataSource` (`massive_client.py`)

- Correctly offloads the synchronous Massive SDK call via `asyncio.to_thread()`, avoiding event-loop blocking — matches the design doc.
- Per-snapshot error handling (`except (AttributeError, TypeError)`) means one malformed ticker snapshot doesn't take down the whole poll cycle — tested (`test_malformed_snapshot_skipped`).
- A poll-level exception (network error, 401, 429) is caught and logged without re-raising, so the poller self-heals on the next interval rather than dying — tested (`test_api_error_does_not_crash`).
- Millisecond → second timestamp conversion (`/ 1000.0`) is correctly applied and tested (`test_timestamp_conversion`).
- `massive` is imported at module level (not lazily), consistent with it being a declared core dependency in `pyproject.toml` rather than an optional one. This was flagged as a fix in the original review cycle per `planning/MARKET_DATA_SUMMARY.md` and is correctly applied in the current code.
- One thing to watch: if `MASSIVE_API_KEY` is unset, this module is still imported (since it's not lazy) as part of `factory.py`'s top-level imports. That's fine as `massive` is a hard dependency, but it does mean the simulator-only path now requires `massive` to be installed too — a minor regression in isolation versus the originally-considered "simulator has zero external dependencies beyond numpy" design goal. Not worth reversing given the explicit tradeoff already documented in `MARKET_DATA_SUMMARY.md` (clarity over conditional-import complexity); just noting it so it's not rediscovered as a surprise later.

### 3.7 `factory.py` and `interface.py`

Both are exactly as specified in the design doc — simple, fully covered, no issues. The ABC's docstring lifecycle example (`start` → `add_ticker`/`remove_ticker` → `stop`) accurately reflects how both implementations behave.

### 3.8 `stream.py`

Logic itself looks correct on inspection:

- `retry: 1000\n\n` sent first, so `EventSource` reconnects after 1s on drop — matches the design doc.
- Version-based skip logic correctly avoids re-sending unchanged data.
- `request.is_disconnected()` checked every loop iteration before sleeping, so the generator exits promptly on client disconnect rather than continuing to compute/serialize for an absent client.
- `asyncio.CancelledError` is caught at the top level for clean shutdown logging.

The logic is sound by inspection, but as noted in §2.1, **none of it is verified by a test**. Given this is the single network-facing endpoint in the whole subsystem and the one piece every frontend feature depends on, it's the highest-value place to add tests next.

---

## 4. Security Review

No injection surfaces: tickers are used only as dict keys and string values passed to a third-party SDK, never interpolated into SQL or shell commands. No secrets are logged (the Massive API key is held in `self._api_key` and never printed). No user-controllable input reaches `eval`/`exec`/`subprocess`. The SSE endpoint doesn't echo back arbitrary client input. Nothing concerning found.

---

## 5. Summary

| Area | Status |
|---|---|
| Tests pass | ✅ 73/73 |
| Lint clean | ✅ ruff: all checks passed |
| Coverage | ⚠️ 91% overall; `stream.py` essentially untested (33%, real gap) |
| Architecture vs design doc | ✅ matches `planning/MARKET_DATA_DESIGN.md` exactly |
| GBM simulator correctness | ✅ sound math, well tested |
| Massive client robustness | ✅ resilient error handling, well tested |
| Ticker normalization | ⚠️ inconsistent between simulator and Massive (minor, no caller yet) |
| Security | ✅ no issues found |

**Action items before this subsystem is exercised by real traffic:**

1. Add tests for `stream.py` (`_generate_events` generator behavior + route smoke test). This is the only module with a real coverage gap.
2. Decide where ticker normalization (`upper().strip()`) lives and apply it consistently — likely at the future watchlist API boundary — before wiring up `POST /api/watchlist`.

Neither item blocks merging this code as-is; both should be tracked before the watchlist/portfolio routes are built on top of this subsystem.

---

## 6. Follow-up: Fixes Applied

Both action items above have been addressed:

1. **`stream.py` coverage** — added `backend/tests/market/test_stream.py` (8 tests): unit tests drive `_generate_events()` directly with a mocked `Request` (covering the retry directive, version-based change detection, empty-cache skip, disconnect handling, and a missing `request.client`), plus two tests that invoke the route's endpoint coroutine directly to verify response headers/media type. `stream.py` is now at 100% coverage.
2. **Ticker normalization** — `PriceCache` now normalizes (`strip().upper()`) on every read/write (`update`, `get`, `remove`, `__contains__`), and `GBMSimulator`/`SimulatorDataSource` normalize on construction, `add_ticker`, `remove_ticker`, and `get_price`. This matches `MassiveDataSource`'s existing normalization, so the same ticker now behaves identically regardless of which data source is active — enforced at the cache boundary so it can't be bypassed by a future caller that forgets to normalize.

**Verification run after fixes:**

```
uv run pytest tests/market -v --cov=app.market --cov-report=term-missing
```

```
Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
app/market/__init__.py             6      0   100%
app/market/cache.py               46      0   100%
app/market/factory.py             15      0   100%
app/market/interface.py           13      0   100%
app/market/massive_client.py      67      4    94%   85-87, 125
app/market/models.py              26      0   100%
app/market/seed_prices.py          8      0   100%
app/market/simulator.py          144      3    98%   160, 279-280
app/market/stream.py              36      0   100%
------------------------------------------------------------
TOTAL                            361      7    98%
============================== 90 passed in 2.35s ===============================
```

`ruff check app/market tests/market` — all checks passed.

The remaining uncovered lines (`massive_client.py` 85-87/125, `simulator.py` 160/279-280) are the same defensive/loop-internal branches discussed in §2.2–§2.4 above and were judged not worth the complexity of forcing in a unit test.
