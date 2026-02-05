  # Day6 Results (Visualization)

  - Date/Hour: 20230709 00
  - Variable: z500
  - Lead: 24h (from steps 24,6)
  - Outputs:
    - figures/day6/field_z500_2023070900_t+024.png
    - figures/day6/rmse_z500_2023070900.png

  Commands:
  - uv run python tools/plot_fields.py --var z500 --lead 24
  - uv run python tools/plot_rmse_curve.py --var z500        
