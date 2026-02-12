# Day5 TODO – RMSE evaluation

## Goal
- Implement RMSE evaluation (start with z500)
- Output rmse.csv + console summary

## Inputs
- Pred: artifacts/day4 (use actual file format there)
- GT: ERA5 from $ERA5_RAW_ROOT or $PROCESSED_ROOT (follow repo conventions)

## Deliverables
1) tools/eval_rmse.py
   - CLI: --pred <path> --gt <path> --var z500 --out <csv>
   - default out: artifacts/day5/rmse.csv
   - print: rmse_mean/min/max + array shapes
2) Update RUNBOOK.md Day5 section with runnable command
