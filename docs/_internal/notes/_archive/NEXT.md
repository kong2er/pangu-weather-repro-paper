# NEXT – pick up guide

## Today (Day4 end) – done
- Local repo synced to GitHub main ✅
- Added notes/STATUS.md (Codex context) ✅
- Split env configs:
  - configs/default.env = AutoDL/cloud defaults ✅
  - configs/local.env   = local-only (gitignored) ✅
- GitHub auth fixed (SSH) ✅

## Local usage (tomorrow)
1) cd ~/projects/pangu-weather-repro-paper
2) source configs/local.env
3) codex
4) Tell codex:
   - Read notes/STATUS.md, notes/TODO_DAY5.md (create if missing), RUNBOOK.md, tools/, artifacts/day4
   - Goal: implement tools/eval_rmse.py for Day5 (start with z500), output rmse.csv, update RUNBOOK Day5 command

## Cloud usage (tomorrow on AutoDL)
1) git pull
2) source configs/default.env
3) run Day5 command from RUNBOOK after tools/eval_rmse.py is merged

## What must be inspected before writing eval_rmse.py
- List artifacts/day4 outputs + formats:
  - ls artifacts/day4
  - find artifacts/day4 -maxdepth 3 -type f | head
