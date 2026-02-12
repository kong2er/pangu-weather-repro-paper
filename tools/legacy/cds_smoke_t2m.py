import os, cdsapi
date = "20230709"
hour = "00"
out = "/root/autodl-tmp/pangu-weather-repro/era5_raw"
os.makedirs(out, exist_ok=True)
target = os.path.join(out, f"smoke_t2m_{date}{hour}.nc")

c = cdsapi.Client()
c.retrieve(
  "reanalysis-era5-single-levels",
  {
    "product_type": "reanalysis",
    "format": "netcdf",
    "variable": ["2m_temperature"],
    "year": "2023",
    "month": "07",
    "day": "09",
    "time": ["00:00"],
  },
  target
)
print("saved:", target)
print("size:", os.path.getsize(target))
