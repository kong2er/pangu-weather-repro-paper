# Repo Sanitize Plan（Step1 扫描与重构映射）

## 1) 当前目录概览（2~3层）
- `pangu_weather_repro/`：包代码（infer/region/visualization/app）
- `scripts/`：复现入口脚本（环境、分阶段执行、验证）
- `tools/`：高级 CLI 工具（forecast/plot/eval/dayX）
- `docs/`：对齐报告与运行说明
- `tests/`：单元测试
- `artifacts/`：阶段报告与轻量产物
- `figures/`：运行生成图（当前含 day6/day7）
- `outputs/`：运行输出（仓库内仅保留占位）

## 2) 混乱来源清单
1. 运行产物被提交：`figures/day6/*.png`、`figures/day7/*.png`、`artifacts/day5/rmse.csv`、`artifacts/day7/metrics_summary.csv`。
2. `scripts/` 与 `tools/` 边界不清，存在 dayX 试验脚本与正式入口并存。
3. 缺少 `figures/outputs` 目录的占位说明，复现者容易把运行产物继续提交。

## 3) 重构映射表（先止血，后归位）
- 运行产物：`git rm --cached` 取消跟踪，保留本地文件。
- 目录占位：增加 `figures/.gitkeep`、`figures/README.md`、`outputs/.gitkeep`、`outputs/README.md`。
- 忽略规则：在 `.gitignore` 固化 `figures/*`、`outputs/*`、`artifacts/day5/*`、`artifacts/day7/*.csv`，并对白名单占位文件放行。
- 后续（Step3+）：将非官方入口脚本逐步归档到 `tools/legacy/`，`scripts/` 仅保留官方入口（不在本次提交执行）。

## 4) 不破坏约束
- 不改核心推理/评估/绘图算法。
- 不删除任何可运行链路依赖脚本。
- 默认不覆盖产物行为保持不变。
