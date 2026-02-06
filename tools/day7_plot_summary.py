#!/usr/bin/env python3
"""Day7 summary plot.

Goal: Plot metric summary CSV into a bar chart figure.
Inputs: artifacts/day7/metrics_summary.csv
Outputs: figures/day7/summary_rmse.png or summary_acc.png
Example: uv run python tools/day7_plot_summary.py --csv artifacts/day7/metrics_summary.csv --metric rmse_latw --out figures/day7/summary_rmse.png
"""
from __future__ import annotations

import argparse
import csv
import os
from typing import Dict, List

import numpy as np


def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        return [r for r in reader]


def _default_out(metric: str) -> str:
    if metric in ("acc", "acc_latw"):
        return os.path.join("figures", "day7", "summary_acc.png")
    return os.path.join("figures", "day7", "summary_rmse.png")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default=os.path.join("artifacts", "day7", "metrics_summary.csv"))
    p.add_argument("--metric", default="rmse_latw")
    p.add_argument("--out", default="")
    args = p.parse_args()

    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        raise RuntimeError(
            "matplotlib is required to plot summary figures. Install matplotlib or run in a plotting env."
        ) from exc

    if not os.path.exists(args.csv):
        raise FileNotFoundError(f"metrics_summary.csv not found: {args.csv}. Run Day7 metrics first.")

    rows = _read_csv(args.csv)
    if not rows:
        raise ValueError("metrics_summary.csv has no data rows")

    print("[day7_plot] csv:", args.csv)
    print("[day7_plot] columns:", list(rows[0].keys()))
    print("[day7_plot] rows:", len(rows))

    metric = args.metric
    if metric not in rows[0]:
        raise ValueError(f"metric {metric} not found in csv")

    vars_list = sorted(set(r["var"] for r in rows))
    leads_list = sorted(set(int(r["lead"]) for r in rows))

    matrix = np.full((len(vars_list), len(leads_list)), np.nan)
    for r in rows:
        v = r["var"]
        l = int(r["lead"])
        i = vars_list.index(v)
        j = leads_list.index(l)
        matrix[i, j] = float(r[metric])

    out_path = args.out if args.out else _default_out(metric)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=160)
    x = np.arange(len(vars_list))
    width = 0.8 / max(1, len(leads_list))

    for j, lead in enumerate(leads_list):
        vals = matrix[:, j]
        ax.bar(x + j * width, vals, width=width, label=f"{lead}h")

    ax.set_xticks(x + width * (len(leads_list) - 1) / 2)
    ax.set_xticklabels(vars_list)
    ax.set_ylabel(metric)
    ax.set_title(f"{metric} Summary by Variable and Lead")
    ax.legend(loc="best")
    ax.grid(axis="y", linestyle=":", alpha=0.5)

    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    print("[day7_plot] out:", out_path)


if __name__ == "__main__":
    main()
