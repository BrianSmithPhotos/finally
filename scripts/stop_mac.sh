#!/usr/bin/env bash
# Stop and remove the FinAlly container. Leaves the data volume untouched.
set -euo pipefail

CONTAINER_NAME="finally"

if [[ "$(docker ps -aq -f name="^${CONTAINER_NAME}$")" ]]; then
  echo "Stopping FinAlly..."
  docker stop "$CONTAINER_NAME" >/dev/null
  docker rm "$CONTAINER_NAME" >/dev/null
  echo "FinAlly stopped."
else
  echo "FinAlly is not running."
fi
