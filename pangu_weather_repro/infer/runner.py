"""Forecast runner supporting short/long rollouts and multi-step models."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np

from .scheduler import Schedule


@dataclass
class ForecastResult:
    out_dir: str
    hours: int
    steps: List[int]
    report_path: str


class ForecastRunner:
    def __init__(
        self,
        models_dir: str,
        use_gpu: bool = True,
        threads: int = 1,
        noarena: bool = False,
        gpu_mem_limit_mb: int | None = None,
        cache_sessions: bool = True,
    ) -> None:
        self.models_dir = models_dir
        self.use_gpu = use_gpu
        self.threads = threads
        self.noarena = noarena
        self.gpu_mem_limit_mb = gpu_mem_limit_mb
        self.cache_sessions = cache_sessions
        self._sessions: Dict[int, "ort.InferenceSession"] = {}

    def _ensure_ort(self):
        try:
            import onnxruntime as ort  # noqa: F401
        except Exception as exc:
            raise RuntimeError(
                "onnxruntime is required. Run: scripts/install_gpu_deps.sh (GPU) "
                "or install CPU extra."
            ) from exc

    def _resolve_model_path(self, step: int) -> str:
        name = f"pangu_weather_{step}.onnx"
        path = os.path.join(self.models_dir, name)
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"model not found: {path}. Set MODELS_ROOT or pass --models-dir to point at ONNX models."
            )
        return path

    def _session_options(self):
        import onnxruntime as ort

        so = ort.SessionOptions()
        so.intra_op_num_threads = self.threads
        so.inter_op_num_threads = 1
        so.enable_cpu_mem_arena = False
        so.enable_mem_pattern = False
        so.enable_mem_reuse = False
        return so

    def _providers(self) -> List:
        if not self.use_gpu:
            return ["CPUExecutionProvider"]
        cuda_provider_options = {
            "arena_extend_strategy": os.environ.get("ORT_ARENA_EXTEND_STRATEGY", "kSameAsRequested"),
            "cudnn_conv_algo_search": os.environ.get("ORT_CUDNN_ALGO_SEARCH", "HEURISTIC"),
            "do_copy_in_default_stream": "1",
            "enable_cuda_graph": "0",
            "tunable_op_enable": "0",
        }
        if self.gpu_mem_limit_mb and self.gpu_mem_limit_mb > 0:
            cuda_provider_options["gpu_mem_limit"] = str(self.gpu_mem_limit_mb * 1024 * 1024)
        return [("CUDAExecutionProvider", cuda_provider_options), "CPUExecutionProvider"]

    def _get_session(self, step: int):
        self._ensure_ort()
        if self.cache_sessions and step in self._sessions:
            return self._sessions[step]
        import onnxruntime as ort

        path = self._resolve_model_path(step)
        sess = ort.InferenceSession(path, sess_options=self._session_options(), providers=self._providers())
        if self.cache_sessions:
            self._sessions[step] = sess
        return sess

    @staticmethod
    def _load_inputs(processed_dir: str) -> Tuple[np.ndarray, np.ndarray]:
        surface_path = os.path.join(processed_dir, "surface.npy")
        pressure_path = os.path.join(processed_dir, "pressure.npy")
        if not os.path.exists(surface_path):
            raise FileNotFoundError(
                f"missing surface.npy: {surface_path}. Run scripts/04_preprocess_era5_to_npy.py."
            )
        if not os.path.exists(pressure_path):
            raise FileNotFoundError(
                f"missing pressure.npy: {pressure_path}. Run scripts/04_preprocess_era5_to_npy.py."
            )
        surface = np.load(surface_path).astype(np.float32)
        pressure = np.load(pressure_path).astype(np.float32)
        if surface.ndim == 4 and surface.shape[1] == 1:
            surface = surface[:, 0]
        if pressure.ndim == 5 and pressure.shape[1] == 1:
            pressure = pressure[:, 0]
        return pressure, surface

    @staticmethod
    def _map_inputs(sess, pressure: np.ndarray, surface: np.ndarray) -> Dict[str, np.ndarray]:
        ins = sess.get_inputs()
        feed: Dict[str, np.ndarray] = {}
        for i in ins:
            name = i.name.lower()
            if "surface" in name:
                feed[i.name] = surface
            elif "upper" in name or "pressure" in name or "input" in name:
                feed[i.name] = pressure

        if len(feed) != len(ins):
            feed = {ins[0].name: pressure, ins[1].name: surface} if len(ins) >= 2 else {ins[0].name: pressure}

        return feed

    @staticmethod
    def _split_outputs(sess, outputs: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        names = [o.name.lower() for o in sess.get_outputs()]
        pressure = None
        surface = None
        for name, arr in zip(names, outputs):
            if "surface" in name:
                surface = arr
            else:
                pressure = arr
        if pressure is None and outputs:
            pressure = outputs[0]
        if surface is None and len(outputs) > 1:
            surface = outputs[1]
        if pressure is None or surface is None:
            raise RuntimeError("Failed to split outputs (pressure/surface)")
        return pressure, surface

    def run_schedule(
        self,
        schedule: Schedule,
        processed_dir: str,
        out_dir: str,
        save_hours: Iterable[int],
        force: bool = False,
        save_all: bool = False,
    ) -> ForecastResult:
        if os.path.exists(out_dir) and not force:
            raise FileExistsError(f"out_dir exists: {out_dir}. Use --force to overwrite.")
        os.makedirs(out_dir, exist_ok=True)

        pressure, surface = self._load_inputs(processed_dir)
        hours = 0
        steps = []
        records = []
        save_hours_set = set(int(h) for h in save_hours)

        for step in schedule.steps:
            sess = self._get_session(step)
            outputs = sess.run(None, self._map_inputs(sess, pressure, surface))
            pressure, surface = self._split_outputs(sess, outputs)

            hours += step
            steps.append(step)
            record = {
                "step": step,
                "hour": hours,
                "providers": sess.get_providers(),
            }
            records.append(record)

            if save_all or hours in save_hours_set:
                np.save(os.path.join(out_dir, f"rollout_pressure_{hours}h.npy"), np.asarray(pressure))
                np.save(os.path.join(out_dir, f"rollout_surface_{hours}h.npy"), np.asarray(surface))

            if not self.cache_sessions:
                # release session to avoid GPU memory accumulation
                try:
                    del sess
                except Exception:
                    pass

        report = {
            "total_hours": hours,
            "steps": steps,
            "providers_used": records[-1]["providers"] if records else [],
            "records": records,
            "processed_dir": processed_dir,
            "models_dir": self.models_dir,
        }
        report_path = os.path.join(out_dir, "forecast_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return ForecastResult(out_dir=out_dir, hours=hours, steps=steps, report_path=report_path)
