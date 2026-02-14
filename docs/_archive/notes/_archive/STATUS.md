# STATUS – Pangu-Weather Repro (for Codex)

## Repo
- Repo: kong2er/pangu-weather-repro-paper
- Branch: main
- Local path: ~/projects/pangu-weather-repro-paper
- Local data root: ~/data/pangu-weather-repro

## Progress
- Day1: env + CDS ok (cloud)
- Day2: ERA5 -> npy pipeline
- Day3: ORT smoke test
- Day4: rollout scripts (30h/56h) + noarena + mem limit workaround

## Next (Day5)
- Implement evaluation metric: RMSE (start with z500)

## What Codex should do
1) Read RUNBOOK.md + tools/ + artifacts/day4
2) Decide pred/gt file formats + paths (based on repo conventions)
3) Add tools/eval_rmse.py (CLI) and update RUNBOOK Day5 command
