# GAP REPORT (Day3–Day8 vs zjobsdev/pangu)

## 本仓库已有能力
- Day8 CPU smoke（contracts 级别校验）
- Day3 GPU smoke（24h ONNX）
- Day4 30h rollout（24+6）
- Day5 RMSE
- Day6 plots（z500 + rmse 曲线）
- 稳定脚本链：create/env/run + final_verify

## 对齐目标（zjobsdev/pangu）
- 1/3/6/24h 模型推理
- 1–84h 逐小时推理
- 84–360h 迭代推理
- 论文级可视化输出
- 地区数据接入的可插拔适配层

## 已实现能力（对齐完成）
- 统一推理入口（`tools/run_forecast.py`）
- 1–84h / 84–360h 调度逻辑（`infer/scheduler.py`，支持 `pangu_ref` 策略）
- 论文级图输出规范与元数据（`tools/plot_paper_bundle.py`）
- Region 适配层 + demo（`pangu_weather_repro/region` + `tools/region_demo.py`）

## 仍需完善（优化项）
- 360h 端到端推理更稳的显存策略（推荐 split + no-cache）
- 论文图风格进一步对齐（色标/字体/地图细节）
- 参考仓库 UI（Streamlit）暂未提供

## 实施路径
- Stage A: 稳定性收口（脚本幂等 + 统一入口 + 一键验收）
- Stage B: 推理对齐（runner + scheduler + CLI）
- Stage C: Region 适配层 + 示例
