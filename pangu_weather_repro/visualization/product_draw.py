"""Product-style drawing primitives (E2 incremental alignment).

Current scope:
- draw_global_fill: global contour-like filled map with metadata sidecar.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from pangu_weather_repro.visualization.geo import (
    detect_geo_resource,
    resolve_geo_assets_dir,
    try_import_cartopy,
)


def _auto_range(data: np.ndarray, vmin: float | None, vmax: float | None) -> tuple[float, float]:
    if vmin is not None and vmax is not None:
        return float(vmin), float(vmax)
    p1, p99 = np.percentile(data, [1, 99])
    return (float(p1) if vmin is None else float(vmin), float(p99) if vmax is None else float(vmax))


def draw_global_fill(
    data: np.ndarray,
    out_png: str | Path,
    *,
    out_json: str | Path | None = None,
    var: str = "z500",
    lead_hour: int = 0,
    units: str = "",
    title: str = "",
    cmap: str = "turbo",
    vmin: float | None = None,
    vmax: float | None = None,
    dpi: int = 220,
    with_geo: bool = False,
    geo_assets_dir: str | None = None,
    force: bool = False,
    extra_meta: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Draw one product image and write metadata json.

    The function is idempotent by default: existing files are not overwritten
    unless force=True.
    """
    import matplotlib.pyplot as plt

    out_png = str(out_png)
    out_json = str(out_json or out_png.replace(".png", ".json"))
    if Path(out_png).exists() and not force:
        return out_png, out_json

    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    data = np.asarray(data)
    if data.ndim != 2:
        raise ValueError(f"draw_global_fill expects 2D array, got {data.shape}")

    ccrs, cfeature = try_import_cartopy()
    assets_dir = resolve_geo_assets_dir(geo_assets_dir)
    resource_hint = detect_geo_resource(assets_dir)
    geo_requested = bool(with_geo)
    geo_ok = geo_requested and ccrs is not None
    geo_error = ""
    vmin_use, vmax_use = _auto_range(data, vmin, vmax)
    extent = (0.0, 360.0, -90.0, 90.0)

    if geo_ok:
        try:
            fig = plt.figure(figsize=(7.0, 3.6), dpi=dpi)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_global()
            ax.coastlines(linewidth=0.5)
            if cfeature is not None:
                ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.25)
            im = ax.imshow(
                data,
                extent=extent,
                origin="upper",
                cmap=cmap,
                vmin=vmin_use,
                vmax=vmax_use,
                transform=ccrs.PlateCarree(),
            )
        except Exception as exc:
            # cartopy may import successfully but fail at runtime if scipy/pykdtree is missing.
            geo_ok = False
            geo_error = str(exc)
            fig, ax = plt.subplots(figsize=(7.0, 3.6), dpi=dpi)
            im = ax.imshow(data, extent=extent, origin="upper", cmap=cmap, vmin=vmin_use, vmax=vmax_use)
            ax.set_xlabel("lon")
            ax.set_ylabel("lat")
    else:
        fig, ax = plt.subplots(figsize=(7.0, 3.6), dpi=dpi)
        im = ax.imshow(data, extent=extent, origin="upper", cmap=cmap, vmin=vmin_use, vmax=vmax_use)
        ax.set_xlabel("lon")
        ax.set_ylabel("lat")

    t = title or f"{var} t+{lead_hour:03d}"
    if units:
        t += f" ({units})"
    ax.set_title(t)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    if units:
        cb.set_label(units)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

    meta = {
        "type": "global_fill",
        "var": var,
        "lead_hour": int(lead_hour),
        "units": units,
        "title": t,
        "cmap": cmap,
        "vmin": float(vmin_use),
        "vmax": float(vmax_use),
        "dpi": int(dpi),
        "with_geo_requested": geo_requested,
        "with_geo": bool(geo_ok),
        "geo_assets_dir": str(assets_dir) if assets_dir else "",
        "geo_resource_hint": resource_hint,
        "geo_error": geo_error,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    if extra_meta:
        meta.update(extra_meta)

    with open(out_json, "w") as f:
        json.dump(meta, f, indent=2)
    return out_png, out_json
