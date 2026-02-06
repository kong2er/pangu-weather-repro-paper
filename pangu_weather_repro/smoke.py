from __future__ import annotations

import argparse
import json
import time

import numpy as np

from .contracts import (
    LAT_SIZE,
    LON_SIZE,
    PRESSURE_LEVELS,
    SURFACE_VARS,
    UPPER_VARS,
    InputSpec,
    build_feed_dict,
    validate_feed_against_onnx_inputs,
)


def _make_dummy_surface() -> np.ndarray:
    base = np.zeros((1,), dtype=np.float32)
    return np.broadcast_to(base, (len(SURFACE_VARS), 1, LAT_SIZE, LON_SIZE))


def _make_dummy_upper() -> np.ndarray:
    base = np.zeros((1,), dtype=np.float32)
    return np.broadcast_to(
        base, (len(UPPER_VARS), 1, len(PRESSURE_LEVELS), LAT_SIZE, LON_SIZE)
    )


def _mock_onnx_inputs():
    return [
        InputSpec(name="input", shape=(len(UPPER_VARS), len(PRESSURE_LEVELS), LAT_SIZE, LON_SIZE)),
        InputSpec(name="input_surface", shape=(len(SURFACE_VARS), LAT_SIZE, LON_SIZE)),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="CPU-only smoke test for contracts.")
    parser.add_argument("--json", action="store_true", help="print JSON report")
    args = parser.parse_args()

    t0 = time.time()
    surface = _make_dummy_surface()
    upper = _make_dummy_upper()

    if SURFACE_VARS != ("msl", "u10", "v10", "t2m"):
        raise ValueError(f"surface var order mismatch: {SURFACE_VARS}")
    if UPPER_VARS != ("z", "q", "t", "u", "v"):
        raise ValueError(f"upper var order mismatch: {UPPER_VARS}")

    feed = build_feed_dict(upper, surface)
    validate_feed_against_onnx_inputs(feed, _mock_onnx_inputs())

    report = {
        "status": "ok",
        "upper_shape": list(feed["input"].shape),
        "surface_shape": list(feed["input_surface"].shape),
        "elapsed_sec": round(time.time() - t0, 4),
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("✅ contracts smoke ok")
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
