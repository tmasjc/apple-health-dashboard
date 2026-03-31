#!/bin/bash
# Start both backend and frontend dev servers
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

echo "Starting FastAPI backend on :8001 ..."
(cd "$ROOT" && uv run uvicorn backend.server:app --port 8001 --reload) &

echo "Starting Vite frontend on :5173 ..."
(cd "$ROOT/frontend" && npm run dev) &

wait
