#!/usr/bin/env python3
"""Generate product-style figures from rollout outputs.

Example:
  scripts/run_gpu.sh tools/plot_product_bundle.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500,t2m --hours 24,30
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from pangu_weather_repro.contracts import SURFACE_VARS
from pangu_weather_repro.visualization.product_draw import (
    draw_diff_fill,
    draw_global_fill,
    draw_msl_wind,
    draw_wind_speed,
    draw_wind_vector,
)

SURFACE_INDEX = {name: idx for idx, name in enumerate(SURFACE_VARS)}
UNITS_MAP = {
    "z500": "m^2 s^-2",
    "msl": "hPa",
    "u10": "m s^-1",
    "v10": "m s^-1",
    "t2m": "K",
}


def _parse_csv_int(text: str) -> list[int]:
    values: list[int] = []
    for raw in text.split(","):
        raw = raw.strip()
        if not raw:
            continue
        values.append(int(raw))
    return values


def _parse_extent(text: str) -> tuple[float, float, float, float]:
    raw = [x.strip() for x in text.split(",") if x.strip()]
    if len(raw) != 4:
        raise ValueError("--extent expects 4 comma-separated values: lon_min,lon_max,lat_min,lat_max")
    return (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))


def _preferred_rollout_dir(output_root: str) -> str:
    preferred = os.path.join(output_root, "day4_rollout_30h")
    if os.path.isdir(preferred):
        return preferred
    for name in sorted(os.listdir(output_root)):
        if name.startswith("day4_rollout_"):
            return os.path.join(output_root, name)
    raise FileNotFoundError(f"no rollout dir found under {output_root}")


def _load_meta(rollout_dir: str) -> dict[str, Any]:
    meta_path = os.path.join(rollout_dir, "eval_z500_meta.json")
    with open(meta_path, "r") as f:
        return json.load(f)


def _lead_hours(meta: dict[str, Any]) -> list[int]:
    steps = [int(x) for x in (meta.get("steps") or [])]
    out: list[int] = []
    acc = 0
    for step in steps:
        acc += step
        out.append(acc)
    return out


def _load_z500_by_idx(rollout_dir: str, idx: int) -> np.ndarray:
    pred_path = os.path.join(rollout_dir, "eval_z500.npz")
    with np.load(pred_path) as data:
        if "pred_z500" not in data:
            raise KeyError(f"pred_z500 missing in {pred_path}")
        arr = data["pred_z500"]
    return np.asarray(arr[idx], dtype=np.float32)


def _load_z500_gt_by_idx(rollout_dir: str, idx: int) -> np.ndarray:
    pred_path = os.path.join(rollout_dir, "eval_z500.npz")
    with np.load(pred_path) as data:
        if "gt_z500" in data:
            arr = data["gt_z500"]
            return np.asarray(arr[idx], dtype=np.float32)

    # Fallback: derive GT from meta gt_paths (ERA5 pressure files).
    meta = _load_meta(rollout_dir)
    gt_paths = meta.get("gt_paths") or []
    if idx >= len(gt_paths):
        raise KeyError(f"gt_paths missing index {idx} in eval_z500_meta.json")
    gt_path = gt_paths[idx]
    try:
        import netCDF4 as nc
    except Exception as exc:
        raise RuntimeError("missing netCDF4 for diff fallback. Run: bash scripts/install_extras.sh rmse") from exc
    if not os.path.exists(gt_path):
        raise FileNotFoundError(gt_path)
    ds = nc.Dataset(gt_path)
    try:
        if "z" not in ds.variables:
            raise KeyError(f"z missing in {gt_path}")
        lvl_name = "level" if "level" in ds.variables else "pressure_level"
        if lvl_name not in ds.variables:
            raise KeyError(f"level axis missing in {gt_path}")
        levels = ds[lvl_name][:]
        idx_arr = np.where(levels == 500)[0]
        if len(idx_arr) == 0:
            raise ValueError(f"500hPa not found in {gt_path}")
        lvl_idx = int(idx_arr[0])
        z = np.asarray(ds["z"][:])
        if z.ndim == 4:
            out = z[0, lvl_idx]
        elif z.ndim == 3:
            out = z[lvl_idx]
        else:
            raise ValueError(f"unsupported z shape: {z.shape}")
        return np.asarray(out, dtype=np.float32)
    finally:
        ds.close()


def _load_surface_by_lead(rollout_dir: str, var: str, lead: int) -> np.ndarray:
    if var not in SURFACE_INDEX:
        raise ValueError(f"unsupported surface var: {var}")
    path = os.path.join(rollout_dir, f"rollout_surface_{lead}h.npy")
    surface = np.load(path)
    # Expected shape: (4, 721, 1440)
    return np.asarray(surface[SURFACE_INDEX[var]], dtype=np.float32)


def _load_uv10_by_lead(rollout_dir: str, lead: int) -> tuple[np.ndarray, np.ndarray]:
    path = os.path.join(rollout_dir, f"rollout_surface_{lead}h.npy")
    surface = np.load(path)
    u10 = np.asarray(surface[SURFACE_INDEX["u10"]], dtype=np.float32)
    v10 = np.asarray(surface[SURFACE_INDEX["v10"]], dtype=np.float32)
    return u10, v10


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate product bundle png/json from rollout outputs (idempotent by default)."
    )
    p.add_argument("--rollout-dir", default="", help="Rollout directory (default: auto from OUTPUT_ROOT).")
    p.add_argument("--out-dir", default=os.path.join("figures", "product"))
    p.add_argument("--vars", default="z500,t2m", help="Comma list from: z500,msl,u10,v10,t2m")
    p.add_argument("--hours", default="", help="Optional comma list of cumulative lead hours, e.g. 24,30")
    p.add_argument(
        "--kinds",
        default="fill",
        help="Comma list from: fill,diff,vector,wind_speed,msl_wind (diff supports z500; vector/wind_speed/msl_wind support uv10).",
    )
    p.add_argument("--with-geo", action="store_true", help="Enable cartopy-based map overlays if available.")
    p.add_argument("--geo-assets-dir", default="assets/geo", help="Optional geo assets directory.")
    p.add_argument("--style-profile", default="standard", help="Style profile for product figures (default: standard).")
    p.add_argument(
        "--extent",
        default="",
        help="Optional map extent lon_min,lon_max,lat_min,lat_max (e.g. 95,145,10,50).",
    )
    p.add_argument("--force", action="store_true", help="Overwrite existing png/json outputs.")
    args = p.parse_args()

    output_root = os.environ.get("OUTPUT_ROOT", "outputs")
    rollout_dir = args.rollout_dir or _preferred_rollout_dir(output_root)
    if not os.path.isdir(rollout_dir):
        raise FileNotFoundError(f"rollout_dir not found: {rollout_dir}")

    meta = _load_meta(rollout_dir)
    leads = _lead_hours(meta)
    if not leads:
        raise ValueError("meta missing steps; cannot infer lead hours")
    lead_filter = set(_parse_csv_int(args.hours)) if args.hours else set(leads)
    extent = _parse_extent(args.extent) if args.extent else None
    vars_list = [x.strip() for x in args.vars.split(",") if x.strip()]
    kinds = [x.strip() for x in args.kinds.split(",") if x.strip()]
    if not vars_list:
        raise ValueError("--vars is empty")
    if not kinds:
        raise ValueError("--kinds is empty")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[STEP] product bundle")
    print(f"[INPUT] rollout_dir={rollout_dir}")
    print(f"[OUTPUT] out_dir={out_dir}")
    print(f"[VARS] {vars_list}")
    print(f"[KINDS] {kinds}")
    print(f"[LEADS] {sorted(lead_filter)}")
    if args.with_geo:
        print(f"[GEO] enabled, assets={args.geo_assets_dir}")
    else:
        print("[GEO] disabled")
    print(f"[STYLE] {args.style_profile}")
    if extent is not None:
        print(f"[EXTENT] {extent}")

    generated = 0
    skipped = 0
    for idx, lead in enumerate(leads):
        if lead not in lead_filter:
            continue
        for var in vars_list:
            try:
                if var == "z500":
                    field = _load_z500_by_idx(rollout_dir, idx)
                elif var in SURFACE_INDEX:
                    field = _load_surface_by_lead(rollout_dir, var, lead)
                else:
                    print(f"[WARN] unsupported var={var}, skip")
                    skipped += 1
                    continue
            except FileNotFoundError as exc:
                print(f"[WARN] missing input for var={var} lead={lead}: {exc}")
                skipped += 1
                continue

            if "fill" in kinds:
                out_png = out_dir / f"product_{var}_t+{lead:03d}.png"
                before = out_png.exists()
                png, meta_json = draw_global_fill(
                    field,
                    out_png,
                    var=var,
                    lead_hour=lead,
                    units=UNITS_MAP.get(var, ""),
                    with_geo=args.with_geo,
                    geo_assets_dir=args.geo_assets_dir,
                    style_profile=args.style_profile,
                    extent=extent,
                    force=args.force,
                    extra_meta={"rollout_dir": rollout_dir, "source": "plot_product_bundle", "extent_cli": list(extent) if extent else []},
                )
                if before and not args.force:
                    skipped += 1
                else:
                    generated += 1
                print(f"[FILE] {png}")
                print(f"[META] {meta_json}")

            if "diff" in kinds:
                if var != "z500":
                    print(f"[WARN] diff not supported for var={var}, skip")
                    skipped += 1
                    continue
                try:
                    gt = _load_z500_gt_by_idx(rollout_dir, idx)
                except Exception as exc:
                    print(f"[WARN] cannot load gt for diff var={var} lead={lead}: {exc}")
                    skipped += 1
                    continue
                out_png = out_dir / f"product_diff_{var}_t+{lead:03d}.png"
                before = out_png.exists()
                png, meta_json = draw_diff_fill(
                    field,
                    gt,
                    out_png,
                    var=var,
                    lead_hour=lead,
                    units=UNITS_MAP.get(var, ""),
                    style_profile=args.style_profile,
                    extent=extent,
                    force=args.force,
                    extra_meta={"rollout_dir": rollout_dir, "source": "plot_product_bundle", "extent_cli": list(extent) if extent else []},
                )
                if before and not args.force:
                    skipped += 1
                else:
                    generated += 1
                print(f"[FILE] {png}")
                print(f"[META] {meta_json}")

            if "vector" in kinds:
                if var != "u10":
                    # vector 图只在 var=u10 时生成一次，避免重复文件。
                    continue
                try:
                    u10, v10 = _load_uv10_by_lead(rollout_dir, lead)
                except Exception as exc:
                    print(f"[WARN] cannot load uv10 for vector lead={lead}: {exc}")
                    skipped += 1
                    continue
                out_png = out_dir / f"product_vector_uv10_t+{lead:03d}.png"
                before = out_png.exists()
                png, meta_json = draw_wind_vector(
                    u10,
                    v10,
                    out_png,
                    lead_hour=lead,
                    style_profile=args.style_profile,
                    with_geo=args.with_geo,
                    geo_assets_dir=args.geo_assets_dir,
                    extent=extent,
                    force=args.force,
                    extra_meta={"rollout_dir": rollout_dir, "source": "plot_product_bundle", "extent_cli": list(extent) if extent else []},
                )
                if before and not args.force:
                    skipped += 1
                else:
                    generated += 1
                print(f"[FILE] {png}")
                print(f"[META] {meta_json}")

            if "wind_speed" in kinds:
                if var != "u10":
                    continue
                try:
                    u10, v10 = _load_uv10_by_lead(rollout_dir, lead)
                except Exception as exc:
                    print(f"[WARN] cannot load uv10 for wind_speed lead={lead}: {exc}")
                    skipped += 1
                    continue
                out_png = out_dir / f"product_wind_speed_t+{lead:03d}.png"
                before = out_png.exists()
                png, meta_json = draw_wind_speed(
                    u10,
                    v10,
                    out_png,
                    lead_hour=lead,
                    style_profile=args.style_profile,
                    with_geo=args.with_geo,
                    geo_assets_dir=args.geo_assets_dir,
                    extent=extent,
                    force=args.force,
                    extra_meta={"rollout_dir": rollout_dir, "source": "plot_product_bundle", "extent_cli": list(extent) if extent else []},
                )
                if before and not args.force:
                    skipped += 1
                else:
                    generated += 1
                print(f"[FILE] {png}")
                print(f"[META] {meta_json}")

            if "msl_wind" in kinds:
                if var != "u10":
                    continue
                try:
                    u10, v10 = _load_uv10_by_lead(rollout_dir, lead)
                    msl = _load_surface_by_lead(rollout_dir, "msl", lead)
                except Exception as exc:
                    print(f"[WARN] cannot load msl/uv10 for msl_wind lead={lead}: {exc}")
                    skipped += 1
                    continue
                out_png = out_dir / f"product_msl_wind_t+{lead:03d}.png"
                before = out_png.exists()
                png, meta_json = draw_msl_wind(
                    msl,
                    u10,
                    v10,
                    out_png,
                    lead_hour=lead,
                    style_profile=args.style_profile,
                    with_geo=args.with_geo,
                    geo_assets_dir=args.geo_assets_dir,
                    extent=extent,
                    force=args.force,
                    extra_meta={"rollout_dir": rollout_dir, "source": "plot_product_bundle", "extent_cli": list(extent) if extent else []},
                )
                if before and not args.force:
                    skipped += 1
                else:
                    generated += 1
                print(f"[FILE] {png}")
                print(f"[META] {meta_json}")

    print(f"[DONE] generated={generated}, skipped={skipped}")
    print("[NEXT] Use: ls -lh figures/product | head")


if __name__ == "__main__":
    main()
