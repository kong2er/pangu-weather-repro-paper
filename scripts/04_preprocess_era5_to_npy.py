import os
import argparse
import numpy as np
import netCDF4 as nc


def load_surface(path):
    ds = nc.Dataset(path)

    t2m = ds["t2m"][:].filled(np.nan)  # 使用 .filled() 方法填充缺失值
    u10 = ds["u10"][:].filled(np.nan)
    v10 = ds["v10"][:].filled(np.nan)
    msl = ds["msl"][:].filled(np.nan)

    surface = np.stack([msl, u10, v10, t2m], axis=0)

    print("surface shape:", surface.shape)
    return surface.astype(np.float32)


def load_pressure(path):
    ds = nc.Dataset(path)

    z = ds["z"][:].filled(np.nan)
    q = ds["q"][:].filled(np.nan)
    t = ds["t"][:].filled(np.nan)
    u = ds["u"][:].filled(np.nan)
    v = ds["v"][:].filled(np.nan)

    pressure = np.stack([z, q, t, u, v], axis=0)

    print("pressure shape:", pressure.shape)
    return pressure.astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="20230709")
    parser.add_argument("--hour", default="00")
    parser.add_argument("--raw-dir", default="/root/autodl-tmp/pangu-weather-repro/era5_raw")
    parser.add_argument("--out-dir", default="/root/autodl-tmp/pangu-weather-repro/processed")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    single_path = f"{args.raw_dir}/era5_single_{args.date}{args.hour}.nc"
    pressure_path = f"{args.raw_dir}/era5_pressure_{args.date}{args.hour}.nc"

    surface = load_surface(single_path)
    pressure = load_pressure(pressure_path)

    np.save(f"{args.out_dir}/surface.npy", surface)
    np.save(f"{args.out_dir}/pressure.npy", pressure)

    print("✅ Saved to:", args.out_dir)


if __name__ == "__main__":
    main()
