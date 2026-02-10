#!/usr/bin/env python3
import argparse
import csv
import os
from datetime import datetime
from typing import List, Dict

try:
    import matplotlib.pyplot as plt
except Exception as exc:
    raise RuntimeError("matplotlib missing. Run: scripts/install_extras.sh plots") from exc
import numpy as np


def _format_date_hour(date: str | None, hour: str | None) -> str:
    if not date or not hour:
        return ""
    try:
        dt = datetime.strptime(f"{date}{hour}", "%Y%m%d%H")
        return dt.strftime("%Y-%m-%d %HZ")
    except Exception:
        return f"{date} {hour}"


def _read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader]
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default=os.path.join("artifacts", "day5", "rmse.csv"))
    p.add_argument("--var", default="z500")
    p.add_argument("--outdir", default=os.path.join("figures", "day6"))
    args = p.parse_args()

    if not os.path.exists(args.csv):
        print(f"rmse.csv not found: {args.csv}. Run: scripts/run_day5_rmse.sh")
        raise SystemExit(2)

    rows = _read_csv(args.csv)
    if not rows:
        raise ValueError("rmse.csv has no data rows")

    print("[plot_rmse] csv:", args.csv)
    print("[plot_rmse] columns:", list(rows[0].keys()))
    print("[plot_rmse] rows:", len(rows))

    rows = [r for r in rows if r.get("var", "") == args.var]
    if not rows:
        raise ValueError(f"no rows for var={args.var} in {args.csv}")

    date = rows[0].get("date", "")
    hour = rows[0].get("hour", "")

    per_step = []
    overall = None
    for r in rows:
        if r.get("step_index", "") == "overall":
            overall = float(r["rmse"])
        else:
            per_step.append(r)

    os.makedirs(args.outdir, exist_ok=True)
    date_hour = f"{date}{hour}" if date and hour else "unknown"
    out_path = os.path.join(args.outdir, f"rmse_{args.var}_{date_hour}.png")

    fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=160)

    if per_step:
        leads = []
        rmses = []
        for r in per_step:
            step_hour = r.get("step_hour", "")
            if step_hour:
                leads.append(int(step_hour))
            else:
                leads.append(int(r.get("step_index", "0")))
            rmses.append(float(r["rmse"]))
        order = np.argsort(leads)
        leads = np.array(leads)[order]
        rmses = np.array(rmses)[order]
        ax.plot(leads, rmses, marker="o", linewidth=2)
        ax.set_xlabel("Lead Time (hours)")
        ax.set_ylabel("RMSE")
        if overall is not None:
            ax.axhline(overall, color="gray", linestyle="--", linewidth=1, label=f"overall={overall:.3f}")
            ax.legend(loc="best")
    else:
        if overall is None:
            overall = float(rows[0]["rmse"])
        ax.axhline(overall, color="C0", linewidth=2)
        ax.scatter([0], [overall], color="C0")
        ax.set_xlabel("Lead Time (hours)")
        ax.set_ylabel("RMSE")
        ax.text(0, overall, f"{overall:.3f}", va="bottom", ha="left")
        ax.set_xticks([0])

    title_time = _format_date_hour(date, hour)
    ax.set_title(f"RMSE {args.var} {title_time}")
    ax.grid(True, linestyle=":", alpha=0.5)

    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)

    print("[plot_rmse] out:", out_path)


if __name__ == "__main__":
    main()
