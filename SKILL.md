---
name: apple-health-dashboard
description: Build, set up, fix, or restart the Apple Health dashboard from an iPhone export zip. ALWAYS use this skill when the user mentions any of: "apple health", "health export", "health dashboard", "health data zip", "export.xml", "setup.sh", "parse_export", iPhone health data, sleep/workout/VO2 stats visualization, or troubleshooting a broken health dashboard (e.g. after moving folders, stale venv, blank page). Also trigger for vague requests like "I want to see my health data", "I have my health export", or "the dashboard isn't working". This skill handles cold start, data refresh, and common failures.
---

# Apple Health Dashboard

Turns a raw Apple Health export zip into a running FastAPI + React dashboard. The project lives at `~/Github/apple-health-dashboard/`. Your job is to take the user from "I have a zip" to "dashboard is open in my browser" with minimal friction.

## Project layout

```
apple-health-dashboard/
├── SKILL.md              # You are here — the skill entry point
├── CLAUDE.md             # Dev reference (architecture, conventions)
├── profile.json          # User display name + gender (gitignored)
├── pyproject.toml
├── scripts/
│   ├── setup.sh          # End-to-end: unzip → parse → install → serve
│   ├── run.sh            # Restart servers only (no setup)
│   └── parse_export.py   # Streaming XML → Parquet converter
├── backend/              # FastAPI API server
├── frontend/             # React + Vite UI
├── data/                 # Parquet files (gitignored, generated)
└── tests/
```

## Step 0 — Locate the zip file

If the user hasn't specified a path, search common spots:

```bash
ls ~/Downloads/*.zip ~/Github/apple-health-dashboard/*.zip 2>/dev/null
```

Then apply this logic:
- **User specified a path**: confirm it exists with `ls -lh <path>` and proceed
- **Exactly one zip found**: use it — no need to ask
- **Multiple zips found**: ask the user which one to use (`AskUserQuestion`)
- **No zip found**: ask where the export zip is (`AskUserQuestion`) — the user exports it from the iPhone Health app via Share > Export All Health Data

Also ask — or read `profile.json` — whether the user wants to update their display name or gender before setup (gender affects VO2 max reference bands):
```json
{ "display_name": "Your Name", "gender": "male" }
```

## Step 1 — Check prerequisites

```bash
command -v uv && uv --version
command -v node && node --version
command -v npm && npm --version
```

If anything is missing:
- **uv** (Python toolchain): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **node / npm**: `brew install node` or nodejs.org

## Step 2 — Fix a stale virtual environment (very common)

If the project was ever moved between folders (e.g., iCloud Drive to GitHub), the `.venv` shebangs point to the old path and nothing will run. Check:

```bash
head -3 ~/Github/apple-health-dashboard/.venv/bin/uvicorn 2>/dev/null
```

If the path in the shebang doesn't match the current project location, the venv is broken. Rebuild it:

```bash
cd ~/Github/apple-health-dashboard && rm -rf .venv && uv sync
```

## Step 3 — Run the setup pipeline

`scripts/setup.sh` does everything in one shot:

```bash
cd ~/Github/apple-health-dashboard && scripts/setup.sh /path/to/export.zip
```

What it does internally:
1. Extracts only `export.xml` from the zip (skips large GPX files)
2. Runs `uv sync` (Python deps)
3. Parses `export.xml` into Parquet files in `data/` via `scripts/parse_export.py`
4. Runs `npm install` in `frontend/`
5. Starts both servers and blocks (Ctrl+C to stop)

The parse step streams a ~2 GB XML file — it takes a few minutes. Let the user know so they don't think it's hung.

## Step 4 — Open the dashboard

Once both servers are running:
```bash
open http://localhost:5173
```

Backend API is at `http://localhost:8001` if the user wants to poke at it directly.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No such file or directory: .venv/bin/python` | Stale venv — `rm -rf .venv && uv sync` |
| Port already in use | `lsof -ti:8001 -ti:5173 \| xargs kill -9` |
| `export.xml` not found | Open the zip manually, confirm it contains `apple_health_export/export.xml` |
| Dashboard shows no charts | Backend may have failed to start — check terminal for errors, try `curl http://localhost:8001/api/meta` |
| Want to refresh with new data | Delete `data/` and `apple_health_export/` then re-run `scripts/setup.sh /new/export.zip` |

## Re-running without setup

If everything is already installed and the user just wants to restart the servers:
```bash
cd ~/Github/apple-health-dashboard && scripts/run.sh
```
