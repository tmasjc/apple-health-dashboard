from backend.constants import (
    ACCENT,
    RAMP_ASSIGN_ORDER,
    WORKOUT_COLORS,
    build_workout_color_map,
)


def test_known_types_get_override_colors() -> None:
    types = ["FunctionalStrengthTraining", "Running", "Walking"]
    result = build_workout_color_map(types)
    for t in types:
        assert result[t] == WORKOUT_COLORS[t]


def test_unknown_types_get_ramp_colors() -> None:
    types = ["Yoga", "Swimming", "Tennis"]
    result = build_workout_color_map(types)
    for t in types:
        assert result[t] in RAMP_ASSIGN_ORDER


def test_most_frequent_unknown_gets_accent() -> None:
    # Input is ordered by session count, most frequent first.
    result = build_workout_color_map(["Yoga", "Swimming"])
    assert result["Yoga"] == ACCENT


def test_mixed_known_and_unknown() -> None:
    types = ["Running", "Yoga", "Walking"]
    result = build_workout_color_map(types)
    assert result["Running"] == WORKOUT_COLORS["Running"]
    assert result["Walking"] == WORKOUT_COLORS["Walking"]
    assert result["Yoga"] in RAMP_ASSIGN_ORDER
    # Yoga should not reuse Running or Walking's colors
    assert result["Yoga"] not in {result["Running"], result["Walking"]}


def test_frequency_ordering_drives_assignment() -> None:
    # More frequent unknown types claim earlier (more prominent) ramp colors.
    result = build_workout_color_map(["Yoga", "Swimming"], overrides={})
    assert RAMP_ASSIGN_ORDER.index(result["Yoga"]) < RAMP_ASSIGN_ORDER.index(
        result["Swimming"]
    )


def test_more_types_than_palette_falls_back() -> None:
    types = [f"Sport{i}" for i in range(20)]
    result = build_workout_color_map(types, overrides={})
    assert len(result) == 20
    assert all(c in RAMP_ASSIGN_ORDER for c in result.values())
