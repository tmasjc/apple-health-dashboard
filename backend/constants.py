"""Apple-inspired color palette and color maps."""

import itertools

BLUE = "#5B9BD5"
GREEN = "#70AD47"
ORANGE = "#ED7D31"
PINK = "#E07B8E"
PURPLE = "#9B7EC8"
TEAL = "#6BC4CE"
RED = "#D46A6A"
INDIGO = "#7B7FB5"

COLORWAY = [BLUE, GREEN, ORANGE, PINK, PURPLE, TEAL, RED, INDIGO]

WORKOUT_COLORS = {
    "FunctionalStrengthTraining": PINK,
    "Walking": GREEN,
    "Running": BLUE,
}



def build_workout_color_map(
    workout_types: list[str],
    overrides: dict[str, str] = WORKOUT_COLORS,
    palette: list[str] = COLORWAY,
) -> dict[str, str]:
    sorted_types = sorted(workout_types)
    used_colors = {overrides[t] for t in sorted_types if t in overrides}
    available = [c for c in palette if c not in used_colors]
    if not available:
        available = palette
    pool = itertools.cycle(available)
    return {
        t: overrides[t] if t in overrides else next(pool)
        for t in sorted_types
    }


SLEEP_STAGE_COLORS = {
    "Deep": INDIGO,
    "Core": BLUE,
    "REM": PURPLE,
    "Awake": ORANGE,
}

CHART_LAYOUT = {
    "paper_bgcolor": "rgba(255, 255, 255, 0)",
    "plot_bgcolor": "rgba(255, 255, 255, 0)",
    "font": {
        "family": (
            "-apple-system, BlinkMacSystemFont, 'SF Pro Text', "
            "system-ui, sans-serif"
        ),
        "color": "#1d1d1f",
        "size": 12,
    },
    "xaxis": {"gridcolor": "#e5e5e7", "zerolinecolor": "#d1d1d6"},
    "yaxis": {"gridcolor": "#e5e5e7", "zerolinecolor": "#d1d1d6"},
    "colorway": COLORWAY,
}
