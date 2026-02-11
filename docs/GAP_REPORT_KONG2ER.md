# GAP 报告（当前仓库 vs 蓝本 `kong2er/pangu`）

## 0) 蓝本定位结果
- `REF_ROOT`: `/tmp/pangu`
- `remote`:
  - `origin https://github.com/kong2er/pangu.git`
  - `github git@github.com:kong2er/Pangu-Weather.git`
- 关键目录（蓝本）:
  - `scripts/`
  - `pangu/`
  - `pangu/visualization/`
  - `pangu/app/`
  - `docs/example_pictures/`

中文说明：
- 已确认机器本地存在蓝本仓库，无需重新 clone。

## 1) 目录级差异
- 蓝本有、当前仓库暂无:
  - Streamlit 页面（`pangu/app/*`）
  - 产品化地图绘制模块（`pangu/visualization/*`）
  - 内置地理边界资源
- 当前仓库有、蓝本无:
  - A/B/C 阶段稳定脚本（`create_*_venv.sh`、`run_*`、`final_verify.sh`）
  - 360h `split/resume/auto-retry` 稳态链路
  - Day3-Day8 的复现实验流水线与验收脚本
  - Region 适配抽象层（`pangu_weather_repro/region/*`）

中文说明：
- 当前仓库在“稳定性与可复现性”上更强；蓝本在“产品展示层”上更完整。

## 2) 入口脚本差异
- 蓝本推理入口:
  - `scripts/run_inference.sh`
  - `pangu/pangu.py`
- 当前推理入口:
  - `tools/run_forecast.py`
  - `pangu_weather_repro/infer/scheduler.py`
  - `pangu_weather_repro/infer/runner.py`
- 蓝本绘图入口:
  - `scripts/plot_one_forecast.py`
  - `pangu/visualization/product_draw.py`
- 当前绘图入口:
  - `tools/plot_fields.py`
  - `tools/plot_rmse_curve.py`
  - `tools/plot_paper_bundle.py`

中文说明：
- 对齐策略采用“保留当前稳定入口 + 增量兼容蓝本能力”，不做推倒重写。

## 3) 推理调度能力对比
- 1/3/6/24h 模型:
  - 当前仓库：已支持（`--short-step 1|3|6|24`）
- 1-84h:
  - 当前仓库：已支持（`--mode short`）
- 84-360h:
  - 当前仓库：已支持（`--mode full` 与 `--mode split`）
- 中断续跑:
  - 当前仓库：已支持（`--resume-from` + `forecast_state.json`）
- OOM 稳态:
  - 当前仓库：已支持（`--no-cache-sessions` + `run_360h_split.sh --auto-retry`）

中文说明：
- “蓝本能力”核心调度已对齐，且在长链稳定性方面当前仓库更稳。

## 4) 输出与可视化差异
- 蓝本:
  - 更偏“业务产品图 + 页面交互”
- 当前:
  - 更偏“复现产物 + 论文图 + 元数据审计”
  - `figures/paper/*.png + *.json` 已支持

中文说明：
- 论文复现目标已满足；若要完全产品化需后续补 app/地图资产层。

## 5) 风险评估（避免崩盘）
- 高风险:
  - 直接搬运蓝本 app/可视化依赖，可能破坏现有稳定环境
- 中风险:
  - 强制输出格式完全等同蓝本，可能影响已有 Day 流程
- 低风险:
  - 通过“可选模块/脚本”增量对齐，不动现有稳定主链

## 6) 后续建议（增量对齐）
1. 保持当前稳定链路为默认主路径（A/B/C 成果不回退）。
2. 新增可选“蓝本风格输出”脚本，不替换现有脚本。
3. 按需增加 app 层，但隔离依赖，不影响 baseline 复现。
