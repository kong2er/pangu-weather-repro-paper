#!/usr/bin/env python3
"""Unified forecast runner for 1/3/6/24h models and short/long schedules.

Example:
  scripts/run_gpu.sh tools/run_forecast.py --mode short --target-hours 84
"""
from __future__ import annotations

import argparse
import os
from typing import List

from pangu_weather_repro.infer.runner import ForecastRunner
from pangu_weather_repro.infer.scheduler import build_schedule


def _parse_hours(text: str) -> List[int]:
    if not text:
        return []
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models-dir", default=os.environ.get("MODELS_ROOT", "models"))
    p.add_argument("--processed-dir", default=os.environ.get("PROCESSED_ROOT", "processed"))
    p.add_argument("--out-dir", default="")
    p.add_argument("--target-hours", type=int, default=30)
    p.add_argument("--mode", choices=["short", "long", "full"], default="short")
    p.add_argument("--strategy", choices=["default", "pangu_ref"], default="default")
    p.add_argument("--short-step", type=int, default=1)
    p.add_argument("--long-step", type=int, default=24)
    p.add_argument("--save-hours", default="1,3,6,24,84,120,168,240,360")
    p.add_argument("--save-all", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-gpu", action="store_true")
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--noarena", action="store_true")
    p.add_argument("--gpu-mem-limit-mb", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    output_root = os.environ.get("OUTPUT_ROOT", "outputs")
    out_dir = args.out_dir or os.path.join(output_root, f"forecast_{args.target_hours}h")

    schedule = build_schedule(
        target_hours=args.target_hours,
        short_until=84,
        short_step=args.short_step,
        long_step=args.long_step,
        mode=args.mode,
        strategy=args.strategy,
    )

    print("[forecast] mode:", args.mode)
    print("[forecast] target_hours:", args.target_hours)
    print("[forecast] schedule steps:", schedule.steps)
    print("[forecast] strategy:", args.strategy)
    print("[forecast] models_dir:", args.models_dir)
    print("[forecast] processed_dir:", args.processed_dir)
    print("[forecast] out_dir:", out_dir)

    if args.dry_run:
        print("[forecast] dry-run only (no inference).")
        return

    missing = []
    for step in sorted(set(schedule.steps)):
        name = os.path.join(args.models_dir, f"pangu_weather_{step}.onnx")
        if not os.path.exists(name):
            missing.append(name)
    if missing:
        print("Missing model files:")
        for m in missing:
            print("  -", m)
        print("Next: bash scripts/01_download_models.sh or set MODELS_ROOT")
        raise SystemExit(2)

    runner = ForecastRunner(
        models_dir=args.models_dir,
        use_gpu=not args.no_gpu,
        threads=args.threads,
        noarena=args.noarena,
        gpu_mem_limit_mb=args.gpu_mem_limit_mb,
    )

    try:
        result = runner.run_schedule(
            schedule=schedule,
            processed_dir=args.processed_dir,
            out_dir=out_dir,
            save_hours=_parse_hours(args.save_hours),
            force=args.force,
            save_all=args.save_all,
        )
        print("[forecast] report:", result.report_path)
    except Exception as exc:
        msg = str(exc)
        if "Failed to allocate memory" in msg or "CUDA out of memory" in msg:
            print("[forecast] OOM detected. Try one of:")
            print("  - add --noarena")
            print("  - add --threads 1")
            print("  - add --gpu-mem-limit-mb 4096 (or smaller)")
            print("  - use --short-step 6 (avoid 1h model in long runs)")
            print("  - reduce target hours or use --mode short with fewer steps")
        raise


if __name__ == "__main__":
    main()
