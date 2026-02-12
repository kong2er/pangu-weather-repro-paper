"""Day4 single-step ONNX inference.

Goal: Run a single ONNX step and log outputs for debugging.
Inputs: processed surface/pressure npy and a 6h ONNX model.
Outputs: output npy files and meta/log under OUTPUT_ROOT.
Example: python tools/legacy/day4_infer_onnx.py
"""
import os, json, time, hashlib
import numpy as np
import onnxruntime as ort

from pangu_weather_repro.contracts import build_feed_dict, InputSpec, validate_feed_against_onnx_inputs
WORK = "/root/autodl-tmp/pangu-weather-repro"
MODEL = f"{WORK}/models/pangu_weather_6.onnx"
P_PATH = f"{WORK}/processed/pressure.npy"
S_PATH = f"{WORK}/processed/surface.npy"

RUN_ID = time.strftime("%Y%m%d%H%M%S")
OUT_DIR = f"{WORK}/outputs/day4_{RUN_ID}"
LOG_DIR = f"{WORK}/logs"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = f"{LOG_DIR}/day4_{RUN_ID}.log"
META_PATH = f"{OUT_DIR}/meta.json"

def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def stats(x: np.ndarray):
    return dict(
        shape=list(x.shape), dtype=str(x.dtype),
        nan=bool(np.isnan(x).any()),
        min=float(np.nanmin(x)), max=float(np.nanmax(x)),
        mean=float(np.nanmean(x)), std=float(np.nanstd(x)),
    )

def log(msg: str):
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def main():
    log(f"[info] model={MODEL}")
    log(f"[info] pressure={P_PATH}")
    log(f"[info] surface={S_PATH}")

    sess = ort.InferenceSession(MODEL, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])

    in_specs = {i.name: i for i in sess.get_inputs()}
    out_specs = sess.get_outputs()

    log("[model] inputs:")
    for i in sess.get_inputs():
        log(f"  - {i.name} shape={i.shape} type={i.type}")
    log("[model] outputs:")
    for o in out_specs:
        log(f"  - {o.name} shape={o.shape} type={o.type}")

    assert "input" in in_specs and "input_surface" in in_specs, f"unexpected input names: {list(in_specs)}"

    pressure = np.load(P_PATH).astype(np.float32, copy=False)
    surface  = np.load(S_PATH).astype(np.float32, copy=False)

    if np.isnan(pressure).any():
        raise ValueError("pressure contains NaN")
    if np.isnan(surface).any():
        raise ValueError("surface contains NaN")

    feed = build_feed_dict(pressure, surface)
    specs = [InputSpec(name=i.name, shape=tuple(i.shape)) for i in sess.get_inputs()]
    validate_feed_against_onnx_inputs(feed, specs)
    log(f"[feed] input shape={feed['input'].shape} dtype={feed['input'].dtype}")
    log(f"[feed] input_surface shape={feed['input_surface'].shape} dtype={feed['input_surface'].dtype}")

    t0 = time.time()
    outs = sess.run(None, feed)
    dt = time.time() - t0
    log(f"[perf] inference_sec={dt:.3f}")

    saved = []
    for spec, arr in zip(out_specs, outs):
        path = f"{OUT_DIR}/{spec.name}.npy"
        np.save(path, arr)
        saved.append({"name": spec.name, "path": path, **stats(arr)})
        log(f"[save] {spec.name} -> {path} shape={arr.shape}")

    meta = {
        "run_id": f"day4_{RUN_ID}",
        "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": {"path": MODEL, "sha256": sha256(MODEL)},
        "inputs": {
            "pressure": {"path": P_PATH, "sha256": sha256(P_PATH), **stats(pressure)},
            "surface":  {"path": S_PATH, "sha256": sha256(S_PATH), **stats(surface)},
        },
        "applied_fixes": {"pressure": None, "surface": None},
        "providers": sess.get_providers(),
        "inference_sec": dt,
        "outputs": saved,
        "log_path": LOG_PATH,
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    log(f"[meta] written: {META_PATH}")

if __name__ == "__main__":
    main()
