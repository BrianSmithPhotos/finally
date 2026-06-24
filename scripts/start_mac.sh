#!/usr/bin/env bash
# FinAlly — start script (macOS / Linux). Idempotent: safe to re-run.
#
#   ./scripts/start_mac.sh           # build image if missing, then run
#   ./scripts/start_mac.sh --build   # force a rebuild, then run
#   ./scripts/start_mac.sh --open    # also open the browser
#
# Builds the `finally` image, runs the `finally` container with the
# `finally-data` volume mounted at /app/db, maps port 8000, reads .env.

set -euo pipefail

IMAGE_NAME="finally"
CONTAINER_NAME="finally"
VOLUME_NAME="finally-data"
PORT="8000"
URL="http://localhost:${PORT}"

# Resolve project root (this script lives in scripts/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

FORCE_BUILD=false
OPEN_BROWSER=false
for arg in "$@"; do
  case "$arg" in
    --build) FORCE_BUILD=true ;;
    --open)  OPEN_BROWSER=true ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed or not on PATH." >&2
  exit 1
fi

# Ensure an .env exists (the container reads it via --env-file).
if [ ! -f .env ]; then
  echo "No .env found; creating one from .env.example."
  echo "  -> Edit .env and set OPENROUTER_API_KEY for chat to work."
  cp .env.example .env
fi

# Build the image if missing or if --build was passed.
if $FORCE_BUILD || [ -z "$(docker images -q "${IMAGE_NAME}" 2>/dev/null)" ]; then
  echo "Building image '${IMAGE_NAME}'..."
  docker build -t "${IMAGE_NAME}" .
else
  echo "Image '${IMAGE_NAME}' already present (use --build to rebuild)."
fi

# Remove any existing container with this name (idempotent restart).
if [ -n "$(docker ps -aq -f name="^${CONTAINER_NAME}$")" ]; then
  echo "Removing existing container '${CONTAINER_NAME}'..."
  docker rm -f "${CONTAINER_NAME}" >/dev/null
fi

echo "Starting container '${CONTAINER_NAME}'..."
docker run -d \
  --name "${CONTAINER_NAME}" \
  --env-file .env \
  -p "${PORT}:8000" \
  -v "${VOLUME_NAME}:/app/db" \
  --restart unless-stopped \
  "${IMAGE_NAME}" >/dev/null

echo ""
echo "FinAlly is starting at: ${URL}"
echo "  Logs:  docker logs -f ${CONTAINER_NAME}"
echo "  Stop:  ./scripts/stop_mac.sh"

if $OPEN_BROWSER; then
  if command -v open >/dev/null 2>&1; then open "${URL}";
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "${URL}";
  fi
fi
