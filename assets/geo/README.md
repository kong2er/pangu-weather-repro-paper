# 地理资源目录说明（E3）

用途：
- 给 `tools/plot_product_bundle.py --with-geo` 提供本地地理资源（可选）。
- 该目录缺失或为空时，绘图会自动回退到普通 `imshow`，流程不报错。

支持放入的文件类型（任意一种即可）：
- `*.shp`（及对应 `.shx/.dbf/.prj`）
- `*.geojson`
- `*.json`（边界数据）

推荐结构：
```text
assets/geo/
  cn_boundary.shp
  cn_boundary.shx
  cn_boundary.dbf
  cn_boundary.prj
```

验证命令：
```bash
scripts/run_gpu.sh tools/plot_product_bundle.py --rollout-dir "$OUTPUT_ROOT/day4_rollout_30h" --vars z500 --hours 24 --with-geo --geo-assets-dir assets/geo --force
```

结果判断：
- 若 cartopy/scipy 依赖完整：`product_*.json` 中 `with_geo: true`
- 若依赖不完整：`with_geo: false` 且 `geo_error` 给出原因（属于可接受回退）
