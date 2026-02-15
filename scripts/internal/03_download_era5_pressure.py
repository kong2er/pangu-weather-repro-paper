import argparse, os, time, ssl
try:
    import cdsapi
except Exception as exc:
    raise RuntimeError(
        "cdsapi is required. Run: scripts/install_extras.sh download"
    ) from exc

def _try_retrieve(client_kwargs, dataset, req, target, retries=3):
    """Try to retrieve with given client kwargs, return True on success."""
    c = cdsapi.Client(**client_kwargs)
    for i in range(retries):
        try:
            c.retrieve(dataset, req, target)
            print("saved:", target)
            print("size:", os.path.getsize(target))
            return True
        except Exception as e:
            is_ssl = "SSL" in str(e) or "CERTIFICATE" in str(e)
            if is_ssl and i == 0:
                # SSL error on first attempt -> signal caller to retry with verify=0
                return False
            print(f"[retry {i+1}/{retries}] failed: {e}")
            time.sleep(10)
    return False

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

    # Try with normal SSL first; if cert error, retry with verify disabled
    if _try_retrieve({}, "reanalysis-era5-pressure-levels", req, target):
        return
    print("[WARN] SSL certificate error, retrying with verify=False ...")
    if _try_retrieve({"verify": 0}, "reanalysis-era5-pressure-levels", req, target):
        return

    raise SystemExit("download failed after retries")

if __name__ == "__main__":
    main()
