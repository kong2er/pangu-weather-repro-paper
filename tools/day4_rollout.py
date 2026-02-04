#!/usr/bin/env python3
import argparse, os, json, time, hashlib
import numpy as np
import onnxruntime as ort


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_cuda_provider_options() -> dict:
    # 只取第一个 GPU id
    dev = os.environ.get("CUDA_VISIBLE_DEVICES", "0").split(",")[0].strip()
    device_id = int(dev) if dev else 0

    opts = {
        "device_id": device_id,
        # 让 cudnn 搜索更稳定（你 Day3 用的也是 DEFAULT）
        "cudnn_conv_algo_search": os.environ.get("ORT_CUDNN_ALGO_SEARCH", "DEFAULT"),
        # 关键：减少内存峰值/碎片风险
        # kSameAsRequested 一般比 NextPowerOfTwo 更稳（更不浪费）
        "arena_extend_strategy": "kSameAsRequested",
        # 某些场景降低同步开销
        "do_copy_in_default_stream": 1,
    }

    # 可选：如果你真的要限制显存，就必须传一个 >0 的 bytes
    lim = os.environ.get("ORT_GPU_MEM_LIMIT", "").strip()
    if lim:
        v = int(lim)
        if v > 0:
            opts["gpu_mem_limit"] = v  # bytes

    return opts


def make_session(model_path: str, use_cuda: bool) -> ort.InferenceSession:
    so = ort.SessionOptions()

    # 关键：关闭 mem pattern（会导致大峰值/碎片），并强制顺序执行
    so.enable_mem_pattern = False
    so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

    # 线程保持 1（你 Day3 就是这样稳）
    so.intra_op_num_threads = int(os.environ.get("ORT_INTRA_OP", "1"))
    so.inter_op_num_threads = int(os.environ.get("ORT_INTER_OP", "1"))

    # 图优化别开太猛，避免额外临时张量峰值（默认 ORT_ENABLE_ALL 有时更吃内存）
    so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC

    if use_cuda:
        cuda_opts = build_cuda_provider_options()
        providers = [("CUDAExecutionProvider", cuda_opts), "CPUExecutionProvider"]
    else:
        providers = ["CPUExecutionProvider"]

    return ort.InferenceSession(model_path, sess_options=so, providers=providers)


def run_one(sess: ort.InferenceSession, pressure: np.ndarray, surface: np.ndarray):
    t0 = time.time()
    out_pressure, out_surface = sess.run(
        None,
        {"input": pressure.astype(np.float32), "input_surface": surface.astype(np.float32)},
    )
    dt = time.time() - t0
    return {
        "providers_actual": sess.get_providers(),
        "dt_sec": dt,
        "out_pressure": out_pressure,
        "out_surface": out_surface,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedule", nargs="+", type=int, required=True, help="e.g. 24 6 or 24 24 6 1 1")
    ap.add_argument("--models-root", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--init-pressure", default="", help="optional .npy")
    ap.add_argument("--init-surface", default="", help="optional .npy")
    ap.add_argument("--providers", default="cuda", choices=["cuda", "cpu"], help="use cuda or cpu")
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    def model_of(h):
        p = os.path.join(args.models_root, f"pangu_weather_{h}.onnx")
        if not os.path.exists(p):
            raise FileNotFoundError(f"missing model for {h}h: {p}")
        return p

    # init state：建议用 smoke 输出作为初值（更合理也更稳定）
    if args.init_pressure and args.init_surface:
        pressure = np.load(args.init_pressure)
        surface = np.load(args.init_surface)
    else:
        pressure = np.random.randn(5, 13, 721, 1440).astype(np.float32)
        surface = np.random.randn(4, 721, 1440).astype(np.float32)

    use_cuda = (args.providers == "cuda")

    report = {
        "schedule": args.schedule,
        "models_root": args.models_root,
        "output_dir": args.output_dir,
        "providers_requested": args.providers,
        "steps": [],
    }

    # session cache：每个 horizon 的模型只建一次（避免重复占用/碎片）
    sessions = {}

    cum = 0
    for i, h in enumerate(args.schedule, start=1):
        cum += h
        mp = model_of(h)

        if h not in sessions:
            sessions[h] = make_session(mp, use_cuda)

        print(f"[Day4] step {i}/{len(args.schedule)}  (+{h}h => t+{cum}h)  model={os.path.basename(mp)}")

        r = run_one(sessions[h], pressure, surface)

        if np.isnan(r["out_pressure"]).any() or np.isnan(r["out_surface"]).any():
            raise RuntimeError(f"NaN detected at step {i} (+{h}h)")

        p_path = os.path.join(args.output_dir, f"t+{cum:03d}h_pressure.npy")
        s_path = os.path.join(args.output_dir, f"t+{cum:03d}h_surface.npy")
        np.save(p_path, r["out_pressure"])
        np.save(s_path, r["out_surface"])

        step_item = {
            "step": i,
            "h": h,
            "t_plus_h": cum,
            "model": os.path.basename(mp),
            "providers_actual": r["providers_actual"],
            "dt_sec": r["dt_sec"],
            "pressure_shape": list(r["out_pressure"].shape),
            "surface_shape": list(r["out_surface"].shape),
            "pressure_sha256": sha256_file(p_path),
            "surface_sha256": sha256_file(s_path),
        }
        report["steps"].append(step_item)

        # 每一步都落盘（方便你看进度+中断可追踪）
        report_path = os.path.join(args.output_dir, "day4_rollout_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        pressure, surface = r["out_pressure"], r["out_surface"]

    print(f"[OK] wrote {os.path.join(args.output_dir, 'day4_rollout_report.json')}")


if __name__ == "__main__":
    main()
