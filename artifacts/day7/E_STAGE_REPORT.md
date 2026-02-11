# E Stage Report（E阶段对齐验收）

## Summary
- streamlit_app_files: true
- product_bundle_cli: true
- product_bundle_check: ok
- product_bundle_note: ran product bundle (z500, t+24)
- product_vector_check: ok
- product_msl_wind_check: ok
- product_wind_speed_check: ok
- product_extent_check: ok

## Paths
- app entry: /root/projects/pangu-weather-repro-uv/pangu_weather_repro/app/app.py
- plots page: /root/projects/pangu-weather-repro-uv/pangu_weather_repro/app/pages/Plots.py
- product cli: /root/projects/pangu-weather-repro-uv/tools/plot_product_bundle.py
- product script: /root/projects/pangu-weather-repro-uv/scripts/run_product_bundle.sh
- rollout_dir: /root/autodl-tmp/pangu-weather-repro/outputs/day4_rollout_30h

## Product Outputs
- png_count: 19
- json_count: 19

## Quick Commands
```bash
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500,t2m,u10,v10,msl --hours 24,30
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars u10 --hours 24,30 --kinds vector,wind_speed,msl_wind
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500 --hours 24 --kinds fill --extent 95,145,10,50 --force
```

## Next
- 如果 product_bundle_check=failed：先执行 `bash scripts/install_extras.sh plots`，再重试本脚本
- 如果 product_vector_check=failed 或 product_msl_wind_check=failed：先执行 `bash scripts/install_extras.sh plots --force`，再重试本脚本
- 如果 product_wind_speed_check=failed：先执行 `bash scripts/install_extras.sh plots --force`，再重试本脚本
- 如果 product_extent_check=failed：先确认命令中的 `--extent` 为 4 个值（lon_min,lon_max,lat_min,lat_max）
- 如果 rollout 缺失：先完成 Day4 产物，再运行本脚本
