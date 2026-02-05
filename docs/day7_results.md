# Day7 Results (Metrics Summary)

- Date/Hour: 20230709 00
- Vars: z500, t2m, u10
- Leads: 6
- Rollout: /root/autodl-tmp/pangu-weather-repro/outputs/day4_rollout_06h
- Output CSV: artifacts/day7/metrics_summary.csv

Metrics:
- rmse: unweighted RMSE
- rmse_latw: latitude-weighted RMSE (cos(lat))
- acc: anomaly correlation using GT mean as climatology
- acc_latw: latitude-weighted ACC

| var | lead | rmse | rmse_latw | acc | acc_latw | n |
|---|---|---:|---:|---:|---:|---:|
| z500 | 6 | 79.883932 | 15.575824 | 0.999687 | 0.999982 | 1038240 |\n| t2m | 6 | 1.223496 | 0.602996 | 0.998195 | 0.999057 | 1038240 |\n| u10 | 6 | 0.555914 | 0.464440 | 0.995220 | 0.996827 | 1038240 |\n