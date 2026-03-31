"""FastAPI server for the Health Dashboard."""

import json
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import aggregations as agg
from .data_loader import get_date_bounds

PROFILE_PATH = Path(__file__).resolve().parent.parent / "profile.json"
DEFAULT_PROFILE = {"display_name": "", "gender": "male"}

app = FastAPI(title="Health Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _read_profile() -> dict:
    try:
        return json.loads(PROFILE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_PROFILE.copy()


class ProfileBody(BaseModel):
    display_name: str = ""
    gender: Literal["male", "female"] = "male"


@app.get("/api/meta")
def meta():
    min_date, max_date = get_date_bounds()
    return {
        "min_date": str(min_date),
        "max_date": str(max_date),
        "profile": _read_profile(),
    }


@app.post("/api/profile")
def save_profile(body: ProfileBody):
    data = body.model_dump()
    PROFILE_PATH.write_text(json.dumps(data, indent=2) + "\n")
    return data


@app.get("/api/kpis")
def kpis(
    start: date = Query(...),
    end: date = Query(...),
):
    return agg.get_kpis(start, end)


@app.get("/api/workouts")
def workouts_endpoint(
    start: date = Query(...),
    end: date = Query(...),
):
    data = agg.get_workouts(start, end)
    return data or {"donut": None, "bar": None, "types": []}


@app.get("/api/vo2")
def vo2(
    start: date = Query(...),
    end: date = Query(...),
    gender: str = Query("male"),
):
    return agg.get_vo2(start, end, gender) or {"traces": [], "layout": {}}


@app.get("/api/rhr-hrv")
def rhr_hrv(
    start: date = Query(...),
    end: date = Query(...),
):
    return agg.get_rhr_hrv(start, end) or {"traces": [], "layout": {}}


@app.get("/api/sleep-stages")
def sleep_stages(
    start: date = Query(...),
    end: date = Query(...),
):
    return agg.get_sleep_stages(start, end) or {"traces": [], "layout": {}}


@app.get("/api/sleep-duration")
def sleep_duration(
    start: date = Query(...),
    end: date = Query(...),
):
    return agg.get_sleep_duration(start, end) or {"traces": [], "layout": {}}


@app.get("/api/sleep-consistency")
def sleep_consistency(
    start: date = Query(...),
    end: date = Query(...),
):
    return agg.get_sleep_consistency(start, end) or {
        "traces": [],
        "layout": {},
    }


@app.get("/api/wrist-temp")
def wrist_temp(
    start: date = Query(...),
    end: date = Query(...),
):
    return agg.get_wrist_temp(start, end) or {"traces": [], "layout": {}}
