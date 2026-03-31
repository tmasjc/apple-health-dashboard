"""
Streaming parser for Apple Health export.xml → Parquet files.
Uses lxml iterparse to handle the ~2 GB XML without loading it into memory.
"""

import sys
import time
from pathlib import Path

import pandas as pd
from lxml.etree import iterparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPORT_XML = PROJECT_ROOT / "apple_health_export" / "export.xml"
DATA_DIR = PROJECT_ROOT / "data"

# Record types we care about, grouped by output file
RECORD_TYPES = {
    # Activity
    "HKQuantityTypeIdentifierActiveEnergyBurned",
    "HKQuantityTypeIdentifierBasalEnergyBurned",
    "HKQuantityTypeIdentifierStepCount",
    "HKQuantityTypeIdentifierDistanceWalkingRunning",
    "HKQuantityTypeIdentifierDistanceCycling",
    "HKQuantityTypeIdentifierFlightsClimbed",
    "HKQuantityTypeIdentifierAppleExerciseTime",
    "HKQuantityTypeIdentifierAppleStandTime",
    "HKQuantityTypeIdentifierPhysicalEffort",
    # Heart
    "HKQuantityTypeIdentifierHeartRate",
    "HKQuantityTypeIdentifierRestingHeartRate",
    "HKQuantityTypeIdentifierWalkingHeartRateAverage",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
    "HKQuantityTypeIdentifierHeartRateRecoveryOneMinute",
    "HKQuantityTypeIdentifierVO2Max",
    "HKCategoryTypeIdentifierHighHeartRateEvent",
    # Sleep
    "HKCategoryTypeIdentifierSleepAnalysis",
    "HKQuantityTypeIdentifierAppleSleepingWristTemperature",
    "HKQuantityTypeIdentifierAppleSleepingBreathingDisturbances",
    # Respiratory / SpO2
    "HKQuantityTypeIdentifierRespiratoryRate",
    "HKQuantityTypeIdentifierOxygenSaturation",
    # Running biomechanics
    "HKQuantityTypeIdentifierRunningSpeed",
    "HKQuantityTypeIdentifierRunningPower",
    "HKQuantityTypeIdentifierRunningStrideLength",
    "HKQuantityTypeIdentifierRunningGroundContactTime",
    "HKQuantityTypeIdentifierRunningVerticalOscillation",
    # Gait / Mobility
    "HKQuantityTypeIdentifierWalkingSpeed",
    "HKQuantityTypeIdentifierWalkingStepLength",
    "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage",
    "HKQuantityTypeIdentifierWalkingAsymmetryPercentage",
    "HKQuantityTypeIdentifierAppleWalkingSteadiness",
    "HKQuantityTypeIdentifierSixMinuteWalkTestDistance",
    "HKQuantityTypeIdentifierStairAscentSpeed",
    "HKQuantityTypeIdentifierStairDescentSpeed",
    # Audio / Environment
    "HKQuantityTypeIdentifierEnvironmentalAudioExposure",
    "HKQuantityTypeIdentifierHeadphoneAudioExposure",
    "HKQuantityTypeIdentifierTimeInDaylight",
    "HKQuantityTypeIdentifierEnvironmentalSoundReduction",
    # Mindfulness
    "HKCategoryTypeIdentifierMindfulSession",
    # Body
    "HKQuantityTypeIdentifierBodyMass",
    "HKQuantityTypeIdentifierHeight",
}


def parse_export():
    DATA_DIR.mkdir(exist_ok=True)

    records = []
    workouts = []
    workout_stats = []
    activity_summaries = []
    record_count = 0

    print(f"Parsing {EXPORT_XML} ...")
    t0 = time.time()

    context = iterparse(
        str(EXPORT_XML), events=("end",), tag=("Record", "Workout", "ActivitySummary")
    )

    for event, elem in context:
        tag = elem.tag

        if tag == "Record":
            rtype = elem.get("type")
            if rtype in RECORD_TYPES:
                raw_value = elem.get("value")
                records.append(
                    {
                        "type": rtype,
                        "sourceName": elem.get("sourceName"),
                        "unit": elem.get("unit"),
                        "value": raw_value,
                        "startDate": elem.get("startDate"),
                        "endDate": elem.get("endDate"),
                    }
                )
            record_count += 1
            if record_count % 500_000 == 0:
                elapsed = time.time() - t0
                print(f"  ... {record_count:,} records scanned ({elapsed:.0f}s)")

        elif tag == "Workout":
            w = {
                "workoutActivityType": elem.get("workoutActivityType"),
                "duration": elem.get("duration"),
                "durationUnit": elem.get("durationUnit"),
                "totalDistance": elem.get("totalDistance"),
                "totalDistanceUnit": elem.get("totalDistanceUnit"),
                "totalEnergyBurned": elem.get("totalEnergyBurned"),
                "totalEnergyBurnedUnit": elem.get("totalEnergyBurnedUnit"),
                "sourceName": elem.get("sourceName"),
                "startDate": elem.get("startDate"),
                "endDate": elem.get("endDate"),
            }
            workouts.append(w)

            # Capture WorkoutStatistics children
            for stat in elem.findall("WorkoutStatistics"):
                workout_stats.append(
                    {
                        "workoutStartDate": w["startDate"],
                        "type": stat.get("type"),
                        "startDate": stat.get("startDate"),
                        "endDate": stat.get("endDate"),
                        "average": stat.get("average"),
                        "minimum": stat.get("minimum"),
                        "maximum": stat.get("maximum"),
                        "sum": stat.get("sum"),
                        "unit": stat.get("unit"),
                    }
                )

        elif tag == "ActivitySummary":
            dc = elem.get("dateComponents", "")
            if dc and dc > "2000":  # skip placeholder dates
                activity_summaries.append(
                    {
                        "date": dc,
                        "activeEnergyBurned": elem.get("activeEnergyBurned"),
                        "activeEnergyBurnedGoal": elem.get("activeEnergyBurnedGoal"),
                        "appleExerciseTime": elem.get("appleExerciseTime"),
                        "appleExerciseTimeGoal": elem.get("appleExerciseTimeGoal"),
                        "appleStandHours": elem.get("appleStandHours"),
                        "appleStandHoursGoal": elem.get("appleStandHoursGoal"),
                    }
                )

        # Free memory
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    elapsed = time.time() - t0
    print(f"Done scanning in {elapsed:.0f}s. Total XML records: {record_count:,}")
    print(f"  Kept records: {len(records):,}")
    print(f"  Workouts: {len(workouts):,}")
    print(f"  Workout stats: {len(workout_stats):,}")
    print(f"  Activity summaries: {len(activity_summaries):,}")

    # Convert and save
    print("Writing parquet files ...")

    df_records = pd.DataFrame(records)
    # Keep raw text value for category types (e.g. sleep stages)
    df_records["value_text"] = df_records["value"]
    df_records["value"] = pd.to_numeric(df_records["value"], errors="coerce")
    df_records["startDate"] = pd.to_datetime(df_records["startDate"], format="mixed")
    df_records["endDate"] = pd.to_datetime(df_records["endDate"], format="mixed")
    # Sort by (type, startDate) so PyArrow row-group statistics enable
    # efficient predicate pushdown when filtering by type + date range.
    df_records = df_records.sort_values(["type", "startDate"]).reset_index(drop=True)
    df_records.to_parquet(
        DATA_DIR / "records.parquet", index=False, row_group_size=50_000,
    )
    print(f"  records.parquet: {len(df_records):,} rows")

    df_workouts = pd.DataFrame(workouts)
    for col in ("duration", "totalDistance", "totalEnergyBurned"):
        df_workouts[col] = pd.to_numeric(df_workouts[col], errors="coerce")
    df_workouts["startDate"] = pd.to_datetime(
        df_workouts["startDate"], format="mixed"
    )
    df_workouts["endDate"] = pd.to_datetime(df_workouts["endDate"], format="mixed")
    df_workouts.to_parquet(DATA_DIR / "workouts.parquet", index=False)
    print(f"  workouts.parquet: {len(df_workouts):,} rows")

    if workout_stats:
        df_wstats = pd.DataFrame(workout_stats)
        for col in ("average", "minimum", "maximum", "sum"):
            df_wstats[col] = pd.to_numeric(df_wstats[col], errors="coerce")
        df_wstats.to_parquet(DATA_DIR / "workout_stats.parquet", index=False)
        print(f"  workout_stats.parquet: {len(df_wstats):,} rows")

    df_activity = pd.DataFrame(activity_summaries)
    for col in df_activity.columns:
        if col != "date":
            df_activity[col] = pd.to_numeric(df_activity[col], errors="coerce")
    df_activity["date"] = pd.to_datetime(df_activity["date"])
    df_activity.to_parquet(DATA_DIR / "activity_summary.parquet", index=False)
    print(f"  activity_summary.parquet: {len(df_activity):,} rows")

    print("All done.")


if __name__ == "__main__":
    parse_export()
