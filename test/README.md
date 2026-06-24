# FinAlly E2E Tests

Playwright end-to-end tests for the fully-integrated FinAlly app (PLAN.md §12).
The app under test is the FastAPI server that also serves the Next.js static
export from `backend/static` on port 8000.

## Layout

```
test/
├── package.json                 # @playwright/test deps + scripts
├── playwright.config.ts         # BASE_URL (default http://localhost:8000), 1 worker
├── docker-compose.test.yml      # app container + Playwright runner (CI)
├── tests/
│   ├── helpers.ts               # selectors, money parsing, backend reset
│   ├── api-contract.spec.ts     # direct REST/SSE shape checks (no browser)
│   └── ui-scenarios.spec.ts     # PLAN §12 UI scenarios in a real browser
└── artifacts/                   # captured failure screenshots
```

## Running locally (fast path)

1. Build the frontend export and serve it through the backend:
   ```bash
   cd frontend && npm install && npm run build
   rm -rf ../backend/static && cp -R out ../backend/static
   ```
   (`backend/static` is a gitignored build artifact.)

2. Start the backend with mock LLM and a throwaway DB:
   ```bash
   cd backend
   LLM_MOCK=true FINALLY_DB_PATH="$TMPDIR/finally-e2e.db" MASSIVE_API_KEY="" \
     .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   Wait for `GET /api/health` → 200. Delete the DB file between runs for a clean
   seeded state.

3. Run the suite:
   ```bash
   cd test
   npm install
   npx playwright install chromium
   BASE_URL=http://127.0.0.1:8000 npx playwright test
   ```

## Running in CI (Docker)

```bash
docker compose -f test/docker-compose.test.yml up --build \
  --abort-on-container-exit --exit-code-from e2e
docker compose -f test/docker-compose.test.yml down -v
```

The app container runs with `LLM_MOCK=true` and an ephemeral DB (no volume), so
each run starts clean-seeded. The Playwright runner uses the official
`mcr.microsoft.com/playwright` image so browser deps stay out of the prod image.

## Notes

- `api-contract.spec.ts` asserts the backend's **actual** response shapes
  (including the nested `{watchlist}` / `{trade, portfolio}` envelopes the FE
  client unwraps). They are the machine-checked evidence behind
  `planning/INTEGRATION_REPORT.md`.
- `ui-scenarios.spec.ts` asserts **correct end-user behavior**.
- **Current status: 15/15 green** (8 API + 7 UI) after the Frontend fixes for the
  watchlist/trade nesting bugs. UI assertions are relative (cash decrease/
  increase, FE == live API value) so the suite is idempotent against the shared
  single-user backend.
