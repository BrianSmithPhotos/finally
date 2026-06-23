#!/usr/bin/env bash
# Build (if needed) and run the FinAlly Docker container.
# Usage: ./scripts/start_mac.sh [--build]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="finally"
CONTAINER_NAME="finally"
VOLUME_NAME="finally-data"
PORT="8000"
URL="http://localhost:${PORT}"

cd "$REPO_ROOT"

FORCE_BUILD=false
if [[ "${1:-}" == "--build" ]]; then
  FORCE_BUILD=true
fi

if [[ ! -f .env ]]; then
  echo "No .env file found at repo root. Copy .env.example to .env and set OPENROUTER_API_KEY." >&2
  exit 1
fi

if "$FORCE_BUILD" || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "Building image ${IMAGE_NAME}..."
  docker build -t "$IMAGE_NAME" .
fi

if [[ "$(docker ps -aq -f name="^${CONTAINER_NAME}$")" ]]; then
  if [[ "$(docker ps -q -f name="^${CONTAINER_NAME}$")" ]]; then
    echo "FinAlly is already running at ${URL}"
    exit 0
  fi
  echo "Removing stopped container ${CONTAINER_NAME}..."
  docker rm "$CONTAINER_NAME" >/dev/null
fi

docker volume create "$VOLUME_NAME" >/dev/null

echo "Starting FinAlly..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "${PORT}:8000" \
  -v "${VOLUME_NAME}:/app/db" \
  --env-file .env \
  -e DB_PATH=/app/db/finally.db \
  "$IMAGE_NAME" >/dev/null

echo "FinAlly is running at ${URL}"

if command -v open >/dev/null 2>&1; then
  open "$URL"
fi
