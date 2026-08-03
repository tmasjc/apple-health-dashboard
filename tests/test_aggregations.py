"""Tests for aggregation functions using temporary Parquet files."""

from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from backend import aggregations, data_loader


def _workout(ts: str) -> dict:
    return {
        "workoutActivityType": "HKWorkoutActivityTypeRunning",
        "duration": 30.0,
        "durationUnit": "min",
        "totalDistance": 5.0,
        "totalDistanceUnit": "km",
        "totalEnergyBurned": 300.0,
        "totalEnergyBurnedUnit": "kcal",
        "sourceName": "Watch",
        "startDate": pd.Timestamp(ts),
        "endDate": pd.Timestamp(ts) + pd.Timedelta(minutes=30),
    }


@pytest.fixture()
def kpi_data_dir(tmp_path):
    """Workouts split across two adjacent 10-day windows.

    Current window  2024-02-01..2024-02-10 → 4 workouts
    Previous window 2024-01-22..2024-01-31 → 2 workouts (one on the very
    first day, which an unequal-length comparison window would drop).
    """
    records_path = tmp_path / "records.parquet"
    workouts_path = tmp_path / "workouts.parquet"
    activity_path = tmp_path / "activity_summary.parquet"

    pd.DataFrame([{
        "type": "HKQuantityTypeIdentifierStepCount",
        "sourceName": "Watch",
        "unit": "count",
        "value": 1000.0,
        "value_text": "1000.0",
        "startDate": pd.Timestamp("2024-02-02"),
        "endDate": pd.Timestamp("2024-02-02 01:00"),
    }]).to_parquet(records_path, index=False)

    pd.DataFrame([
        _workout("2024-01-22 08:00"),   # first day of the previous window
        _workout("2024-01-30 08:00"),
        _workout("2024-02-01 08:00"),
        _workout("2024-02-04 08:00"),
        _workout("2024-02-04 18:00"),   # two sessions in one day
        _workout("2024-02-10 08:00"),   # last day of the current window
        _workout("2024-02-11 08:00"),   # outside the current window
    ]).to_parquet(workouts_path, index=False)

    pd.DataFrame([{
        "date": pd.Timestamp("2024-02-02"),
        "activeEnergyBurned": 500.0,
        "activeEnergyBurnedGoal": 600.0,
        "appleExerciseTime": 30.0,
        "appleExerciseTimeGoal": 30.0,
        "appleStandHours": 10.0,
        "appleStandHoursGoal": 12.0,
    }]).to_parquet(activity_path, index=False)

    with patch.object(data_loader, "DATA_DIR", tmp_path), \
         patch.object(data_loader, "RECORDS_PATH", records_path):
        data_loader._cached_tz.cache_clear()
        data_loader.get_workouts.cache_clear()
        data_loader.get_activity.cache_clear()
        data_loader.get_date_bounds.cache_clear()
        yield tmp_path
        data_loader._cached_tz.cache_clear()
        data_loader.get_workouts.cache_clear()
        data_loader.get_activity.cache_clear()
        data_loader.get_date_bounds.cache_clear()


def test_kpis_counts_workout_sessions(kpi_data_dir):
    kpis = aggregations.get_kpis(date(2024, 2, 1), date(2024, 2, 10))

    # Sessions, not active days — 2024-02-04 contributes two.
    assert kpis["workouts"]["value"] == 4


def test_kpis_workout_delta_uses_equal_length_window(kpi_data_dir):
    kpis = aggregations.get_kpis(date(2024, 2, 1), date(2024, 2, 10))

    # Previous window must be the same 10 days long, so it catches both
    # workouts (4 vs 2 = +100%), not just the one after an off-by-one start.
    assert kpis["workouts"]["delta"] == 100.0


def test_kpis_workouts_zero_outside_data_range(kpi_data_dir):
    kpis = aggregations.get_kpis(date(2023, 5, 1), date(2023, 5, 10))

    assert kpis["workouts"] == {"value": 0, "delta": 0}
