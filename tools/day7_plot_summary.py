#!/usr/bin/env python3
import argparse
import csv
import os
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np


def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        return [r for r in reader]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default=os.path.join("artifacts", "day7", "metrics_summary.csv"))
    p.add_argument("--out", default=os.path.join("figures", "day7", "summary_rmse.png"))
    args = p.parse_args()

    if not os.path.exists(args.csv):
        raise FileNotFoundError(f"metrics_summary.csv not found: {args.csv}. Run Day7 metrics first.")

    rows = _read_csv(args.csv)
    if not rows:
        raise ValueError("metrics_summary.csv has no data rows")

    print("[day7_plot] csv:", args.csv)
    print("[day7_plot] columns:", list(rows[0].keys()))
    print("[day7_plot] rows:", len(rows))

    vars_list = sorted(set(r["var"] for r in rows))
    leads_list = sorted(set(int(r["lead"]) for r in rows))

    matrix = np.full((len(vars_list), len(leads_list)), np.nan)
    for r in rows:
        v = r["var"]
        l = int(r["lead"])
        i = vars_list.index(v)
        j = leads_list.index(l)
        matrix[i, j] = float(r["rmse"])

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=160)
    x = np.arange(len(vars_list))
    width = 0.8 / max(1, len(leads_list))

    for j, lead in enumerate(leads_list):
        vals = matrix[:, j]
        ax.bar(x + j * width, vals, width=width, label=f"{lead}h")

    ax.set_xticks(x + width * (len(leads_list) - 1) / 2)
    ax.set_xticklabels(vars_list)
    ax.set_ylabel("RMSE")
    ax.set_title("RMSE Summary by Variable and Lead")
    ax.legend(loc="best")
    ax.grid(axis="y", linestyle=":", alpha=0.5)

    fig.savefig(args.out, dpi=160, bbox_inches="tight")
    plt.close(fig)

    print("[day7_plot] out:", args.out)


if __name__ == "__main__":
    main()
