# Apple Health Dashboard — Setup Guide

This file contains step-by-step instructions for an LLM assistant to help a user set up the Apple Health Dashboard. If you are an LLM reading this, follow the steps below to guide the user from "I have an Apple Health export zip" to "dashboard is running in my browser."

The user has either cloned this repository with `git` or downloaded and extracted it as a zip. This file lives in the project root — use its location to determine `PROJECT_DIR`.

## Project layout

```
apple-health-dashboard/
├── SETUP.md              # You are here
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

## Important: Run commands on the user's machine

All commands must run directly on the user's local machine — not in a sandbox or containerized environment. The setup installs Python and Node dependencies, writes files to disk, and starts persistent dev servers. If your tool for running shell commands uses sandboxing by default, disable it for every command in this guide.

---

## Step 1 — Locate the export zip

If the user hasn't told you where their Apple Health export zip is, search common locations:

```bash
ls ~/Downloads/*.zip "$PROJECT_DIR"/*.zip 2>/dev/null
```

- **User specified a path**: confirm it exists with `ls -lh <path>` and proceed.
- **Exactly one zip found**: use it automatically.
- **Multiple zips found**: ask the user which one to use.
- **No zip found**: ask the user where their export zip is. They can export it from the iPhone Health app via **Share → Export All Health Data**.

Also check whether `$PROJECT_DIR/profile.json` exists. If not, ask the user for their display name and gender (gender affects VO2 max reference bands), then create the file:

```json
{ "display_name": "Your Name", "gender": "male" }
```

## Step 2 — Check prerequisites

Run these commands to verify the required tools are installed:

```bash
command -v uv && uv --version
command -v node && node --version
command -v npm && npm --version
```

If anything is missing, help the user install it:
- **uv** (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **node / npm**: `brew install node` (macOS) or download from https://nodejs.org

## Step 3 — Fix a stale virtual environment

If the project was previously set up in a different directory (e.g. moved from iCloud Drive), the `.venv` shebangs will point to the old path and nothing will run. Check:

```bash
head -3 "$PROJECT_DIR/.venv/bin/uvicorn" 2>/dev/null
```

If the shebang path does not match `$PROJECT_DIR`, the venv is broken. Rebuild it:

```bash
cd "$PROJECT_DIR" && rm -rf .venv && uv sync
```

If `.venv` does not exist at all, skip this step — the setup script will create it.

## Step 4 — Run the setup pipeline

Run the setup script with `NO_SERVE=1` so it completes and exits instead of blocking on long-running servers:

```bash
cd "$PROJECT_DIR" && NO_SERVE=1 scripts/setup.sh /path/to/export.zip
```

Replace `/path/to/export.zip` with the actual path from Step 1.

What the script does:
1. Extracts `export.xml` from the zip (skips large GPX files)
2. Installs Python dependencies via `uv sync`
3. Parses `export.xml` into Parquet files in `data/` — this streams a ~2 GB XML file and takes a few minutes. **Tell the user this is expected so they don't think it's stuck.**
4. Installs frontend dependencies via `npm install`

## Step 5 — Start the dashboard

The dashboard runs two long-lived dev servers (backend + frontend). Start them as background processes so they persist and your shell tool returns immediately:

```bash
cd "$PROJECT_DIR" && scripts/run.sh &
```

If your environment requires permission to run background processes or open network ports, prompt the user for approval before executing.

After starting, verify both servers are healthy:

```bash
sleep 3 && curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/meta && echo " backend OK"
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 && echo " frontend OK"
```

Once both return `200`, tell the user to open http://localhost:5173 in their browser.

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8001

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No such file or directory: .venv/bin/python` | Stale venv — `cd "$PROJECT_DIR" && rm -rf .venv && uv sync` |
| Port already in use | `lsof -ti:8001 -ti:5173 \| xargs kill -9` |
| `export.xml` not found in zip | Open the zip manually and confirm it contains `apple_health_export/export.xml` |
| Dashboard shows no charts | Backend may have failed — check terminal for errors, try `curl http://localhost:8001/api/meta` |
| Refresh with new data | Delete `$PROJECT_DIR/data/` and `$PROJECT_DIR/apple_health_export/`, then re-run Step 4 with the new zip |

## Restarting without full setup

If everything is already installed and parsed, just restart the servers:

```bash
cd "$PROJECT_DIR" && scripts/run.sh &
```
