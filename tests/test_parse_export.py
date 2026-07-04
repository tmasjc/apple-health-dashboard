"""Tests for parse_export timestamp handling (local wall-clock + interval)."""

import pandas as pd

from scripts.parse_export import _offset_minutes, _to_naive_local


def _interval_minutes(start_raw: list[str], end_raw: list[str]) -> pd.Series:
    """Reproduce _flush_records' timestamp normalization and return the interval."""
    start_str = pd.Series(start_raw)
    end_str = pd.Series(end_raw)
    start_local = _to_naive_local(start_str)
    end_local = _to_naive_local(end_str)
    offset_delta = _offset_minutes(start_str) - _offset_minutes(end_str)
    start = start_local
    end = end_local + pd.to_timedelta(offset_delta, unit="m")
    return (end - start).dt.total_seconds() / 60, start, end


def test_to_naive_local_drops_offset():
    """Local wall-clock time is preserved and the UTC offset is dropped."""
    result = _to_naive_local(pd.Series(["2024-06-01 23:15:00 -0700"]))
    assert result.iloc[0] == pd.Timestamp("2024-06-01 23:15:00")


def test_offset_minutes_signed():
    """UTC offsets parse to signed minutes; a missing offset is treated as 0."""
    offsets = _offset_minutes(
        pd.Series(["... -0700", "... +0530", "no-offset"])
    )
    assert list(offsets) == [-420, 330, 0]


def test_interval_same_offset_is_true_elapsed():
    """A normal segment keeps its local wall-clock and correct duration."""
    dur, start, end = _interval_minutes(
        ["2024-06-01 23:00:00 -0700"], ["2024-06-02 06:30:00 -0700"]
    )
    assert dur.iloc[0] == 450.0  # 7.5 hours
    assert start.iloc[0] == pd.Timestamp("2024-06-01 23:00:00")
    assert end.iloc[0] == pd.Timestamp("2024-06-02 06:30:00")


def test_interval_across_dst_fallback_stays_positive():
    """A segment straddling the autumn DST fall-back keeps its true 45-min length.

    Stripping start/end offsets independently would yield a naive wall-clock
    difference of -15 min; realigning endDate into startDate's offset frame
    recovers the real elapsed interval.
    """
    dur, start, _ = _interval_minutes(
        ["2024-11-03 01:30:00 -0700"], ["2024-11-03 01:15:00 -0800"]
    )
    assert dur.iloc[0] == 45.0
    assert start.iloc[0] == pd.Timestamp("2024-11-03 01:30:00")  # local preserved
