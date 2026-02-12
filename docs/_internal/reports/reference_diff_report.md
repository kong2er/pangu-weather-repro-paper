# Reference Diff Report (zjobsdev/pangu)

## Summary
This report documents capability differences between this repo and zjobsdev/pangu.

## Reference Notes
See: docs/reference_pangu.md

## Alignment Status (本仓库 vs 参考仓库)
- 模型选择（1/3/6/24h）：已支持（tools/run_forecast.py + infer/scheduler）
- 1–84h 逐小时：已支持（mode=short）
- 84–360h 迭代：已支持（mode=long/full；建议使用 split）
- 论文级图：已支持（tools/plot_paper_bundle.py，输出 png+json）
- Region 适配：接口已实现（pangu_weather_repro/region + tools/region_demo.py）

## Gaps (still missing / partial)
- Streamlit UI（参考仓库提供，当前仅 CLI）
- 更完整的论文图样式对齐（地图风格/配色/变量范围可继续细化）
- 完整的 360h 端到端推理（受显存限制，推荐 split + no-cache）

## Recommended Runs
- 84h：scripts/run_gpu.sh tools/run_forecast.py --mode short --target-hours 84
- 360h：scripts/run_360h_split.sh
- 论文图：scripts/run_gpu.sh tools/plot_paper_bundle.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h"
