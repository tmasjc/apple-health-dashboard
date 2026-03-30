"""Data aggregation functions — each returns JSON-serialisable dicts."""

from __future__ import annotations

import math
from datetime import date
from typing import Any

import pandas as pd

from .constants import (
    BLUE, GREEN, ORANGE, PINK, PURPLE, TEAL,
    CHART_LAYOUT, SLEEP_STAGE_COLORS, build_workout_color_map,
)
from .data_loader import activity, records, sleep_df, workouts


# ── Helpers ─────────────────────────────────────────────────────────────────


def filter_date(
    df: pd.DataFrame,
    start: date,
    end: date,
    col: str = "startDate",
) -> pd.DataFrame:
    if df.empty:
        return df
    series = df[col]
    if pd.api.types.is_datetime64_any_dtype(series):
        ts_start = pd.Timestamp(start)
        ts_end = pd.Timestamp(end) + pd.Timedelta(days=1)
        tz = getattr(series.dt, "tz", None)
        if tz is not None:
            ts_start = ts_start.tz_localize(tz)
            ts_end = ts_end.tz_localize(tz)
        return df[(series >= ts_start) & (series <= ts_end)]
    return df[(series >= start) & (series <= end)]


def _base_layout(height: int = 400, **overrides: Any) -> dict:
    layout = {**CHART_LAYOUT, "height": height, "margin": {"l": 48, "r": 24, "t": 32, "b": 40}}
    layout.update(overrides)
    return layout


def _get_type(df: pd.DataFrame, type_name: str) -> pd.DataFrame:
    return df[df["type"] == type_name].copy()


def _safe_list(values) -> list:
    """Convert to list, replacing NaN/inf with None for JSON compliance."""
    return [None if (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else v for v in values]


def _hour_to_time_str(h: float, short: bool = False) -> str:
    if h < 0:
        h += 24
    hour = int(h) % 24
    minute = int((h % 1) * 60)
    period = "AM" if hour < 12 else "PM"
    display_h = hour % 12 or 12
    if short:
        if minute == 0:
            return f"{display_h} {period}"
        return f"{display_h}:{minute:02d} {period}"
    return f"{display_h}:{minute:02d} {period}"


# ── KPI ─────────────────────────────────────────────────────────────────────


def get_kpis(start: date, end: date) -> dict:
    act_f = filter_date(activity, start, end, col="date")
    rec_f = filter_date(records, start, end)

    # Preceding period of equal length for delta calculation
    range_days = (end - start).days
    prev_start = start - pd.Timedelta(days=range_days)
    prev_end = start - pd.Timedelta(days=1)
    act_prev = filter_date(activity, prev_start, prev_end, col="date")

    def _kpi(col: str) -> dict:
        if act_f.empty:
            return {"value": 0, "delta": 0}
        cur = act_f[col].mean()
        prev = act_prev[col].mean() if not act_prev.empty else 0
        delta = ((cur - prev) / prev * 100) if prev else 0
        return {"value": round(float(cur), 1), "delta": round(float(delta), 1)}

    result = {
        "active_kcal": _kpi("activeEnergyBurned"),
        "exercise_min": _kpi("appleExerciseTime"),
        "stand_hrs": _kpi("appleStandHours"),
    }

    steps = _get_type(rec_f, "HKQuantityTypeIdentifierStepCount")
    if not steps.empty and not act_f.empty:
        steps_daily = steps.groupby("date")["value"].sum()
        # Current range dates
        cur_dates = pd.date_range(start=start, end=end).date
        cur_steps = steps_daily.reindex(cur_dates).mean()
        # Previous range dates
        prev_dates = pd.date_range(start=prev_start, end=prev_end).date
        rec_prev = filter_date(records, prev_start, prev_end)
        steps_prev = _get_type(rec_prev, "HKQuantityTypeIdentifierStepCount")
        if not steps_prev.empty:
            steps_daily_prev = steps_prev.groupby("date")["value"].sum()
            prev_steps = steps_daily_prev.reindex(prev_dates).mean()
        else:
            prev_steps = 0
        delta_steps = (
            ((cur_steps - prev_steps) / prev_steps * 100) if prev_steps else 0
        )
        result["steps"] = {
            "value": round(float(cur_steps), 0) if not pd.isna(cur_steps) else 0,
            "delta": round(float(delta_steps), 1) if not pd.isna(delta_steps) else 0,
        }
    else:
        result["steps"] = {"value": 0, "delta": 0}

    return result


# ── Workouts ────────────────────────────────────────────────────────────────


def get_workouts(start: date, end: date) -> dict | None:
    wk = filter_date(workouts, start, end)
    if wk.empty:
        return None

    # Donut data
    wk_counts = (
        wk["workoutActivityType"]
        .str.replace("HKWorkoutActivityType", "")
        .value_counts()
    )
    color_map = build_workout_color_map(wk_counts.index.tolist())
    donut_traces = [
        {
            "type": "pie",
            "labels": wk_counts.index.tolist(),
            "values": wk_counts.values.tolist(),
            "hole": 0.45,
            "marker": {
                "colors": [
                    color_map[t] for t in wk_counts.index
                ],
                "line": {"color": "#000000", "width": 1},
            },
            "textfont": {"color": "#1d1d1f"},
            "showlegend": False,
            "hovertemplate": "%{label}: %{value} sessions<extra></extra>",
        }
    ]

    # Bar data
    wk2 = wk.copy()
    wk2["type_short"] = wk2["workoutActivityType"].str.replace(
        "HKWorkoutActivityType", ""
    )
    wk2["month"] = wk2["startDate"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        wk2.groupby(["month", "type_short"]).size().reset_index(name="count")
    )
    bar_traces = []
    for wtype in monthly["type_short"].unique():
        sub = monthly[monthly["type_short"] == wtype]
        bar_traces.append(
            {
                "type": "bar",
                "x": sub["month"].dt.strftime("%Y-%m").tolist(),
                "y": sub["count"].tolist(),
                "name": wtype,
                "marker": {
                    "color": color_map.get(wtype, "#8E8E93"),
                    "line": {"color": "#000000", "width": 1},
                },
                "showlegend": False,
                "hovertemplate": f"{wtype}: " + "%{y} sessions<extra></extra>",
            }
        )

    # All workout types present (for shared legend)
    all_types = sorted(set(wk_counts.index.tolist()))

    return {
        "donut": {
            "traces": donut_traces,
            "layout": _base_layout(),
        },
        "bar": {
            "traces": bar_traces,
            "layout": _base_layout(
                barmode="stack",
                xaxis={"gridcolor": "#e5e5e7", "zerolinecolor": "#d1d1d6"},
                yaxis={
                    "gridcolor": "#e5e5e7",
                    "zerolinecolor": "#d1d1d6",
                    "title": {"text": "Sessions"},
                },
            ),
        },
        "types": [
            {"name": t, "color": color_map[t]}
            for t in all_types
        ],
    }


# ── VO2 Max ─────────────────────────────────────────────────────────────────


VO2_BANDS: dict[str, list[tuple[str, float, float, str]]] = {
    "male": [
        ("Superior",   51.1, 60.0, GREEN),
        ("Excellent",  43.9, 51.1, BLUE),
        ("Good",       36.7, 43.9, ORANGE),
        ("Below Good", 20.0, 36.7, "#FF3B30"),
    ],
    "female": [
        ("Superior",   44.2, 55.0, GREEN),
        ("Excellent",  37.8, 44.2, BLUE),
        ("Good",       30.2, 37.8, ORANGE),
        ("Below Good", 20.0, 30.2, "#FF3B30"),
    ],
}


def get_vo2(start: date, end: date, gender: str = "male") -> dict | None:
    rec_f = filter_date(records, start, end)
    vo2 = _get_type(rec_f, "HKQuantityTypeIdentifierVO2Max")
    if vo2.empty:
        return None

    vo2_daily = (
        vo2.groupby("date")["value"].mean().reset_index().sort_values("date")
    )

    bands = VO2_BANDS.get(gender, VO2_BANDS["male"])
    shapes = [
        {
            "type": "rect", "xref": "paper", "x0": 0, "x1": 1,
            "y0": y0, "y1": y1, "fillcolor": color, "opacity": 0.08,
            "line": {"width": 0},
        }
        for _, y0, y1, color in bands
    ]
    annotations = [
        {
            "x": 1, "xref": "paper", "xanchor": "right",
            "y": (y0 + y1) / 2, "text": label, "showarrow": False,
            "font": {"size": 10, "color": "#86868b"},
        }
        for label, y0, y1, _ in bands
    ]

    traces = [
        {
            "type": "scatter",
            "x": [str(d) for d in vo2_daily["date"]],
            "y": _safe_list(vo2_daily["value"]),
            "mode": "markers",
            "name": "VO2 Max",
            "marker": {"color": BLUE, "size": 5, "opacity": 0.6},
            "hovertemplate": "%{x}<br>%{y:.1f} mL/min/kg<extra></extra>",
        }
    ]

    if len(vo2_daily) > 10:
        vo2_daily["rolling"] = (
            vo2_daily["value"].rolling(10, min_periods=3).mean()
        )
        traces.append(
            {
                "type": "scatter",
                "x": [str(d) for d in vo2_daily["date"]],
                "y": _safe_list(vo2_daily["rolling"]),
                "mode": "lines",
                "name": "Trend",
                "line": {"color": ORANGE, "width": 2, "shape": "spline"},
                "hovertemplate": "%{x}<br>Trend: %{y:.1f}<extra></extra>",
            }
        )

    return {
        "traces": traces,
        "layout": _base_layout(
            shapes=shapes,
            annotations=annotations,
            yaxis={
                "title": {"text": "mL/min/kg"},
                "gridcolor": "#e5e5e7",
                "zerolinecolor": "#d1d1d6",
            },
        ),
    }


# ── RHR & HRV ──────────────────────────────────────────────────────────────


def get_rhr_hrv(start: date, end: date) -> dict | None:
    rec_f = filter_date(records, start, end)
    rhr = _get_type(rec_f, "HKQuantityTypeIdentifierRestingHeartRate")
    hrv = _get_type(rec_f, "HKQuantityTypeIdentifierHeartRateVariabilitySDNN")
    if rhr.empty or hrv.empty:
        return None

    rhr["week"] = rhr["startDate"].dt.to_period("W").dt.to_timestamp()
    hrv["week"] = hrv["startDate"].dt.to_period("W").dt.to_timestamp()
    rhr_w = rhr.groupby("week")["value"].mean()
    hrv_w = hrv.groupby("week")["value"].mean()

    traces = [
        {
            "type": "scatter",
            "x": rhr_w.index.strftime("%Y-%m-%d").tolist(),
            "y": [round(v, 1) for v in rhr_w.values],
            "name": "Resting HR (bpm)",
            "line": {"color": PINK, "width": 2, "shape": "spline"},
            "yaxis": "y",
            "hovertemplate": "%{x}<br>RHR: %{y:.1f} bpm<extra></extra>",
        },
        {
            "type": "scatter",
            "x": hrv_w.index.strftime("%Y-%m-%d").tolist(),
            "y": [round(v, 1) for v in hrv_w.values],
            "name": "HRV SDNN (ms)",
            "line": {"color": BLUE, "width": 2, "shape": "spline"},
            "yaxis": "y2",
            "hovertemplate": "%{x}<br>HRV: %{y:.1f} ms<extra></extra>",
        },
    ]

    layout = _base_layout(
        yaxis={
            "title": {"text": "Resting HR (bpm)"},
            "gridcolor": "#e5e5e7",
            "zerolinecolor": "#d1d1d6",
        },
        yaxis2={
            "title": {"text": "HRV SDNN (ms)"},
            "overlaying": "y",
            "side": "right",
            "gridcolor": "#e5e5e7",
            "zerolinecolor": "#d1d1d6",
        },
    )

    return {"traces": traces, "layout": layout}


# ── Sleep Stages ────────────────────────────────────────────────────────────


def get_sleep_stages(start: date, end: date) -> dict | None:
    sdf = filter_date(sleep_df, start, end, col="night")
    if sdf.empty:
        return None

    stage_order = ["Deep", "Core", "REM", "Awake"]
    staged = sdf[sdf["stage"].isin(stage_order)].copy()
    if staged.empty:
        return None

    staged["week"] = (
        pd.to_datetime(staged["night"]).dt.to_period("W").dt.to_timestamp()
    )

    weekly = (
        staged.groupby(["week", "stage"])["duration_min"]
        .sum()
        .unstack(fill_value=0)
    )
    for s in stage_order:
        if s not in weekly.columns:
            weekly[s] = 0
    weekly = weekly[stage_order].sort_index()

    nights_per_week = staged.groupby("week")["night"].nunique()
    for s in stage_order:
        weekly[s] = weekly[s] / nights_per_week / 60

    traces = []
    for stage in stage_order:
        traces.append(
            {
                "type": "bar",
                "x": weekly.index.strftime("%Y-%m-%d").tolist(),
                "y": [round(v, 2) for v in weekly[stage]],
                "name": stage,
                "marker": {"color": SLEEP_STAGE_COLORS[stage]},
                "hovertemplate": f"{stage}: " + "%{y:.1f} hrs<extra></extra>",
            }
        )

    return {
        "traces": traces,
        "layout": _base_layout(
            barmode="stack",
            yaxis={
                "title": {"text": "Avg Hours / Night"},
                "gridcolor": "#e5e5e7",
                "zerolinecolor": "#d1d1d6",
            },
        ),
    }


# ── Sleep Duration ──────────────────────────────────────────────────────────


def get_sleep_duration(start: date, end: date) -> dict | None:
    sdf = filter_date(sleep_df, start, end, col="night")
    if sdf.empty:
        return None

    total_per_night = (
        sdf[sdf["stage"].isin(["Deep", "Core", "REM"])]
        .groupby("night")["duration_min"]
        .sum()
        .sort_index()
    )
    if total_per_night.empty:
        return None

    total_hrs = total_per_night / 60
    rolling = total_hrs.rolling(7, min_periods=1).mean()

    traces = [
        {
            "type": "scatter",
            "x": [str(d) for d in total_hrs.index],
            "y": [round(v, 2) for v in total_hrs.values],
            "mode": "markers",
            "name": "Nightly",
            "marker": {"size": 3, "opacity": 0.4, "color": BLUE},
            "hovertemplate": "%{x}<br>%{y:.1f} hrs<extra></extra>",
        },
        {
            "type": "scatter",
            "x": [str(d) for d in rolling.index],
            "y": [round(v, 2) for v in rolling.values],
            "mode": "lines",
            "name": "7-day avg",
            "line": {"color": GREEN, "width": 2, "shape": "spline"},
            "hovertemplate": "%{x}<br>Avg: %{y:.1f} hrs<extra></extra>",
        },
    ]

    return {
        "traces": traces,
        "layout": _base_layout(
            yaxis={
                "title": {"text": "Hours"},
                "gridcolor": "#e5e5e7",
                "zerolinecolor": "#d1d1d6",
            },
        ),
    }


# ── Sleep Consistency ───────────────────────────────────────────────────────


def get_sleep_consistency(start: date, end: date) -> dict | None:
    sdf = filter_date(sleep_df, start, end, col="night")
    if sdf.empty:
        return None

    asleep = sdf[sdf["stage"].isin(["Deep", "Core", "REM", "Asleep"])]
    if asleep.empty:
        return None

    bed = asleep.groupby("night")["startDate"].min()
    wake = asleep.groupby("night")["endDate"].max()
    consistency = pd.DataFrame({"bedtime": bed, "waketime": wake}).dropna()
    consistency["bed_hour"] = (
        consistency["bedtime"].dt.hour + consistency["bedtime"].dt.minute / 60
    )
    consistency["wake_hour"] = (
        consistency["waketime"].dt.hour
        + consistency["waketime"].dt.minute / 60
    )
    consistency["bed_hour_adj"] = consistency["bed_hour"].apply(
        lambda h: h - 24 if h >= 18 else h
    )
    consistency = consistency[
        (consistency["bed_hour_adj"] >= -6)
        & (consistency["bed_hour_adj"] <= 6)
    ]
    if consistency.empty:
        return None

    consistency["bed_roll"] = (
        consistency["bed_hour_adj"].rolling(7, min_periods=1).mean()
    )
    consistency["wake_roll"] = (
        consistency["wake_hour"].rolling(7, min_periods=1).mean()
    )

    consistency["bed_label"] = consistency["bed_hour_adj"].apply(
        _hour_to_time_str
    )
    consistency["wake_label"] = consistency["wake_hour"].apply(
        _hour_to_time_str
    )
    consistency["bed_roll_label"] = consistency["bed_roll"].apply(
        _hour_to_time_str
    )
    consistency["wake_roll_label"] = consistency["wake_roll"].apply(
        _hour_to_time_str
    )

    bed_ticks = list(range(-6, 7))
    bed_labels = [_hour_to_time_str(h, short=True) for h in bed_ticks]
    wake_ticks = list(range(4, 14))
    wake_labels = [_hour_to_time_str(h, short=True) for h in wake_ticks]

    idx_str = [str(d) for d in consistency.index]

    traces = [
        {
            "type": "scatter",
            "x": idx_str,
            "y": _safe_list(consistency["bed_hour_adj"]),
            "mode": "markers",
            "marker": {"size": 3, "opacity": 0.4, "color": PURPLE},
            "name": "Bedtime",
            "text": consistency["bed_label"].tolist(),
            "hovertemplate": "%{x}<br>%{text}<extra></extra>",
            "xaxis": "x",
            "yaxis": "y",
        },
        {
            "type": "scatter",
            "x": idx_str,
            "y": _safe_list(consistency["bed_roll"]),
            "mode": "lines",
            "line": {"color": PURPLE, "width": 2, "shape": "spline"},
            "name": "Bedtime trend",
            "showlegend": False,
            "text": consistency["bed_roll_label"].tolist(),
            "hovertemplate": "%{x}<br>Avg: %{text}<extra></extra>",
            "xaxis": "x",
            "yaxis": "y",
        },
        {
            "type": "scatter",
            "x": idx_str,
            "y": _safe_list(consistency["wake_hour"]),
            "mode": "markers",
            "marker": {"size": 3, "opacity": 0.4, "color": ORANGE},
            "name": "Wake",
            "text": consistency["wake_label"].tolist(),
            "hovertemplate": "%{x}<br>%{text}<extra></extra>",
            "xaxis": "x2",
            "yaxis": "y2",
        },
        {
            "type": "scatter",
            "x": idx_str,
            "y": _safe_list(consistency["wake_roll"]),
            "mode": "lines",
            "line": {"color": ORANGE, "width": 2, "shape": "spline"},
            "name": "Wake trend",
            "showlegend": False,
            "text": consistency["wake_roll_label"].tolist(),
            "hovertemplate": "%{x}<br>Avg: %{text}<extra></extra>",
            "xaxis": "x2",
            "yaxis": "y2",
        },
    ]

    layout = _base_layout(
        showlegend=False,
        grid={"rows": 1, "columns": 2, "pattern": "independent"},
        margin={"l": 64, "r": 56, "t": 32, "b": 40},
        xaxis={"gridcolor": "#e5e5e7", "zerolinecolor": "#d1d1d6",
               "domain": [0, 0.47]},
        yaxis={"gridcolor": "#e5e5e7", "zerolinecolor": "#d1d1d6",
               "tickvals": bed_ticks, "ticktext": bed_labels,
               "domain": [0, 1]},
        xaxis2={"gridcolor": "#e5e5e7", "zerolinecolor": "#d1d1d6",
                "domain": [0.53, 1], "anchor": "y2"},
        yaxis2={"gridcolor": "#e5e5e7", "zerolinecolor": "#d1d1d6",
                "tickvals": wake_ticks, "ticktext": wake_labels,
                "domain": [0, 1], "anchor": "x2"},
        annotations=[
            {"text": "Bedtime", "x": 0.235, "xref": "paper",
             "y": 1.06, "yref": "paper", "showarrow": False,
             "font": {"size": 14, "color": "#1d1d1f"}},
            {"text": "Wake Time", "x": 0.765, "xref": "paper",
             "y": 1.06, "yref": "paper", "showarrow": False,
             "font": {"size": 14, "color": "#1d1d1f"}},
        ],
    )

    return {"traces": traces, "layout": layout}


# ── Wrist Temperature ───────────────────────────────────────────────────────


def get_wrist_temp(start: date, end: date) -> dict | None:
    rec_f = filter_date(records, start, end)
    wtemp = _get_type(
        rec_f, "HKQuantityTypeIdentifierAppleSleepingWristTemperature"
    )
    if wtemp.empty:
        return None

    wtemp = wtemp.sort_values("startDate")
    traces = [
        {
            "type": "scatter",
            "x": wtemp["startDate"].dt.strftime("%Y-%m-%d").tolist(),
            "y": [round(v, 2) for v in wtemp["value"]],
            "mode": "markers",
            "name": "Wrist Temp",
            "marker": {"color": TEAL, "size": 4, "opacity": 0.5},
            "hovertemplate": "%{x}<br>%{y:.2f} °C<extra></extra>",
        }
    ]

    if len(wtemp) > 7:
        wtemp_daily = (
            wtemp.groupby("date")["value"]
            .mean()
            .reset_index()
            .sort_values("date")
        )
        wtemp_daily["rolling"] = (
            wtemp_daily["value"].rolling(7, min_periods=1).mean()
        )
        traces.append(
            {
                "type": "scatter",
                "x": [str(d) for d in wtemp_daily["date"]],
                "y": [round(v, 2) for v in wtemp_daily["rolling"]],
                "mode": "lines",
                "name": "7-day avg",
                "line": {"color": TEAL, "width": 2, "shape": "spline"},
                "hovertemplate": "%{x}<br>Avg: %{y:.2f} °C<extra></extra>",
            }
        )

    return {
        "traces": traces,
        "layout": _base_layout(
            yaxis={
                "title": {"text": "°C delta"},
                "gridcolor": "#e5e5e7",
                "zerolinecolor": "#d1d1d6",
            },
        ),
    }
