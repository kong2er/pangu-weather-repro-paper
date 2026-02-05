# RUNBOOK – Pangu-Weather Reproduction

---

## 🇨🇳 中文工程手册（从开机到可复现）

本 RUNBOOK 记录了在 **AutoDL GPU 实例**上，
从零开始复现 **Pangu-Weather（ONNXRuntime-GPU）**的完整工程流程。
 
目标： 
- 任意时间新开实例 
- 按本文档逐步执行 
- 得到一致的输入、输出与结果 

---

## Day1：环境与 ERA5 数据准备（✅ 已完成）

### 1. 运行环境

- 平台：AutoDL
- GPU：RTX 4090（24GB）
- OS：Ubuntu 22.04
- Python：3.10
- 包管理：**uv（不使用 conda）**

创建并同步环境：

```bash
uv venv --python 3.10
uv sync
```
#### 验证 ONNXRuntime GPU Provider：
```bash
python - <<'PY'
import onnxruntime as ort
print("Available providers:"
, ort.get_available_providers())
PY
```
#### 期望输出包含：
CUDAExecutionProvider

---

### 2. 项目目录结构约定
```
pangu-weather-repro-uv/
├── configs/                  # 配置文件
│   ├── default.env
│   └── default.yaml
├── scripts/                  # 可执行流水线脚本
│   ├── 03_download_era5_single.py
│   ├── 03_download_era5_pressure.py
│   └── 04_preprocess_era5_to_npy.py   # Day2
├── src/pangu_repro/          # 核心 Python 模块
│   ├── adapters/             # Data Adapter（ERA5 → 模型输入）
│   └── plotting/             # 论文级绘图管线
├── tests/                    # 测试脚本
├── figures/                  # 输出图像
├── README.md
├── RUNBOOK.md
├── pyproject.toml
└── uv.lock
```

---

### 3. CDS（Copernicus）API 配置
在 Copernicus Climate Data Store 申请 API Key，
并写入以下文件：
```
~/.cdsapirc
```
格式示例：
```
url: https://cds.climate.copernicus.eu/api/v2
key: <uid>:<api-key>
```
验证 CDS 是否可用（已完成）：
```bash
uv run python scripts/cds_smoke_t2m.py
```

### 4. ERA5 数据下载（2023-07-09 00UTC）
下载 单层变量：
```bash
uv run python scripts/03_download_era5_single.py \
  --date 20230709 \
  --hour 00
```
下载 压力层变量（13 层）：
```bash
uv run python scripts/03_download_era5_pressure.py \
  --date 20230709 \
  --hour 00
```
数据存放路径（数据盘，不随关机丢失）：
```
/root/autodl-tmp/pangu-weather-repro/era5_raw/
```
验证文件存在：
```bash
ls /root/autodl-tmp/pangu-weather-repro/era5_raw
```
期望看到：
- era5_single_2023070900.nc
- era5_pressure_2023070900.nc

---

## Day2：ERA5 → NumPy 预处理（⬅️ 当前进行中）
### 目标
- 将 ERA5 NetCDF 数据转换为 Pangu-Weather 模型输入格式：
	-input_surface.npy
	-input_pressure.npy
- 确保：
	-shape 正确
	-dtype 正确
	-无 NaN
	-变量顺序严格一致
#### 关键脚本
``` 
scripts/04_preprocess_era5_to_npy.py
```
该脚本将使用 Data Adapter 架构，
便于未来替换其他数据源（如自有模式数据）。

---

## Day3：ONNX 推理 Smoke Test（参考）

如遇到显存/内存分配失败，优先用 noarena 方案运行：

```bash
uv run python tools/run_smoke_gpu_noarena.py --step 24
```

如仍失败，可强制 CPU：

```bash
FORCE_CPU=1 uv run python scripts/06_infer_smoke.py --step 24
```

---

## Day4：多步 Rollout + OOM 规避（⬅️ 当前问题）

### 常见报错原因
`BFCArena::AllocateRawInternal Failed to allocate memory` 通常是 **显存/内存碎片化**
或 **CUDA arena 预分配** 导致的峰值超限。建议按以下顺序排查：

1. **禁用 arena / mem pattern**（减少峰值）
2. **限制 GPU 可用显存**（让 ORT 更保守）
3. **GPU 失败时自动回落到 CPU**

### 1) 24h + 6h 组合测试（Day4 Step 1/2）
```bash
uv run python tools/day4_rollout.py --steps 24,6 --noarena
# or: uv run python tools/day4_rollout_codex.py --steps 24,6 --noarena
```

### 2) 更长 horizon（示例：56h = 24+24+6+1+1）
```bash
uv run python tools/day4_rollout.py --steps 24,24,6,1,1 --noarena
```

### 3) GPU 显存限制（避免突刺）
```bash
ORT_GPU_MEM_LIMIT_MB=12000 uv run python tools/day4_rollout.py --steps 24,6 --noarena
```

### 4) 强制 CPU（稳定但慢）
```bash
uv run python tools/day4_rollout.py --steps 24,6 --force-cpu
```

---

## Day5：RMSE 评估（z500）

### 1) 生成评估包（rollout 同时导出）
```bash
uv run python tools/day4_rollout.py --steps 24,6 --noarena --out-dir "$OUTPUT_ROOT/day4_rollout_30h"
# 评估包默认输出：$OUTPUT_ROOT/day4_rollout_30h/eval_z500.npz
# 元信息：$OUTPUT_ROOT/day4_rollout_30h/eval_z500_meta.json
```

### 2) 计算 RMSE
```bash
uv run python tools/eval_rmse.py \
  --pred "$OUTPUT_ROOT/day4_rollout_30h/eval_z500.npz" \
  --var z500 \
  --out artifacts/day5/rmse.csv
```

### 3) 说明（ERA5 对齐时次）
- Day4 `24h + 6h` 预测对应的真值文件：`era5_pressure_2023071000.nc`
- Day4 `24h + 6h` 预测对应的真值文件：`era5_pressure_2023071006.nc`
- 若 ERA5 下载队列拥堵，建议在 CDS 网页侧等到 `Successful` 后用下载链接直接 `wget` 到 `$ERA5_RAW_ROOT`。

---

## Day6：可视化（论文级示例图）

### 依赖
- 先完成 Day4 rollout，生成 `eval_z500_meta.json`
- 再完成 Day5，生成 `artifacts/day5/rmse.csv`

### 1) 生成 GT / Pred / Error 三联图
```bash
uv run python tools/plot_fields.py --var z500 --lead 24
```

### 2) 生成 RMSE 曲线图
```bash
uv run python tools/plot_rmse_curve.py --var z500
```
