#!/usr/bin/env python3
import argparse
import csv
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np

from tools._metrics import acc_simple, load_latitude, rmse, rmse_latw

SURFACE_ORDER = ["msl", "u10", "v10", "t2m"]
PRESSURE_ORDER = ["z", "q", "t", "u", "v"]
PRESSURE_LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50]


def _latest_rollout_dir(output_root: str) -> str:
    if not os.path.isdir(output_root):
        raise FileNotFoundError(f"OUTPUT_ROOT not found: {output_root}")
    cands = []
    for name in os.listdir(output_root):
        if name.startswith("day4_rollout_"):
            path = os.path.join(output_root, name)
            if os.path.isdir(path):
                cands.append(path)
    if not cands:
        raise FileNotFoundError(f"no day4_rollout_* under {output_root}")
    cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return cands[0]


def _load_meta(meta_path: str) -> Dict:
    with open(meta_path, "r") as f:
        return json.load(f)


def _sum_steps(steps: List[int]) -> List[int]:
    out = []
    total = 0
    for s in steps:
        total += int(s)
        out.append(total)
    return out


def _parse_date_hour(date: str, hour: str) -> datetime:
    return datetime.strptime(f"{date}{hour}", "%Y%m%d%H")


def _lead_datetimes(start: datetime, leads: List[int]) -> List[datetime]:
    return [start + timedelta(hours=int(h)) for h in leads]


def _era5_paths(era5_root: str, dt: datetime) -> Tuple[str, str]:
    stamp = dt.strftime("%Y%m%d%H")
    return (
        os.path.join(era5_root, f"era5_single_{stamp}.nc"),
        os.path.join(era5_root, f"era5_pressure_{stamp}.nc"),
    )


def _squeeze_if_needed(arr: np.ndarray) -> np.ndarray:
    if arr.ndim >= 1 and arr.shape[0] == 1:
        return np.squeeze(arr, axis=0)
    return arr


def _parse_var(var: str) -> Tuple[str, str, int | None]:
    if var in SURFACE_ORDER:
        return ("surface", var, None)
    if var[-3:].isdigit():
        base = var[:-3]
        level = int(var[-3:])
        if base in PRESSURE_ORDER and level in PRESSURE_LEVELS:
            return ("pressure", base, level)
    raise ValueError(f"unsupported var: {var}. Use surface vars {SURFACE_ORDER} or pressure vars like z500/t850/u850/v850/q850")


def _load_pred_field(rollout_dir: str, var: str, lead: int) -> Tuple[np.ndarray, str]:
    stamp = f"{int(lead)}h"
    surface_path = os.path.join(rollout_dir, f"rollout_surface_{stamp}.npy")
    pressure_path = os.path.join(rollout_dir, f"rollout_pressure_{stamp}.npy")
    if not os.path.exists(surface_path) or not os.path.exists(pressure_path):
        raise FileNotFoundError(f"missing rollout outputs for lead {lead}: {surface_path} / {pressure_path}")
    surface = _squeeze_if_needed(np.load(surface_path))
    pressure = _squeeze_if_needed(np.load(pressure_path))

    kind, base, level = _parse_var(var)
    if kind == "surface":
        if surface.ndim != 3:
            raise ValueError(f"surface shape unexpected: {surface.shape}")
        idx = SURFACE_ORDER.index(base)
        return surface[idx], surface_path

    if pressure.ndim != 4:
        raise ValueError(f"pressure shape unexpected: {pressure.shape}")
    v_idx = PRESSURE_ORDER.index(base)
    l_idx = PRESSURE_LEVELS.index(level)
    return pressure[v_idx, l_idx], pressure_path


def _load_gt_field(era5_root: str, var: str, dt: datetime) -> Tuple[np.ndarray, str]:
    import netCDF4 as nc

    single_path, pressure_path = _era5_paths(era5_root, dt)
    kind, base, level = _parse_var(var)

    if kind == "surface":
        if not os.path.exists(single_path):
            raise FileNotFoundError(single_path)
        ds = nc.Dataset(single_path)
        try:
            data = ds[base][:]
            if hasattr(data, "filled"):
                data = data.filled(np.nan)
            return np.asarray(data)[0].astype(np.float32), single_path
        finally:
            ds.close()

    if not os.path.exists(pressure_path):
        raise FileNotFoundError(pressure_path)
    ds = nc.Dataset(pressure_path)
    try:
        lvl_name = "level" if "level" in ds.variables else "pressure_level"
        levels = ds[lvl_name][:]
        l_idx = int(np.where(levels == level)[0][0])
        data = ds[base][:]
        if hasattr(data, "filled"):
            data = data.filled(np.nan)
        return np.asarray(data)[0, l_idx].astype(np.float32), pressure_path
    finally:
        ds.close()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rollout-dir", default="")
    p.add_argument("--vars", default="z500,t2m,u10")
    p.add_argument("--leads", default="6,24")
    p.add_argument("--out", default=os.path.join("artifacts", "day7", "metrics_summary.csv"))
    p.add_argument("--md", default=os.path.join("docs", "day7_results.md"))
    args = p.parse_args()

    output_root = os.environ.get("OUTPUT_ROOT", "/root/autodl-tmp/pangu-weather-repro/outputs")
    era5_root = os.environ.get("ERA5_RAW_ROOT", "/root/autodl-tmp/pangu-weather-repro/era5_raw")

    rollout_dir = args.rollout_dir or _latest_rollout_dir(output_root)
    meta_path = os.path.join(rollout_dir, "eval_z500_meta.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"meta not found: {meta_path}. Run Day4 rollout first.")

    meta = _load_meta(meta_path)
    date = meta.get("date", "")
    hour = meta.get("hour", "")
    steps = meta.get("steps", [])

    vars_list = [v.strip() for v in args.vars.split(",") if v.strip()]
    leads = [int(x) for x in args.leads.split(",") if x.strip()]

    print("[day7] rollout_dir:", rollout_dir)
    print("[day7] meta:", meta_path)
    print("[day7] vars:", vars_list)
    print("[day7] leads:", leads)

    if not date or not hour:
        raise ValueError("meta missing date/hour")

    lead_hours_available = _sum_steps(steps)
    for h in leads:
        if h not in lead_hours_available:
            raise ValueError(f"lead {h} not in rollout steps {lead_hours_available}")

    start_dt = _parse_date_hour(date, hour)
    lead_dts = {h: dt for h, dt in zip(lead_hours_available, _lead_datetimes(start_dt, lead_hours_available))}

    lat_cache: Dict[str, np.ndarray] = {}
    rows = []
    for var in vars_list:
        for lead in leads:
            pred, pred_path = _load_pred_field(rollout_dir, var, lead)
            gt, gt_path = _load_gt_field(era5_root, var, lead_dts[lead])
            if pred.shape != gt.shape:
                raise ValueError(f"shape mismatch var={var} lead={lead} pred={pred.shape} gt={gt.shape}")

            if gt_path not in lat_cache:
                try:
                    lat_cache[gt_path] = load_latitude(gt_path)
                except Exception as e:
                    raise ValueError(f"latitude not found in {gt_path}. {e}. Please provide ERA5 file with latitude.")
            lat = lat_cache[gt_path]

            r = rmse(pred, gt)
            rw = rmse_latw(pred, gt, lat)
            a = acc_simple(pred, gt, None)
            aw = acc_simple(pred, gt, lat)

            rows.append({
                "var": var,
                "lead": str(lead),
                "rmse": r,
                "rmse_latw": rw,
                "acc": a,
                "acc_latw": aw,
                "n": int(np.isfinite(gt).sum()),
                "date": date,
                "hour": hour,
                "rollout_dir": rollout_dir,
                "pred_path": pred_path,
                "gt_path": gt_path,
            })

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "var",
                "lead",
                "rmse",
                "rmse_latw",
                "acc",
                "acc_latw",
                "n",
                "date",
                "hour",
                "rollout_dir",
                "pred_path",
                "gt_path",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    os.makedirs(os.path.dirname(args.md), exist_ok=True)
    with open(args.md, "w") as f:
        f.write("# Day7 Results (Metrics Summary)\n\n")
        f.write(f"- Date/Hour: {date} {hour}\n")
        f.write(f"- Vars: {', '.join(vars_list)}\n")
        f.write(f"- Leads: {', '.join(str(x) for x in leads)}\n")
        f.write(f"- Rollout: {rollout_dir}\n")
        f.write(f"- Output CSV: {args.out}\n\n")
        f.write("Metrics:\n")
        f.write("- rmse: unweighted RMSE\n")
        f.write("- rmse_latw: latitude-weighted RMSE (cos(lat))\n")
        f.write("- acc: anomaly correlation using GT mean as climatology\n")
        f.write("- acc_latw: latitude-weighted ACC\n\n")
        f.write("| var | lead | rmse | rmse_latw | acc | acc_latw | n |\n")
        f.write("|---|---|---:|---:|---:|---:|---:|\n")
        for r in rows:
            f.write(
                f"| {r['var']} | {r['lead']} | {r['rmse']:.6f} | {r['rmse_latw']:.6f} | {r['acc']:.6f} | {r['acc_latw']:.6f} | {r['n']} |\\n"
            )

    print("[day7] out:", args.out)
    print("[day7] md:", args.md)


if __name__ == "__main__":
    main()
