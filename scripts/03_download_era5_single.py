import argparse, os, time
import cdsapi

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default="20230709")  # YYYYMMDD
    p.add_argument("--hour", default="00")        # HH
    p.add_argument("--out-dir", default="/root/autodl-tmp/pangu-weather-repro/era5_raw")
    args = p.parse_args()

    y, m, d = args.date[:4], args.date[4:6], args.date[6:8]
    os.makedirs(args.out_dir, exist_ok=True)
    target = os.path.join(args.out_dir, f"era5_single_{args.date}{args.hour}.nc")

    variables = [
        "2m_temperature",
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "mean_sea_level_pressure",
        "surface_pressure",
    ]

    c = cdsapi.Client()
    req = {
        "product_type": "reanalysis",
        "format": "netcdf",
        "variable": variables,
        "year": y,
        "month": m,
        "day": d,
        "time": [f"{args.hour}:00"],
    }

    # 简单重试
    for i in range(3):
        try:
            c.retrieve("reanalysis-era5-single-levels", req, target)
            print("saved:", target, "size:", os.path.getsize(target))
            return
        except Exception as e:
            print(f"[retry {i+1}/3] failed:", e)
            time.sleep(10)
    raise SystemExit("download failed after retries")

if __name__ == "__main__":
    main()
