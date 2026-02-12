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
from pangu_weather_repro.visualization.style import (
    get_diff_style,
    get_fill_style,
    get_style,
    get_vector_style,
)

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
    defaults = get_fill_style(var, style_profile)
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
    defaults = get_diff_style(var, style_profile)
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


def _convert_for_display(var: str, data: np.ndarray, style_profile: str) -> tuple[np.ndarray, str]:
    """Convert variable values only for display (no model math change)."""
    fill = get_fill_style(var, style_profile)
    unit_label = str(fill.get("unit_label", ""))
    if fill.get("convert_from_pa"):
        return np.asarray(data, dtype=np.float32) / 100.0, unit_label
    return np.asarray(data, dtype=np.float32), unit_label


def _series_stats(data: np.ndarray) -> dict[str, float]:
    arr = np.asarray(data, dtype=np.float32)
    return {
        "data_min": float(np.nanmin(arr)),
        "data_max": float(np.nanmax(arr)),
        "data_mean": float(np.nanmean(arr)),
        "data_std": float(np.nanstd(arr)),
    }


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
    raw_data = np.asarray(data)
    data, unit_from_style = _convert_for_display(var, raw_data, style_profile)
    if data.ndim != 2:
        raise ValueError(f"draw_global_fill expects 2D array, got {data.shape}")
    units_use = units or unit_from_style

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
    fig_style = get_style(style_profile).get("figure", {})
    figsize = tuple(fig_style.get("figsize_fill", (7.0, 3.6)))

    if geo_ok:
        try:
            fig = plt.figure(figsize=figsize, dpi=dpi)
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
            fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
            im = ax.imshow(data, extent=extent, origin="upper", cmap=cmap_use, vmin=vmin_use, vmax=vmax_use)
            ax.set_xlabel("lon")
            ax.set_ylabel("lat")
    else:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        im = ax.imshow(data, extent=extent, origin="upper", cmap=cmap_use, vmin=vmin_use, vmax=vmax_use)
        ax.set_xlabel("lon")
        ax.set_ylabel("lat")

    t = title or f"{var} t+{lead_hour:03d}"
    if units_use:
        t += f" ({units_use})"
    ax.set_title(t)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    if units_use:
        cb.set_label(units_use)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

    meta = {
        "type": "global_fill",
        "var": var,
        "lead_hour": int(lead_hour),
        "units": units_use,
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
    meta.update(_series_stats(data))
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
    pred_raw = np.asarray(pred, dtype=np.float32)
    ref_raw = np.asarray(ref, dtype=np.float32)
    pred_show, unit_from_style = _convert_for_display(var, pred_raw, style_profile)
    ref_show, _ = _convert_for_display(var, ref_raw, style_profile)
    if pred.shape != ref.shape or pred.ndim != 2:
        raise ValueError(f"draw_diff_fill expects two 2D arrays with same shape, got {pred.shape} vs {ref.shape}")

    diff = pred_show - ref_show
    cmap_use, vmin, vmax, range_source = _resolve_diff_style(
        var,
        style_profile=style_profile,
        cmap=cmap,
        vlim=vlim,
        diff=diff,
    )

    extent = _normalize_extent(extent)
    fig_style = get_style(style_profile).get("figure", {})
    figsize = tuple(fig_style.get("figsize_fill", (7.0, 3.6)))
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    im = ax.imshow(diff, extent=extent, origin="upper", cmap=cmap_use, vmin=vmin, vmax=vmax)
    ax.set_xlabel("lon")
    ax.set_ylabel("lat")
    t = title or f"{var} pred-ref t+{lead_hour:03d}"
    units_use = units or unit_from_style
    if units_use:
        t += f" ({units_use})"
    ax.set_title(t)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    if units_use:
        cb.set_label(units_use)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

    meta = {
        "type": "diff_fill",
        "var": var,
        "lead_hour": int(lead_hour),
        "units": units_use,
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
    meta.update(_series_stats(diff))
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
    vec_style = get_vector_style(style_profile)

    lat = np.linspace(90.0, -90.0, u.shape[0], dtype=np.float32)
    lon = np.linspace(0.0, 360.0, u.shape[1], endpoint=False, dtype=np.float32)
    lon2d, lat2d = np.meshgrid(lon, lat)

    if geo_ok:
        try:
            fig_style = get_style(style_profile).get("figure", {})
            figsize = tuple(fig_style.get("figsize_vector", (7.2, 3.8)))
            fig = plt.figure(figsize=figsize, dpi=dpi)
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
                color=str(vec_style.get("color", "black")),
                linewidth=float(vec_style.get("width", 0.0018)),
                scale=float(vec_style.get("scale", 250.0)),
                headwidth=float(vec_style.get("headwidth", 3.5)),
                headlength=float(vec_style.get("headlength", 4.0)),
            )
        except Exception as exc:
            geo_ok = False
            geo_error = str(exc)
            fig_style = get_style(style_profile).get("figure", {})
            figsize = tuple(fig_style.get("figsize_vector", (7.2, 3.8)))
            fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
            bg = ax.imshow(speed, extent=extent, origin="upper", cmap="viridis", alpha=0.82)
            ax.quiver(
                lon2d[::stride, ::stride],
                lat2d[::stride, ::stride],
                u[::stride, ::stride],
                v[::stride, ::stride],
                color=str(vec_style.get("color", "black")),
                linewidth=float(vec_style.get("width", 0.0018)),
                scale=float(vec_style.get("scale", 250.0)),
                headwidth=float(vec_style.get("headwidth", 3.5)),
                headlength=float(vec_style.get("headlength", 4.0)),
            )
            ax.set_xlabel("lon")
            ax.set_ylabel("lat")
    else:
        fig_style = get_style(style_profile).get("figure", {})
        figsize = tuple(fig_style.get("figsize_vector", (7.2, 3.8)))
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        bg = ax.imshow(speed, extent=extent, origin="upper", cmap="viridis", alpha=0.82)
        ax.quiver(
            lon2d[::stride, ::stride],
            lat2d[::stride, ::stride],
            u[::stride, ::stride],
            v[::stride, ::stride],
            color=str(vec_style.get("color", "black")),
            linewidth=float(vec_style.get("width", 0.0018)),
            scale=float(vec_style.get("scale", 250.0)),
            headwidth=float(vec_style.get("headwidth", 3.5)),
            headlength=float(vec_style.get("headlength", 4.0)),
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
    meta.update(_series_stats(speed))
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
    msl_raw = np.asarray(msl, dtype=np.float32)
    u = np.asarray(u, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)
    if msl_raw.ndim != 2 or u.shape != v.shape or u.shape != msl_raw.shape:
        raise ValueError(f"draw_msl_wind expects same-shape 2D arrays, got msl={msl_raw.shape}, u={u.shape}, v={v.shape}")

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

    msl_show, unit_from_style = _convert_for_display("msl", msl_raw, style_profile)
    fill_cfg = get_fill_style("msl", style_profile)
    vmin = float(fill_cfg.get("vmin", np.nanpercentile(msl_show, 1)))
    vmax = float(fill_cfg.get("vmax", np.nanpercentile(msl_show, 99)))
    contour_cfg = get_style(style_profile).get("contour", {}).get("msl_wind", {})
    vec_style = get_vector_style(style_profile)
    fig_style = get_style(style_profile).get("figure", {})
    figsize = tuple(fig_style.get("figsize_vector", (7.2, 3.8)))

    if geo_ok:
        try:
            fig = plt.figure(figsize=figsize, dpi=dpi)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(extent, crs=ccrs.PlateCarree())
            ax.coastlines(linewidth=0.5)
            if cfeature is not None:
                ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.25)
            bg = ax.imshow(
                msl_show,
                extent=extent,
                origin="upper",
                cmap=str(fill_cfg.get("cmap", "coolwarm")),
                vmin=vmin,
                vmax=vmax,
                transform=ccrs.PlateCarree(),
                alpha=0.88,
            )
            if contour_cfg.get("enabled", True):
                cs = ax.contour(
                    lon2d,
                    lat2d,
                    msl_show,
                    levels=contour_cfg.get("levels", [960, 980, 1000, 1020, 1040]),
                    colors=str(contour_cfg.get("color", "k")),
                    linewidths=float(contour_cfg.get("linewidth", 0.6)),
                    transform=ccrs.PlateCarree(),
                )
                ax.clabel(cs, inline=True, fontsize=int(contour_cfg.get("label_fontsize", 7)), fmt="%d")
            ax.quiver(
                lon2d[::stride, ::stride],
                lat2d[::stride, ::stride],
                u[::stride, ::stride],
                v[::stride, ::stride],
                transform=ccrs.PlateCarree(),
                color=str(vec_style.get("color", "black")),
                linewidth=float(vec_style.get("width", 0.0018)),
                scale=float(vec_style.get("scale", 250.0)),
                headwidth=float(vec_style.get("headwidth", 3.5)),
                headlength=float(vec_style.get("headlength", 4.0)),
            )
        except Exception as exc:
            geo_ok = False
            geo_error = str(exc)
            fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
            bg = ax.imshow(msl_show, extent=extent, origin="upper", cmap=str(fill_cfg.get("cmap", "coolwarm")), vmin=vmin, vmax=vmax, alpha=0.88)
            if contour_cfg.get("enabled", True):
                cs = ax.contour(
                    lon2d,
                    lat2d,
                    msl_show,
                    levels=contour_cfg.get("levels", [960, 980, 1000, 1020, 1040]),
                    colors=str(contour_cfg.get("color", "k")),
                    linewidths=float(contour_cfg.get("linewidth", 0.6)),
                )
                ax.clabel(cs, inline=True, fontsize=int(contour_cfg.get("label_fontsize", 7)), fmt="%d")
            ax.quiver(
                lon2d[::stride, ::stride],
                lat2d[::stride, ::stride],
                u[::stride, ::stride],
                v[::stride, ::stride],
                color=str(vec_style.get("color", "black")),
                linewidth=float(vec_style.get("width", 0.0018)),
                scale=float(vec_style.get("scale", 250.0)),
                headwidth=float(vec_style.get("headwidth", 3.5)),
                headlength=float(vec_style.get("headlength", 4.0)),
            )
            ax.set_xlabel("lon")
            ax.set_ylabel("lat")
    else:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        bg = ax.imshow(msl_show, extent=extent, origin="upper", cmap=str(fill_cfg.get("cmap", "coolwarm")), vmin=vmin, vmax=vmax, alpha=0.88)
        if contour_cfg.get("enabled", True):
            cs = ax.contour(
                lon2d,
                lat2d,
                msl_show,
                levels=contour_cfg.get("levels", [960, 980, 1000, 1020, 1040]),
                colors=str(contour_cfg.get("color", "k")),
                linewidths=float(contour_cfg.get("linewidth", 0.6)),
            )
            ax.clabel(cs, inline=True, fontsize=int(contour_cfg.get("label_fontsize", 7)), fmt="%d")
        ax.quiver(
            lon2d[::stride, ::stride],
            lat2d[::stride, ::stride],
            u[::stride, ::stride],
            v[::stride, ::stride],
            color=str(vec_style.get("color", "black")),
            linewidth=float(vec_style.get("width", 0.0018)),
            scale=float(vec_style.get("scale", 250.0)),
            headwidth=float(vec_style.get("headwidth", 3.5)),
            headlength=float(vec_style.get("headlength", 4.0)),
        )
        ax.set_xlabel("lon")
        ax.set_ylabel("lat")

    t = title or f"msl+uv10 t+{lead_hour:03d}"
    ax.set_title(t)
    cb = fig.colorbar(bg, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label(unit_from_style or "hPa")
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
        "msl_unit": unit_from_style or "hPa",
        "with_geo_requested": geo_requested,
        "with_geo": bool(geo_ok),
        "geo_assets_dir": str(assets_dir) if assets_dir else "",
        "geo_resource_hint": resource_hint,
        "geo_error": geo_error,
        "extent": list(extent),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
    meta.update(_series_stats(msl_show))
    if extra_meta:
        meta.update(extra_meta)

    with open(out_json, "w") as f:
        json.dump(meta, f, indent=2)
    return out_png, out_json
