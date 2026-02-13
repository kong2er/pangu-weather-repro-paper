# 功能调用说明书（中文）

本文档面向复现执行人员，按“功能 -> 命令 -> 实际意义”给出可直接复制的调用方式。

## 1. 环境初始化（CPU/GPU）
- 命令：
```bash
bash scripts/create_cpu_venv.sh
bash scripts/create_gpu_venv.sh
```
- 实际意义：创建并维护幂等虚拟环境，避免不同机器依赖漂移。

## 2. 环境切换
- CPU：
```bash
source scripts/env_cpu.sh
```
- GPU：
```bash
source scripts/env_gpu.sh
```
- 实际意义：确保后续命令使用正确解释器与运行上下文。

## 3. CPU 冒烟测试（Day8）
- 命令：
```bash
bash scripts/run_day8_cpu_smoke.sh
```
- 实际意义：快速验证包结构、输入输出契约、基础执行链路。

## 4. Day3 前置数据准备（ERA5 -> numpy）
- 命令：
```bash
bash scripts/prepare_era5_inputs.sh --yes
```
- 实际意义：生成 Day3 所需的 `processed/surface.npy` 和 `processed/pressure.npy`，避免 GPU smoke 因缺输入失败。

## 5. GPU 冒烟测试（Day3）
- 命令：
```bash
bash scripts/run_day3_smoke_gpu.sh
```
- 实际意义：验证 24h 模型可在 GPU 侧正常推理并生成 smoke 报告。

## 6. 84h 推理（短时效）
- 命令：
```bash
scripts/run_gpu.sh tools/run_forecast.py \
  --strategy kong2er_ref \
  --mode short \
  --target-hours 84 \
  --noarena --threads 1 \
  --out-dir "$OUTPUT_ROOT/forecast_84h_$(date +%Y%m%d_%H%M%S)"
```
- 实际意义：验证短时效预测链路与调度策略。

## 7. 360h 稳态推理（推荐）
- 命令：
```bash
bash scripts/run_360h_split.sh --auto-retry
```
- 实际意义：分段推理 + 自动降载重试，降低 OOM 风险，适合云端稳定执行。

## 8. RMSE 评估（Day5）
- 命令：
```bash
bash scripts/internal/run_day5_rmse.sh
```
- 实际意义：生成误差评估结果，用于量化预测质量。

## 9. 论文图生成（Day6）
- 命令：
```bash
bash scripts/internal/run_day6_plots.sh
```
- 实际意义：生成字段图和 RMSE 曲线图，形成论文图产物。

## 10. 产品图族（E 阶段）
- 一键命令：
```bash
bash scripts/run_product_all.sh --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --hours 24,30 --impl auto --force
```
- 实际意义：批量生成 fill/diff/vector/wind_speed/msl_wind 图和对应元数据 JSON。

## 11. Streamlit 页面
- 命令：
```bash
bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501
```
- 实际意义：可视化查看 Home / Forecast / Plots 页面内容。

## 12. 轻量健康检查
- 命令：
```bash
bash scripts/verify_repo_health.sh
```
- 实际意义：快速验证入口脚本、核心导入和测试状态，不跑重推理。

## 13. 最终全链验收
- 命令：
```bash
bash scripts/final_verify.sh --with-e-stage --e-stage-force
```
- 实际意义：串联 CPU/GPU/评估/绘图/E 阶段核查，输出最终 PASS 结论。

## 14. 关机前空间清理（可选）
- 先看占用：
```bash
bash scripts/internal/cleanup_check.sh
```
- 预览清理：
```bash
bash scripts/internal/cleanup_autodl.sh --dry-run
```
- 执行清理：
```bash
bash scripts/internal/cleanup_autodl.sh --force --keep-latest 2 --keep-days 3
```
- 实际意义：删除可再生成的临时产物与缓存，保留模型与关键数据目录。

## 15. 推荐执行顺序（最短）
1. S1：创建并激活环境
2. S2-S3：CPU/GPU 冒烟
3. S4-S5：84h 与 360h 推理
4. S6-S7：评估与图像
5. S8：最终验收
