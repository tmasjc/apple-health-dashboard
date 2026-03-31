#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# setup.sh — End-to-end pipeline: unzip → parse → install → serve
#
# Assumes:
#   • The Apple Health export zip lives in the project root (./‹name›.zip)
#   • uv, node, and npm are available on PATH
#
# Usage:
#   scripts/setup.sh                 # auto-detect the zip in project root
#   scripts/setup.sh /path/to.zip    # specify a zip explicitly
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"

# ── Colours for log output ───────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'  # no colour

step() { echo -e "\n${GREEN}▶ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
fail() { echo -e "${RED}✖ $1${NC}"; exit 1; }

# ── 0. Prerequisite checks ──────────────────────────────────────────────────
step "Checking prerequisites"

command -v uv  >/dev/null 2>&1 || fail "uv not found. Install: https://docs.astral.sh/uv/"
command -v node >/dev/null 2>&1 || fail "node not found. Install Node.js >= 18."
command -v npm  >/dev/null 2>&1 || fail "npm not found. Comes with Node.js."

echo "  uv   : $(uv --version)"
echo "  node : $(node --version)"
echo "  npm  : $(npm --version)"

# ── 1. Locate the zip ───────────────────────────────────────────────────────
step "Locating Apple Health export zip"

if [[ -n "${1:-}" ]]; then
    ZIP_FILE="$1"
else
    # Auto-detect: find a .zip in the project root
    ZIP_FILE=""
    for f in "$ROOT"/*.zip; do
        [[ -f "$f" ]] && ZIP_FILE="$f" && break
    done
fi

[[ -z "$ZIP_FILE" ]] && fail "No zip file found in $ROOT. Pass the path as an argument: scripts/setup.sh /path/to/export.zip"
[[ ! -f "$ZIP_FILE" ]] && fail "File not found: $ZIP_FILE"

ZIP_SIZE=$(stat -f%z "$ZIP_FILE" 2>/dev/null || stat -c%s "$ZIP_FILE" 2>/dev/null)
echo "  Found: $ZIP_FILE ($(( ZIP_SIZE / 1024 / 1024 )) MB)"

# ── 2. Unzip the export ─────────────────────────────────────────────────────
EXPORT_DIR="$ROOT/apple_health_export"
EXPORT_XML="$EXPORT_DIR/export.xml"

if [[ -f "$EXPORT_XML" ]]; then
    warn "export.xml already exists at $EXPORT_XML — skipping unzip."
else
    step "Unzipping Apple Health export to $ROOT/"
    # Only extract export.xml (skip GPX routes — they can be large and are unused)
    unzip -o "$ZIP_FILE" "apple_health_export/export.xml" -d "$ROOT"
    echo "  Extracted: $EXPORT_XML"
fi

# ── 3. Install Python dependencies ──────────────────────────────────────────
step "Installing Python dependencies (uv sync)"
(cd "$ROOT" && uv sync)

# ── 4. Parse export.xml → Parquet files ──────────────────────────────────────
DATA_DIR="$ROOT/data"
PARQUET_FILES=("records.parquet" "workouts.parquet" "workout_stats.parquet" "activity_summary.parquet")

# Check if all expected parquet files exist
ALL_PRESENT=true
for pf in "${PARQUET_FILES[@]}"; do
    if [[ ! -f "$DATA_DIR/$pf" ]]; then
        ALL_PRESENT=false
        break
    fi
done

if $ALL_PRESENT; then
    warn "All Parquet files already present in $DATA_DIR — skipping parse."
    warn "To re-parse, delete the data/ directory and re-run this script."
else
    step "Parsing export.xml → Parquet (this may take a few minutes for large exports)"
    mkdir -p "$DATA_DIR"
    (cd "$ROOT" && uv run python scripts/parse_export.py)
fi

# ── 5. Install frontend dependencies ────────────────────────────────────────
step "Installing frontend dependencies (npm install)"
(cd "$ROOT/frontend" && npm install)

# ── 6. Start the dashboard ──────────────────────────────────────────────────
step "Starting dashboard"
echo "  Backend  → http://localhost:8001  (FastAPI + uvicorn)"
echo "  Frontend → http://localhost:5173  (Vite dev server)"
echo ""
echo "  Press Ctrl+C to stop both servers."
echo ""

# Trap SIGINT/SIGTERM to kill both background jobs
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill 0 2>/dev/null
    wait 2>/dev/null
    echo -e "${GREEN}Done.${NC}"
}
trap cleanup SIGINT SIGTERM

(cd "$ROOT" && uv run uvicorn backend.server:app --port 8001 --reload) &
(cd "$ROOT/frontend" && npm run dev) &

wait
