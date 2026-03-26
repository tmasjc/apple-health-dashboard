"""
Apple Health Dashboard — Streamlit app.
Run: uv run streamlit run app.py
"""

from datetime import timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"

st.set_page_config(page_title="Health Dashboard", layout="wide")

# ── Apple-inspired color palette ──────────────────────────────────────────────

BLUE = "#007AFF"
GREEN = "#34C759"
ORANGE = "#FF9500"
PINK = "#FF2D55"
PURPLE = "#AF52DE"
TEAL = "#5AC8FA"
RED = "#FF3B30"
INDIGO = "#5856D6"

COLORWAY = [BLUE, GREEN, ORANGE, PINK, PURPLE, TEAL, RED, INDIGO]

WORKOUT_COLORS = {
    "FunctionalStrengthTraining": PINK,
    "Walking": GREEN,
    "Running": BLUE,
    "Cycling": ORANGE,
    "HighIntensityIntervalTraining": PURPLE,
    "Elliptical": TEAL,
    "Rowing": INDIGO,
    "Hiking": "#30D158",
    "Other": "#8E8E93",
}

SLEEP_STAGE_COLORS = {
    "Deep": INDIGO,
    "Core": BLUE,
    "REM": PURPLE,
    "Awake": ORANGE,
}

# ── Plotly template (Apple-inspired) ──────────────────────────────────────────

CHART_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(255, 255, 255, 0)",
        plot_bgcolor="rgba(255, 255, 255, 0)",
        font=dict(family="-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif", color="#1d1d1f", size=12),
        xaxis=dict(
            gridcolor="#e5e5e7",
            zerolinecolor="#d1d1d6",
        ),
        yaxis=dict(
            gridcolor="#e5e5e7",
            zerolinecolor="#d1d1d6",
        ),
        colorway=COLORWAY,
    )
)

# ── Apple-inspired CSS ────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    .stApp, [data-testid="stAppViewContainer"] {
        background: #f5f5f7;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
    }

    /* Title */
    h1 {
        color: #1d1d1f !important;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }

    .section-header {
        color: #1d1d1f;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif;
        font-size: 1.25rem;
        font-weight: 600;
        letter-spacing: -0.01em;
        border-bottom: 1px solid #d1d1d6;
        padding-bottom: 0.5rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }

    .chart-title {
        color: #1d1d1f;
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }

    /* Chart containers */
    [data-testid="stPlotlyChart"] {
        background: #ffffff;
        border: 1px solid #e5e5e7;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        padding: 0.5rem;
    }

    /* KPI metric cards */
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e5e7;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
    }
    [data-testid="stMetric"] label {
        color: #6e6e73 !important;
        font-family: -apple-system, system-ui, sans-serif !important;
        font-size: 0.75rem !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #1d1d1f !important;
        font-family: -apple-system, system-ui, sans-serif !important;
        font-weight: 600 !important;
    }

    /* General text */
    .stMarkdown, p, span, div { color: #1d1d1f; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #f5f5f7; }
    ::-webkit-scrollbar-thumb { background: #c7c7cc; border-radius: 3px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Data loading (cached) ───────────────────────────────────────────────────


@st.cache_data
def load_records():
    df = pd.read_parquet(DATA_DIR / "records.parquet")
    df["date"] = df["startDate"].dt.date
    return df


@st.cache_data
def load_workouts():
    return pd.read_parquet(DATA_DIR / "workouts.parquet")


@st.cache_data
def load_activity():
    return pd.read_parquet(DATA_DIR / "activity_summary.parquet")


records = load_records()
workouts = load_workouts()
activity = load_activity()


def get_type(df, type_name):
    return df[df["type"] == type_name].copy()


@st.cache_data
def prepare_sleep(records_df):
    sleep = records_df[records_df["type"] == "HKCategoryTypeIdentifierSleepAnalysis"].copy()
    if sleep.empty:
        return pd.DataFrame()
    stage_map = {
        "HKCategoryValueSleepAnalysisAsleepCore": "Core",
        "HKCategoryValueSleepAnalysisAsleepDeep": "Deep",
        "HKCategoryValueSleepAnalysisAsleepREM": "REM",
        "HKCategoryValueSleepAnalysisAwake": "Awake",
        "HKCategoryValueSleepAnalysisInBed": "InBed",
        "HKCategoryValueSleepAnalysisAsleepUnspecified": "Asleep",
    }
    sleep["stage"] = sleep["value_text"].map(stage_map).fillna("Unknown")
    sleep["duration_min"] = (sleep["endDate"] - sleep["startDate"]).dt.total_seconds() / 60
    sleep["night"] = (sleep["startDate"] - pd.Timedelta(hours=12)).dt.date
    return sleep


sleep_df = prepare_sleep(records)


# ── Helpers ──────────────────────────────────────────────────────────────────


def filter_date(df, start, end, col="startDate"):
    if df.empty:
        return df
    series = df[col]
    if pd.api.types.is_datetime64_any_dtype(series):
        ts_start = pd.Timestamp(start)
        ts_end = pd.Timestamp(end) + pd.Timedelta(days=1)
        # Match timezone if the column is tz-aware
        tz = getattr(series.dt, "tz", None)
        if tz is not None:
            ts_start = ts_start.tz_localize(tz)
            ts_end = ts_end.tz_localize(tz)
        return df[(series >= ts_start) & (series <= ts_end)]
    # date column (python date objects)
    return df[(series >= start) & (series <= end)]


def style_layout(fig, height=400, **kwargs):
    fig.update_layout(template=CHART_TEMPLATE, height=height, **kwargs)
    return fig


# ── Chart builders ───────────────────────────────────────────────────────────


def build_workout_breakdown(wk):
    wk_counts = (
        wk["workoutActivityType"]
        .str.replace("HKWorkoutActivityType", "")
        .value_counts()
    )
    fig = px.pie(
        names=wk_counts.index,
        values=wk_counts.values,
        hole=0.45,
        color=wk_counts.index,
        color_discrete_map=WORKOUT_COLORS,
    )
    fig.update_traces(
        marker=dict(line=dict(color="#ffffff", width=2)),
        textfont=dict(color="#1d1d1f"),
    )
    return style_layout(fig, height=400)


def build_monthly_volume(wk):
    wk = wk.copy()
    wk["type_short"] = wk["workoutActivityType"].str.replace("HKWorkoutActivityType", "")
    wk["month"] = wk["startDate"].dt.to_period("M").dt.to_timestamp()
    monthly = wk.groupby(["month", "type_short"]).size().reset_index(name="count")
    fig = px.bar(
        monthly, x="month", y="count", color="type_short",
        color_discrete_map=WORKOUT_COLORS,
        labels={"count": "Sessions", "type_short": "Type"},
    )
    return style_layout(fig, barmode="stack", height=400)


def build_vo2_trend(rec):
    vo2 = get_type(rec, "HKQuantityTypeIdentifierVO2Max")
    if vo2.empty:
        return None
    vo2_daily = vo2.groupby("date")["value"].mean().reset_index().sort_values("date")
    fig = go.Figure()
    fig.add_hrect(y0=51.1, y1=60, fillcolor=GREEN, opacity=0.08, line_width=0, annotation_text="Superior")
    fig.add_hrect(y0=43.9, y1=51.1, fillcolor=BLUE, opacity=0.08, line_width=0, annotation_text="Excellent")
    fig.add_hrect(y0=36.7, y1=43.9, fillcolor=ORANGE, opacity=0.08, line_width=0, annotation_text="Good")
    fig.add_hrect(y0=20, y1=36.7, fillcolor=RED, opacity=0.08, line_width=0, annotation_text="Below Good")
    fig.add_trace(
        go.Scatter(
            x=vo2_daily["date"].astype(str), y=vo2_daily["value"],
            mode="markers", name="VO2 Max",
            marker=dict(color=BLUE, size=5, opacity=0.6),
        )
    )
    if len(vo2_daily) > 10:
        vo2_daily["rolling"] = vo2_daily["value"].rolling(10, min_periods=3).mean()
        fig.add_trace(
            go.Scatter(
                x=vo2_daily["date"].astype(str), y=vo2_daily["rolling"],
                mode="lines", name="Trend",
                line=dict(color=ORANGE, width=2, shape="spline"),
            )
        )
    return style_layout(fig, yaxis_title="mL/min/kg", height=400)


def build_rhr_hrv(rec):
    rhr = get_type(rec, "HKQuantityTypeIdentifierRestingHeartRate")
    hrv = get_type(rec, "HKQuantityTypeIdentifierHeartRateVariabilitySDNN")
    if rhr.empty or hrv.empty:
        return None
    rhr["week"] = rhr["startDate"].dt.to_period("W").dt.to_timestamp()
    hrv["week"] = hrv["startDate"].dt.to_period("W").dt.to_timestamp()
    rhr_w = rhr.groupby("week")["value"].mean()
    hrv_w = hrv.groupby("week")["value"].mean()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=rhr_w.index, y=rhr_w.values, name="Resting HR (bpm)", line=dict(color=PINK, width=2, shape="spline")),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=hrv_w.index, y=hrv_w.values, name="HRV SDNN (ms)", line=dict(color=BLUE, width=2, shape="spline")),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="Resting HR (bpm)", secondary_y=False)
    fig.update_yaxes(title_text="HRV SDNN (ms)", secondary_y=True)
    return style_layout(fig, height=400)


def build_sleep_stages(sdf):
    if sdf.empty:
        return None
    stage_order = ["Deep", "Core", "REM", "Awake"]
    staged = sdf[sdf["stage"].isin(stage_order)].copy()
    staged["week"] = pd.to_datetime(staged["night"]).dt.to_period("W").dt.to_timestamp()

    weekly = (
        staged.groupby(["week", "stage"])["duration_min"]
        .sum()
        .unstack(fill_value=0)
    )
    for s in stage_order:
        if s not in weekly.columns:
            weekly[s] = 0
    weekly = weekly[stage_order].sort_index()
    # Convert to avg hours per night in that week
    nights_per_week = staged.groupby("week")["night"].nunique()
    for s in stage_order:
        weekly[s] = weekly[s] / nights_per_week / 60

    fig = go.Figure()
    for stage in stage_order:
        fig.add_trace(
            go.Bar(
                x=weekly.index.astype(str),
                y=weekly[stage],
                name=stage,
                marker_color=SLEEP_STAGE_COLORS[stage],
                hovertemplate=f"{stage}: " + "%{y:.1f} hrs<extra></extra>",
            )
        )
    return style_layout(fig, barmode="stack", yaxis_title="Avg Hours / Night", height=400)


def build_sleep_duration(sdf):
    if sdf.empty:
        return None
    total_per_night = (
        sdf[sdf["stage"].isin(["Deep", "Core", "REM"])]
        .groupby("night")["duration_min"]
        .sum()
        .sort_index()
    )
    total_hrs = total_per_night / 60
    rolling = total_hrs.rolling(7, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=total_hrs.index.astype(str), y=total_hrs.values,
            mode="markers", name="Nightly",
            marker=dict(size=3, opacity=0.4, color=BLUE),
            hovertemplate="%{x}<br>%{y:.1f} hrs<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=rolling.index.astype(str), y=rolling.values,
            mode="lines", name="7-day avg",
            line=dict(color=GREEN, width=2, shape="spline"),
            hovertemplate="%{x}<br>Avg: %{y:.1f} hrs<extra></extra>",
        )
    )
    return style_layout(fig, yaxis_title="Hours", height=400)


def _hour_to_time_str(h):
    """Convert decimal hour (possibly negative for before-midnight) to readable time."""
    if h < 0:
        h += 24
    hour = int(h) % 24
    minute = int((h % 1) * 60)
    period = "AM" if hour < 12 else "PM"
    display_h = hour % 12 or 12
    return f"{display_h}:{minute:02d} {period}"


def build_sleep_consistency(sdf):
    if sdf.empty:
        return None
    asleep = sdf[sdf["stage"].isin(["Deep", "Core", "REM", "Asleep"])]
    if asleep.empty:
        return None
    bed = asleep.groupby("night")["startDate"].min()
    wake = asleep.groupby("night")["endDate"].max()
    consistency = pd.DataFrame({"bedtime": bed, "waketime": wake}).dropna()
    consistency["bed_hour"] = consistency["bedtime"].dt.hour + consistency["bedtime"].dt.minute / 60
    consistency["wake_hour"] = consistency["waketime"].dt.hour + consistency["waketime"].dt.minute / 60
    # Shift evening hours (>=18) to negative so the y-axis is continuous around midnight
    # Filter out daytime outliers (6 AM - 6 PM bedtimes are likely naps)
    consistency["bed_hour_adj"] = consistency["bed_hour"].apply(lambda h: h - 24 if h >= 18 else h)
    consistency = consistency[
        (consistency["bed_hour_adj"] >= -6) & (consistency["bed_hour_adj"] <= 6)  # 6 PM to 6 AM
    ]

    consistency["bed_roll"] = consistency["bed_hour_adj"].rolling(7, min_periods=1).mean()
    consistency["wake_roll"] = consistency["wake_hour"].rolling(7, min_periods=1).mean()

    # Format hover text
    consistency["bed_label"] = consistency["bed_hour_adj"].apply(_hour_to_time_str)
    consistency["wake_label"] = consistency["wake_hour"].apply(_hour_to_time_str)
    consistency["bed_roll_label"] = consistency["bed_roll"].apply(_hour_to_time_str)
    consistency["wake_roll_label"] = consistency["wake_roll"].apply(_hour_to_time_str)

    fig = make_subplots(rows=1, cols=2, subplot_titles=["Bedtime", "Wake Time"])
    fig.add_trace(
        go.Scatter(
            x=consistency.index.astype(str), y=consistency["bed_hour_adj"],
            mode="markers", marker=dict(size=3, opacity=0.4, color=PURPLE), name="Bedtime",
            text=consistency["bed_label"],
            hovertemplate="%{x}<br>%{text}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=consistency.index.astype(str), y=consistency["bed_roll"],
            mode="lines", line=dict(color=PURPLE, width=2, shape="spline"), name="Bedtime trend", showlegend=False,
            text=consistency["bed_roll_label"],
            hovertemplate="%{x}<br>Avg: %{text}<extra></extra>",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=consistency.index.astype(str), y=consistency["wake_hour"],
            mode="markers", marker=dict(size=3, opacity=0.4, color=ORANGE), name="Wake",
            text=consistency["wake_label"],
            hovertemplate="%{x}<br>%{text}<extra></extra>",
        ),
        row=1, col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=consistency.index.astype(str), y=consistency["wake_roll"],
            mode="lines", line=dict(color=ORANGE, width=2, shape="spline"), name="Wake trend", showlegend=False,
            text=consistency["wake_roll_label"],
            hovertemplate="%{x}<br>Avg: %{text}<extra></extra>",
        ),
        row=1, col=2,
    )
    # Format y-axis ticks as readable times
    bed_ticks = list(range(-6, 7))
    bed_labels = [_hour_to_time_str(h) for h in bed_ticks]
    fig.update_yaxes(tickvals=bed_ticks, ticktext=bed_labels, row=1, col=1)
    wake_ticks = list(range(4, 14))
    wake_labels = [_hour_to_time_str(h) for h in wake_ticks]
    fig.update_yaxes(tickvals=wake_ticks, ticktext=wake_labels, row=1, col=2)
    return style_layout(fig, showlegend=False, height=400)


def build_wrist_temp(rec):
    wtemp = get_type(rec, "HKQuantityTypeIdentifierAppleSleepingWristTemperature")
    if wtemp.empty:
        return None
    wtemp = wtemp.sort_values("startDate")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=wtemp["startDate"], y=wtemp["value"],
            mode="markers", name="Wrist Temp",
            marker=dict(color=TEAL, size=4, opacity=0.5),
        )
    )
    if len(wtemp) > 7:
        wtemp_daily = wtemp.groupby("date")["value"].mean().reset_index().sort_values("date")
        wtemp_daily["rolling"] = wtemp_daily["value"].rolling(7, min_periods=1).mean()
        fig.add_trace(
            go.Scatter(
                x=wtemp_daily["date"].astype(str), y=wtemp_daily["rolling"],
                mode="lines", name="7-day avg",
                line=dict(color=TEAL, width=2, shape="spline"),
            )
        )
    return style_layout(fig, yaxis_title="°C delta", height=400)


# ═════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ═════════════════════════════════════════════════════════════════════════════

st.title("Health Dashboard")

# ── Global date range controller ─────────────────────────────────────────────

min_date = records["startDate"].min().date()
max_date = records["startDate"].max().date()
default_start = max_date - timedelta(days=180)

col_d1, col_d2 = st.columns(2)
with col_d1:
    d_start = st.date_input("Start date", value=default_start, min_value=min_date, max_value=max_date)
with col_d2:
    d_end = st.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)

if d_start and d_end and d_start <= d_end:

    # Filter datasets
    rec_f = filter_date(records, d_start, d_end)
    wk_f = filter_date(workouts, d_start, d_end)
    act_f = filter_date(activity, d_start, d_end, col="date")
    sleep_f = filter_date(sleep_df, d_start, d_end, col="night") if not sleep_df.empty else sleep_df

    # ── OVERVIEW ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)

    if not act_f.empty:
        range_end = act_f["date"].max()
        last30 = act_f[act_f["date"] > range_end - pd.Timedelta(days=30)]
        prev30 = act_f[
            (act_f["date"] > range_end - pd.Timedelta(days=60))
            & (act_f["date"] <= range_end - pd.Timedelta(days=30))
        ]

        def kpi(col):
            cur = last30[col].mean() if not last30.empty else 0
            prev = prev30[col].mean() if not prev30.empty else 0
            delta = ((cur - prev) / prev * 100) if prev else 0
            return cur, delta

        c1, c2, c3, c4 = st.columns(4)
        v, d = kpi("activeEnergyBurned")
        c1.metric("Avg Active kcal / day", f"{v:.0f}", f"{d:+.1f}%")
        v, d = kpi("appleExerciseTime")
        c2.metric("Avg Exercise min / day", f"{v:.0f}", f"{d:+.1f}%")
        v, d = kpi("appleStandHours")
        c3.metric("Avg Stand hrs / day", f"{v:.1f}", f"{d:+.1f}%")

        steps = get_type(rec_f, "HKQuantityTypeIdentifierStepCount")
        if not steps.empty:
            steps_daily = steps.groupby("date")["value"].sum()
            last30_dates = pd.date_range(end=range_end, periods=30).date
            prev30_dates = pd.date_range(end=range_end - pd.Timedelta(days=30), periods=30).date
            cur_steps = steps_daily.reindex(last30_dates).mean()
            prev_steps = steps_daily.reindex(prev30_dates).mean()
            delta_steps = ((cur_steps - prev_steps) / prev_steps * 100) if prev_steps else 0
            c4.metric(
                "Avg Steps / day",
                f"{cur_steps:,.0f}" if not pd.isna(cur_steps) else "N/A",
                f"{delta_steps:+.1f}%",
            )
        else:
            c4.metric("Avg Steps / day", "N/A", "")
    else:
        st.info("No activity data in selected range.")

    # ── FITNESS ──────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Fitness</div>', unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="chart-title">Workout Breakdown</div>', unsafe_allow_html=True)
        if not wk_f.empty:
            st.plotly_chart(build_workout_breakdown(wk_f), use_container_width=True)
        else:
            st.info("No workout data in selected range.")
    with right:
        st.markdown('<div class="chart-title">Monthly Workout Volume</div>', unsafe_allow_html=True)
        if not wk_f.empty:
            st.plotly_chart(build_monthly_volume(wk_f), use_container_width=True)
        else:
            st.info("No workout data in selected range.")

    # ── HEART ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Heart</div>', unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="chart-title">VO2 Max Trend</div>', unsafe_allow_html=True)
        fig_vo2 = build_vo2_trend(rec_f)
        if fig_vo2:
            st.plotly_chart(fig_vo2, use_container_width=True)
        else:
            st.info("No VO2 Max data in selected range.")
    with right:
        st.markdown('<div class="chart-title">Resting Heart Rate & HRV (Weekly)</div>', unsafe_allow_html=True)
        fig_rhr = build_rhr_hrv(rec_f)
        if fig_rhr:
            st.plotly_chart(fig_rhr, use_container_width=True)
        else:
            st.info("No RHR/HRV data in selected range.")

    # ── SLEEP ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">Sleep</div>', unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="chart-title">Sleep Stages by Night</div>', unsafe_allow_html=True)
        fig_stages = build_sleep_stages(sleep_f)
        if fig_stages:
            st.plotly_chart(fig_stages, use_container_width=True)
        else:
            st.info("No sleep stage data in selected range.")
    with right:
        st.markdown('<div class="chart-title">Total Sleep Duration Trend</div>', unsafe_allow_html=True)
        fig_dur = build_sleep_duration(sleep_f)
        if fig_dur:
            st.plotly_chart(fig_dur, use_container_width=True)
        else:
            st.info("No sleep duration data in selected range.")

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="chart-title">Sleep Consistency (Bedtime & Wake Time)</div>', unsafe_allow_html=True)
        fig_consist = build_sleep_consistency(sleep_f)
        if fig_consist:
            st.plotly_chart(fig_consist, use_container_width=True)
        else:
            st.info("No sleep consistency data in selected range.")
    with right:
        st.markdown('<div class="chart-title">Sleeping Wrist Temperature</div>', unsafe_allow_html=True)
        fig_wt = build_wrist_temp(rec_f)
        if fig_wt:
            st.plotly_chart(fig_wt, use_container_width=True)
        else:
            st.info("No wrist temperature data available.")
