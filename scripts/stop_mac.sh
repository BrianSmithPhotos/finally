#!/usr/bin/env bash
# FinAlly — stop script (macOS / Linux). Idempotent: safe to re-run.
# Stops and removes the container. PRESERVES the `finally-data` volume (data
# persists across restarts).
#
#   ./scripts/stop_mac.sh

set -euo pipefail

CONTAINER_NAME="finally"

if ! command -v docker >/dev/null 2>&1; then
  echo "Error: docker is not installed or not on PATH." >&2
  exit 1
fi

if [ -n "$(docker ps -aq -f name="^${CONTAINER_NAME}$")" ]; then
  echo "Stopping and removing container '${CONTAINER_NAME}'..."
  docker rm -f "${CONTAINER_NAME}" >/dev/null
  echo "Done. The 'finally-data' volume was preserved."
else
  echo "No container named '${CONTAINER_NAME}' is running."
fi
