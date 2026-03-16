#!/usr/bin/env bash
# Restart What2Watch (rebuilds containers)
set -e
cd "$(dirname "$0")/.."
echo "Restarting What2Watch..."
docker compose down
docker compose up -d --build
echo ""
echo "Services:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  Database:  localhost:5432"
echo ""
echo "Use 'docker compose logs -f' to follow logs."
