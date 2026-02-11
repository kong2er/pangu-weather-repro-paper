#!/usr/bin/env python3
"""Unified forecast runner for 1/3/6/24h models and short/long schedules.

Example:
  scripts/run_gpu.sh tools/run_forecast.py --mode short --target-hours 84
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import List

from pangu_weather_repro.infer.runner import ForecastRunner
from pangu_weather_repro.infer.scheduler import build_schedule


def _parse_hours(text: str) -> List[int]:
    if not text:
        return []
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def _load_resume_hour(out_dir: str) -> int:
    state_path = os.path.join(out_dir, "forecast_state.json")
    report_path = os.path.join(out_dir, "forecast_report.json")
    if os.path.exists(state_path):
        try:
            import json

            with open(state_path, "r") as f:
                state = json.load(f)
            return int(state.get("last_hour", 0))
        except Exception:
            return 0
    if os.path.exists(report_path):
        try:
            import json

            with open(report_path, "r") as f:
                report = json.load(f)
            return int(report.get("total_hours", 0))
        except Exception:
            return 0
    return 0


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models-dir", default=os.environ.get("MODELS_ROOT", "models"))
    p.add_argument("--processed-dir", default=os.environ.get("PROCESSED_ROOT", "processed"))
    p.add_argument("--out-dir", default="")
    p.add_argument("--target-hours", type=int, default=30)
    p.add_argument("--mode", choices=["short", "long", "full", "split"], default="short")
    p.add_argument("--strategy", choices=["default", "pangu_ref", "kong2er_ref"], default="default")
    p.add_argument("--short-step", type=int, default=1)
    p.add_argument("--long-step", type=int, default=24)
    p.add_argument("--save-hours", default="1,3,6,24,84,120,168,240,360")
    p.add_argument("--save-all", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--resume-from", default="")
    p.add_argument("--no-gpu", action="store_true")
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--noarena", action="store_true")
    p.add_argument("--gpu-mem-limit-mb", type=int, default=None)
    p.add_argument("--no-cache-sessions", action="store_true")
    p.add_argument("--cache-sessions", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    output_root = os.environ.get("OUTPUT_ROOT", "outputs")
    out_dir = args.resume_from or args.out_dir or os.path.join(output_root, f"forecast_{args.target_hours}h")

    normalized_strategy = "pangu_ref" if args.strategy == "kong2er_ref" else args.strategy

    if args.mode == "split":
        if args.target_hours <= 84:
            raise SystemExit("split mode requires target_hours > 84")
        schedule = None
    else:
        schedule = build_schedule(
            target_hours=args.target_hours,
            short_until=84,
            short_step=args.short_step,
            long_step=args.long_step,
            mode=args.mode,
            strategy=normalized_strategy,
        )

    print("[forecast] mode:", args.mode)
    print("[forecast] target_hours:", args.target_hours)
    if schedule is not None:
        print("[forecast] schedule steps:", schedule.steps)
    print("[forecast] strategy:", args.strategy)
    print("[forecast] models_dir:", args.models_dir)
    print("[forecast] processed_dir:", args.processed_dir)
    print("[forecast] out_dir:", out_dir)
    if args.resume_from:
        print("[forecast] resume_from:", args.resume_from)

    if args.dry_run:
        if args.mode == "split":
            short_sched = build_schedule(
                target_hours=84,
                short_until=84,
                short_step=args.short_step,
                long_step=args.long_step,
                mode="short",
                strategy=normalized_strategy,
            )
            long_sched = build_schedule(
                target_hours=args.target_hours - 84,
                short_until=84,
                short_step=args.short_step,
                long_step=args.long_step,
                mode="long",
                strategy=normalized_strategy,
            )
            print("[forecast] split short steps:", short_sched.steps)
            print("[forecast] split long steps:", long_sched.steps)
        print("[forecast] dry-run only (no inference).")
        return

    steps_to_check = []
    if args.mode == "split":
        short_sched = build_schedule(
            target_hours=84,
            short_until=84,
            short_step=args.short_step,
            long_step=args.long_step,
            mode="short",
            strategy=normalized_strategy,
        )
        long_sched = build_schedule(
            target_hours=args.target_hours - 84,
            short_until=84,
            short_step=args.short_step,
            long_step=args.long_step,
            mode="long",
            strategy=normalized_strategy,
        )
        if args.resume_from:
            out_dir_short = out_dir + "_84h"
            out_dir_long = out_dir + "_276h"
            if os.path.exists(out_dir_short) and _load_resume_hour(out_dir_short) == 0:
                raise SystemExit(
                    f"resume requested but no state/report found in {out_dir_short}. "
                    "Use --force or a new --out-dir."
                )
            if os.path.exists(out_dir_long) and _load_resume_hour(out_dir_long) == 0:
                raise SystemExit(
                    f"resume requested but no state/report found in {out_dir_long}. "
                    "Use --force or a new --out-dir."
                )
        steps_to_check = sorted(set(short_sched.steps + long_sched.steps))
    else:
        if args.resume_from and os.path.exists(out_dir) and _load_resume_hour(out_dir) == 0:
            raise SystemExit(
                f"resume requested but no state/report found in {out_dir}. "
                "Use --force or a new --out-dir."
            )
        steps_to_check = sorted(set(schedule.steps))

    missing = []
    for step in steps_to_check:
        name = os.path.join(args.models_dir, f"pangu_weather_{step}.onnx")
        if not os.path.exists(name):
            missing.append(name)
    if missing:
        print("Missing model files:")
        for m in missing:
            print("  -", m)
        print("Next: bash scripts/01_download_models.sh or set MODELS_ROOT")
        raise SystemExit(2)

    cache_sessions = args.cache_sessions
    if args.mode in {"split", "full", "long"}:
        cache_sessions = False if not args.cache_sessions else True
    if args.no_cache_sessions:
        cache_sessions = False

    runner = ForecastRunner(
        models_dir=args.models_dir,
        use_gpu=not args.no_gpu,
        threads=args.threads,
        noarena=args.noarena,
        gpu_mem_limit_mb=args.gpu_mem_limit_mb,
        cache_sessions=cache_sessions,
    )

    try:
        run_started = time.time()
        if args.mode == "split":
            out_dir_short = out_dir + "_84h"
            out_dir_long = out_dir + "_276h"
            resume_short = _load_resume_hour(out_dir_short) if args.resume_from else 0
            resume_long = _load_resume_hour(out_dir_long) if args.resume_from else 0

            if resume_short >= 84:
                print("[forecast] short segment already done, skip.")
            else:
                result_short = runner.run_schedule(
                    schedule=short_sched,
                    processed_dir=args.processed_dir,
                    out_dir=out_dir_short,
                    save_hours=_parse_hours(args.save_hours),
                    force=args.force,
                    save_all=args.save_all,
                    resume_from_hour=resume_short if resume_short > 0 else None,
                )
                print("[forecast] report short:", result_short.report_path)

            if resume_long >= args.target_hours:
                print("[forecast] long segment already done, skip.")
                return

            if resume_short < 84 and not os.path.exists(out_dir_short):
                raise SystemExit("short segment missing; run split without --resume-from first.")

            result_long = runner.run_schedule(
                schedule=long_sched,
                processed_dir=args.processed_dir,
                out_dir=out_dir_long,
                save_hours=_parse_hours(args.save_hours),
                force=args.force,
                save_all=args.save_all,
                resume_from_hour=resume_long if resume_long > 0 else None,
                init_from_dir=out_dir_short,
                init_from_hour=84,
            )
            print("[forecast] report long:", result_long.report_path)
            final_summary = {
                "strategy": args.strategy,
                "strategy_effective": normalized_strategy,
                "mode": args.mode,
                "split": True,
                "resume_enabled": bool(args.resume_from),
                "target_hours": args.target_hours,
                "threads": args.threads,
                "gpu_mem_limit_mb": args.gpu_mem_limit_mb,
                "providers": result_long.steps and runner._providers() or [],
                "segments": [
                    {
                        "name": "short_84h",
                        "out_dir": out_dir_short,
                        "report_path": os.path.join(out_dir_short, "forecast_report.json"),
                    },
                    {
                        "name": "long_276h",
                        "out_dir": out_dir_long,
                        "report_path": result_long.report_path,
                    },
                ],
                "elapsed_sec": round(time.time() - run_started, 3),
            }
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "forecast_report.json"), "w") as f:
                json.dump(final_summary, f, indent=2)
            print("[forecast] report:", os.path.join(out_dir, "forecast_report.json"))
        else:
            resume_hour = _load_resume_hour(out_dir) if args.resume_from else 0
            result = runner.run_schedule(
                schedule=schedule,
                processed_dir=args.processed_dir,
                out_dir=out_dir,
                save_hours=_parse_hours(args.save_hours),
                force=args.force,
                save_all=args.save_all,
                resume_from_hour=resume_hour if resume_hour > 0 else None,
            )
            print("[forecast] report:", result.report_path)
            final_summary = {
                "strategy": args.strategy,
                "strategy_effective": normalized_strategy,
                "mode": args.mode,
                "split": False,
                "resume_enabled": bool(args.resume_from),
                "target_hours": args.target_hours,
                "threads": args.threads,
                "gpu_mem_limit_mb": args.gpu_mem_limit_mb,
                "steps": result.steps,
                "out_dir": result.out_dir,
                "segment_report_path": result.report_path,
                "elapsed_sec": round(time.time() - run_started, 3),
            }
            with open(os.path.join(out_dir, "forecast_report.json"), "w") as f:
                json.dump(final_summary, f, indent=2)
            print("[forecast] summary:", os.path.join(out_dir, "forecast_report.json"))
    except Exception as exc:
        msg = str(exc)
        if "out_dir exists" in msg:
            print("[forecast] out_dir exists. Next:")
            print("  - use --resume-from <out_dir> to continue")
            print("  - or pass --out-dir to a new directory")
            print("  - or add --force to overwrite")
        oom_signals = [
            "Failed to allocate memory",
            "CUDA out of memory",
            "BFCArena::AllocateRawInternal",
            "Available memory of",
            "smaller than requested bytes",
        ]
        if any(s in msg for s in oom_signals):
            print("[forecast] OOM detected. Try one of:")
            print("  - add --noarena")
            print("  - add --threads 1")
            print("  - add --gpu-mem-limit-mb 4096 (or smaller)")
            print("  - use --short-step 6 (avoid 1h model in long runs)")
            print("  - add --no-cache-sessions (avoid GPU mem accumulation)")
            print("  - use --mode split (run 84h then 276h)")
            print("  - use --resume-from <out_dir> to continue after crash")
            print("  - use scripts/run_360h_split.sh --auto-retry")
            print("  - reduce target hours or use --mode short with fewer steps")
        raise


if __name__ == "__main__":
    main()
