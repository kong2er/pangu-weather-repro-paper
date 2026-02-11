"""Forecast page for Streamlit skeleton."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


def _ort_info() -> str:
    try:
        import onnxruntime as ort

        return str(ort.get_available_providers())
    except Exception as exc:
        return f"onnxruntime unavailable: {exc}"


st.title("Forecast")
root_dir = Path(__file__).resolve().parents[3]
models_root = Path(os.environ.get("MODELS_ROOT", str(root_dir / "models")))
processed_root = Path(os.environ.get("PROCESSED_ROOT", str(root_dir / "processed")))

st.write("Models root:", str(models_root))
st.write("Processed root:", str(processed_root))
st.write("ORT providers:", _ort_info())

checks = {
    "pangu_weather_1.onnx": (models_root / "pangu_weather_1.onnx").exists(),
    "pangu_weather_3.onnx": (models_root / "pangu_weather_3.onnx").exists(),
    "pangu_weather_6.onnx": (models_root / "pangu_weather_6.onnx").exists(),
    "pangu_weather_24.onnx": (models_root / "pangu_weather_24.onnx").exists(),
}
st.subheader("Model Presence")
st.write(checks)
