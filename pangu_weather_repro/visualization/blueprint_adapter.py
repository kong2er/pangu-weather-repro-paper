"""Thin adapter for selecting plotting implementation.

This keeps CLI stable while allowing gradual vendor/blueprint alignment.
"""
from __future__ import annotations

from typing import Callable

from pangu_weather_repro.visualization import product_draw as native


DrawFn = Callable[..., tuple[str, str]]


def resolve_product_draw_impl(impl: str = "auto") -> tuple[str, dict[str, DrawFn], str]:
    """Resolve drawing implementation with safe fallback.

    Returns:
      selected_impl: final implementation name
      funcs: draw function mapping
      note: runtime note for logs
    """
    impl = (impl or "auto").strip().lower()
    funcs = {
        "draw_global_fill": native.draw_global_fill,
        "draw_diff_fill": native.draw_diff_fill,
        "draw_wind_vector": native.draw_wind_vector,
        "draw_wind_speed": native.draw_wind_speed,
        "draw_msl_wind": native.draw_msl_wind,
    }
    if impl == "native":
        return "native", funcs, "native implementation selected"

    if impl in {"blueprint", "auto"}:
        try:
            # Validation import only; runtime still calls stable wrappers here.
            # This avoids breaking current reproducible flow if optional deps are missing.
            import vendor.blueprint.pangu.visualization.product_draw  # type: ignore # noqa: F401
            if impl == "blueprint":
                return "blueprint", funcs, "blueprint source available; adapter uses stable wrappers"
            return "native", funcs, "auto: blueprint source detected, using stable wrappers"
        except Exception as exc:  # pragma: no cover - environment dependent
            if impl == "blueprint":
                return "native", funcs, f"blueprint unavailable ({exc}); fallback to native"
            return "native", funcs, "auto: blueprint unavailable, using native"

    return "native", funcs, f"unknown impl '{impl}', fallback to native"

