# Reference Repo: zjobsdev/pangu (Summary / 对齐说明)

Source: https://github.com/zjobsdev/pangu

## Observed Capabilities (from README)
- Supports 1/3/6/24-hour models for inference.
- Supports 1–84h hourly rollouts and 84–360h iterative rollouts.
- Provides a demo with CLI and a Streamlit app.
- Includes example output pictures under `docs/example_pictures/`.

## Directory Clues (from repo root)
- `pangu/` (core package)
- `docs/example_pictures/`
- `README.rst`
- `setup.py`

## Alignment Targets（对齐目标）
- Model selection API: 1h / 3h / 6h / 24h
- Scheduling: short range 1–84h hourly, long range 84–360h iterative
- Visualization: reproducible plots suitable for paper figures
- Extensibility: region input adapter interface

## Current Alignment (本仓库当前对齐进度)
- 模型选择 + 调度：已实现 `tools/run_forecast.py`
- 360h：建议 `scripts/run_360h_split.sh`（更稳）
- 论文图：`tools/plot_paper_bundle.py`（png+json）
- Region：`pangu_weather_repro/region` + `tools/region_demo.py`

## Notes
- 参考仓库带 Streamlit UI，本仓库目前以 CLI 为主。
- 论文图可进一步对齐色标/范围/字体风格（见 `tools/plot_paper_bundle.py` 参数）。
