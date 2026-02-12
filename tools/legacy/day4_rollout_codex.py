import argparse
import json
import os
from typing import Dict, List, Tuple

import numpy as np
import onnxruntime as ort


def _resolve_model_path(models_dir: str, step: int) -> str:
    name = f"pangu_weather_{step}.onnx"
    path = os.path.join(models_dir, name)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return path


def _session_options(threads: int, noarena: bool) -> ort.SessionOptions:
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
    if gpu_mem_limit_mb:
        cuda_provider_options["gpu_mem_limit"] = str(gpu_mem_limit_mb * 1024 * 1024)
    return [("CUDAExecutionProvider", cuda_provider_options), "CPUExecutionProvider"]


def _load_inputs(processed_dir: str) -> Tuple[np.ndarray, np.ndarray]:
    surface = np.load(os.path.join(processed_dir, "surface.npy")).astype(np.float32)
    pressure = np.load(os.path.join(processed_dir, "pressure.npy")).astype(np.float32)
    if surface.ndim == 4 and surface.shape[1] == 1:
        surface = surface[:, 0]
    if pressure.ndim == 5 and pressure.shape[1] == 1:
        pressure = pressure[:, 0]
    return pressure, surface


def _map_inputs(sess: ort.InferenceSession, pressure: np.ndarray, surface: np.ndarray) -> Dict[str, np.ndarray]:
    ins = sess.get_inputs()
    feed: Dict[str, np.ndarray] = {}
    for i in ins:
        name = i.name.lower()
        if "surface" in name:
            feed[i.name] = surface
        elif "upper" in name or "pressure" in name:
            feed[i.name] = pressure
    if len(feed) != len(ins):
        feed = {ins[0].name: surface, ins[1].name: pressure}

    # Fix known swapped input ordering by matching expected shapes.
    try:
        exp = {i.name: tuple(i.shape) for i in ins}
        got_in = tuple(getattr(feed.get("input"), "shape", ()))
        got_sfc = tuple(getattr(feed.get("input_surface"), "shape", ()))
        if ("input" in feed and "input_surface" in feed and
            got_in == exp.get("input_surface") and got_sfc == exp.get("input")):
            feed = dict(feed)
            feed["input"], feed["input_surface"] = feed["input_surface"], feed["input"]
    except Exception:
        pass
    return feed


def _split_outputs(sess: ort.InferenceSession, outputs: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    names = [o.name.lower() for o in sess.get_outputs()]
    pressure = None
    surface = None
    for name, arr in zip(names, outputs):
        if "surface" in name:
            surface = arr
        elif "upper" in name or "pressure" in name:
            pressure = arr
    if pressure is None or surface is None:
        surface, pressure = outputs[0], outputs[1]
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
    so = _session_options(threads, noarena)
    providers = _providers(use_gpu, gpu_mem_limit_mb)
    sess = ort.InferenceSession(model_path, providers=providers, sess_options=so)
    feed = _map_inputs(sess, pressure, surface)
    out_names = [o.name for o in sess.get_outputs()]
    outputs = sess.run(out_names, feed)
    next_pressure, next_surface = _split_outputs(sess, outputs)
    return next_pressure, next_surface, sess.get_providers()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--models-dir", default=os.environ.get("MODELS_ROOT", "/root/autodl-tmp/pangu-weather-repro/models"))
    p.add_argument("--processed-dir", default=os.environ.get("PROCESSED_ROOT", "/root/autodl-tmp/pangu-weather-repro/processed"))
    p.add_argument("--out-dir", default=os.environ.get("OUTPUT_ROOT", "/root/autodl-tmp/pangu-weather-repro/outputs"))
    p.add_argument("--steps", default="24,6", help="Comma-separated step hours, e.g. 24,6 or 24,24,6,1,1")
    p.add_argument("--force-cpu", action="store_true")
    p.add_argument("--gpu-mem-limit-mb", type=int, default=int(os.environ.get("ORT_GPU_MEM_LIMIT_MB", "0")))
    p.add_argument("--threads", type=int, default=int(os.environ.get("OMP_NUM_THREADS", "1")))
    p.add_argument("--noarena", action="store_true", help="Disable ORT arena/mem pattern to reduce peak spikes")
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    steps = [int(s.strip()) for s in args.steps.split(",") if s.strip()]
    if not steps:
        raise ValueError("No steps provided.")

    pressure, surface = _load_inputs(args.processed_dir)

    report = {
        "steps": steps,
        "providers_used": [],
        "pressure_shape": list(pressure.shape),
        "surface_shape": list(surface.shape),
        "outputs": [],
    }

    for idx, step in enumerate(steps, start=1):
        model_path = _resolve_model_path(args.models_dir, step)
        use_gpu = not args.force_cpu
        try:
            pressure, surface, providers = _run_step(
                model_path,
                pressure,
                surface,
                args.threads,
                use_gpu=use_gpu,
                noarena=args.noarena,
                gpu_mem_limit_mb=args.gpu_mem_limit_mb or None,
            )
        except Exception as exc:
            msg = str(exc)
            if use_gpu and ("Failed to allocate memory" in msg or "CUDA" in msg):
                print(f"⚠️ GPU OOM on step {step}, retrying on CPU...")
                pressure, surface, providers = _run_step(
                    model_path,
                    pressure,
                    surface,
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
        report["outputs"].append(
            {
                "step": step,
                "stamp": stamp,
                "pressure_shape": list(np.asarray(pressure).shape),
                "surface_shape": list(np.asarray(surface).shape),
            }
        )

    rep_path = os.path.join(args.out_dir, "rollout_report.json")
    with open(rep_path, "w") as f:
        json.dump(report, f, indent=2)
    print("✅ rollout ok, wrote:", rep_path)


if __name__ == "__main__":
    main()
