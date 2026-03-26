"""Load parquet files into memory at import time."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ── Load raw dataframes ─────────────────────────────────────────────────────

records: pd.DataFrame = pd.read_parquet(DATA_DIR / "records.parquet")
records["date"] = records["startDate"].dt.date

workouts: pd.DataFrame = pd.read_parquet(DATA_DIR / "workouts.parquet")

activity: pd.DataFrame = pd.read_parquet(DATA_DIR / "activity_summary.parquet")

# ── Prepare sleep dataframe ─────────────────────────────────────────────────

_STAGE_MAP = {
    "HKCategoryValueSleepAnalysisAsleepCore": "Core",
    "HKCategoryValueSleepAnalysisAsleepDeep": "Deep",
    "HKCategoryValueSleepAnalysisAsleepREM": "REM",
    "HKCategoryValueSleepAnalysisAwake": "Awake",
    "HKCategoryValueSleepAnalysisInBed": "InBed",
    "HKCategoryValueSleepAnalysisAsleepUnspecified": "Asleep",
}


def _prepare_sleep() -> pd.DataFrame:
    sleep = records[
        records["type"] == "HKCategoryTypeIdentifierSleepAnalysis"
    ].copy()
    if sleep.empty:
        return pd.DataFrame()
    sleep["stage"] = sleep["value_text"].map(_STAGE_MAP).fillna("Unknown")
    sleep["duration_min"] = (
        (sleep["endDate"] - sleep["startDate"]).dt.total_seconds() / 60
    )
    sleep["night"] = (
        (sleep["startDate"] - pd.Timedelta(hours=12)).dt.date
    )
    return sleep


sleep_df: pd.DataFrame = _prepare_sleep()

# ── Date bounds ─────────────────────────────────────────────────────────────

min_date = records["startDate"].min().date()
max_date = records["startDate"].max().date()
