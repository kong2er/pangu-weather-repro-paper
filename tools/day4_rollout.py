#!/usr/bin/env python3
"""Day4 rollout.

Goal: Run multi-step ONNX rollout and write eval package for Day5+ metrics.
Inputs: processed surface/pressure (.npy) and ONNX models under MODELS_ROOT.
Outputs: rollout_pressure_*.npy, rollout_surface_*.npy, eval_z500.npz, meta json.
Example: uv run python tools/day4_rollout.py --steps 6 --noarena --out-dir "$OUTPUT_ROOT/day4_rollout_06h"
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np

PRESSURE_VARS = ["z", "q", "t", "u", "v"]
PRESSURE_LEVELS = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 50]


def _resolve_model_path(models_dir: str, step: int) -> str:
    name = f"pangu_weather_{step}.onnx"
    path = os.path.join(models_dir, name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"model not found: {path}. "
            "Set MODELS_ROOT or pass --models-dir to point at downloaded ONNX models."
        )
    return path


def _session_options(threads: int, noarena: bool):
    import onnxruntime as ort

    so = ort.SessionOptions()
    so.intra_op_num_threads = threads
    so.inter_op_num_threads = 1
    if noarena:
        so.enable_cpu_mem_arena = False
        so.enable_mem_pattern = False
        so.enable_mem_reuse = False
    return so


def _providers(use_gpu: bool, gpu_mem_limit_mb: int | None) -> List:
    if not use_gpu:
        return ["CPUExecutionProvider"]
    cuda_provider_options = {
        "arena_extend_strategy": os.environ.get("ORT_ARENA_EXTEND_STRATEGY", "kNextPowerOfTwo"),
        "cudnn_conv_algo_search": os.environ.get("ORT_CUDNN_ALGO_SEARCH", "DEFAULT"),
        "do_copy_in_default_stream": "1",
        "enable_cuda_graph": "0",
        "tunable_op_enable": "0",
    }
    # 关键：不要默认写 mem_limit（0 会让可用显存变成 0）
    if gpu_mem_limit_mb and gpu_mem_limit_mb > 0:
        cuda_provider_options["gpu_mem_limit"] = str(gpu_mem_limit_mb * 1024 * 1024)
    return [("CUDAExecutionProvider", cuda_provider_options), "CPUExecutionProvider"]


def _load_inputs(processed_dir: str) -> Tuple[np.ndarray, np.ndarray]:
    surface_path = os.path.join(processed_dir, "surface.npy")
    pressure_path = os.path.join(processed_dir, "pressure.npy")
    if not os.path.exists(surface_path):
        raise FileNotFoundError(
            f"missing surface.npy: {surface_path}. "
            "Run scripts/04_preprocess_era5_to_npy.py to generate processed inputs."
        )
    if not os.path.exists(pressure_path):
        raise FileNotFoundError(
            f"missing pressure.npy: {pressure_path}. "
            "Run scripts/04_preprocess_era5_to_npy.py to generate processed inputs."
        )
    surface = np.load(surface_path).astype(np.float32)
    pressure = np.load(pressure_path).astype(np.float32)
    if surface.ndim == 4 and surface.shape[1] == 1:
        surface = surface[:, 0]
    if pressure.ndim == 5 and pressure.shape[1] == 1:
        pressure = pressure[:, 0]
    return pressure, surface


def _map_inputs(sess, pressure: np.ndarray, surface: np.ndarray) -> Dict[str, np.ndarray]:
    ins = sess.get_inputs()
    feed: Dict[str, np.ndarray] = {}
    for i in ins:
        name = i.name.lower()
        if "surface" in name:
            feed[i.name] = surface
        elif "upper" in name or "pressure" in name or "input" in name:
            feed[i.name] = pressure

    # fallback: strict order
    if len(feed) != len(ins):
        feed = {ins[0].name: pressure, ins[1].name: surface} if len(ins) >= 2 else {ins[0].name: pressure}

    # Fix known swapped input ordering by matching expected shapes.
    try:
        exp = {i.name: tuple(i.shape) for i in ins}
        if "input" in feed and "input_surface" in feed:
            got_in = tuple(getattr(feed.get("input"), "shape", ()))
            got_sfc = tuple(getattr(feed.get("input_surface"), "shape", ()))
            if got_in == exp.get("input_surface") and got_sfc == exp.get("input"):
                feed = dict(feed)
                feed["input"], feed["input_surface"] = feed["input_surface"], feed["input"]
    except Exception:
        pass
    return feed


def _split_outputs(sess, outputs: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    names = [o.name.lower() for o in sess.get_outputs()]
    pressure = None
    surface = None
    for name, arr in zip(names, outputs):
        if "surface" in name:
            surface = arr
        else:
            pressure = arr
    if pressure is None or surface is None:
        # last resort
        pressure, surface = outputs[0], outputs[1]
    return pressure, surface


def _run_step(
    model_path: str,
    pressure: np.ndarray,
    surface: np.ndarray,
    threads: int,
    use_gpu: bool,
    noarena: bool,
    gpu_mem_limit_mb: int | None,
) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    try:
        import onnxruntime as ort
    except Exception as exc:
        raise RuntimeError(
            "onnxruntime is required for rollout. Install onnxruntime or run in a prepared env."
        ) from exc
    so = _session_options(threads, noarena)
    providers = _providers(use_gpu, gpu_mem_limit_mb)
    sess = ort.InferenceSession(model_path, providers=providers, sess_options=so)
    feed = _map_inputs(sess, pressure, surface)
    out_names = [o.name for o in sess.get_outputs()]
    outputs = sess.run(out_names, feed)
    next_pressure, next_surface = _split_outputs(sess, outputs)
    return next_pressure, next_surface, sess.get_providers()


def _extract_z500(pressure: np.ndarray) -> np.ndarray:
    arr = np.asarray(pressure)
    var_idx = PRESSURE_VARS.index("z")
    lvl_idx = PRESSURE_LEVELS.index(500)
    if arr.ndim == 4:  # [C, L, H, W]
        z = arr[var_idx, lvl_idx]
    elif arr.ndim == 5:  # [T, C, L, H, W]
        z = arr[:, var_idx, lvl_idx]
        if z.ndim == 3 and z.shape[0] == 1:
            z = z[0]
    elif arr.ndim == 3:  # [L, H, W]
        z = arr[lvl_idx]
    elif arr.ndim == 2:  # [H, W]
        z = arr
    else:
        raise ValueError(f"unsupported pressure shape for z500: {arr.shape}")
    return np.asarray(z).astype(np.float32, copy=False)


def _parse_start_dt(date: str, hour: str) -> datetime | None:
    if not date or not hour:
        return None
    try:
        return datetime.strptime(f"{date}{hour}", "%Y%m%d%H")
    except Exception:
        return None


def _step_datetimes(start: datetime | None, steps: List[int]) -> List[datetime]:
    if start is None:
        return []
    times = []
    total = 0
    for s in steps:
        total += s
        times.append(start + timedelta(hours=total))
    return times


def _era5_pressure_path(root: str, dt: datetime) -> str:
    stamp = dt.strftime("%Y%m%d%H")
    return os.path.join(root, f"era5_pressure_{stamp}.nc")


def _load_era5_z500(path: str) -> Tuple[np.ndarray | None, str | None]:
    if not os.path.exists(path):
        return None, "missing_file"
    try:
        import netCDF4 as nc  # lazy import
    except Exception:
        return None, "netCDF4_unavailable"
    ds = nc.Dataset(path)
    try:
        if "z" not in ds.variables:
            return None, "missing_var_z"
        lvl_name = "level" if "level" in ds.variables else "pressure_level"
        if lvl_name not in ds.variables:
            return None, "missing_level_axis"
        levels = ds[lvl_name][:]
        lvl_idx = int(np.where(levels == 500)[0][0])
        z = ds["z"][:]
        if hasattr(z, "filled"):
            z = z.filled(np.nan)
        z500 = np.asarray(z)[0, lvl_idx]
        return z500.astype(np.float32), None
    finally:
        ds.close()


def _write_eval_package(
    out_dir: str,
    pred_z500: np.ndarray,
    steps: List[int],
    date: str | None,
    hour: str | None,
    era5_raw_root: str | None,
) -> Tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    eval_path = os.path.join(out_dir, "eval_z500.npz")
    meta_path = os.path.join(out_dir, "eval_z500_meta.json")

    start_dt = _parse_start_dt(date or "", hour or "")
    step_times = _step_datetimes(start_dt, steps)
    gt_list = []
    gt_paths = []
    gt_missing = []
    gt_z500 = None
    if era5_raw_root and step_times:
        for dt in step_times:
            p = _era5_pressure_path(era5_raw_root, dt)
            gt_paths.append(p)
            arr, err = _load_era5_z500(p)
            if err:
                gt_missing.append({"path": p, "reason": err})
            else:
                gt_list.append(arr)
        if gt_list and not gt_missing:
            gt_z500 = np.stack(gt_list, axis=0)

    if pred_z500.ndim == 2:
        pred_store = pred_z500[None, ...]
    else:
        pred_store = pred_z500

    savez_kwargs = {"pred_z500": pred_store}
    if gt_z500 is not None:
        savez_kwargs["gt_z500"] = gt_z500
    np.savez(eval_path, **savez_kwargs)

    meta = {
        "var": "z500",
        "units": "m^2 s^-2",
        "pressure_vars": PRESSURE_VARS,
        "pressure_levels": PRESSURE_LEVELS,
        "date": date,
        "hour": hour,
        "steps": steps,
        "step_datetimes_utc": [dt.strftime("%Y-%m-%dT%H:%M:%SZ") for dt in step_times],
        "pred_shape": list(pred_store.shape),
        "pred_dtype": str(pred_store.dtype),
        "pred_path": eval_path,
        "gt_paths": gt_paths,
        "gt_missing": gt_missing,
        "gt_shape": list(gt_z500.shape) if gt_z500 is not None else None,
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    return eval_path, meta_path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models-dir", default=os.environ.get("MODELS_ROOT", "/root/autodl-tmp/pangu-weather-repro/models"))
    p.add_argument("--processed-dir", default=os.environ.get("PROCESSED_ROOT", "/root/autodl-tmp/pangu-weather-repro/processed"))
    p.add_argument("--out-dir", required=True)
    p.add_argument("--steps", default="24,6")
    p.add_argument("--init-pressure", default="")
    p.add_argument("--init-surface", default="")
    p.add_argument("--force-cpu", action="store_true")
    p.add_argument("--gpu-mem-limit-mb", type=int, default=int(os.environ.get("ORT_GPU_MEM_LIMIT_MB", "0")))
    p.add_argument("--threads", type=int, default=int(os.environ.get("OMP_NUM_THREADS", "1")))
    p.add_argument("--noarena", action="store_true")
    p.add_argument("--date", default=os.environ.get("DATE", ""))
    p.add_argument("--hour", default=os.environ.get("HOUR", ""))
    p.add_argument("--era5-raw-root", default=os.environ.get("ERA5_RAW_ROOT", ""))
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    steps = [int(s.strip()) for s in args.steps.split(",") if s.strip()]
    if not steps:
        raise ValueError("No steps provided.")

    if args.init_pressure and args.init_surface:
        pressure = np.load(args.init_pressure).astype(np.float32)
        surface = np.load(args.init_surface).astype(np.float32)
    else:
        pressure, surface = _load_inputs(args.processed_dir)

    report = {
        "steps": steps,
        "providers_used": [],
        "pressure_shape": list(pressure.shape),
        "surface_shape": list(surface.shape),
        "outputs": [],
    }
    pred_z500_list: List[np.ndarray] = []

    for idx, step in enumerate(steps, start=1):
        model_path = _resolve_model_path(args.models_dir, step)
        use_gpu = not args.force_cpu

        try:
            pressure, surface, providers = _run_step(
                model_path, pressure, surface,
                args.threads,
                use_gpu=use_gpu,
                noarena=args.noarena,
                gpu_mem_limit_mb=args.gpu_mem_limit_mb or None,
            )
        except Exception as exc:
            msg = str(exc)
            if use_gpu and ("Failed to allocate memory" in msg or "BFCArena" in msg or "CUDA" in msg):
                print(f"⚠️ GPU OOM/alloc fail on step {step}, retrying on CPU...")
                pressure, surface, providers = _run_step(
                    model_path, pressure, surface,
                    args.threads,
                    use_gpu=False,
                    noarena=args.noarena,
                    gpu_mem_limit_mb=None,
                )
            else:
                raise

        stamp = f"{sum(steps[:idx])}h"
        np.save(os.path.join(args.out_dir, f"rollout_pressure_{stamp}.npy"), np.asarray(pressure))
        np.save(os.path.join(args.out_dir, f"rollout_surface_{stamp}.npy"), np.asarray(surface))

        report["providers_used"].append(providers)
        report["outputs"].append({
            "step": step,
            "stamp": stamp,
            "pressure_shape": list(np.asarray(pressure).shape),
            "surface_shape": list(np.asarray(surface).shape),
            "providers": providers,
        })

        pred_z500 = _extract_z500(pressure)
        if pred_z500.ndim == 3 and pred_z500.shape[0] == 1:
            pred_z500 = pred_z500[0]
        if pred_z500.ndim != 2:
            raise ValueError(f"z500 must be 2D per step, got {pred_z500.shape}")
        pred_z500_list.append(pred_z500)

        print(f"{idx} {stamp} providers: {providers}")

    rep_path = os.path.join(args.out_dir, "rollout_report.json")
    with open(rep_path, "w") as f:
        json.dump(report, f, indent=2)
    print("✅ rollout ok, wrote:", rep_path)

    pred_z500_stack = np.stack(pred_z500_list, axis=0) if pred_z500_list else np.zeros((0,))
    eval_path, meta_path = _write_eval_package(
        args.out_dir,
        pred_z500_stack,
        steps,
        args.date,
        args.hour,
        args.era5_raw_root,
    )
    print("✅ eval package:", eval_path)
    print("✅ eval meta:", meta_path)


if __name__ == "__main__":
    main()
