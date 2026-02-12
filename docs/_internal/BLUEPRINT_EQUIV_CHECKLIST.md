# BLUEPRINT EQUIV CHECKLIST（蓝本功能 1:1 对齐清单）

## 0. 蓝本定位结果
- `REF_ROOT`: `/tmp/pangu`
- `remote`:
  - `origin https://github.com/kong2er/pangu.git`
  - `github git@github.com:kong2er/Pangu-Weather.git`

中文注释：
- 已确认本机存在蓝本仓库，无需再 clone。
- 当前文档基于本机已探测到的蓝本目录与文件清单。

## 1. 蓝本 Streamlit 页面体系（`pangu/app/*`）

### 1.1 入口文件
- `pangu/app/main_page.py`
- `pangu/app/__init__.py`

### 1.2 页面文件（`pangu/app/pages/*`）
- `时间垂直剖面.py`
- `海区风力释用产品.py`
- `短中期逐3小时预报.py`
- `模型稳定性.py`
- `短中期2米温度预报.py`

### 1.3 页面输入/输出/依赖（对齐要点）
- 输入：
  - 模型输出目录（预测结果）
  - 时间、变量、区域等筛选参数
- 输出：
  - 页面级可视化图、统计摘要、图例说明
- 依赖：
  - `streamlit`
  - 业务图绘制模块（`pangu/visualization/*`）
  - 数据读写依赖（`numpy/xarray/matplotlib/cartopy` 等按页面需要）

中文注释：
- E1 阶段先做“页面骨架可启动”；业务逻辑和图种在 E2/E3 增量补齐。

## 2. 蓝本产品化可视化图种（`pangu/visualization/*`）

### 2.1 已发现核心文件
- `pangu/visualization/product_draw.py`
- `pangu/visualization/__init__.py`
- `pangu/visualization/Country/中华人民共和国.{shp,shx,dbf,prj,json}`

### 2.2 图种能力（按蓝本定位的业务图族）
- 等压面风场/高度场组合图（如 H500 + UV）
- 海平面气压 + 近地风场（MSL + UV10）
- 2 米温度等产品图
- 区域剖面或业务化组合图（页面侧调用）

### 2.3 输入/输出/资源依赖
- 输入：
  - 预测场（多变量、多时效）
  - 可选区域/边界裁剪参数
- 输出：
  - 产品图 PNG（业务命名风格）
  - 可选统计/说明文本
- 依赖资源：
  - 国家/行政区边界 shapefile（Country 目录）
  - 海岸线、边界线、投影与字体配置

中文注释：
- E2 先补 3-5 个核心图种；E3 再补地理资源驱动样式与回退机制。

## 3. 对应到当前仓库的落点设计（新增优先，不破坏主链）

### 3.1 Streamlit 骨架（E1）
- 新增：
  - `pangu_weather_repro/app/app.py`
  - `pangu_weather_repro/app/pages/Home.py`
  - `pangu_weather_repro/app/pages/Forecast.py`
  - `pangu_weather_repro/app/pages/Plots.py`
  - `scripts/run_streamlit.sh`
- 依赖安装：
  - `scripts/install_extras.sh streamlit`（显式安装，默认不污染）

### 3.2 产品图族（E2）
- 新增：
  - `pangu_weather_repro/visualization/product_draw.py`
  - `pangu_weather_repro/visualization/style.py`
  - `tools/plot_product_bundle.py`
- 最小图种目标：
  - `z500`, `t2m`, `u10`, `v10`, `msl`
- 输出：
  - `figures/product/*.png`
  - `figures/product/*.json`

### 3.3 地理资源驱动样式（E3）
- 新增：
  - `pangu_weather_repro/visualization/geo.py`
  - `assets/geo/README.md`（放置 shapefile/geojson 说明）
- 参数：
  - `--with-geo`
  - `--geo-assets-dir`
  - `--extent`
- 回退：
  - 缺 `cartopy` 或缺地理资源时自动退化为普通 `imshow`（不崩）

### 3.4 对齐验证与报告（E4）
- 新增：
  - `scripts/run_e_stage_verify.sh`
  - `artifacts/day7/E_STAGE_REPORT.md`
- 不改：
  - `final_verify.sh` 语义不变（保持 A/B/C/D 稳定链）

## 4. 风险与策略
- 风险高：
  - 直接搬蓝本 app/visualization 全量代码导致依赖冲突
- 风险中：
  - 地理资源/字体在不同机器上路径不一致
- 风险低：
  - 采用“新增模块 + feature flag + fallback”增量补齐

中文注释：
- 执行策略：先骨架、后图种、再地理样式，始终保持 `final_verify PASS`。
