# Apple Health Dashboard

A personal dashboard for visualizing Apple Health data, built with FastAPI and React/Vite.

## Quick Start

This project is designed to be set up by a LLM agent. Just activate your LLM in this directory and say:

> I have my Apple Health export zip. Set up the dashboard.

The agent reads `SKILL.md` and handles everything: locating your zip, installing dependencies, parsing the data, and launching the dashboard.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python toolchain)
- [Node.js](https://nodejs.org/) >= 18

## Manual Setup

If you prefer to run it yourself:

```bash
# Full pipeline: unzip, parse, install, serve
scripts/setup.sh /path/to/apple_health_export.zip

# Or restart servers only (after initial setup)
scripts/run.sh
```

Then open http://localhost:5173.

## Exporting Data from iPhone

Open the **Health** app on your iPhone, tap your profile picture, then **Export All Health Data**. This produces a zip file you can AirDrop or transfer to your Mac.
