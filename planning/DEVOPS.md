# DEVOPS — Build, Run, Deploy

How to build and run FinAlly as a single Docker container. Owned by the DevOps
Engineer agent. See PLAN.md §4 (Directory Structure), §5 (Env Vars), and §11
(Docker & Deployment) for the spec this implements.

## TL;DR

```bash
cp .env.example .env          # then set OPENROUTER_API_KEY
./scripts/start_mac.sh        # build (if needed) + run -> http://localhost:8000
./scripts/stop_mac.sh         # stop (data preserved)
```

Windows: `./scripts/start_windows.ps1` / `./scripts/stop_windows.ps1`.

## Names (consistent across all entrypoints)

| Thing      | Name            |
|------------|-----------------|
| Image      | `finally`       |
| Container  | `finally`       |
| Volume     | `finally-data`  |
| Port       | `8000` (host → container `8000`) |

## Architecture of the image (multi-stage `Dockerfile`)

- **Stage 1 — `node:20-slim`**: `npm ci` then `npm run build` in `frontend/`,
  producing the Next.js static export at `frontend/out`. `next.config.mjs`
  emits `output: 'export'` for production builds. Fonts are self-hosted
  (`@fontsource`), so no network is needed beyond npm install.
- **Stage 2 — `python:3.12-slim`**: installs `uv` (copied from the official
  `ghcr.io/astral-sh/uv` image), runs `uv sync --frozen --no-dev` for a
  reproducible runtime venv (no pytest/ruff dev deps), copies `backend/` to
  `/app`, then copies the stage-1 `out/` into `/app/static`. Runs
  `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

The backend serves the frontend: `app/main.py` mounts static files from
`Path(__file__).parent.parent / "static"` → `/app/static`. If that directory is
absent the backend runs API-only (it is always present in the image).

Final image is ~660 MB. It ships **no** `node_modules` and **no** dev deps.

## Database & persistence

- SQLite file lives at `/app/db/finally.db` inside the container.
- The container sets `FINALLY_DB_PATH=/app/db/finally.db` explicitly. This is
  **required**: the backend's project-root default (`_PROJECT_ROOT/db`) resolves
  to `/db` inside the image (wrong), because `backend/` is copied to `/app`.
  The env var pins the DB onto the mounted volume.
- The schema (`backend/db/schema.sql`) is copied to `/app/db/schema.sql` and the
  backend reads it from there. On a **fresh empty named volume**, Docker
  auto-populates the mount with the image's `/app/db` contents, so `schema.sql`
  is present and lazy-init seeds the DB on first request. Verified working.
- The named volume `finally-data` is mounted at `/app/db`, so the DB and seeded
  data persist across container restarts/rebuilds. `stop` scripts never remove
  the volume; to wipe data: `docker volume rm finally-data`.

## Environment variables (PLAN §5)

Read from `.env` at the project root (passed via `--env-file .env`):

| Var | Required | Behavior |
|-----|----------|----------|
| `OPENROUTER_API_KEY` | for chat | LLM chat via OpenRouter. |
| `MASSIVE_API_KEY`    | optional | If set/non-empty → real Massive market data; empty → built-in simulator. |
| `LLM_MOCK`           | optional | `true` → deterministic mock LLM responses (E2E/CI, no key needed). |

`.env.example` is committed (no secrets). The `start_*` scripts auto-create
`.env` from `.env.example` if it is missing.

## Run options

### Scripts (recommended)
```bash
./scripts/start_mac.sh            # build if image missing, then run
./scripts/start_mac.sh --build    # force rebuild
./scripts/start_mac.sh --open     # also open browser
./scripts/stop_mac.sh             # stop + remove container, keep volume
```
Windows equivalents use `-Build` / `-Open` switches. All scripts are idempotent.

### Raw docker
```bash
docker build -t finally .
docker run -d --name finally \
  --env-file .env \
  -p 8000:8000 \
  -v finally-data:/app/db \
  --restart unless-stopped \
  finally
# stop (keep data):
docker rm -f finally
```

### docker compose
```bash
docker compose up --build     # build + run
docker compose down           # stop (volume preserved)
```

## Health & smoke checks

```bash
curl http://localhost:8000/api/health      # -> {"status":"ok"}
curl -I http://localhost:8000/             # -> 200 text/html (frontend)
curl http://localhost:8000/api/portfolio   # -> 200 JSON (seeded portfolio)
```
The image also defines a `HEALTHCHECK` hitting `/api/health`.

## Build context hygiene

`.dockerignore` excludes `.git`, `.env`, `frontend/node_modules`, `frontend/.next`,
`frontend/out`, `backend/.venv`, caches, `backend/tests`, and `db/*.db` so the
build context stays small and no stale artifacts or secrets leak into the image.

## Cloud deployment (stretch, not built)

The single container (port 8000, one volume) is suitable for AWS App Runner,
Render, Fly.io, etc. Provide `OPENROUTER_API_KEY` (and optionally
`MASSIVE_API_KEY`) as platform env vars, and attach persistent storage at
`/app/db` if you want the SQLite DB to survive redeploys. A Terraform config
under `deploy/` would live here if added later.

## Verification status (this environment)

Built and smoke-tested successfully on Docker 29.5 (desktop-linux):
- `docker build -t finally .` — full multi-stage build succeeds (~660 MB image).
- Container run: `/api/health` 200, `/` 200 (text/html), `/api/portfolio` 200.
- DB created at `/app/db/finally.db`; `FINALLY_DB_PATH` override confirmed.
- Fresh empty `finally-data` volume start verified (schema present, DB seeded).
- Confirmed no `pytest`/dev deps and no `node_modules` in the final image.
- `uv sync --frozen --no-dev` resolves locally (used `UV_CACHE_DIR=$TMPDIR/...`
  to work around a sandboxed `~/.cache/uv`; this is not committed anywhere).
```
