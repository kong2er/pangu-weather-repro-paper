#!/usr/bin/env python3
"""Region demo: crop global inputs to a bbox and save region arrays."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime

import numpy as np

from pangu_weather_repro.region.adapter import GlobalGridCropAdapter


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--processed-dir", default=os.environ.get("PROCESSED_ROOT", "processed"))
    p.add_argument("--out-dir", default=os.path.join("outputs", "region_demo"))
    p.add_argument("--lat-min", type=float, default=28.0)
    p.add_argument("--lat-max", type=float, default=35.0)
    p.add_argument("--lon-min", type=float, default=118.0)
    p.add_argument("--lon-max", type=float, default=123.0)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    if os.path.exists(args.out_dir) and not args.force:
        raise SystemExit(f"out_dir exists: {args.out_dir}. Use --force to overwrite.")
    os.makedirs(args.out_dir, exist_ok=True)

    surface_path = os.path.join(args.processed_dir, "surface.npy")
    pressure_path = os.path.join(args.processed_dir, "pressure.npy")
    if not os.path.exists(surface_path) or not os.path.exists(pressure_path):
        raise SystemExit("missing processed inputs. Run scripts/04_preprocess_era5_to_npy.py")

    surface = np.load(surface_path).astype(np.float32)
    pressure = np.load(pressure_path).astype(np.float32)

    adapter = GlobalGridCropAdapter(
        pressure=pressure,
        surface=surface,
        lat_min=args.lat_min,
        lat_max=args.lat_max,
        lon_min=args.lon_min,
        lon_max=args.lon_max,
    )
    region_pressure, region_surface = adapter.to_model_inputs()

    np.save(os.path.join(args.out_dir, "region_pressure.npy"), region_pressure)
    np.save(os.path.join(args.out_dir, "region_surface.npy"), region_surface)

    meta = {
        "lat_min": args.lat_min,
        "lat_max": args.lat_max,
        "lon_min": args.lon_min,
        "lon_max": args.lon_max,
        "processed_dir": args.processed_dir,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "pressure_shape": list(region_pressure.shape),
        "surface_shape": list(region_surface.shape),
    }
    with open(os.path.join(args.out_dir, "region_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print("[region] out_dir:", args.out_dir)
    print("[region] pressure:", region_pressure.shape)
    print("[region] surface:", region_surface.shape)


if __name__ == "__main__":
    main()
