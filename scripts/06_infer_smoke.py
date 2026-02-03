import os, argparse, json, hashlib
import numpy as np
import onnxruntime as ort
import os

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

# === REPRO PATCH: providers + feed mapping (idempotent) ===
def _resolve_model_path(step: int) -> str:
    mp = os.environ.get("MODEL_PATH")
    if mp:
        return mp
    mr = os.environ.get("MODELS_ROOT")
    if not mr:
        raise RuntimeError("MODEL_PATH not set and MODELS_ROOT missing; please source configs/default.env")
    return os.path.join(mr, f"pangu_weather_{step}.onnx")

def _resolve_providers():
    """
    Prefer GPU if available, otherwise fall back to CPU.
    You can force CPU by setting FORCE_CPU=1 in env.
    """
    try:
        import onnxruntime as ort
        avail = ort.get_available_providers()
    except Exception:
        return ["CPUExecutionProvider"]

    if os.environ.get("FORCE_CPU", "").strip() == "1":
        return ["CPUExecutionProvider"]

    # Prefer CUDA if present; keep CPU fallback for reproducibility
    if "CUDAExecutionProvider" in avail:
        return ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return ["CPUExecutionProvider"]

def _fix_swapped_feed(sess, feed: dict) -> dict:
    """
    Fix the known issue: 'input' and 'input_surface' may be swapped.
    We detect by matching shapes against model expected shapes.
    """
    try:
        exp = {i.name: tuple(i.shape) for i in sess.get_inputs()}
        got_in = tuple(getattr(feed.get("input"), "shape", ()))
        got_sfc = tuple(getattr(feed.get("input_surface"), "shape", ()))
        if ("input" in feed and "input_surface" in feed and
            got_in == exp.get("input_surface") and got_sfc == exp.get("input")):
            feed = dict(feed)
            feed["input"], feed["input_surface"] = feed["input_surface"], feed["input"]
    except Exception:
        pass
    return feed
# === END REPRO PATCH ===


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models-dir", default=os.environ.get("MODELS_ROOT", "/root/autodl-tmp/pangu-weather-repro/models"))
    p.add_argument("--processed-dir", default=os.environ.get("PROCESSED_ROOT", "/root/autodl-tmp/pangu-weather-repro/processed"))
    p.add_argument("--out-dir", default=os.environ.get("OUTPUT_ROOT", "/root/autodl-tmp/pangu-weather-repro/outputs"))
    p.add_argument("--step", choices=["6", "24"], default="6", help="smoke step hours")
    p.add_argument("--use-gpu", action="store_true")
    p.add_argument("--threads", type=int, default=int(os.environ.get("OMP_NUM_THREADS", "1")))
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    surface = np.load(os.path.join(args.processed_dir, "surface.npy")).astype(np.float32)
    pressure = np.load(os.path.join(args.processed_dir, "pressure.npy")).astype(np.float32)

    # squeeze time dim (your current files are (C,1,H,W) and (C,1,L,H,W))
    if surface.ndim == 4 and surface.shape[1] == 1:
        surface = surface[:, 0]
    if pressure.ndim == 5 and pressure.shape[1] == 1:
        pressure = pressure[:, 0]

    model_name = f"pangu_weather_{args.step}.onnx"
    model_path = os.path.join(args.models_dir, model_name)
    if not os.path.exists(model_path):
        raise FileNotFoundError(model_path)

    so = ort.SessionOptions()
    so.intra_op_num_threads = args.threads
    so.inter_op_num_threads = 1

    providers = ["CPUExecutionProvider"]
    if args.use_gpu:
        # prefer CUDA, fall back to CPU
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

    model_path = _resolve_model_path(args.step)

    providers = _resolve_providers()

    sess = ort.InferenceSession(model_path, providers=providers)

    ins = sess.get_inputs()
    outs = sess.get_outputs()

    # Map inputs by name heuristics
    feed = {}
    for i in ins:
        name = i.name.lower()
        if "surface" in name:
            feed[i.name] = surface
        elif "upper" in name or "pressure" in name:
            feed[i.name] = pressure
        else:
            # last resort: fill in order (surface first, then pressure)
            pass

    # Fallback: if names unknown, feed by index order
    if len(feed) != len(ins):
        feed = {ins[0].name: surface, ins[1].name: pressure}

    out_names = [o.name for o in outs]
    feed = _fix_swapped_feed(sess, feed)
    y = sess.run(out_names, feed)

    # Save npy outputs (smoke stage)
    out_files = []
    for name, arr in zip(out_names, y):
        fn = os.path.join(args.out_dir, f"smoke_{args.step}h_{name}.npy")
        np.save(fn, np.asarray(arr))
        out_files.append(fn)

    report = {
        "model": model_name,
        "providers_used": sess.get_providers(),
        "surface_shape": list(surface.shape),
        "pressure_shape": list(pressure.shape),
        "outputs": [{"name": n, "shape": list(np.asarray(a).shape)} for n, a in zip(out_names, y)],
        "files": {os.path.basename(f): sha256_file(f) for f in out_files},
    }
    rep_path = os.path.join(args.out_dir, f"smoke_{args.step}h_report.json")
    with open(rep_path, "w") as f:
        json.dump(report, f, indent=2)
    print("✅ smoke ok, wrote:", rep_path)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
