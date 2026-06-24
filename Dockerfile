# syntax=docker/dockerfile:1

# =============================================================================
# FinAlly — multi-stage build (PLAN.md §11)
#   Stage 1 (Node 20): build the Next.js static export -> frontend/out
#   Stage 2 (Python 3.12 + uv): runtime; serves API + static frontend on :8000
# Final image ships NO node_modules and NO dev/test deps.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: build the frontend static export
# -----------------------------------------------------------------------------
FROM node:20-slim AS frontend-build

WORKDIR /frontend

# Install deps first (cached unless package manifests change).
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Build the static export. Fonts are self-hosted (@fontsource) so no network
# is required at build time. Production build (NODE_ENV defaults to production
# under `next build`) emits `output: 'export'` -> ./out.
COPY frontend/ ./
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Python runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# uv: fast, reproducible Python project manager (copied from official image).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV \
    # Don't write .pyc, unbuffered logs for clean container output.
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # uv: install into a project .venv, link from a build-cache mount.
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    # Put the project venv on PATH so `uvicorn`/`python` resolve directly.
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    # DB lives on the mounted volume at /app/db (see _resolve_db_path()).
    # The backend's project-root default would resolve to /db inside the image,
    # so we pin it explicitly to the volume mount.
    FINALLY_DB_PATH=/app/db/finally.db

WORKDIR /app

# --- Resolve dependencies first for layer caching ---
# Copy only the lockfile + manifest, then sync deps without the project itself.
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# --- Copy backend source and finish the install ---
COPY backend/ ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Drop the frontend static export into backend/static (/app/static) ---
# main.py serves Path(__file__).parent.parent/"static" == /app/static.
COPY --from=frontend-build /frontend/out ./static

# --- Volume mount target for the SQLite DB ---
RUN mkdir -p /app/db

EXPOSE 8000

# Lightweight container healthcheck against the API health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"

# Serve FastAPI (app.main:app) on all interfaces.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
