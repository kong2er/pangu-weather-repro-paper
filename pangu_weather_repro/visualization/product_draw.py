"""Product-style drawing primitives (E2 incremental alignment).

Current scope:
- draw_global_fill: global contour-like filled map with metadata sidecar.
- draw_diff_fill: pred-ref difference map.
- draw_wind_vector: near-surface wind vector (u/v) map.
- draw_msl_wind: msl filled map with uv10 vectors.
"""
from __future__ import annotations

import json
import logging
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
    get_colorbar_style,
    get_diff_style,
    get_fill_style,
    get_font_style,
    get_map_style,
    get_style,
    get_vector_style,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 经纬度网格缓存 — 避免 meshgrid 重复计算（同一 shape 只算一次）
# ---------------------------------------------------------------------------
_GRID_CACHE: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}


def _get_latlon_grid(nlat: int, nlon: int) -> tuple[np.ndarray, np.ndarray]:
    """返回 (lon2d, lat2d) 网格，结果会被缓存以避免重复计算。"""
    key = (nlat, nlon)
    if key not in _GRID_CACHE:
        lat = np.linspace(90.0, -90.0, nlat, dtype=np.float32)
        lon = np.linspace(0.0, 360.0, nlon, endpoint=False, dtype=np.float32)
        _GRID_CACHE[key] = np.meshgrid(lon, lat)
    return _GRID_CACHE[key]


# ---------------------------------------------------------------------------
# 中国 SHP 文件路径（蓝本使用的省界/国界 shapefile）
# ---------------------------------------------------------------------------
_CHINA_SHP_PATH = Path(__file__).resolve().parents[2] / "vendor" / "blueprint" / "pangu" / "visualization" / "Country" / "中华人民共和国.shp"


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


def _is_global_extent(extent: tuple[float, float, float, float]) -> bool:
    lon_min, lon_max, lat_min, lat_max = extent
    return abs(lon_min - 0.0) < 1e-6 and abs(lon_max - 360.0) < 1e-6 and abs(lat_min + 90.0) < 1e-6 and abs(lat_max - 90.0) < 1e-6


def _resolve_vector_stride(
    extent: tuple[float, float, float, float],
    stride: int | None,
    vec_style: dict[str, Any],
) -> int:
    if stride is not None and int(stride) > 0:
        return int(stride)
    if _is_global_extent(extent):
        return int(vec_style.get("stride_global", 10))
    return int(vec_style.get("stride_regional", 12))


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
    """转换变量值用于显示（不影响模型计算）。"""
    fill = get_fill_style(var, style_profile)
    unit_label = str(fill.get("unit_label", ""))
    arr = np.asarray(data, dtype=np.float32)
    # Pa -> hPa 转换
    if fill.get("convert_from_pa"):
        arr = arr / 100.0
    # K -> °C 转换（蓝本 t2m 使用摄氏度）
    if fill.get("convert_from_kelvin"):
        arr = arr - 273.15
    return arr, unit_label


def _series_stats(data: np.ndarray) -> dict[str, float]:
    arr = np.asarray(data, dtype=np.float32)
    return {
        "data_min": float(np.nanmin(arr)),
        "data_max": float(np.nanmax(arr)),
        "data_mean": float(np.nanmean(arr)),
        "data_std": float(np.nanstd(arr)),
    }


# ---------------------------------------------------------------------------
# 蓝本对齐辅助函数：地图样式、色条、标题、字体
# ---------------------------------------------------------------------------

def _apply_font_style(style_profile: str) -> None:
    """根据配置设置 matplotlib 字体（通过 rcParams）。"""
    font_cfg = get_font_style(style_profile)
    if not font_cfg:
        return
    import matplotlib as mpl
    family = font_cfg.get("family")
    if family:
        mpl.rcParams["font.family"] = family if isinstance(family, list) else [family]


def _apply_map_features(ax: Any, style_profile: str, ccrs: Any, cfeature: Any) -> None:
    """在 GeoAxes 上应用海岸线、边界、网格线等地图要素。

    standard 配置沿用原有行为（coastlines lw=0.5 + BORDERS 110m）。
    blueprint 配置使用中国 SHP 边界 + 可配置网格线。
    """
    map_style = get_map_style(style_profile)
    coastline_lw = float(map_style.get("coastline_linewidth", 0.5))

    # --- 中国 SHP 边界支持 ---
    if map_style.get("use_china_shapefile") and _CHINA_SHP_PATH.exists():
        try:
            import cartopy.io.shapereader as shpreader
            from cartopy.feature import ShapelyFeature
            reader = shpreader.Reader(str(_CHINA_SHP_PATH))
            china_feature = ShapelyFeature(
                reader.geometries(),
                ccrs.PlateCarree(),
                facecolor="none",
                edgecolor=str(map_style.get("coastline_edgecolor", "0.5")),
                linewidth=coastline_lw,
                zorder=100,
            )
            ax.add_feature(china_feature)
        except Exception as exc:
            logger.warning("加载中国 SHP 文件失败，回退到默认海岸线: %s", exc)
            ax.coastlines(linewidth=coastline_lw)
            if cfeature is not None:
                ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.25)
    else:
        # standard 配置：使用默认海岸线
        ax.coastlines(linewidth=coastline_lw)
        if cfeature is not None:
            ax.add_feature(cfeature.BORDERS.with_scale("110m"), linewidth=0.25)

    # --- 网格线配置 ---
    grid_cfg = map_style.get("gridlines", {})
    if grid_cfg.get("enabled", False):
        gl = ax.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=grid_cfg.get("draw_labels", True),
            linestyle=str(grid_cfg.get("linestyle", ":")),
            color=str(grid_cfg.get("color", "gray")),
            alpha=float(grid_cfg.get("alpha", 1.0)),
            linewidth=float(grid_cfg.get("linewidth", 1)),
        )
        gl.top_labels = grid_cfg.get("top_labels", False)
        gl.right_labels = grid_cfg.get("right_labels", False)


def _add_colorbar(fig: Any, ax: Any, im: Any, units_use: str, style_profile: str) -> Any:
    """添加色条 — 根据配置使用标准或内嵌样式。

    standard 配置：fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)（与原实现一致）。
    blueprint 配置：使用 inset_axes 内嵌色条（右下角，带白色背景框）。
    """
    cb_style = get_colorbar_style(style_profile)

    if cb_style.get("style") == "inset":
        try:
            from mpl_toolkits.axes_grid1.inset_locator import inset_axes
            # 内嵌色条：在图右下角创建一个小的轴
            cax = inset_axes(
                ax,
                width=str(cb_style.get("inset_width", "5%")),
                height=str(cb_style.get("inset_height", "33%")),
                loc=str(cb_style.get("inset_loc", "lower right")),
                borderpad=2,
            )
            # 添加白色半透明背景
            bg_alpha = float(cb_style.get("background_alpha", 0.95))
            cax.patch.set_facecolor("white")
            cax.patch.set_alpha(bg_alpha)
            cb = fig.colorbar(im, cax=cax)
            cb.ax.tick_params(
                direction=str(cb_style.get("tick_direction", "in")),
                length=float(cb_style.get("tick_length", 2)),
                labelsize=int(cb_style.get("tick_labelsize", 10)),
            )
            if units_use:
                cb.set_label(units_use)
            return cb
        except Exception as exc:
            logger.warning("内嵌色条创建失败，回退到标准色条: %s", exc)

    # 标准色条（默认）
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    if units_use:
        cb.set_label(units_use)
    return cb


def _set_title(ax: Any, title: str, style_profile: str) -> None:
    """设置图标题 — blueprint 使用左对齐标题，standard 居中。"""
    font_cfg = get_font_style(style_profile)
    fontsize = font_cfg.get("title_fontsize")

    if style_profile == "blueprint":
        # 蓝本使用左对齐标题
        kwargs: dict[str, Any] = {"loc": "left"}
        if fontsize:
            kwargs["fontsize"] = fontsize
        ax.set_title(title, **kwargs)
    else:
        ax.set_title(title)


def _resolve_extent_with_default(
    extent: tuple[float, float, float, float] | None,
    style_profile: str,
) -> tuple[float, float, float, float]:
    """解析 extent 参数，blueprint 配置默认使用中国区域范围。"""
    if extent is not None:
        return _normalize_extent(extent)
    # 如果是 blueprint 配置且未指定 extent，使用默认中国区域
    style = get_style(style_profile)
    default_extent = style.get("extent_default")
    if default_extent is not None:
        return tuple(float(x) for x in default_extent)
    return _normalize_extent(None)


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
    # 应用字体配置
    _apply_font_style(style_profile)
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
    # 解析 extent（blueprint 默认使用中国区域）
    extent = _resolve_extent_with_default(extent, style_profile)
    fig_style = get_style(style_profile).get("figure", {})
    figsize = tuple(fig_style.get("figsize_fill", (7.0, 3.6)))

    if geo_ok:
        try:
            fig = plt.figure(figsize=figsize, dpi=dpi)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(extent, crs=ccrs.PlateCarree())
            # 应用地图要素（海岸线、边界、网格线）
            _apply_map_features(ax, style_profile, ccrs, cfeature)
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
    _set_title(ax, t, style_profile)
    _add_colorbar(fig, ax, im, units_use, style_profile)
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
    _apply_font_style(style_profile)
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

    extent = _resolve_extent_with_default(extent, style_profile)
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
    _set_title(ax, t, style_profile)
    _add_colorbar(fig, ax, im, units_use, style_profile)
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
    stride: int | None = None,
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
    _apply_font_style(style_profile)
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
    extent = _resolve_extent_with_default(extent, style_profile)
    speed = np.sqrt(u * u + v * v)
    vec_style = get_vector_style(style_profile)
    stride_use = _resolve_vector_stride(extent, stride, vec_style)
    quiver_kwargs = {
        "color": str(vec_style.get("color", "black")),
        "linewidth": float(vec_style.get("width", 0.0012)),
        "scale": float(vec_style.get("scale", 650.0)),
        "headwidth": float(vec_style.get("headwidth", 3.0)),
        "headlength": float(vec_style.get("headlength", 3.8)),
        "headaxislength": float(vec_style.get("headaxislength", 3.5)),
        "alpha": float(vec_style.get("alpha", 0.78)),
        "pivot": str(vec_style.get("pivot", "middle")),
    }

    # 使用缓存的经纬度网格
    lon2d, lat2d = _get_latlon_grid(u.shape[0], u.shape[1])

    if geo_ok:
        try:
            fig_style = get_style(style_profile).get("figure", {})
            figsize = tuple(fig_style.get("figsize_vector", (7.2, 3.8)))
            fig = plt.figure(figsize=figsize, dpi=dpi)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(extent, crs=ccrs.PlateCarree())
            # 应用地图要素
            _apply_map_features(ax, style_profile, ccrs, cfeature)
            bg = ax.imshow(
                speed,
                extent=extent,
                origin="upper",
                cmap="viridis",
                transform=ccrs.PlateCarree(),
                alpha=0.82,
            )
            q = ax.quiver(
                lon2d[::stride_use, ::stride_use],
                lat2d[::stride_use, ::stride_use],
                u[::stride_use, ::stride_use],
                v[::stride_use, ::stride_use],
                transform=ccrs.PlateCarree(),
                **quiver_kwargs,
            )
        except Exception as exc:
            geo_ok = False
            geo_error = str(exc)
            fig_style = get_style(style_profile).get("figure", {})
            figsize = tuple(fig_style.get("figsize_vector", (7.2, 3.8)))
            fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
            bg = ax.imshow(speed, extent=extent, origin="upper", cmap="viridis", alpha=0.82)
            q = ax.quiver(
                lon2d[::stride_use, ::stride_use],
                lat2d[::stride_use, ::stride_use],
                u[::stride_use, ::stride_use],
                v[::stride_use, ::stride_use],
                **quiver_kwargs,
            )
            ax.set_xlabel("lon")
            ax.set_ylabel("lat")
    else:
        fig_style = get_style(style_profile).get("figure", {})
        figsize = tuple(fig_style.get("figsize_vector", (7.2, 3.8)))
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        bg = ax.imshow(speed, extent=extent, origin="upper", cmap="viridis", alpha=0.82)
        q = ax.quiver(
            lon2d[::stride_use, ::stride_use],
            lat2d[::stride_use, ::stride_use],
            u[::stride_use, ::stride_use],
            v[::stride_use, ::stride_use],
            **quiver_kwargs,
        )
        ax.set_xlabel("lon")
        ax.set_ylabel("lat")

    t = title or f"uv10 vector t+{lead_hour:03d}"
    _set_title(ax, t, style_profile)
    _add_colorbar(fig, ax, bg, "m s^-1", style_profile)
    # Keep one stable legend arrow for readability across leads.
    ax.quiverkey(
        q,
        X=float(vec_style.get("key_pos_x", 0.86)),
        Y=float(vec_style.get("key_pos_y", 1.03)),
        U=float(vec_style.get("key_speed", 10.0)),
        label=str(vec_style.get("key_label", "10 m s^-1")),
        labelpos="E",
        coordinates="axes",
    )
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

    meta = {
        "type": "wind_vector",
        "lead_hour": int(lead_hour),
        "title": t,
        "dpi": int(dpi),
        "stride": int(stride_use),
        "vector_scale": float(quiver_kwargs["scale"]),
        "vector_width": float(quiver_kwargs["linewidth"]),
        "vector_alpha": float(quiver_kwargs["alpha"]),
        "vector_pivot": str(quiver_kwargs["pivot"]),
        "vector_key_speed": float(vec_style.get("key_speed", 10.0)),
        "vector_key_label": str(vec_style.get("key_label", "10 m s^-1")),
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
    stride: int | None = None,
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
    _apply_font_style(style_profile)
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
    extent = _resolve_extent_with_default(extent, style_profile)

    # 使用缓存的经纬度网格
    lon2d, lat2d = _get_latlon_grid(u.shape[0], u.shape[1])

    msl_show, unit_from_style = _convert_for_display("msl", msl_raw, style_profile)
    fill_cfg = get_fill_style("msl", style_profile)
    vmin = float(fill_cfg.get("vmin", np.nanpercentile(msl_show, 1)))
    vmax = float(fill_cfg.get("vmax", np.nanpercentile(msl_show, 99)))
    contour_cfg = get_style(style_profile).get("contour", {}).get("msl_wind", {})
    vec_style = get_vector_style(style_profile)
    stride_use = _resolve_vector_stride(extent, stride, vec_style)
    quiver_kwargs = {
        "color": str(vec_style.get("color", "black")),
        "linewidth": float(vec_style.get("width", 0.0012)),
        "scale": float(vec_style.get("scale", 650.0)),
        "headwidth": float(vec_style.get("headwidth", 3.0)),
        "headlength": float(vec_style.get("headlength", 3.8)),
        "headaxislength": float(vec_style.get("headaxislength", 3.5)),
        "alpha": float(vec_style.get("alpha", 0.78)),
        "pivot": str(vec_style.get("pivot", "middle")),
    }
    fig_style = get_style(style_profile).get("figure", {})
    figsize = tuple(fig_style.get("figsize_vector", (7.2, 3.8)))

    if geo_ok:
        try:
            fig = plt.figure(figsize=figsize, dpi=dpi)
            ax = plt.axes(projection=ccrs.PlateCarree())
            ax.set_extent(extent, crs=ccrs.PlateCarree())
            # 应用地图要素
            _apply_map_features(ax, style_profile, ccrs, cfeature)
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
            q = ax.quiver(
                lon2d[::stride_use, ::stride_use],
                lat2d[::stride_use, ::stride_use],
                u[::stride_use, ::stride_use],
                v[::stride_use, ::stride_use],
                transform=ccrs.PlateCarree(),
                **quiver_kwargs,
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
            q = ax.quiver(
                lon2d[::stride_use, ::stride_use],
                lat2d[::stride_use, ::stride_use],
                u[::stride_use, ::stride_use],
                v[::stride_use, ::stride_use],
                **quiver_kwargs,
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
        q = ax.quiver(
            lon2d[::stride_use, ::stride_use],
            lat2d[::stride_use, ::stride_use],
            u[::stride_use, ::stride_use],
            v[::stride_use, ::stride_use],
            **quiver_kwargs,
        )
        ax.set_xlabel("lon")
        ax.set_ylabel("lat")

    t = title or f"msl+uv10 t+{lead_hour:03d}"
    _set_title(ax, t, style_profile)
    _add_colorbar(fig, ax, bg, unit_from_style or "hPa", style_profile)
    ax.quiverkey(
        q,
        X=float(vec_style.get("key_pos_x", 0.86)),
        Y=float(vec_style.get("key_pos_y", 1.03)),
        U=float(vec_style.get("key_speed", 10.0)),
        label=str(vec_style.get("key_label", "10 m s^-1")),
        labelpos="E",
        coordinates="axes",
    )
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

    meta = {
        "type": "msl_wind",
        "lead_hour": int(lead_hour),
        "title": t,
        "dpi": int(dpi),
        "stride": int(stride_use),
        "vector_scale": float(quiver_kwargs["scale"]),
        "vector_width": float(quiver_kwargs["linewidth"]),
        "vector_alpha": float(quiver_kwargs["alpha"]),
        "vector_pivot": str(quiver_kwargs["pivot"]),
        "vector_key_speed": float(vec_style.get("key_speed", 10.0)),
        "vector_key_label": str(vec_style.get("key_label", "10 m s^-1")),
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
