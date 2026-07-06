"""Horizon Mono design tokens: Solar Coral accent + light/dark themes."""

ACCENT = "#E85D3A"
ACCENT_DEEP = "#B8401F"

# Coral ramp, dark → light
CORAL_RAMP = [
    "#B8401F", "#E85D3A", "#F07B54", "#F49775",
    "#F8B296", "#FBC9B4", "#FDDCCE", "#FEEDE5",
]

# Assignment order for workout types not named in WORKOUT_COLORS:
# most frequent gets the accent, then progressively deeper/lighter ramp steps.
RAMP_ASSIGN_ORDER = [
    "#E85D3A", "#B8401F", "#F07B54", "#F49775",
    "#F8B296", "#FBC9B4", "#FDDCCE", "#FEEDE5",
]

THEMES = {
    "light": {
        "bg": "#F4F4F6",
        "card": "#FFFFFF",
        "border": "#E4E5EA",
        "text": "#141519",
        "sub": "#73767F",
        "nav_bg": "#E9EAEF",
        "grid": "rgba(20,21,25,0.07)",
        "tick": "#8A8D96",
        "muted": "#D9DBE2",
        "dot": "#B8BBC6",
        "hrv": "#C39B8D",
    },
    "dark": {
        "bg": "#0E0F13",
        "card": "#16181E",
        "border": "#262932",
        "text": "#F0F1F5",
        "sub": "#8D919E",
        "nav_bg": "#1C1F27",
        "grid": "rgba(255,255,255,0.08)",
        "tick": "#767B88",
        "muted": "#2A2E3A",
        "dot": "#3E4454",
        "hrv": "#D89A85",
    },
}

WORKOUT_COLORS = {
    "FunctionalStrengthTraining": "#E85D3A",
    "HighIntensityIntervalTraining": "#B8401F",
    "Cycling": "#F07B54",
    "Running": "#F49775",
    "Rowing": "#F8B296",
    "Walking": "#FBC9B4",
    "Hiking": "#FDDCCE",
    "Elliptical": "#FEEDE5",
}


def build_workout_color_map(
    workout_types: list[str],
    overrides: dict[str, str] = WORKOUT_COLORS,
    palette: list[str] = RAMP_ASSIGN_ORDER,
) -> dict[str, str]:
    """Map workout types to coral-ramp colors.

    ``workout_types`` must be ordered by session count, most frequent first;
    unlisted types take ramp colors in that order (most frequent = accent),
    skipping colors already claimed by named types present in the input.
    """
    used_colors = {overrides[t] for t in workout_types if t in overrides}
    available = [c for c in palette if c not in used_colors]
    result: dict[str, str] = {}
    for t in workout_types:
        if t in overrides:
            result[t] = overrides[t]
        elif available:
            result[t] = available.pop(0)
        else:
            result[t] = palette[-1]
    return result


def sleep_stage_colors(theme: str = "light") -> dict[str, str]:
    return {
        "Deep": "#B8401F",
        "Core": "#F07B54",
        "REM": "#F8B296",
        "Awake": THEMES[theme]["muted"],
    }


FONT_FAMILY = "'Space Grotesk', system-ui, sans-serif"


def chart_layout(theme: str = "light") -> dict:
    t = THEMES[theme]
    axis = {
        "gridcolor": t["grid"],
        "zerolinecolor": t["grid"],
        "linecolor": "rgba(0,0,0,0)",
    }
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": FONT_FAMILY, "color": t["tick"], "size": 11},
        "xaxis": axis,
        "yaxis": dict(axis),
        "showlegend": False,
    }
