# Apple Health Dashboard

Visualize your Apple Health data with a FastAPI + React dashboard.

## Setup

Install [`SKILL.md`](SKILL.md) as a skill in Claude Code (or any agent that supports skills), then say:

> Set up the dashboard with my health export.

The skill handles everything: locating your zip, installing dependencies, parsing the data, and launching the dashboard.

**Requires:** [uv](https://docs.astral.sh/uv/), [Node.js](https://nodejs.org/) >= 18

**Manual alternative:**

```bash
scripts/setup.sh /path/to/export.zip   # full pipeline
scripts/run.sh                          # restart servers only
```

Dashboard runs at http://localhost:5173.

## Getting Your Data

iPhone Health app > profile picture > **Export All Health Data** > AirDrop or transfer the zip to your Mac.
