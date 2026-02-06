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

    surface = np.load(os.path.join(args.processed_dir, "surface.npy")).astype(np.float32)
    pressure = np.load(os.path.join(args.processed_dir, "pressure.npy")).astype(np.float32)

    validate_surface(surface, allow_time_dim=True)
    validate_upper(pressure, allow_time_dim=True)

    print("✅ Input validation passed")
    print("surface:", surface.shape)
    print("pressure:", pressure.shape)


if __name__ == "__main__":
    main()
