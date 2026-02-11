"""Helpers for filtering product plot filenames."""
from __future__ import annotations

import re


def parse_product_name(name: str) -> tuple[str, str, str]:
    """Parse product image name into (kind, var, lead)."""
    if not name.startswith("product_") or not name.endswith(".png"):
        return ("other", "other", "other")

    m = re.match(r"^product_diff_([a-z0-9_]+)_t\+(\d{3})\.png$", name)
    if m:
        return ("diff", m.group(1), m.group(2))

    m = re.match(r"^product_vector_([a-z0-9_]+)_t\+(\d{3})\.png$", name)
    if m:
        return ("vector", m.group(1), m.group(2))

    m = re.match(r"^product_wind_speed_t\+(\d{3})\.png$", name)
    if m:
        return ("wind_speed", "wind_speed", m.group(1))

    m = re.match(r"^product_msl_wind_t\+(\d{3})\.png$", name)
    if m:
        return ("msl_wind", "msl_wind", m.group(1))

    m = re.match(r"^product_([a-z0-9_]+)_t\+(\d{3})\.png$", name)
    if m:
        return ("fill", m.group(1), m.group(2))

    return ("other", "other", "other")
