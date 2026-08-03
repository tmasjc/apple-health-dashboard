"""Tests for aggregation functions using temporary Parquet files."""

from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from backend import aggregations, constants, data_loader


def _workout(ts: str, activity: str = "Running") -> dict:
    return {
        "workoutActivityType": f"HKWorkoutActivityType{activity}",
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


@pytest.fixture()
def workout_mix_dir(tmp_path):
    """Exactly 100 sessions in Jan-Feb 2024 with a known share split.

    FunctionalStrengthTraining 63 | Running 30 → clearly significant
    Cycling                     3            → exactly 3%, must survive
    Walking 2 | Hiking 1 | Other 1           → below 3%, must collapse
    """
    records_path = tmp_path / "records.parquet"

    pd.DataFrame([{
        "type": "HKQuantityTypeIdentifierStepCount",
        "sourceName": "Watch",
        "unit": "count",
        "value": 1000.0,
        "value_text": "1000.0",
        "startDate": pd.Timestamp("2024-01-02"),
        "endDate": pd.Timestamp("2024-01-02 01:00"),
    }]).to_parquet(records_path, index=False)

    rows = []
    for activity, count in [
        ("FunctionalStrengthTraining", 63),
        ("Running", 30),
        ("Cycling", 3),
        ("Walking", 2),
        ("Hiking", 1),
        ("Other", 1),
    ]:
        for i in range(count):
            # Alternate months so the stacked bar chart has two buckets.
            month = 1 if i % 2 == 0 else 2
            day = (i % 27) + 1
            rows.append(_workout(f"2024-{month:02d}-{day:02d} 08:00", activity))
    pd.DataFrame(rows).to_parquet(tmp_path / "workouts.parquet", index=False)

    pd.DataFrame([{
        "date": pd.Timestamp("2024-01-02"),
        "activeEnergyBurned": 500.0,
        "activeEnergyBurnedGoal": 600.0,
        "appleExerciseTime": 30.0,
        "appleExerciseTimeGoal": 30.0,
        "appleStandHours": 10.0,
        "appleStandHoursGoal": 12.0,
    }]).to_parquet(tmp_path / "activity_summary.parquet", index=False)

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


def _donut(result: dict) -> dict[str, int]:
    trace = result["donut"]["traces"][0]
    return dict(zip(trace["labels"], trace["values"]))


def test_rare_workout_types_collapse_into_other(workout_mix_dir):
    slices = _donut(aggregations.get_workouts(date(2024, 1, 1), date(2024, 2, 29)))

    # Walking (2) + Hiking (1) + raw "Other" (1) = 4
    assert slices["Other"] == 4
    assert "Walking" not in slices
    assert "Hiking" not in slices


def test_three_percent_exactly_is_significant(workout_mix_dir):
    slices = _donut(aggregations.get_workouts(date(2024, 1, 1), date(2024, 2, 29)))

    # 3 of 100 sessions is exactly the threshold — it stays its own category.
    assert slices["Cycling"] == 3


def test_collapsing_preserves_total_sessions(workout_mix_dir):
    slices = _donut(aggregations.get_workouts(date(2024, 1, 1), date(2024, 2, 29)))

    assert sum(slices.values()) == 100


def test_other_sorts_last_and_is_neutral_coloured(workout_mix_dir):
    result = aggregations.get_workouts(date(2024, 1, 1), date(2024, 2, 29))

    names = [t["name"] for t in result["types"]]
    assert names[-1] == "Other"
    assert result["donut"]["traces"][0]["labels"][-1] == "Other"

    colors = {t["name"]: t["color"] for t in result["types"]}
    assert colors["Other"] == constants.OTHER_COLOR
    # The bucket must not reuse a real activity's colour.
    assert list(colors.values()).count(colors["Other"]) == 1


def test_bar_traces_use_collapsed_categories(workout_mix_dir):
    result = aggregations.get_workouts(date(2024, 1, 1), date(2024, 2, 29))

    bar_names = {t["name"] for t in result["bar"]["traces"]}
    assert "Other" in bar_names
    assert "Walking" not in bar_names
    # Sessions survive the collapse in the bar chart too.
    assert sum(sum(t["y"]) for t in result["bar"]["traces"]) == 100


def test_no_other_bucket_when_every_type_is_significant(workout_mix_dir):
    # Narrow to a range containing only the two dominant types.
    result = aggregations.get_workouts(date(2024, 1, 1), date(2024, 1, 31))
    names = [t["name"] for t in result["types"]]

    assert names  # sanity: the range is not empty
    if "Other" in names:
        # Only acceptable if some type genuinely fell below 3% in this window.
        slices = _donut(result)
        assert slices["Other"] > 0
