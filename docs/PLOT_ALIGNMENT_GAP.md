# Plot Alignment Gap (kong2er/pangu vs repro)

中文说明：
- 本文档只讨论“后处理 + 可视化层”的差异，不涉及推理模型与核心算法。
- 目标是把本仓库出图风格、标注与数值展示尽量对齐蓝本仓库 `~/projects/pangu`。

## A-H 差异表

| 维度 | 蓝本（kong2er/pangu） | 当前仓库（改造前） | 当前仓库（本次对齐后） |
|---|---|---|---|
| A) 单位处理 | 常见业务图直接展示业务单位（如 msl 常用 hPa） | `msl` 在部分图与元数据里混用 `Pa` 文案 | 统一展示层按样式转换：`msl` 显示为 `hPa`，并在 JSON 写入单位与统计 |
| B) 经纬度 | 区域化 extent 常见，网格线与边界配合 | 默认全局 `0..360/-90..90`，区域参数可用但风格不统一 | 支持 `--extent`，元数据记录 `extent_cli`，区域图流程统一 |
| C) 色标 | 变量有固定色阶/范围，业务风格稳定 | 多处 hardcode，变量间不一致 | 集中到 `visualization/style.py`：变量 cmap/vmin/vmax/levels 配置化 |
| D) 等值线 | 业务图常有等值线与标签 | 仅部分图有简单填色 | `msl_wind` 增加可配置等值线（levels/linewidth/label） |
| E) 风矢量 | 矢量密度与参数有业务化控制 | quiver 参数分散，抽稀不统一 | 统一 vector 配置（stride/scale/width/head 参数），并写入元数据 |
| F) 地理底图 | cartopy + 边界/网格较完整 | 依赖缺失时易报错 | 保留 `--with-geo`，并在缺 cartopy/scipy 时自动回退，不中断 |
| G) 标题/脚注 | 标题包含时效/变量/单位，信息完整 | 标题与单位格式不完全统一 | 标题统一为 `var t+XXX (unit)`；JSON 包含 style_profile/source/time |
| H) 输出尺寸与边距 | 图幅、色标、布局较固定 | figsize/dpi 在不同函数中不统一 | 统一从样式配置读取 `figsize`/`dpi`，`tight_layout` 一致 |

## 本次采用的对齐策略

1. 不改模型推理，仅改展示层（单位转换、色标、矢量、标题、元数据）。
2. 新增集中样式配置，避免多个脚本散落 hardcode。
3. 所有产品图输出增加统计信息（min/max/mean/std）用于数值自检。
4. 保留 CLI 兼容：`scripts/run_product_all.sh`、`tools/plot_product_bundle.py` 参数不破坏。

## 对齐验收入口

```bash
source configs/default.env && source scripts/env_gpu.sh
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force
scripts/run_gpu.sh tools/compare_plots_against_reference.py --pred-dir figures/product --out artifacts/day7/plot_alignment_report.md
```

