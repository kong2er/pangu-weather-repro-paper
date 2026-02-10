#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt


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


def _preferred_rollout_dir(output_root: str) -> str:
    if not os.path.isdir(output_root):
        print(f"OUTPUT_ROOT not found: {output_root}")
        raise SystemExit(2)
    prefer = os.path.join(output_root, "day4_rollout_30h")
    if os.path.isdir(prefer):
        return prefer
    cands = []
    if os.path.isdir(output_root):
        for name in os.listdir(output_root):
            if name.startswith("day4_rollout_"):
                path = os.path.join(output_root, name)
                if os.path.isdir(path):
                    cands.append(path)
    cands.sort()
    print("no preferred rollout (day4_rollout_30h). Available:", cands or "NONE")
    raise SystemExit(2)


def _load_meta(meta_path: str) -> Dict[str, Any]:
    with open(meta_path, "r") as f:
        return json.load(f)


def _pick_key(meta: Dict[str, Any], keys: List[str]) -> Any:
    for k in keys:
        if k in meta:
            return meta[k]
    return None


def _sum_steps(steps: List[int]) -> List[int]:
    out = []
    total = 0
    for s in steps:
        total += int(s)
        out.append(total)
    return out


def _load_pred_gt_from_npz(npz_path: str, var: str) -> Tuple[np.ndarray, np.ndarray | None]:
    data = np.load(npz_path)
    pred = None
    if f"pred_{var}" in data:
        pred = data[f"pred_{var}"]
    elif "pred_z500" in data:
        pred = data["pred_z500"]
    if pred is None:
        raise ValueError("pred not found in npz")
    gt = None
    if f"gt_{var}" in data:
        gt = data[f"gt_{var}"]
    elif "gt_z500" in data:
        gt = data["gt_z500"]
    return pred, gt


def _load_era5_z500(path: str) -> np.ndarray:
    try:
        import netCDF4 as nc
    except Exception as exc:
        raise RuntimeError("netCDF4 missing. Run: scripts/install_extras.sh rmse") from exc
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


def _select_lead_index(steps: List[int], lead: int | None) -> int:
    if not steps:
        return 0
    lead_hours = _sum_steps(steps)
    if lead is None:
        return len(lead_hours) - 1
    if lead not in lead_hours:
        print(f"lead {lead} not in available leads: {lead_hours}")
        raise SystemExit(2)
    return lead_hours.index(lead)


def _format_date_hour(date: str | None, hour: str | None) -> str:
    if not date or not hour:
        return ""
    try:
        dt = datetime.strptime(f"{date}{hour}", "%Y%m%d%H")
        return dt.strftime("%Y-%m-%d %HZ")
    except Exception:
        return f"{date} {hour}"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--var", default="z500")
    p.add_argument("--rollout-dir", default="")
    p.add_argument("--meta", default="")
    p.add_argument("--outdir", default=os.path.join("figures", "day6"))
    p.add_argument("--lead", type=int, default=None)
    p.add_argument("--vmin", type=float, default=None)
    p.add_argument("--vmax", type=float, default=None)
    p.add_argument("--err-max", type=float, default=None)
    args = p.parse_args()

    output_root = os.environ.get("OUTPUT_ROOT", "/root/autodl-tmp/pangu-weather-repro/outputs")
    rollout_dir = args.rollout_dir or _preferred_rollout_dir(output_root)
    meta_path = args.meta or os.path.join(rollout_dir, "eval_z500_meta.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(
            f"meta not found: {meta_path}. Run Day4 rollout with eval package export first."
        )

    meta = _load_meta(meta_path)
    print("[plot_fields] rollout_dir:", rollout_dir)
    print("[plot_fields] meta:", meta_path)
    print("[plot_fields] meta keys:", sorted(list(meta.keys())))

    pred_path = _pick_key(meta, ["pred_path", "pred", "pred_pathz"]) or os.path.join(rollout_dir, "eval_z500.npz")
    gt_paths = _pick_key(meta, ["gt_paths", "gt_path", "gt"]) or []
    units = _pick_key(meta, ["units", "unit"]) or ""
    steps = _pick_key(meta, ["steps", "lead_steps"]) or []
    date = _pick_key(meta, ["date", "DATE"]) or ""
    hour = _pick_key(meta, ["hour", "HOUR"]) or ""

    pred, gt = _load_pred_gt_from_npz(pred_path, args.var)
    gt_available = True

    if gt is None:
        if isinstance(gt_paths, list) and gt_paths:
            missing = [p for p in gt_paths if not os.path.exists(p)]
            if missing:
                print("missing gt_paths:", missing)
                print("Tip: use --rollout-dir $OUTPUT_ROOT/day4_rollout_30h or download missing ERA5.")
                gt_available = False
            else:
                gt_list = [_load_era5_z500(p) for p in gt_paths]
                gt = np.stack(gt_list, axis=0)
        else:
            gt_available = False

    if gt_available and pred.shape != gt.shape:
        raise ValueError(f"shape mismatch pred={pred.shape} gt={gt.shape}")

    lead_idx = _select_lead_index(steps, args.lead)
    lead_hours = _sum_steps(steps)
    lead_val = lead_hours[lead_idx] if lead_hours else ""

    if pred.ndim == 3:
        pred2 = pred[lead_idx]
        gt2 = gt[lead_idx] if gt_available else None
    else:
        pred2 = pred
        gt2 = gt if gt_available else None

    vmin = args.vmin if args.vmin is not None else float(np.nanmin(pred2))
    vmax = args.vmax if args.vmax is not None else float(np.nanmax(pred2))
    err_max = None
    if gt_available and gt2 is not None:
        err = pred2 - gt2
        err_max = args.err_max if args.err_max is not None else float(np.nanmax(np.abs(err)))

    os.makedirs(args.outdir, exist_ok=True)
    date_hour = f"{date}{hour}" if date and hour else "unknown"
    lead_tag = f"t+{int(lead_val):03d}" if isinstance(lead_val, int) else "t+unk"
    out_path = os.path.join(args.outdir, f"field_{args.var}_{date_hour}_{lead_tag}.png")

    print("[plot_fields] pred:", pred_path)
    print("[plot_fields] gt:", gt_paths if gt_paths else "(from npz)" if gt_available else "(missing)")
    print("[plot_fields] shape:", pred.shape, "dtype:", pred.dtype)
    print("[plot_fields] units:", units)
    print("[plot_fields] lead:", lead_val, "index:", lead_idx)
    print("[plot_fields] out:", out_path)

    if gt_available and gt2 is not None:
        fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.2), dpi=160)
    else:
        fig, axes = plt.subplots(1, 1, figsize=(5.0, 4.2), dpi=160)
        axes = [axes]
    title_time = _format_date_hour(date, hour)

    if gt_available and gt2 is not None:
        im0 = axes[0].imshow(gt2, vmin=vmin, vmax=vmax, cmap="viridis")
        axes[0].set_title(f"GT {args.var} {title_time} {lead_tag}")
        plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04, label=units)

        im1 = axes[1].imshow(pred2, vmin=vmin, vmax=vmax, cmap="viridis")
        axes[1].set_title(f"Pred {args.var} {title_time} {lead_tag}")
        plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04, label=units)

        im2 = axes[2].imshow(err, vmin=-err_max, vmax=err_max, cmap="RdBu_r")
        axes[2].set_title(f"Error (Pred-GT) {title_time} {lead_tag}")
        plt.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04, label=units)
    else:
        im1 = axes[0].imshow(pred2, vmin=vmin, vmax=vmax, cmap="viridis")
        axes[0].set_title(f"Pred {args.var} {title_time} {lead_tag}")
        plt.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04, label=units)

    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])

    plt.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
