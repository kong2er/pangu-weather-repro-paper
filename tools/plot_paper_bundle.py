#!/usr/bin/env python3
"""Generate paper-grade plots with metadata.

Example:
  scripts/run_gpu.sh tools/plot_paper_bundle.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --var z500
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, List

import numpy as np


def _load_meta(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def _pick_key(meta: Dict[str, Any], keys: List[str]):
    for k in keys:
        if k in meta:
            return meta[k]
    return None


def _preferred_rollout_dir(output_root: str) -> str:
    if not os.path.isdir(output_root):
        print(f"OUTPUT_ROOT not found: {output_root}")
        raise SystemExit(2)
    prefer = os.path.join(output_root, "day4_rollout_30h")
    if os.path.isdir(prefer):
        return prefer
    # fallback: pick any rollout dir
    for name in os.listdir(output_root):
        if name.startswith("day4_rollout_"):
            return os.path.join(output_root, name)
    raise SystemExit("No rollout dir found under OUTPUT_ROOT")


def _git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _load_pred_npz(path: str, var: str) -> np.ndarray:
    with np.load(path) as data:
        if f"pred_{var}" in data:
            return data[f"pred_{var}"]
        if "pred_z500" in data:
            return data["pred_z500"]
        raise ValueError(f"pred npz missing pred_{var} or pred_z500")


def _ensure_matplotlib():
    try:
        import matplotlib.pyplot as plt  # noqa: F401
    except Exception as exc:
        raise RuntimeError("matplotlib missing. Run: scripts/install_extras.sh plots") from exc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--var", default="z500")
    p.add_argument("--rollout-dir", default="")
    p.add_argument("--meta", default="")
    p.add_argument("--outdir", default=os.path.join("figures", "paper"))
    p.add_argument("--no-map", action="store_true")
    p.add_argument("--dpi", type=int, default=220)
    p.add_argument("--force", action="store_true")
    args = p.parse_args()

    _ensure_matplotlib()
    import matplotlib.pyplot as plt

    output_root = os.environ.get("OUTPUT_ROOT", "outputs")
    rollout_dir = args.rollout_dir or _preferred_rollout_dir(output_root)
    meta_path = args.meta or os.path.join(rollout_dir, "eval_z500_meta.json")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(
            f"meta not found: {meta_path}. Run Day4 rollout with eval package export first."
        )

    meta = _load_meta(meta_path)
    pred_path = _pick_key(meta, ["pred_path", "pred"]) or os.path.join(rollout_dir, "eval_z500.npz")
    steps = _pick_key(meta, ["steps", "lead_steps"]) or []
    date = _pick_key(meta, ["date"]) or ""
    hour = _pick_key(meta, ["hour"]) or ""
    units = _pick_key(meta, ["units"]) or ""

    pred = _load_pred_npz(pred_path, args.var)
    if pred.ndim == 2:
        pred = pred[None, ...]

    os.makedirs(args.outdir, exist_ok=True)
    git_hash = _git_hash()
    for idx, step in enumerate(steps or [0]):
        lead = sum(steps[: idx + 1]) if steps else 0
        out_png = os.path.join(args.outdir, f"paper_{args.var}_t+{lead:03d}.png")
        out_json = out_png.replace(".png", ".json")
        if os.path.exists(out_png) and not args.force:
            print("skip existing:", out_png)
            continue

        data = pred[idx]
        fig, ax = plt.subplots(figsize=(6.0, 3.2), dpi=args.dpi)
        im = ax.imshow(data, cmap="viridis")
        ax.set_title(f"{args.var} t+{lead:03d} ({units})")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        fig.tight_layout()
        fig.savefig(out_png)
        plt.close(fig)

        meta_out = {
            "var": args.var,
            "lead": lead,
            "date": date,
            "hour": hour,
            "units": units,
            "pred_path": pred_path,
            "rollout_dir": rollout_dir,
            "git": git_hash,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "no_map": args.no_map,
        }
        with open(out_json, "w") as f:
            json.dump(meta_out, f, indent=2)

        print("[paper]", out_png)


if __name__ == "__main__":
    main()
