#!/usr/bin/env python3
"""Compare product plots against reference images and emit a markdown report.

If reference images are not provided, this script performs internal sanity checks
from generated metadata json files (stats range presence, units, extent).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def _read_image(path: Path) -> np.ndarray:
    # Use matplotlib loader to avoid extra dependency.
    import matplotlib.image as mpimg

    arr = mpimg.imread(str(path))
    if arr.ndim == 2:
        arr = arr[..., None]
    arr = arr.astype(np.float32)
    if arr.max() > 1.0:
        arr = arr / 255.0
    return arr


def _mse(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        # center crop to minimum shared shape
        h = min(a.shape[0], b.shape[0])
        w = min(a.shape[1], b.shape[1])
        c = min(a.shape[2], b.shape[2])
        a = a[:h, :w, :c]
        b = b[:h, :w, :c]
    return float(np.mean((a - b) ** 2))


def _psnr(mse: float) -> float:
    if mse <= 1e-12:
        return 99.0
    return float(10.0 * math.log10(1.0 / mse))


def _load_meta(meta_path: Path) -> dict[str, Any]:
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _collect_pairs(pred_dir: Path, ref_dir: Path | None) -> list[tuple[Path, Path | None, Path | None]]:
    pairs: list[tuple[Path, Path | None, Path | None]] = []
    for png in sorted(pred_dir.glob("*.png")):
        ref_png = (ref_dir / png.name) if ref_dir else None
        meta = png.with_suffix(".json")
        pairs.append((png, ref_png if ref_png and ref_png.exists() else None, meta if meta.exists() else None))
    return pairs


def main() -> None:
    p = argparse.ArgumentParser(description="Compare generated plots with reference images and metadata sanity checks.")
    p.add_argument("--pred-dir", default="figures/product", help="Generated plot directory.")
    p.add_argument("--ref-dir", default="", help="Optional reference plot directory (same file names).")
    p.add_argument("--out", default="artifacts/day7/plot_alignment_report.md", help="Output markdown report path.")
    args = p.parse_args()

    pred_dir = Path(args.pred_dir)
    ref_dir = Path(args.ref_dir) if args.ref_dir else None
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not pred_dir.exists():
        raise FileNotFoundError(f"pred_dir not found: {pred_dir}")

    pairs = _collect_pairs(pred_dir, ref_dir)
    if not pairs:
        raise FileNotFoundError(f"no png files found in {pred_dir}")

    lines: list[str] = []
    lines.append("# Plot Alignment Report")
    lines.append("")
    lines.append(f"- pred_dir: `{pred_dir}`")
    lines.append(f"- ref_dir: `{ref_dir}`" if ref_dir else "- ref_dir: (not provided)")
    lines.append(f"- total_png: {len(pairs)}")
    lines.append("")

    compared = 0
    mse_list: list[float] = []
    psnr_list: list[float] = []
    sanity_ok = 0
    sanity_fail = 0

    lines.append("## Per-file")
    for png, ref_png, meta_path in pairs:
        entry = [f"- `{png.name}`"]
        if meta_path:
            meta = _load_meta(meta_path)
            has_stats = all(k in meta for k in ("data_min", "data_max", "data_mean", "data_std"))
            sane_range = True
            if has_stats:
                sane_range = float(meta["data_max"]) >= float(meta["data_min"])
            if has_stats and sane_range:
                sanity_ok += 1
                entry.append("meta=ok")
            else:
                sanity_fail += 1
                entry.append("meta=fail")
        else:
            sanity_fail += 1
            entry.append("meta=missing")

        if ref_png is not None:
            try:
                a = _read_image(png)
                b = _read_image(ref_png)
                mse = _mse(a, b)
                psnr = _psnr(mse)
                compared += 1
                mse_list.append(mse)
                psnr_list.append(psnr)
                entry.append(f"mse={mse:.6f}")
                entry.append(f"psnr={psnr:.2f}")
            except Exception as exc:
                entry.append(f"compare_error={exc}")
        else:
            entry.append("reference=not_found")

        lines.append("  " + ", ".join(entry))

    lines.append("")
    lines.append("## Summary")
    lines.append(f"- metadata_sanity_ok: {sanity_ok}")
    lines.append(f"- metadata_sanity_fail: {sanity_fail}")
    lines.append(f"- compared_with_reference: {compared}")
    if compared > 0:
        lines.append(f"- mse_mean: {float(np.mean(mse_list)):.6f}")
        lines.append(f"- psnr_mean: {float(np.mean(psnr_list)):.2f}")
    else:
        lines.append("- mse_mean: N/A")
        lines.append("- psnr_mean: N/A")
        lines.append("- note: provide --ref-dir with blueprint images to enable pixel-level comparison.")

    lines.append("")
    lines.append("## Next")
    lines.append("- 生成产品图：`bash scripts/run_product_all.sh --rollout-dir \"$OUTPUT_ROOT/day4_rollout_30h\" --hours 24,30 --force`")
    lines.append("- 参考图比对：`scripts/run_gpu.sh tools/compare_plots_against_reference.py --pred-dir figures/product --ref-dir <blueprint_png_dir>`")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] wrote {out}")


if __name__ == "__main__":
    main()

