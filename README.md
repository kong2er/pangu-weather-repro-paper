# Pangu-Weather Reproduction (UV + ONNXRuntime)

---

## CN 中文说明（项目概览）

本仓库用于 **复现 Pangu-Weather 全球天气预报模型**，目标是构建一个：

- ✅ 可复现（Reproducible）
- ✅ 可工程化（Production-ready）
- ✅ 可审计（Audit-friendly）

的 **研究级 / 工程级复现项目**。

### 核心技术栈

- **数据**：ERA5 再分析数据（Copernicus Climate Data Store）
- **模型**：Pangu-Weather（ONNX 格式）
- **推理**：ONNXRuntime-GPU（CUDA）
- **环境管理**：`uv`（不使用 conda）
- **平台**：AutoDL / Linux GPU Server

---

## 📁 项目结构说明

```text
pangu-weather-repro-uv/
├── configs/                  # 配置文件（路径 / 变量 / 策略）
│   ├── default.env            # 路径与环境变量（数据盘）
│   └── default.yaml           # 运行参数（变量顺序、层数等）
├── scripts/                  # 流水线脚本（按编号执行）
│   ├── 03_download_era5_single.py
│   ├── 03_download_era5_pressure.py
│   ├── 04_preprocess_era5_to_npy.py   # ERA5 → NumPy（Day2）
│   └── 05_validate_inputs.py          # 输入一致性校验
├── src/pangu_repro/           # 核心 Python 模块
│   ├── adapters/              # ERA5 → 模型输入适配层
│   ├── inference/             # ONNX 推理封装
│   └── plotting/              # 可视化与论文级绘图
├── tests/                     # 单元测试 / 形状校验
├── figures/                   # 输出图片
├── README.md                  # 项目总览（你正在看的）
├── RUNBOOK.md                 # 操作手册（一步一步）
├── pyproject.toml
└── uv.lock
```

---

### 🚀 快速开始（Day1 已验证）
```bash
# 1. 创建并同步环境
uv 
sync

# 2. 下载 ERA5 数据（2023-07-09 00UTC）
uv run python scripts/03_download_era5_single.py   --date 20230709 --hour 00
uv run python scripts/03_download_era5_pressure.py --date 20230709 --hour 00
```
#### 数据将被保存到 数据盘（不会随关机丢失）：
```
/root/autodl-tmp/pangu-weather-repro/era5_raw/
```

---

🧭 当前进度
- Day1：环境搭建 + CDS API + ERA5 下载 ✅
- Day2：ERA5 → NumPy 预处理（进行中）
- Day3：模型推理、评估与可视化（计划中）
详细步骤请查看 👉 RUNBOOK.md
