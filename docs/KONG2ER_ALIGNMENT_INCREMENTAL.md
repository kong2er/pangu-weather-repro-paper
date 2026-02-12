# KONG2ER Alignment Incremental Backlog（增量对齐任务单）

中文说明：
- 原则：不动核心算法，只补包装层、入口层、文档层。
- 目标：保持 `final_verify PASS`，同时提升复现人员流畅度。

## 已完成（对齐）
1. Streamlit 骨架：`Home/Forecast/Plots`
2. 产品图族：`fill/diff/vector/msl_wind/wind_speed`
3. 地理样式回退：缺 cartopy/scipy 时不崩
4. 360h 稳态链：`split/resume/auto-retry`
5. 入口分层：`docs/ENTRYPOINT_MATRIX.md`

## 待补齐（仅包装层）
1. 页面术语映射（蓝本中文页面名 -> 本仓库页面功能）
- 建议文件：`docs/APP_PAGE_MAPPING.md`
- 风险：低（纯文档）

2. 产品图命名别名
- 给 `run_product_bundle.sh` 增加蓝本术语 alias（只参数映射，不改绘图逻辑）
- 风险：低（CLI 兼容层）

3. 一键对齐验证汇总
- 在 `run_e_stage_verify.sh` 增加 `KONG2ER_GAP_RUNTIME.md` 链接提示
- 风险：低（报告层）

## 推荐执行顺序
1. 先执行：`bash scripts/run_kong2er_gap_check.sh`
2. 再执行：`bash scripts/verify_repo_health.sh`
3. 最后执行：`bash scripts/final_verify.sh --with-e-stage --e-stage-force`

## 验收标准
- `artifacts/day7/KONG2ER_GAP_RUNTIME.md` 生成成功
- `verify_repo_health` 通过
- `FINAL VERIFY PASS`
