# Plot Alignment Report

- pred_dir: `figures/product`
- ref_dir: (not provided)
- total_png: 18

## Per-file
  - `product_diff_z500_t+024.png`, meta=ok, reference=not_found
  - `product_diff_z500_t+030.png`, meta=ok, reference=not_found
  - `product_msl_t+024.png`, meta=ok, reference=not_found
  - `product_msl_t+030.png`, meta=ok, reference=not_found
  - `product_msl_wind_t+024.png`, meta=ok, reference=not_found
  - `product_msl_wind_t+030.png`, meta=ok, reference=not_found
  - `product_t2m_t+024.png`, meta=ok, reference=not_found
  - `product_t2m_t+030.png`, meta=ok, reference=not_found
  - `product_u10_t+024.png`, meta=ok, reference=not_found
  - `product_u10_t+030.png`, meta=ok, reference=not_found
  - `product_v10_t+024.png`, meta=ok, reference=not_found
  - `product_v10_t+030.png`, meta=ok, reference=not_found
  - `product_vector_uv10_t+024.png`, meta=ok, reference=not_found
  - `product_vector_uv10_t+030.png`, meta=ok, reference=not_found
  - `product_wind_speed_t+024.png`, meta=ok, reference=not_found
  - `product_wind_speed_t+030.png`, meta=ok, reference=not_found
  - `product_z500_t+024.png`, meta=ok, reference=not_found
  - `product_z500_t+030.png`, meta=ok, reference=not_found

## Summary
- metadata_sanity_ok: 18
- metadata_sanity_fail: 0
- compared_with_reference: 0
- mse_mean: N/A
- psnr_mean: N/A
- note: provide --ref-dir with blueprint images to enable pixel-level comparison.

## Next
- 生成产品图：`bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force`
- 参考图比对：`scripts/run_gpu.sh tools/compare_plots_against_reference.py --pred-dir figures/product --ref-dir <blueprint_png_dir>`
