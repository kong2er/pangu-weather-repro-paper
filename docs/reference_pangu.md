# Reference Repo: zjobsdev/pangu (Summary)

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

## Alignment Targets
- Model selection API: 1h / 3h / 6h / 24h
- Scheduling: short range 1–84h hourly, long range 84–360h iterative
- Visualization: reproducible plots suitable for paper figures
- Extensibility: region input adapter interface
