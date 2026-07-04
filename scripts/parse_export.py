"""
Streaming parser for Apple Health export.xml → Parquet files.
Uses lxml iterparse to handle the ~2 GB XML without loading it into memory.
Records are flushed to Parquet in batches to avoid OOM on large exports.
"""

import sys
import time
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
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


BATCH_SIZE = 50_000

RECORDS_SCHEMA = pa.schema(
    [
        ("type", pa.string()),
        ("sourceName", pa.string()),
        ("unit", pa.string()),
        ("value", pa.float64()),
        ("value_text", pa.string()),
        ("startDate", pa.timestamp("us")),
        ("endDate", pa.timestamp("us")),
    ]
)

# Apple Health timestamps look like "2024-11-03 01:30:00 -0700". We store the
# local wall-clock time (offset dropped) so charts show local hours rather than
# UTC-shifted ones. An explicit format vectorizes parsing; format="mixed" would
# re-infer the format per element across millions of rows on the hot path.
_OFFSET_RE = r"\s*([+-]\d{4})$"
_TS_FMT = "%Y-%m-%d %H:%M:%S"


def _to_naive_local(ts: pd.Series) -> pd.Series:
    """Parse Apple-Health timestamps to naive local wall-clock (UTC offset dropped)."""
    stripped = ts.str.replace(_OFFSET_RE, "", regex=True)
    return pd.to_datetime(stripped, format=_TS_FMT)


def _offset_minutes(ts: pd.Series) -> pd.Series:
    """Extract the signed UTC offset, in minutes, from Apple-Health timestamps."""
    offset = ts.str.extract(_OFFSET_RE, expand=False)
    sign = offset.str[0].map({"+": 1, "-": -1})
    hours = pd.to_numeric(offset.str[1:3], errors="coerce")
    minutes = pd.to_numeric(offset.str[3:5], errors="coerce")
    return (sign * (hours * 60 + minutes)).fillna(0)


def _flush_records(batch: list[dict], writer: pq.ParquetWriter) -> None:
    """Convert a batch of raw record dicts to a typed RecordBatch and write it."""
    df = pd.DataFrame(batch)
    df["value_text"] = df["value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    # Store local wall-clock time (offset dropped); without this PyArrow converts
    # tz-aware datetimes to UTC on write to the tz-naive schema, shifting hours.
    # Realign endDate into startDate's offset frame so (endDate - startDate) stays
    # the true elapsed interval even when a record straddles a DST / timezone
    # change and its two boundaries carry different UTC offsets (stripping them
    # independently would corrupt the duration — negative or off by the offset).
    start_local = _to_naive_local(df["startDate"])
    end_local = _to_naive_local(df["endDate"])
    offset_delta = _offset_minutes(df["startDate"]) - _offset_minutes(df["endDate"])
    df["startDate"] = start_local
    df["endDate"] = end_local + pd.to_timedelta(offset_delta, unit="m")
    table = pa.Table.from_pandas(df, schema=RECORDS_SCHEMA, preserve_index=False)
    writer.write_table(table)


def parse_export():
    DATA_DIR.mkdir(exist_ok=True)

    records_batch: list[dict] = []
    workouts: list[dict] = []
    workout_stats: list[dict] = []
    activity_summaries: list[dict] = []
    record_count = 0
    kept_count = 0

    records_path = DATA_DIR / "records.parquet"
    records_tmp = DATA_DIR / "records.parquet.tmp"

    print(f"Parsing {EXPORT_XML} ...")
    t0 = time.time()

    context = iterparse(
        str(EXPORT_XML), events=("end",), tag=("Record", "Workout", "ActivitySummary")
    )

    writer = pq.ParquetWriter(str(records_tmp), RECORDS_SCHEMA)

    try:
        for event, elem in context:
            tag = elem.tag

            if tag == "Record":
                rtype = elem.get("type")
                if rtype in RECORD_TYPES:
                    records_batch.append(
                        {
                            "type": rtype,
                            "sourceName": elem.get("sourceName"),
                            "unit": elem.get("unit"),
                            "value": elem.get("value"),
                            "startDate": elem.get("startDate"),
                            "endDate": elem.get("endDate"),
                        }
                    )
                    kept_count += 1
                    if len(records_batch) >= BATCH_SIZE:
                        _flush_records(records_batch, writer)
                        records_batch.clear()
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
                if dc and dc > "2000":
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

            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

        # Flush remaining records
        if records_batch:
            _flush_records(records_batch, writer)
            records_batch.clear()

    finally:
        writer.close()

    # Atomically replace the output file
    records_tmp.rename(records_path)

    # Re-read and sort so row-group statistics enable predicate pushdown
    table = pq.read_table(str(records_path))
    table = table.sort_by([("type", "ascending"), ("startDate", "ascending")])
    pq.write_table(table, str(records_path), row_group_size=BATCH_SIZE)

    elapsed = time.time() - t0
    print(f"Done scanning in {elapsed:.0f}s. Total XML records: {record_count:,}")
    print(f"  Kept records: {kept_count:,}")
    print(f"  Workouts: {len(workouts):,}")
    print(f"  Workout stats: {len(workout_stats):,}")
    print(f"  Activity summaries: {len(activity_summaries):,}")

    print("Writing remaining parquet files ...")

    df_workouts = pd.DataFrame(workouts)
    for col in ("duration", "totalDistance", "totalEnergyBurned"):
        df_workouts[col] = pd.to_numeric(df_workouts[col], errors="coerce")
    df_workouts["startDate"] = _to_naive_local(df_workouts["startDate"])
    df_workouts["endDate"] = _to_naive_local(df_workouts["endDate"])
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
