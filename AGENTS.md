# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A personal health dashboard visualising Apple Health data. It has two generations:

1. **Legacy Streamlit app** (`app.py`) — standalone, run with `uv run streamlit run app.py`
2. **Current full-stack app** (FastAPI + React/Vite) — the active version

## Running the App

```bash
# Start both backend and frontend dev servers concurrently:
./run.sh

# Or start them individually:
uv run uvicorn backend.server:app --port 8001 --reload   # API at localhost:8001
cd frontend && npm run dev                                 # UI at localhost:5173
```

Frontend proxies `/api` requests to the backend via Vite config.

```bash
# Frontend lint
cd frontend && npx eslint .

# Frontend build
cd frontend && npm run build
```

## Data Pipeline

`parse_export.py` is a streaming XML parser (lxml iterparse) that converts Apple Health `export.xml` (~2 GB) into Parquet files in `data/`. The `data/` directory is gitignored. Four Parquet files are produced: `records.parquet`, `workouts.parquet`, `workout_stats.parquet`, `activity_summary.parquet`.

Run the parser: `uv run python parse_export.py` (expects `apple_health_export/export.xml` inside the project root).

## Architecture

### Backend (`backend/`)

- **`data_loader.py`** — Loads all Parquet files into pandas DataFrames at import time; prepares a derived `sleep_df` DataFrame. Exposes `records`, `workouts`, `activity`, `sleep_df`, `min_date`, `max_date`.
- **`aggregations.py`** — Pure functions (`get_kpis`, `get_workouts`, `get_vo2`, `get_rhr_hrv`, `get_sleep_stages`, `get_sleep_duration`, `get_sleep_consistency`, `get_wrist_temp`) that filter/aggregate DataFrames and return Plotly-compatible JSON dicts (traces + layout).
- **`constants.py`** — Color palette and shared Plotly layout config.
- **`server.py`** — FastAPI app. All endpoints accept `start` and `end` date query params and delegate to `aggregations`.

API endpoints: `/api/meta`, `/api/kpis`, `/api/workouts`, `/api/vo2`, `/api/rhr-hrv`, `/api/sleep-stages`, `/api/sleep-duration`, `/api/sleep-consistency`, `/api/wrist-temp`.

### Frontend (`frontend/`)

React 19 + TypeScript + Vite. Charts rendered with `react-plotly.js`. Data fetching via TanStack React Query.

- **`src/api/`** — API client (`fetchApi`) and TypeScript types for API responses.
- **`src/hooks/useHealthData.ts`** — React Query hooks for each endpoint. `usePlotEndpoint` is generic for any traces+layout endpoint.
- **`src/components/`** — `KpiCards`, `WorkoutPanel`, `ChartCard`, `PlotlyChart`, `DateRangeSlider`, `Plot`.
- **`src/theme/`** — CSS styles and color constants.

### Key Pattern

Backend aggregation functions return `{"traces": [...], "layout": {...}}` dicts that the frontend passes directly to Plotly. The frontend does not transform chart data — it renders whatever the backend returns.
