"""Day2 validate processed inputs.

Goal: Check surface/pressure arrays against contract.
Inputs: surface.npy and pressure.npy under PROCESSED_ROOT.
Outputs: Console validation report.
Example: uv run python scripts/05_validate_inputs.py --processed-dir "$PROCESSED_ROOT"
"""
import argparse
import os

import numpy as np

from pangu_weather_repro.contracts import validate_surface, validate_upper


def main() -> None:
    p = argparse.ArgumentParser(description="Validate processed inputs against contracts")
    p.add_argument(
        "--processed-dir",
        default=os.environ.get("PROCESSED_ROOT", "/root/autodl-tmp/pangu-weather-repro/processed"),
    )
    args = p.parse_args()

    surface_path = os.path.join(args.processed_dir, "surface.npy")
    pressure_path = os.path.join(args.processed_dir, "pressure.npy")
    if not os.path.exists(surface_path):
        raise FileNotFoundError(
            f"missing surface.npy: {surface_path}. Run scripts/04_preprocess_era5_to_npy.py first."
        )
    if not os.path.exists(pressure_path):
        raise FileNotFoundError(
            f"missing pressure.npy: {pressure_path}. Run scripts/04_preprocess_era5_to_npy.py first."
        )
    surface = np.load(surface_path).astype(np.float32)
    pressure = np.load(pressure_path).astype(np.float32)

    validate_surface(surface, allow_time_dim=True)
    validate_upper(pressure, allow_time_dim=True)

    print("✅ Input validation passed")
    print("surface:", surface.shape)
    print("pressure:", pressure.shape)


if __name__ == "__main__":
    main()
