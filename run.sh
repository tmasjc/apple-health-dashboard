#!/bin/bash
# Start both backend and frontend dev servers
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting FastAPI backend on :8001 ..."
(cd "$DIR" && uv run uvicorn backend.server:app --port 8001 --reload) &

echo "Starting Vite frontend on :5173 ..."
(cd "$DIR/frontend" && npm run dev) &

wait
