"""Centralized plot style presets for product/paper rendering.

This module keeps visual defaults in one place so product/paper outputs stay
consistent and easier to align with the reference repository style.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 延迟注册蓝本配色方案 BlAqGrYeOrReVi200
# 尝试从 cmaps 包导入；若缺失则回退到 matplotlib 内置 turbo 并记录警告。
# ---------------------------------------------------------------------------
_BLUEPRINT_CMAP_REGISTERED = False


def _ensure_blueprint_cmap() -> str:
    """注册 BlAqGrYeOrReVi200 色表并返回可用的 colormap 名称。"""
    global _BLUEPRINT_CMAP_REGISTERED
    if _BLUEPRINT_CMAP_REGISTERED:
        return "BlAqGrYeOrReVi200"
    try:
        import cmaps  # noqa: F401 — 导入即注册
        import matplotlib.pyplot as plt
        # 验证 colormap 已注册
        plt.colormaps.get_cmap("BlAqGrYeOrReVi200")
        _BLUEPRINT_CMAP_REGISTERED = True
        return "BlAqGrYeOrReVi200"
    except Exception:
        logger.warning(
            "cmaps 包未安装或 BlAqGrYeOrReVi200 色表不可用，回退到 turbo。"
            "如需蓝本精确配色，请安装: pip install cmaps"
        )
        return "turbo"


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
            # Default target: clean and readable vector field on 721x1440 grids.
            "stride_global": 10,
            "stride_regional": 12,
            "scale": 650.0,
            "width": 0.0012,
            "headwidth": 3.0,
            "headlength": 3.8,
            "headaxislength": 3.5,
            "alpha": 0.78,
            "pivot": "middle",
            "color": "black",
            "key_speed": 10.0,
            "key_label": "10 m s^-1",
            "key_pos_x": 0.86,
            "key_pos_y": 1.03,
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
    },
    # ------------------------------------------------------------------
    # 蓝本 (blueprint) 配置 — 与 ~/projects/pangu/ 参考仓库对齐
    # 图幅、配色、矢量间距、地图样式、colorbar 等均匹配蓝本实现。
    # ------------------------------------------------------------------
    "blueprint": {
        "figure": {"dpi": 220, "figsize_fill": (12, 10), "figsize_vector": (12, 10)},
        "fill_defaults": {
            "t2m": {
                # 蓝本使用 BlAqGrYeOrReVi200 色表（需 cmaps 包），
                # 运行时通过 _ensure_blueprint_cmap() 延迟注册
                "cmap": "BlAqGrYeOrReVi200",
                "vmin": 5.0,
                "vmax": 45.0,
                "levels_step": 0.5,
                "unit_label": "\u00b0C",
                "convert_from_kelvin": True,  # 模型输出 K -> 显示 °C
            },
            "z500": {
                "cmap": "turbo",
                "vmin": 47000.0,
                "vmax": 59000.0,
                "levels": [47000, 49000, 51000, 53000, 55000, 57000, 59000],
                "unit_label": "m\u00b2 s\u207b\u00b2",
            },
            "msl": {
                "cmap": "coolwarm",
                "vmin": 950.0,
                "vmax": 1050.0,
                "levels": [950, 970, 990, 1010, 1030, 1050],
                "unit_label": "hPa",
                "convert_from_pa": True,
            },
            "u10": {"cmap": "PuOr_r", "vmin": -30.0, "vmax": 30.0, "unit_label": "m s\u207b\u00b9"},
            "v10": {"cmap": "PuOr_r", "vmin": -30.0, "vmax": 30.0, "unit_label": "m s\u207b\u00b9"},
            "wind_speed": {
                "cmap": "viridis",
                "vmin": 0.0,
                "vmax": 35.0,
                "levels": [0, 5, 10, 15, 20, 25, 30, 35],
                "unit_label": "m s\u207b\u00b9",
            },
        },
        "diff_defaults": {
            "z500": {"cmap": "RdBu_r", "vlim": 300.0},
            "msl": {"cmap": "RdBu_r", "vlim": 15.0},
        },
        "vector": {
            # 蓝本矢量参数：步长 30、缩放 700
            "stride_global": 30,
            "stride_regional": 30,
            "scale": 700.0,
            "width": 0.0012,
            "headwidth": 3.0,
            "headlength": 3.8,
            "headaxislength": 3.5,
            "alpha": 0.78,
            "pivot": "middle",
            "color": "black",
            "key_speed": 10.0,
            "key_label": "10 m s\u207b\u00b9",
            "key_pos_x": 0.86,
            "key_pos_y": 1.03,
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
        # 地图样式：中国 SHP 边界、网格线
        "map": {
            "coastline_linewidth": 1.5,
            "coastline_edgecolor": "0.5",
            "use_china_shapefile": True,
            "gridlines": {
                "enabled": True,
                "linestyle": ":",
                "color": "gray",
                "alpha": 1.0,
                "linewidth": 1,
                "draw_labels": True,
                "top_labels": False,
                "right_labels": False,
            },
        },
        # 色条样式：内嵌（右下角）
        "colorbar": {
            "style": "inset",
            "inset_width": "5%",
            "inset_height": "33%",
            "inset_loc": "lower right",
            "background_alpha": 0.95,
            "tick_direction": "in",
            "tick_length": 2,
            "tick_labelsize": 10,
        },
        # 字体配置（通过 rcParams 设置，无需本地字体文件）
        "font": {
            "family": ["Arial", "DejaVu Sans", "sans-serif"],
            "title_fontsize": 12,
            "label_fontsize": 14,
        },
        # 默认区域范围（中国区域）
        "extent_default": (95, 145, 10, 50),
    },
}


def get_style(profile: str = "standard") -> dict[str, Any]:
    """获取指定风格配置，未知 profile 回退到 standard。"""
    return STYLE_PRESETS.get(profile, STYLE_PRESETS["standard"])


def get_fill_style(var: str, profile: str = "standard") -> dict[str, Any]:
    """获取填色图变量的默认配色参数。"""
    style = get_style(profile).get("fill_defaults", {}).get(var, {})
    # 蓝本 t2m 使用延迟注册的 colormap
    if profile == "blueprint" and var == "t2m" and style.get("cmap") == "BlAqGrYeOrReVi200":
        resolved_cmap = _ensure_blueprint_cmap()
        style = {**style, "cmap": resolved_cmap}
    return style


def get_diff_style(var: str, profile: str = "standard") -> dict[str, Any]:
    """获取差值图变量的默认配色参数。"""
    return get_style(profile).get("diff_defaults", {}).get(var, {})


def get_vector_style(profile: str = "standard") -> dict[str, Any]:
    """获取矢量图默认参数。"""
    return get_style(profile).get("vector", {})


def get_map_style(profile: str = "standard") -> dict[str, Any]:
    """获取地图样式配置（海岸线、网格线、SHP 等）。

    standard 配置返回空字典（保持原有行为不变）。
    """
    return get_style(profile).get("map", {})


def get_colorbar_style(profile: str = "standard") -> dict[str, Any]:
    """获取色条样式配置。

    standard 配置返回空字典（使用默认 matplotlib colorbar）。
    """
    return get_style(profile).get("colorbar", {})


def get_font_style(profile: str = "standard") -> dict[str, Any]:
    """获取字体配置。"""
    return get_style(profile).get("font", {})
