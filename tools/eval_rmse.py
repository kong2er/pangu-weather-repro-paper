#!/usr/bin/env python3
import argparse
import csv
import json
import os
from typing import Any, Dict, List, Tuple

import numpy as np


def _load_meta_for_pred(pred_path: str) -> Dict[str, Any] | None:
    base = os.path.splitext(pred_path)[0]
    candidates = [
        f"{base}_meta.json",
        os.path.join(os.path.dirname(pred_path), "eval_z500_meta.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r") as f:
                return json.load(f)
    return None


def _load_era5_z500(path: str) -> np.ndarray:
    import netCDF4 as nc  # lazy import
    ds = nc.Dataset(path)
    try:
        if "z" not in ds.variables:
            raise ValueError("ERA5 file missing variable 'z'")
        lvl_name = "level" if "level" in ds.variables else "pressure_level"
        if lvl_name not in ds.variables:
            raise ValueError("ERA5 file missing level axis")
        levels = ds[lvl_name][:]
        lvl_idx = int(np.where(levels == 500)[0][0])
        z = ds["z"][:]
        if hasattr(z, "filled"):
            z = z.filled(np.nan)
        z500 = np.asarray(z)[0, lvl_idx]
        return z500.astype(np.float32)
    finally:
        ds.close()


def _load_pred_gt(pred_path: str, gt_path: str | None, var: str) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any] | None, str]:
    if pred_path.endswith(".npz"):
        data = np.load(pred_path)
        if var not in data and f"pred_{var}" in data:
            pred = data[f"pred_{var}"]
        elif "pred_z500" in data:
            pred = data["pred_z500"]
        else:
            raise ValueError(f"pred npz missing pred_{var} or pred_z500")
        if gt_path:
            gt = _load_gt_from_path(gt_path, var)
            gt_src = gt_path
        elif "gt_z500" in data:
            gt = data["gt_z500"]
            gt_src = f"{pred_path}::gt_z500"
        else:
            meta = _load_meta_for_pred(pred_path)
            if meta and meta.get("gt_paths"):
                gt = _load_gt_from_era5_list(meta["gt_paths"])
                gt_src = "ERA5::" + ",".join(meta["gt_paths"])
            else:
                raise ValueError("gt not provided and not found in pred package/meta")
        meta = _load_meta_for_pred(pred_path)
        return pred, gt, meta, gt_src
    else:
        pred = np.load(pred_path)
        if gt_path is None:
            raise ValueError("--gt is required when --pred is not npz")
        gt = _load_gt_from_path(gt_path, var)
        return pred, gt, None, gt_path


def _load_gt_from_path(path: str, var: str) -> np.ndarray:
    if path.endswith(".npz"):
        data = np.load(path)
        key = f"gt_{var}"
        if key in data:
            return data[key]
        if var in data:
            return data[var]
        if "gt_z500" in data:
            return data["gt_z500"]
        raise ValueError(f"gt npz missing {key}/{var}/gt_z500")
    if path.endswith(".npy"):
        return np.load(path)
    if path.endswith(".nc"):
        return _load_era5_z500(path)
    raise ValueError(f"unsupported gt path: {path}")


def _load_gt_from_era5_list(paths: List[str]) -> np.ndarray:
    arrays = []
    for p in paths:
        if not os.path.exists(p):
            raise FileNotFoundError(p)
        arrays.append(_load_era5_z500(p))
    return np.stack(arrays, axis=0)


def _rmse(pred: np.ndarray, gt: np.ndarray) -> float:
    diff = pred.astype(np.float64) - gt.astype(np.float64)
    return float(np.sqrt(np.mean(diff * diff)))


def main() -> None:
    p = argparse.ArgumentParser()
    default_pred = os.path.join(
        os.environ.get("OUTPUT_ROOT", "/root/autodl-tmp/pangu-weather-repro/outputs"),
        "day4_rollout_30h",
        "eval_z500.npz",
    )
    p.add_argument("--pred", default=default_pred)
    p.add_argument("--gt", default="")
    p.add_argument("--var", default="z500")
    p.add_argument("--out", default=os.path.join("artifacts", "day5", "rmse.csv"))
    args = p.parse_args()

    pred, gt, meta, gt_src = _load_pred_gt(args.pred, args.gt or None, args.var)

    if pred.shape != gt.shape:
        raise ValueError(f"shape mismatch pred={pred.shape} gt={gt.shape}")

    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    rows = []
    date = meta.get("date") if meta else ""
    hour = meta.get("hour") if meta else ""
    steps = meta.get("steps") if meta else []
    steps_str = ",".join(str(s) for s in steps) if steps else ""

    if pred.ndim == 2:
        rmse_val = _rmse(pred, gt)
        n = int(pred.size)
        rows.append({
            "var": args.var,
            "rmse": rmse_val,
            "n": n,
            "shape": "x".join(str(x) for x in pred.shape),
            "date": date,
            "hour": hour,
            "steps": steps_str,
            "step_index": "overall",
            "step_hour": "",
            "dtype": str(pred.dtype),
            "pred_path": args.pred,
            "gt_path": gt_src,
        })
        step_rmses = [rmse_val]
    elif pred.ndim == 3:
        step_rmses = []
        for i in range(pred.shape[0]):
            rmse_val = _rmse(pred[i], gt[i])
            step_rmses.append(rmse_val)
            step_hour = steps[i] if i < len(steps) else ""
            rows.append({
                "var": args.var,
                "rmse": rmse_val,
                "n": int(pred[i].size),
                "shape": "x".join(str(x) for x in pred[i].shape),
                "date": date,
                "hour": hour,
                "steps": steps_str,
                "step_index": str(i + 1),
                "step_hour": str(step_hour),
                "dtype": str(pred.dtype),
                "pred_path": args.pred,
                "gt_path": gt_src,
            })
        overall = _rmse(pred, gt)
        rows.append({
            "var": args.var,
            "rmse": overall,
            "n": int(pred.size),
            "shape": "x".join(str(x) for x in pred.shape),
            "date": date,
            "hour": hour,
            "steps": steps_str,
            "step_index": "overall",
            "step_hour": "",
            "dtype": str(pred.dtype),
            "pred_path": args.pred,
            "gt_path": gt_src,
        })
    else:
        raise ValueError(f"unsupported pred ndim: {pred.ndim}")

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "var",
                "rmse",
                "n",
                "shape",
                "date",
                "hour",
                "steps",
                "step_index",
                "step_hour",
                "dtype",
                "pred_path",
                "gt_path",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    rmse_mean = float(np.mean(step_rmses))
    rmse_min = float(np.min(step_rmses))
    rmse_max = float(np.max(step_rmses))

    print("RMSE summary")
    print(f"  rmse_mean: {rmse_mean}")
    print(f"  rmse_min:  {rmse_min}")
    print(f"  rmse_max:  {rmse_max}")
    print(f"  shape:     {pred.shape}")
    print(f"  dtype:     {pred.dtype}")
    print(f"  pred:      {args.pred}")
    print(f"  gt:        {gt_src}")
    print(f"  out:       {args.out}")


if __name__ == "__main__":
    main()
