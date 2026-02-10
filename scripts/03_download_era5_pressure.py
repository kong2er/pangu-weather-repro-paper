import argparse, os, time
try:
    import cdsapi
except Exception as exc:
    raise RuntimeError(
        "cdsapi is required. Run: scripts/install_extras.sh download"
    ) from exc

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--date", default="20230709")
    p.add_argument("--hour", default="00")
    p.add_argument("--out-dir", default="/root/autodl-tmp/pangu-weather-repro/era5_raw")
    args = p.parse_args()

    y, m, d = args.date[:4], args.date[4:6], args.date[6:8]
    os.makedirs(args.out_dir, exist_ok=True)
    target = os.path.join(args.out_dir, f"era5_pressure_{args.date}{args.hour}.nc")

    levels = ["1000","925","850","700","600","500","400","300","250","200","150","100","50"]
    variables = [
        "geopotential",
        "temperature",
        "u_component_of_wind",
        "v_component_of_wind",
        "specific_humidity",
    ]

    c = cdsapi.Client()
    req = {
        "product_type": "reanalysis",
        "format": "netcdf",
        "variable": variables,
        "pressure_level": levels,
        "year": y,
        "month": m,
        "day": d,
        "time": [f"{args.hour}:00"],
    }

    for i in range(3):
        try:
            c.retrieve("reanalysis-era5-pressure-levels", req, target)
            print("saved:", target)
            print("size:", os.path.getsize(target))
            return
        except Exception as e:
            print(f"[retry {i+1}/3] failed: {e}")
            time.sleep(10)

    raise SystemExit("download failed after retries")

if __name__ == "__main__":
    main()
