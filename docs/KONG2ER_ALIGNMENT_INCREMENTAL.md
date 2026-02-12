# KONG2ER Alignment Incremental Checklist（可执行清单）

中文说明：
- 目标：在不改核心算法的前提下，持续对齐蓝本仓库能力。
- 约束：只做文档层、脚本包装层、参数映射层，保持 `final_verify PASS`。

## 使用方式
- 每次只做 1 个条目，完成后执行对应验收命令。
- 验收通过再进入下一个条目。

## A. 基线核查（必须先通过）
- 目标：确认当前仓库已具备蓝本关键能力骨架。
- 命令：
```bash
bash scripts/run_kong2er_gap_check.sh
bash scripts/verify_repo_health.sh
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```
- 产物：
  - `artifacts/day7/KONG2ER_GAP_RUNTIME.md`
- 验收标准：
  - `KONG2ER_GAP_RUNTIME.md` 中关键项均为 `true`
  - `verify_repo_health` 通过
  - `FINAL VERIFY PASS`
- 失败修复：
```bash
git pull --rebase paper cleanup/repo-sanitize && bash scripts/run_kong2er_gap_check.sh
```

## B. 页面术语映射（文档层）
- 状态：`DONE`
- 目标：蓝本中文页面 -> 当前页面/命令映射。
- 文件：`docs/APP_PAGE_MAPPING.md`
- 验收命令：
```bash
sed -n '1,240p' docs/APP_PAGE_MAPPING.md
```
- 验收标准：包含 5 个蓝本页面映射与对应命令。

## C. 入口分层清晰化（文档层）
- 状态：`DONE`
- 目标：复现人员只看官方入口，不误用 legacy。
- 文件：`docs/ENTRYPOINT_MATRIX.md`、`scripts/README.md`
- 验收命令：
```bash
sed -n '1,220p' docs/ENTRYPOINT_MATRIX.md
sed -n '1,120p' scripts/README.md
```
- 验收标准：包含 官方/高级/归档 三层。

## D. 产品图别名映射（包装层）
- 状态：`DONE`
- 目标：支持蓝本常见图种术语（`fill/diff/vector/wind_speed/msl_wind`）。
- 命令：
```bash
source configs/default.env && source scripts/env_gpu.sh
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --force
```
- 产物：
  - `figures/product/product_*.png`
  - `figures/product/product_*.json`
- 验收标准：`run_product_all.sh` 成功，`run_e_stage_verify.sh --force` 中图种检查为 `ok`。
- 失败修复：
```bash
bash scripts/install_extras.sh plots --force
```

## E. 对齐报告汇总（报告层）
- 状态：`DONE`
- 目标：一键输出 E 阶段与蓝本差异报告。
- 命令：
```bash
bash scripts/run_e_stage_verify.sh --force
bash scripts/run_kong2er_gap_check.sh
```
- 产物：
  - `artifacts/day7/E_STAGE_REPORT.md`
  - `artifacts/day7/KONG2ER_GAP_RUNTIME.md`
- 验收标准：两个报告均成功生成，且关键项通过。

## F. 后续候选条目（待做，低风险）
1. 在 Streamlit Plots 页补“蓝本页面别名”快速导航（仅文案与命令模板，不改算法）。
2. 在 `scripts/run_product_bundle.sh` 增加 `--preset` 参数（预填 vars/kinds/extent），仍映射到现有 CLI。
3. 在 `run_e_stage_verify.sh` 增加 `--strict` 模式，允许把 `KONG2ER_GAP_RUNTIME.md` 关键项 false 作为非零退出。

## 收官建议
- 当前状态已经满足“稳定复现 + 蓝本增量对齐”目标。
- 若进入下一轮迭代，优先做 `F.1` 与 `F.2`，避免新增复杂依赖。
