"""Tests for data_loader query functions using temporary Parquet files."""

from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from backend import data_loader


@pytest.fixture()
def tmp_data_dir(tmp_path):
    """Create temporary Parquet files and patch data_loader paths."""
    records_path = tmp_path / "records.parquet"
    workouts_path = tmp_path / "workouts.parquet"
    activity_path = tmp_path / "activity_summary.parquet"

    # Build records
    rows = []
    base = pd.Timestamp("2024-01-01")
    for day_offset in range(30):
        ts = base + pd.Timedelta(days=day_offset)
        rows.append({
            "type": "HKQuantityTypeIdentifierStepCount",
            "sourceName": "Watch",
            "unit": "count",
            "value": 1000.0 + day_offset,
            "value_text": str(1000.0 + day_offset),
            "startDate": ts,
            "endDate": ts + pd.Timedelta(hours=1),
        })
        rows.append({
            "type": "HKQuantityTypeIdentifierHeartRate",
            "sourceName": "Watch",
            "unit": "count/min",
            "value": 70.0 + day_offset,
            "value_text": str(70.0 + day_offset),
            "startDate": ts,
            "endDate": ts + pd.Timedelta(minutes=5),
        })

    # Add sleep records for night boundary testing
    # Sleep at 11 PM on Jan 5 → night = Jan 5
    sleep_start_1 = pd.Timestamp("2024-01-05 23:00")
    rows.append({
        "type": "HKCategoryTypeIdentifierSleepAnalysis",
        "sourceName": "Watch",
        "unit": "",
        "value": float("nan"),
        "value_text": "HKCategoryValueSleepAnalysisAsleepCore",
        "startDate": sleep_start_1,
        "endDate": sleep_start_1 + pd.Timedelta(hours=2),
    })
    # Sleep at 1 AM on Jan 6 → night = Jan 5 (after 12h subtraction)
    sleep_start_2 = pd.Timestamp("2024-01-06 01:00")
    rows.append({
        "type": "HKCategoryTypeIdentifierSleepAnalysis",
        "sourceName": "Watch",
        "unit": "",
        "value": float("nan"),
        "value_text": "HKCategoryValueSleepAnalysisAsleepDeep",
        "startDate": sleep_start_2,
        "endDate": sleep_start_2 + pd.Timedelta(hours=1),
    })

    df = pd.DataFrame(rows).sort_values(["type", "startDate"]).reset_index(drop=True)
    df.to_parquet(records_path, index=False, row_group_size=10)

    # Build workouts
    pd.DataFrame([{
        "workoutActivityType": "HKWorkoutActivityTypeRunning",
        "duration": 30.0,
        "durationUnit": "min",
        "totalDistance": 5.0,
        "totalDistanceUnit": "km",
        "totalEnergyBurned": 300.0,
        "totalEnergyBurnedUnit": "kcal",
        "sourceName": "Watch",
        "startDate": pd.Timestamp("2024-01-10"),
        "endDate": pd.Timestamp("2024-01-10 00:30"),
    }]).to_parquet(workouts_path, index=False)

    # Build activity
    pd.DataFrame([{
        "date": pd.Timestamp("2024-01-10"),
        "activeEnergyBurned": 500.0,
        "activeEnergyBurnedGoal": 600.0,
        "appleExerciseTime": 30.0,
        "appleExerciseTimeGoal": 30.0,
        "appleStandHours": 10.0,
        "appleStandHoursGoal": 12.0,
    }]).to_parquet(activity_path, index=False)

    with patch.object(data_loader, "DATA_DIR", tmp_path), \
         patch.object(data_loader, "RECORDS_PATH", records_path):
        # Clear all caches so tests use the temp files
        data_loader._cached_tz.cache_clear()
        data_loader.get_workouts.cache_clear()
        data_loader.get_activity.cache_clear()
        data_loader.get_date_bounds.cache_clear()
        yield tmp_path
        # Clean up caches after test
        data_loader._cached_tz.cache_clear()
        data_loader.get_workouts.cache_clear()
        data_loader.get_activity.cache_clear()
        data_loader.get_date_bounds.cache_clear()


def test_query_records_filters_by_type(tmp_data_dir):
    df = data_loader.query_records(
        date(2024, 1, 1), date(2024, 1, 30),
        record_type="HKQuantityTypeIdentifierStepCount",
    )
    assert not df.empty
    assert (df["type"] == "HKQuantityTypeIdentifierStepCount").all()


def test_query_records_filters_by_date(tmp_data_dir):
    df = data_loader.query_records(
        date(2024, 1, 5), date(2024, 1, 10),
    )
    assert not df.empty
    dates = df["startDate"].dt.date
    assert dates.min() >= date(2024, 1, 5)
    # end + 1 day is included (matches original filter_date behavior)
    assert dates.max() <= date(2024, 1, 11)


def test_query_records_no_type_returns_all(tmp_data_dir):
    df = data_loader.query_records(date(2024, 1, 1), date(2024, 1, 5))
    types = df["type"].unique()
    assert len(types) >= 2  # At least StepCount and HeartRate


def test_query_records_adds_date_column(tmp_data_dir):
    df = data_loader.query_records(date(2024, 1, 1), date(2024, 1, 5))
    assert "date" in df.columns
    assert df["date"].iloc[0] == df["startDate"].iloc[0].date()


def test_query_records_empty_range(tmp_data_dir):
    df = data_loader.query_records(date(2025, 1, 1), date(2025, 1, 5))
    assert df.empty


def test_query_sleep_computes_derived_columns(tmp_data_dir):
    df = data_loader.query_sleep(date(2024, 1, 5), date(2024, 1, 6))
    assert not df.empty
    assert "stage" in df.columns
    assert "duration_min" in df.columns
    assert "night" in df.columns
    assert set(df["stage"].unique()) <= {"Core", "Deep", "REM", "Awake", "InBed", "Asleep", "Unknown"}


def test_query_sleep_night_boundary(tmp_data_dir):
    # Both sleep records (11 PM Jan 5 and 1 AM Jan 6) have night = Jan 5
    df = data_loader.query_sleep(date(2024, 1, 5), date(2024, 1, 5))
    assert len(df) == 2
    assert (df["night"] == date(2024, 1, 5)).all()


def test_query_sleep_empty(tmp_data_dir):
    df = data_loader.query_sleep(date(2024, 1, 20), date(2024, 1, 25))
    assert df.empty


def test_get_date_bounds(tmp_data_dir):
    min_d, max_d = data_loader.get_date_bounds()
    assert min_d == date(2024, 1, 1)
    assert max_d == date(2024, 1, 30)


def test_get_workouts_caches(tmp_data_dir):
    a = data_loader.get_workouts()
    b = data_loader.get_workouts()
    assert a is b


def test_get_activity_caches(tmp_data_dir):
    a = data_loader.get_activity()
    b = data_loader.get_activity()
    assert a is b
