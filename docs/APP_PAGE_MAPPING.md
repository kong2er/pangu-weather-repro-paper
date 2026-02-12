# APP PAGE MAPPING（蓝本页面到当前仓库映射）

中文说明：
- 该文档用于复现人员快速定位：蓝本页面能力在当前仓库对应到哪个页面/命令。
- 原则：不改核心算法，仅做页面与脚本映射。

## 1) 页面映射总表

| 蓝本页面（pangu/app/pages） | 当前页面（pangu_weather_repro/app/pages） | 当前推荐脚本/命令 |
|---|---|---|
| 时间垂直剖面.py | Plots.py（产品图筛选 + 元数据预览） | `bash scripts/run_product_bundle.sh --vars z500,t2m --hours 24,30 --kinds fill --force` |
| 海区风力释用产品.py | Plots.py（vector / wind_speed / msl_wind） | `bash scripts/run_product_bundle.sh --vars u10 --hours 24,30 --kinds vector,wind_speed,msl_wind --force` |
| 短中期逐3小时预报.py | Forecast.py（模型/providers/目录可视化） + run_forecast CLI | `scripts/run_gpu.sh tools/run_forecast.py --strategy kong2er_ref --mode short --target-hours 84 --noarena --threads 1` |
| 模型稳定性.py | Forecast.py（providers + 模型存在性） + `run_360h_split.sh` | `bash scripts/run_360h_split.sh --auto-retry` |
| 短中期2米温度预报.py | Plots.py（t2m fill 图） | `bash scripts/run_product_bundle.sh --vars t2m --hours 24,30 --kinds fill --force` |

## 2) 页面能力对应说明
- Home.py：环境与目录可见性（复现入口状态看板）
- Forecast.py：模型可用性与 ORT providers 快速检查
- Plots.py：产品图结果浏览、kind/var/lead 筛选、CLI 模板生成

## 3) 与蓝本一致性状态
- 已对齐：页面入口、多页面结构、产品图族筛选工作流
- 已增强：脚本 `[NEXT]` 提示、默认不覆盖、E 阶段自动验收
- 暂不强制对齐：蓝本全部业务中文页面细节与外部资产耦合逻辑（保持当前仓库稳定优先）

## 4) 复现人员推荐顺序
1. 先跑主链：`bash scripts/final_verify.sh --with-e-stage --e-stage-force`
2. 再起页面：`bash scripts/run_streamlit.sh --host 0.0.0.0 --port 8501`
3. 最后按页面给出的 CLI 模板补图
