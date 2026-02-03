import os
import runpy
import onnxruntime as ort

# ---- session options: bypass BFCArena limitations ----
so = ort.SessionOptions()
so.enable_cpu_mem_arena = False       # critical: bypass CPU BFCArena pool cap/fragmentation
so.enable_mem_pattern = False         # reduce big preplanned allocations
so.enable_mem_reuse = False           # reduce peak spikes due to reuse planning

# (optional) stability: avoid huge parallelism side effects
so.intra_op_num_threads = int(os.environ.get("ORT_INTRA_OP", "1"))
so.inter_op_num_threads = int(os.environ.get("ORT_INTER_OP", "1"))

ARENA_STRATEGY = os.environ.get("ORT_ARENA_EXTEND_STRATEGY", "kNextPowerOfTwo")
CUDNN_SEARCH   = os.environ.get("ORT_CUDNN_ALGO_SEARCH", "DEFAULT")

cuda_provider_options = {
    # don't set gpu_mem_limit here; let it use full VRAM
    "arena_extend_strategy": ARENA_STRATEGY,
    "cudnn_conv_algo_search": CUDNN_SEARCH,
    "do_copy_in_default_stream": "1",
    "enable_cuda_graph": "0",
    "tunable_op_enable": "0",
}

providers = [
    ("CUDAExecutionProvider", cuda_provider_options),
    "CPUExecutionProvider",
]

# ---- Force providers and session options into any InferenceSession created by the script ----
_orig_init = ort.InferenceSession.__init__
def patched_init(self, *args, **kwargs):
    kwargs["providers"] = providers
    kwargs["sess_options"] = so
    return _orig_init(self, *args, **kwargs)
ort.InferenceSession.__init__ = patched_init

# ---- Auto-fix swapped inputs (rank bug you hit earlier) ----
_orig_run = ort.InferenceSession.run
def patched_run(self, output_names, input_feed, *args, **kwargs):
    try:
        exp = {i.name: tuple(i.shape) for i in self.get_inputs()}
        got_in = tuple(getattr(input_feed.get("input"), "shape", ()))
        got_sfc = tuple(getattr(input_feed.get("input_surface"), "shape", ()))
        if ("input" in input_feed and "input_surface" in input_feed and
            got_in == exp.get("input_surface") and got_sfc == exp.get("input")):
            input_feed = dict(input_feed)
            input_feed["input"], input_feed["input_surface"] = input_feed["input_surface"], input_feed["input"]
    except Exception:
        pass
    return _orig_run(self, output_names, input_feed, *args, **kwargs)
ort.InferenceSession.run = patched_run

runpy.run_path("scripts/06_infer_smoke.py", run_name="__main__")
