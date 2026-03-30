from backend.constants import (
    COLORWAY,
    WORKOUT_COLORS,
    build_workout_color_map,
)

GREY = "#8E8E93"


def test_known_types_get_override_colors() -> None:
    types = ["Running", "Walking", "Cycling"]
    result = build_workout_color_map(types)
    for t in types:
        assert result[t] == WORKOUT_COLORS[t]


def test_unknown_types_get_palette_colors() -> None:
    types = ["Yoga", "Swimming", "Tennis"]
    result = build_workout_color_map(types)
    for t in types:
        assert result[t] != GREY
        assert result[t] in COLORWAY


def test_mixed_known_and_unknown() -> None:
    types = ["Running", "Yoga", "Walking"]
    result = build_workout_color_map(types)
    assert result["Running"] == WORKOUT_COLORS["Running"]
    assert result["Walking"] == WORKOUT_COLORS["Walking"]
    assert result["Yoga"] in COLORWAY
    # Yoga should not reuse Running or Walking's colors
    assert result["Yoga"] not in {result["Running"], result["Walking"]}


def test_stable_ordering() -> None:
    types = ["Yoga", "Swimming", "Tennis", "Boxing"]
    a = build_workout_color_map(types)
    b = build_workout_color_map(list(reversed(types)))
    assert a == b


def test_more_types_than_palette_wraps() -> None:
    types = [f"Sport{i}" for i in range(20)]
    result = build_workout_color_map(types, overrides={})
    assert len(result) == 20
    assert all(c in COLORWAY for c in result.values())
