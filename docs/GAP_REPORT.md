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

## 能力差距（必须实现）
- 统一推理入口（模型选择 + 调度策略）
- 1–84h / 84–360h 调度逻辑
- 论文级图输出规范与元数据

## 能力差距（先搭接口）
- RegionDatasetAdapter 抽象层（地区数据接入）
- 参照仓库能力对照报告与同步脚本

## 实施路径
- Stage A: 稳定性收口（脚本幂等 + 统一入口 + 一键验收）
- Stage B: 推理对齐（runner + scheduler + CLI）
- Stage C: Region 适配层 + 示例
