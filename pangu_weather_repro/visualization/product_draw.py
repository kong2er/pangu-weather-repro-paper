"""Product-style drawing primitives (E2 incremental alignment).

Current scope:
- draw_global_fill: global contour-like filled map with metadata sidecar.
- draw_diff_fill: pred-ref difference map.
- draw_wind_vector: near-surface wind vector (u/v) map.
- draw_msl_wind: msl filled map with uv10 vectors.
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

# 产品图默认样式（G1）：优先保证可复现一致性。
# 若调用方显式传 vmin/vmax/cmap，则以调用方为准。
STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "standard": {
        "fill_defaults": {
            "z500": {"cmap": "turbo", "vmin": 47000.0, "vmax": 59000.0},
            "t2m": {"cmap": "coolwarm", "vmin": 220.0, "vmax": 320.0},
            "u10": {"cmap": "viridis", "vmin": -30.0, "vmax": 30.0},
            "v10": {"cmap": "viridis", "vmin": -30.0, "vmax": 30.0},
            "wind_speed": {"cmap": "viridis", "vmin": 0.0, "vmax": 35.0},
            "msl": {"cmap": "coolwarm", "vmin": 95000.0, "vmax": 105000.0},
        },
        "diff_defaults": {
            "z500": {"cmap": "RdBu_r", "vlim": 300.0},
        },
    }
}


def _auto_range(data: np.ndarray, vmin: float | None, vmax: float | None) -> tuple[float, float]:
    if vmin is not None and vmax is not None:
        return float(vmin), float(vmax)
    p1, p99 = np.percentile(data, [1, 99])
    return (float(p1) if vmin is None else float(vmin), float(p99) if vmax is None else float(vmax))


def _normalize_extent(extent: tuple[float, float, float, float] | None) -> tuple[float, float, float, float]:
    if extent is None:
        return (0.0, 360.0, -90.0, 90.0)
    if len(extent) != 4:
        raise ValueError(f"extent must be 4 values, got: {extent}")
    return tuple(float(x) for x in extent)


def _resolve_fill_style(
    data: np.ndarray,
    var: str,
    *,
    style_profile: str,
    cmap: str | None,
    vmin: float | None,
    vmax: float | None,
) -> tuple[str, float, float, str]:
    profile = STYLE_PRESETS.get(style_profile, STYLE_PRESETS["standard"])
    defaults = profile.get("fill_defaults", {}).get(var, {})
    cmap_use = str(cmap if cmap is not None else defaults.get("cmap", "turbo"))
    vmin_default = defaults.get("vmin")
    vmax_default = defaults.get("vmax")

    if vmin is not None and vmax is not None:
        return cmap_use, float(vmin), float(vmax), "explicit"
    if vmin_default is not None and vmax_default is not None and vmin is None and vmax is None:
        return cmap_use, float(vmin_default), float(vmax_default), "style_default"

    # mixed / fallback case
    p1, p99 = np.percentile(np.asarray(data), [1, 99])
    vmin_use = float(p1) if vmin is None else float(vmin)
    vmax_use = float(p99) if vmax is None else float(vmax)
    return cmap_use, vmin_use, vmax_use, "percentile"


def _resolve_diff_style(
    var: str,
    *,
    style_profile: str,
    cmap: str | None,
    vlim: float | None,
    diff: np.ndarray,
) -> tuple[str, float, float, str]:
    profile = STYLE_PRESETS.get(style_profile, STYLE_PRESETS["standard"])
    defaults = profile.get("diff_defaults", {}).get(var, {})
    cmap_use = str(cmap if cmap is not None else defaults.get("cmap", "RdBu_r"))
    if vlim is not None:
        vmax = float(vlim)
        return cmap_use, -vmax, vmax, "explicit"
    if defaults.get("vlim") is not None:
        vmax = float(defaults["vlim"])
        return cmap_use, -vmax, vmax, "style_default"
    vmax = float(np.nanpercentile(np.abs(diff), 99))
    vmax = max(vmax, 1e-6)
    return cmap_use, -vmax, vmax, "percentile"


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
    style_profile: str = "standard",
    with_geo: bool = False,
    geo_assets_dir: str | None = None,
    extent: tuple[float, float, float, float] | None = None,
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
    cmap_use, vmin_use, vmax_use, range_source = _resolve_fill_style(
        data,
        var,
        style_profile=style_profile,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
    )
    extent = _normalize_extent(extent)

    if geo_ok:
        try:
            fig = plt.figure(figsize=(7.0, 3.6), dpi=dpi)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(extent, crs=ccrs.PlateCarree())
            ax.coastlines(linewidth=0.5)
            if cfeature is not None:
                ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.25)
            im = ax.imshow(
                data,
                extent=extent,
                origin="upper",
                cmap=cmap_use,
                vmin=vmin_use,
                vmax=vmax_use,
                transform=ccrs.PlateCarree(),
            )
        except Exception as exc:
            # cartopy may import successfully but fail at runtime if scipy/pykdtree is missing.
            geo_ok = False
            geo_error = str(exc)
            fig, ax = plt.subplots(figsize=(7.0, 3.6), dpi=dpi)
            im = ax.imshow(data, extent=extent, origin="upper", cmap=cmap_use, vmin=vmin_use, vmax=vmax_use)
            ax.set_xlabel("lon")
            ax.set_ylabel("lat")
    else:
        fig, ax = plt.subplots(figsize=(7.0, 3.6), dpi=dpi)
        im = ax.imshow(data, extent=extent, origin="upper", cmap=cmap_use, vmin=vmin_use, vmax=vmax_use)
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
        "cmap": cmap_use,
        "vmin": float(vmin_use),
        "vmax": float(vmax_use),
        "range_source": range_source,
        "dpi": int(dpi),
        "style_profile": style_profile,
        "with_geo_requested": geo_requested,
        "with_geo": bool(geo_ok),
        "geo_assets_dir": str(assets_dir) if assets_dir else "",
        "geo_resource_hint": resource_hint,
        "geo_error": geo_error,
        "extent": list(extent),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    if extra_meta:
        meta.update(extra_meta)

    with open(out_json, "w") as f:
        json.dump(meta, f, indent=2)
    return out_png, out_json


def draw_diff_fill(
    pred: np.ndarray,
    ref: np.ndarray,
    out_png: str | Path,
    *,
    out_json: str | Path | None = None,
    var: str = "z500",
    lead_hour: int = 0,
    units: str = "",
    title: str = "",
    cmap: str = "RdBu_r",
    vlim: float | None = None,
    extent: tuple[float, float, float, float] | None = None,
    dpi: int = 220,
    style_profile: str = "standard",
    force: bool = False,
    extra_meta: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Draw pred-ref difference map and write metadata json."""
    import matplotlib.pyplot as plt

    out_png = str(out_png)
    out_json = str(out_json or out_png.replace(".png", ".json"))
    if Path(out_png).exists() and not force:
        return out_png, out_json

    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    pred = np.asarray(pred, dtype=np.float32)
    ref = np.asarray(ref, dtype=np.float32)
    if pred.shape != ref.shape or pred.ndim != 2:
        raise ValueError(f"draw_diff_fill expects two 2D arrays with same shape, got {pred.shape} vs {ref.shape}")

    diff = pred - ref
    cmap_use, vmin, vmax, range_source = _resolve_diff_style(
        var,
        style_profile=style_profile,
        cmap=cmap,
        vlim=vlim,
        diff=diff,
    )

    extent = _normalize_extent(extent)
    fig, ax = plt.subplots(figsize=(7.0, 3.6), dpi=dpi)
    im = ax.imshow(diff, extent=extent, origin="upper", cmap=cmap_use, vmin=vmin, vmax=vmax)
    ax.set_xlabel("lon")
    ax.set_ylabel("lat")
    t = title or f"{var} pred-ref t+{lead_hour:03d}"
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
        "type": "diff_fill",
        "var": var,
        "lead_hour": int(lead_hour),
        "units": units,
        "title": t,
        "cmap": cmap_use,
        "vmin": vmin,
        "vmax": vmax,
        "range_source": range_source,
        "extent": list(extent),
        "dpi": int(dpi),
        "style_profile": style_profile,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    if extra_meta:
        meta.update(extra_meta)

    with open(out_json, "w") as f:
        json.dump(meta, f, indent=2)
    return out_png, out_json


def draw_wind_vector(
    u: np.ndarray,
    v: np.ndarray,
    out_png: str | Path,
    *,
    out_json: str | Path | None = None,
    lead_hour: int = 0,
    title: str = "",
    dpi: int = 220,
    style_profile: str = "standard",
    with_geo: bool = False,
    geo_assets_dir: str | None = None,
    extent: tuple[float, float, float, float] | None = None,
    stride: int = 18,
    force: bool = False,
    extra_meta: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Draw 10m wind vectors and write metadata json."""
    import matplotlib.pyplot as plt

    out_png = str(out_png)
    out_json = str(out_json or out_png.replace(".png", ".json"))
    if Path(out_png).exists() and not force:
        return out_png, out_json

    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    u = np.asarray(u, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)
    if u.shape != v.shape or u.ndim != 2:
        raise ValueError(f"draw_wind_vector expects two 2D arrays with same shape, got {u.shape} vs {v.shape}")

    ccrs, cfeature = try_import_cartopy()
    assets_dir = resolve_geo_assets_dir(geo_assets_dir)
    resource_hint = detect_geo_resource(assets_dir)
    geo_requested = bool(with_geo)
    geo_ok = geo_requested and ccrs is not None
    geo_error = ""
    extent = _normalize_extent(extent)
    speed = np.sqrt(u * u + v * v)

    lat = np.linspace(90.0, -90.0, u.shape[0], dtype=np.float32)
    lon = np.linspace(0.0, 360.0, u.shape[1], endpoint=False, dtype=np.float32)
    lon2d, lat2d = np.meshgrid(lon, lat)

    if geo_ok:
        try:
            fig = plt.figure(figsize=(7.2, 3.8), dpi=dpi)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(extent, crs=ccrs.PlateCarree())
            ax.coastlines(linewidth=0.5)
            if cfeature is not None:
                ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.25)
            bg = ax.imshow(
                speed,
                extent=extent,
                origin="upper",
                cmap="viridis",
                transform=ccrs.PlateCarree(),
                alpha=0.82,
            )
            ax.quiver(
                lon2d[::stride, ::stride],
                lat2d[::stride, ::stride],
                u[::stride, ::stride],
                v[::stride, ::stride],
                transform=ccrs.PlateCarree(),
                color="white",
                linewidth=0.25,
                scale=250.0,
            )
        except Exception as exc:
            geo_ok = False
            geo_error = str(exc)
            fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=dpi)
            bg = ax.imshow(speed, extent=extent, origin="upper", cmap="viridis", alpha=0.82)
            ax.quiver(
                lon2d[::stride, ::stride],
                lat2d[::stride, ::stride],
                u[::stride, ::stride],
                v[::stride, ::stride],
                color="white",
                linewidth=0.25,
                scale=250.0,
            )
            ax.set_xlabel("lon")
            ax.set_ylabel("lat")
    else:
        fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=dpi)
        bg = ax.imshow(speed, extent=extent, origin="upper", cmap="viridis", alpha=0.82)
        ax.quiver(
            lon2d[::stride, ::stride],
            lat2d[::stride, ::stride],
            u[::stride, ::stride],
            v[::stride, ::stride],
            color="white",
            linewidth=0.25,
            scale=250.0,
        )
        ax.set_xlabel("lon")
        ax.set_ylabel("lat")

    t = title or f"uv10 vector t+{lead_hour:03d}"
    ax.set_title(t)
    cb = fig.colorbar(bg, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label("m s^-1")
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

    meta = {
        "type": "wind_vector",
        "lead_hour": int(lead_hour),
        "title": t,
        "dpi": int(dpi),
        "stride": int(stride),
        "style_profile": style_profile,
        "with_geo_requested": geo_requested,
        "with_geo": bool(geo_ok),
        "geo_assets_dir": str(assets_dir) if assets_dir else "",
        "geo_resource_hint": resource_hint,
        "geo_error": geo_error,
        "extent": list(extent),
        "speed_min": float(np.nanmin(speed)),
        "speed_max": float(np.nanmax(speed)),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    if extra_meta:
        meta.update(extra_meta)

    with open(out_json, "w") as f:
        json.dump(meta, f, indent=2)
    return out_png, out_json


def draw_wind_speed(
    u: np.ndarray,
    v: np.ndarray,
    out_png: str | Path,
    *,
    out_json: str | Path | None = None,
    lead_hour: int = 0,
    title: str = "",
    dpi: int = 220,
    style_profile: str = "standard",
    with_geo: bool = False,
    geo_assets_dir: str | None = None,
    extent: tuple[float, float, float, float] | None = None,
    force: bool = False,
    extra_meta: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Draw uv10 wind speed filled map and write metadata json."""
    u = np.asarray(u, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)
    if u.shape != v.shape or u.ndim != 2:
        raise ValueError(f"draw_wind_speed expects two 2D arrays with same shape, got {u.shape} vs {v.shape}")
    speed = np.sqrt(u * u + v * v)
    return draw_global_fill(
        speed,
        out_png,
        out_json=out_json,
        var="wind_speed",
        lead_hour=lead_hour,
        units="m s^-1",
        title=title or f"wind speed t+{lead_hour:03d}",
        dpi=dpi,
        style_profile=style_profile,
        with_geo=with_geo,
        geo_assets_dir=geo_assets_dir,
        extent=extent,
        force=force,
        extra_meta=extra_meta,
    )


def draw_msl_wind(
    msl: np.ndarray,
    u: np.ndarray,
    v: np.ndarray,
    out_png: str | Path,
    *,
    out_json: str | Path | None = None,
    lead_hour: int = 0,
    title: str = "",
    dpi: int = 220,
    style_profile: str = "standard",
    with_geo: bool = False,
    geo_assets_dir: str | None = None,
    extent: tuple[float, float, float, float] | None = None,
    stride: int = 18,
    force: bool = False,
    extra_meta: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Draw MSL + uv10 combined product and write metadata json."""
    import matplotlib.pyplot as plt

    out_png = str(out_png)
    out_json = str(out_json or out_png.replace(".png", ".json"))
    if Path(out_png).exists() and not force:
        return out_png, out_json

    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    msl = np.asarray(msl, dtype=np.float32)
    u = np.asarray(u, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)
    if msl.ndim != 2 or u.shape != v.shape or u.shape != msl.shape:
        raise ValueError(f"draw_msl_wind expects same-shape 2D arrays, got msl={msl.shape}, u={u.shape}, v={v.shape}")

    ccrs, cfeature = try_import_cartopy()
    assets_dir = resolve_geo_assets_dir(geo_assets_dir)
    resource_hint = detect_geo_resource(assets_dir)
    geo_requested = bool(with_geo)
    geo_ok = geo_requested and ccrs is not None
    geo_error = ""
    extent = _normalize_extent(extent)
    lat = np.linspace(90.0, -90.0, u.shape[0], dtype=np.float32)
    lon = np.linspace(0.0, 360.0, u.shape[1], endpoint=False, dtype=np.float32)
    lon2d, lat2d = np.meshgrid(lon, lat)

    vmin = float(np.nanpercentile(msl, 1))
    vmax = float(np.nanpercentile(msl, 99))

    if geo_ok:
        try:
            fig = plt.figure(figsize=(7.2, 3.8), dpi=dpi)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(extent, crs=ccrs.PlateCarree())
            ax.coastlines(linewidth=0.5)
            if cfeature is not None:
                ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.25)
            bg = ax.imshow(
                msl,
                extent=extent,
                origin="upper",
                cmap="coolwarm",
                vmin=vmin,
                vmax=vmax,
                transform=ccrs.PlateCarree(),
                alpha=0.88,
            )
            ax.quiver(
                lon2d[::stride, ::stride],
                lat2d[::stride, ::stride],
                u[::stride, ::stride],
                v[::stride, ::stride],
                transform=ccrs.PlateCarree(),
                color="black",
                linewidth=0.25,
                scale=250.0,
            )
        except Exception as exc:
            geo_ok = False
            geo_error = str(exc)
            fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=dpi)
            bg = ax.imshow(msl, extent=extent, origin="upper", cmap="coolwarm", vmin=vmin, vmax=vmax, alpha=0.88)
            ax.quiver(
                lon2d[::stride, ::stride],
                lat2d[::stride, ::stride],
                u[::stride, ::stride],
                v[::stride, ::stride],
                color="black",
                linewidth=0.25,
                scale=250.0,
            )
            ax.set_xlabel("lon")
            ax.set_ylabel("lat")
    else:
        fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=dpi)
        bg = ax.imshow(msl, extent=extent, origin="upper", cmap="coolwarm", vmin=vmin, vmax=vmax, alpha=0.88)
        ax.quiver(
            lon2d[::stride, ::stride],
            lat2d[::stride, ::stride],
            u[::stride, ::stride],
            v[::stride, ::stride],
            color="black",
            linewidth=0.25,
            scale=250.0,
        )
        ax.set_xlabel("lon")
        ax.set_ylabel("lat")

    t = title or f"msl+uv10 t+{lead_hour:03d}"
    ax.set_title(t)
    cb = fig.colorbar(bg, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label("Pa")
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

    meta = {
        "type": "msl_wind",
        "lead_hour": int(lead_hour),
        "title": t,
        "dpi": int(dpi),
        "stride": int(stride),
        "style_profile": style_profile,
        "msl_vmin": vmin,
        "msl_vmax": vmax,
        "with_geo_requested": geo_requested,
        "with_geo": bool(geo_ok),
        "geo_assets_dir": str(assets_dir) if assets_dir else "",
        "geo_resource_hint": resource_hint,
        "geo_error": geo_error,
        "extent": list(extent),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    if extra_meta:
        meta.update(extra_meta)

    with open(out_json, "w") as f:
        json.dump(meta, f, indent=2)
    return out_png, out_json
