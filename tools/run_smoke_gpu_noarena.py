"""GPU smoke wrapper with no-arena session options.

Goal: Run scripts/internal/06_infer_smoke.py with safer ORT settings on GPU.
Inputs: Environment from configs/default.env and ONNX models in MODELS_ROOT.
Outputs: smoke report and output npy files under OUTPUT_ROOT.
Example: uv run python tools/run_smoke_gpu_noarena.py --script scripts/internal/06_infer_smoke.py
"""
from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    p = argparse.ArgumentParser()
    p.add_argument("--script", default="scripts/internal/06_infer_smoke.py")
    args, rest = p.parse_known_args()

    try:
        import onnxruntime as ort
    except Exception as exc:
        raise RuntimeError(
            "onnxruntime is required for GPU smoke. "
            "Try: scripts/create_gpu_venv.sh --update"
        ) from exc

    # ---- session options: bypass BFCArena limitations ----
    so = ort.SessionOptions()
    so.enable_cpu_mem_arena = False
    so.enable_mem_pattern = False
    so.enable_mem_reuse = False

    so.intra_op_num_threads = int(os.environ.get("ORT_INTRA_OP", "1"))
    so.inter_op_num_threads = int(os.environ.get("ORT_INTER_OP", "1"))

    arena_strategy = os.environ.get("ORT_ARENA_EXTEND_STRATEGY", "kNextPowerOfTwo")
    cudnn_search = os.environ.get("ORT_CUDNN_ALGO_SEARCH", "DEFAULT")

    cuda_provider_options = {
        "arena_extend_strategy": arena_strategy,
        "cudnn_conv_algo_search": cudnn_search,
        "do_copy_in_default_stream": "1",
        "enable_cuda_graph": "0",
        "tunable_op_enable": "0",
    }

    providers = [
        ("CUDAExecutionProvider", cuda_provider_options),
        "CPUExecutionProvider",
    ]

    _orig_init = ort.InferenceSession.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["providers"] = providers
        kwargs["sess_options"] = so
        return _orig_init(self, *args, **kwargs)

    ort.InferenceSession.__init__ = patched_init

    _orig_run = ort.InferenceSession.run

    def patched_run(self, output_names, input_feed, *args, **kwargs):
        try:
            exp = {i.name: tuple(i.shape) for i in self.get_inputs()}
            got_in = tuple(getattr(input_feed.get("input"), "shape", ()))
            got_sfc = tuple(getattr(input_feed.get("input_surface"), "shape", ()))
            if (
                "input" in input_feed
                and "input_surface" in input_feed
                and got_in == exp.get("input_surface")
                and got_sfc == exp.get("input")
            ):
                input_feed = dict(input_feed)
                input_feed["input"], input_feed["input_surface"] = (
                    input_feed["input_surface"],
                    input_feed["input"],
                )
        except Exception:
            pass
        return _orig_run(self, output_names, input_feed, *args, **kwargs)

    ort.InferenceSession.run = patched_run

    sys.argv = [args.script] + rest
    try:
        runpy.run_path(args.script, run_name="__main__")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Import failed. Use scripts/run_gpu.sh to set PYTHONPATH/LD_LIBRARY_PATH."
        ) from exc


if __name__ == "__main__":
    main()
