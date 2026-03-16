#!/usr/bin/env bash
# Stop What2Watch
set -e
cd "$(dirname "$0")/.."
echo "Stopping What2Watch..."
docker compose down
echo "All services stopped."
