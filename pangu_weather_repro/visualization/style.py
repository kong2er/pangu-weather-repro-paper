"""Centralized plot style presets for product/paper rendering.

This module keeps visual defaults in one place so product/paper outputs stay
consistent and easier to align with the reference repository style.
"""
from __future__ import annotations

from typing import Any

STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "standard": {
        "figure": {"dpi": 220, "figsize_fill": (7.2, 3.8), "figsize_vector": (7.2, 3.8)},
        "fill_defaults": {
            "z500": {
                "cmap": "turbo",
                "vmin": 47000.0,
                "vmax": 59000.0,
                "levels": [47000, 49000, 51000, 53000, 55000, 57000, 59000],
                "unit_label": "m^2 s^-2",
            },
            "t2m": {
                "cmap": "coolwarm",
                "vmin": 220.0,
                "vmax": 320.0,
                "levels": [220, 240, 260, 280, 300, 320],
                "unit_label": "K",
            },
            "u10": {"cmap": "PuOr_r", "vmin": -30.0, "vmax": 30.0, "unit_label": "m s^-1"},
            "v10": {"cmap": "PuOr_r", "vmin": -30.0, "vmax": 30.0, "unit_label": "m s^-1"},
            "wind_speed": {
                "cmap": "viridis",
                "vmin": 0.0,
                "vmax": 35.0,
                "levels": [0, 5, 10, 15, 20, 25, 30, 35],
                "unit_label": "m s^-1",
            },
            # Use hPa for product readability while keeping model data in Pa.
            "msl": {
                "cmap": "coolwarm",
                "vmin": 950.0,
                "vmax": 1050.0,
                "levels": [950, 970, 990, 1010, 1030, 1050],
                "unit_label": "hPa",
                "convert_from_pa": True,
            },
        },
        "diff_defaults": {
            "z500": {"cmap": "RdBu_r", "vlim": 300.0},
            "msl": {"cmap": "RdBu_r", "vlim": 15.0},
        },
        "vector": {
            "stride_global": 18,
            "stride_regional": 10,
            "scale": 250.0,
            "width": 0.0018,
            "headwidth": 3.5,
            "headlength": 4.0,
            "color": "black",
        },
        "contour": {
            "msl_wind": {
                "enabled": True,
                "levels": [960, 980, 1000, 1020, 1040],
                "linewidth": 0.6,
                "color": "k",
                "label_fontsize": 7,
            }
        },
    }
}


def get_style(profile: str = "standard") -> dict[str, Any]:
    return STYLE_PRESETS.get(profile, STYLE_PRESETS["standard"])


def get_fill_style(var: str, profile: str = "standard") -> dict[str, Any]:
    return get_style(profile).get("fill_defaults", {}).get(var, {})


def get_diff_style(var: str, profile: str = "standard") -> dict[str, Any]:
    return get_style(profile).get("diff_defaults", {}).get(var, {})


def get_vector_style(profile: str = "standard") -> dict[str, Any]:
    return get_style(profile).get("vector", {})
