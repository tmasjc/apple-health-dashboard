"""Lazy data access — queries Parquet on demand instead of loading into memory."""

from __future__ import annotations

import functools
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RECORDS_PATH = DATA_DIR / "records.parquet"

# ── Sleep stage mapping ────────────────────────────────────────────────────

_STAGE_MAP = {
    "HKCategoryValueSleepAnalysisAsleepCore": "Core",
    "HKCategoryValueSleepAnalysisAsleepDeep": "Deep",
    "HKCategoryValueSleepAnalysisAsleepREM": "REM",
    "HKCategoryValueSleepAnalysisAwake": "Awake",
    "HKCategoryValueSleepAnalysisInBed": "InBed",
    "HKCategoryValueSleepAnalysisAsleepUnspecified": "Asleep",
}

# ── Helpers ────────────────────────────────────────────────────────────────


def _get_startdate_tz() -> str | None:
    """Read the timezone of the startDate column from the Parquet schema."""
    schema = pq.read_schema(RECORDS_PATH)
    arrow_type = schema.field("startDate").type
    return str(arrow_type.tz) if hasattr(arrow_type, "tz") and arrow_type.tz else None


@functools.cache
def _cached_tz() -> str | None:
    return _get_startdate_tz()


# ── Query functions ────────────────────────────────────────────────────────


def query_records(
    start: date,
    end: date,
    record_type: str | None = None,
) -> pd.DataFrame:
    """Read records from Parquet with predicate pushdown on type and date."""
    ts_start = pd.Timestamp(start)
    ts_end = pd.Timestamp(end) + pd.Timedelta(days=1)

    tz = _cached_tz()
    if tz is not None:
        ts_start = ts_start.tz_localize(tz)
        ts_end = ts_end.tz_localize(tz)

    filters: list[tuple] = [
        ("startDate", ">=", ts_start),
        ("startDate", "<=", ts_end),
    ]
    if record_type is not None:
        filters.append(("type", "==", record_type))

    df = pd.read_parquet(RECORDS_PATH, filters=filters)
    if not df.empty:
        df["date"] = df["startDate"].dt.date
    return df


def query_sleep(start: date, end: date) -> pd.DataFrame:
    """Query sleep records and compute stage, duration, night columns.

    Widens the Parquet date filter by 1 day on each side to capture records
    whose derived 'night' (startDate - 12h) falls in [start, end].
    """
    widened_start = start - timedelta(days=1)
    widened_end = end + timedelta(days=1)

    df = query_records(
        widened_start, widened_end,
        record_type="HKCategoryTypeIdentifierSleepAnalysis",
    )
    if df.empty:
        return pd.DataFrame()

    df["stage"] = df["value_text"].map(_STAGE_MAP).fillna("Unknown")
    df["duration_min"] = (
        (df["endDate"] - df["startDate"]).dt.total_seconds() / 60
    )
    df["night"] = (df["startDate"] - pd.Timedelta(hours=12)).dt.date

    return df[(df["night"] >= start) & (df["night"] <= end)]


@functools.cache
def get_workouts() -> pd.DataFrame:
    """Load workouts (small dataset, cached after first call)."""
    return pd.read_parquet(DATA_DIR / "workouts.parquet")


@functools.cache
def get_activity() -> pd.DataFrame:
    """Load activity summary (tiny dataset, cached after first call)."""
    return pd.read_parquet(DATA_DIR / "activity_summary.parquet")


@functools.cache
def get_date_bounds() -> tuple[date, date]:
    """Read min/max startDate from Parquet row-group statistics."""
    pf = pq.ParquetFile(RECORDS_PATH)
    col_idx = pf.schema_arrow.get_field_index("startDate")

    overall_min = None
    overall_max = None
    for i in range(pf.metadata.num_row_groups):
        stats = pf.metadata.row_group(i).column(col_idx).statistics
        if stats is not None and stats.has_min_max:
            if overall_min is None or stats.min < overall_min:
                overall_min = stats.min
            if overall_max is None or stats.max > overall_max:
                overall_max = stats.max

    if overall_min is None:
        dates = pd.read_parquet(RECORDS_PATH, columns=["startDate"])
        return dates["startDate"].min().date(), dates["startDate"].max().date()

    return pd.Timestamp(overall_min).date(), pd.Timestamp(overall_max).date()
