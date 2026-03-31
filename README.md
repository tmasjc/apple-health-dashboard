# Apple Health Dashboard

Visualize your Apple Health data — sleep stages, workouts, VO2 max, resting heart rate, HRV, wrist temperature, and more — in a local dashboard built with FastAPI and React.

## 1. Get Your Health Data

1. Open the **Health** app on your iPhone
2. Tap your profile picture (top right)
3. Scroll down and tap **Export All Health Data**
4. Confirm the export — this may take a few minutes depending on how much data you have
5. Transfer the resulting zip file to your Mac (AirDrop, iCloud Drive, USB, etc.)

## 2. Set Up the Dashboard

**Prerequisites:** [uv](https://docs.astral.sh/uv/) (Python toolchain) and [Node.js](https://nodejs.org/) >= 18.

### Option A — With an LLM (non-technical)

Open any LLM that can run shell commands — Claude Code, Cursor, Windsurf, GitHub Copilot, ChatGPT with terminal access, etc. Point it at this project and say:

> Set up the Apple Health dashboard with my health export. Follow the instructions in SETUP.md.

The LLM will read [`SETUP.md`](SETUP.md), install dependencies, parse your data, and start the dashboard for you.

### Option B — With the terminal (technical)

```bash
scripts/setup.sh /path/to/export.zip   # full pipeline: unzip, install deps, parse, serve
```

To restart the servers later without re-parsing:

```bash
scripts/run.sh
```

## 3. What You Get

Once setup completes, open http://localhost:5173 in your browser. The dashboard shows:

- **KPI cards** — daily step count, distance, flights climbed, active energy
- **Workouts** — history with duration, calories, heart rate, and distance
- **VO2 max** — trend over time with age/gender reference bands
- **Resting heart rate & HRV** — daily trends
- **Sleep stages** — nightly breakdown (REM, deep, core, awake)
- **Sleep duration & consistency** — how long and how consistently you sleep
- **Wrist temperature** — nightly baseline deviations

All charts are interactive (zoom, pan, hover for details) and filterable by date range.
