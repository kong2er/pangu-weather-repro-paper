# E Stage Report（E阶段对齐验收）

## Summary
- streamlit_app_files: true
- product_bundle_cli: true
- product_bundle_check: skipped
- product_bundle_note: rollout dir missing, config missing, or product cli/runner unavailable

## Paths
- app entry: /home/kongkong/projects/pangu-weather-repro-paper/pangu_weather_repro/app/app.py
- plots page: /home/kongkong/projects/pangu-weather-repro-paper/pangu_weather_repro/app/pages/Plots.py
- product cli: /home/kongkong/projects/pangu-weather-repro-paper/tools/plot_product_bundle.py
- product script: /home/kongkong/projects/pangu-weather-repro-paper/scripts/run_product_bundle.sh
- rollout_dir: /root/autodl-tmp/pangu-weather-repro/outputs/day4_rollout_30h

## Product Outputs
- png_count: 0
- json_count: 0

## Quick Commands
```bash
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
bash scripts/run_product_bundle.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500,t2m,u10,v10,msl --hours 24,30
```

## Next
- 如果 product_bundle_check=failed：先执行 `bash scripts/install_extras.sh plots`，再重试本脚本
- 如果 rollout 缺失：先完成 Day4 产物，再运行本脚本
