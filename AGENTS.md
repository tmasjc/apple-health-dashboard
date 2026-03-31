# CLAUDE.md

This file provides development guidance for contributors. For setup and running instructions, see `SKILL.md`.

## Architecture

### Backend (`backend/`)

- **`data_loader.py`** — Query-based data access using PyArrow filtered reads. Exposes `query_records(start, end, record_type)`, `query_sleep(start, end)`, `get_workouts()`, `get_activity()`, `get_date_bounds()`. Records are read from Parquet on demand with predicate pushdown; workouts and activity are lazily cached in memory.
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

### Scripts (`scripts/`)

- **`setup.sh`** — Full pipeline: unzip export, install deps, parse XML, start servers.
- **`run.sh`** — Restart servers only (skips setup steps).
- **`parse_export.py`** — Streaming XML parser (lxml iterparse) converting Apple Health `export.xml` (~2 GB) into four Parquet files in `data/`: `records.parquet`, `workouts.parquet`, `workout_stats.parquet`, `activity_summary.parquet`.

## Dev Commands

```bash
# Frontend lint
cd frontend && npx eslint .

# Frontend build
cd frontend && npm run build

# Python tests
uv run pytest

# Start servers (dev)
scripts/run.sh
```

Frontend proxies `/api` requests to the backend via Vite config.
