"""FastAPI server for the Health Dashboard."""

from datetime import date, timedelta

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from . import aggregations as agg
from .data_loader import max_date, min_date

app = FastAPI(title="Health Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/meta")
def meta():
    return {"min_date": str(min_date), "max_date": str(max_date)}


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
):
    return agg.get_vo2(start, end) or {"traces": [], "layout": {}}


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
