"""Geographic helpers for product plots.

中文说明：
- 该模块负责处理 cartopy 可用性与地理资源目录探测。
- 若依赖或资源缺失，应回退到普通 imshow 绘图，避免流程中断。
"""
from __future__ import annotations

from pathlib import Path


def try_import_cartopy():
    """Return (ccrs, cfeature) or (None, None) when unavailable."""
    try:
        import cartopy.crs as ccrs  # type: ignore
        import cartopy.feature as cfeature  # type: ignore

        return ccrs, cfeature
    except Exception:
        return None, None


def resolve_geo_assets_dir(geo_assets_dir: str | None) -> Path | None:
    """Return geo assets directory if exists, else None."""
    if not geo_assets_dir:
        return None
    p = Path(geo_assets_dir).expanduser().resolve()
    return p if p.exists() else None


def detect_geo_resource(geo_assets_dir: Path | None) -> str:
    """Lightweight check for common vector resource files."""
    if geo_assets_dir is None:
        return "none"
    for pattern in ("*.shp", "*.geojson", "*.json"):
        if any(geo_assets_dir.rglob(pattern)):
            return pattern
    return "none"

