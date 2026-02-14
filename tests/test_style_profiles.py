"""Style profile 配置验证测试。

验证 standard 配置未被修改、blueprint 配置正确、未知 profile 回退等。
"""
from __future__ import annotations

from pangu_weather_repro.visualization.style import (
    get_colorbar_style,
    get_fill_style,
    get_map_style,
    get_style,
    get_vector_style,
)


def test_standard_profile_unchanged():
    """standard 配置核心参数不变，确保向后兼容。"""
    s = get_style("standard")
    fig = s["figure"]
    assert fig["dpi"] == 220
    assert fig["figsize_fill"] == (7.2, 3.8)
    assert fig["figsize_vector"] == (7.2, 3.8)

    t2m = s["fill_defaults"]["t2m"]
    assert t2m["cmap"] == "coolwarm"
    assert t2m["vmin"] == 220.0
    assert t2m["vmax"] == 320.0
    assert t2m["unit_label"] == "K"

    vec = s["vector"]
    assert vec["stride_global"] == 10
    assert vec["scale"] == 650.0

    # standard 不含 map/colorbar/font 配置
    assert "map" not in s
    assert "colorbar" not in s
    assert "font" not in s


def test_blueprint_profile_exists():
    """blueprint 配置存在且包含蓝本关键参数。"""
    s = get_style("blueprint")
    assert s is not None

    fig = s["figure"]
    assert fig["figsize_fill"] == (12, 10)
    assert fig["figsize_vector"] == (12, 10)

    vec = s["vector"]
    assert vec["scale"] == 700.0
    assert vec["stride_global"] == 30
    assert vec["stride_regional"] == 30


def test_blueprint_t2m_celsius():
    """blueprint t2m 使用摄氏度（K->°C 转换）。"""
    t2m = get_fill_style("t2m", "blueprint")
    assert t2m.get("convert_from_kelvin") is True
    assert t2m["vmin"] == 5.0
    assert t2m["vmax"] == 45.0
    assert "°C" in t2m["unit_label"] or "\u00b0C" in t2m["unit_label"]


def test_blueprint_map_gridlines():
    """blueprint 地图配置包含网格线和中国 SHP 支持。"""
    m = get_map_style("blueprint")
    assert m["coastline_linewidth"] == 1.5
    assert m["use_china_shapefile"] is True

    grid = m["gridlines"]
    assert grid["enabled"] is True
    assert grid["linestyle"] == ":"
    assert grid["color"] == "gray"


def test_blueprint_colorbar_inset():
    """blueprint 使用内嵌色条样式。"""
    cb = get_colorbar_style("blueprint")
    assert cb["style"] == "inset"
    assert cb["inset_loc"] == "lower right"


def test_blueprint_extent_default():
    """blueprint 默认使用中国区域范围。"""
    s = get_style("blueprint")
    extent = s.get("extent_default")
    assert extent is not None
    assert extent == (95, 145, 10, 50)


def test_unknown_profile_fallback():
    """未知 profile 回退到 standard 配置。"""
    unknown = get_style("nonexistent_profile")
    standard = get_style("standard")
    assert unknown is standard


def test_standard_map_style_empty():
    """standard 的 map 样式返回空字典，不改变原有行为。"""
    m = get_map_style("standard")
    assert m == {}


def test_standard_colorbar_style_empty():
    """standard 的 colorbar 样式返回空字典，使用默认 matplotlib colorbar。"""
    cb = get_colorbar_style("standard")
    assert cb == {}


def test_standard_vector_params():
    """standard 矢量参数完整性检查。"""
    v = get_vector_style("standard")
    assert v["stride_global"] == 10
    assert v["stride_regional"] == 12
    assert v["scale"] == 650.0
    assert v["width"] == 0.0012
    assert v["alpha"] == 0.78
    assert v["pivot"] == "middle"
