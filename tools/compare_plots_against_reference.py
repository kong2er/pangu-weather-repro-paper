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


def _histogram_similarity(a: np.ndarray, b: np.ndarray, bins: int = 256) -> float:
    """计算两幅图像的直方图交叉相似度（0-1，越高越相似）。

    对每个通道分别计算归一化直方图的交叉量，然后取所有通道的均值。
    """
    if a.shape != b.shape:
        h = min(a.shape[0], b.shape[0])
        w = min(a.shape[1], b.shape[1])
        c = min(a.shape[2], b.shape[2])
        a = a[:h, :w, :c]
        b = b[:h, :w, :c]

    n_channels = a.shape[2] if a.ndim == 3 else 1
    similarities = []
    for ch in range(n_channels):
        a_ch = a[:, :, ch].ravel() if a.ndim == 3 else a.ravel()
        b_ch = b[:, :, ch].ravel() if b.ndim == 3 else b.ravel()
        # 归一化直方图
        hist_a, _ = np.histogram(a_ch, bins=bins, range=(0.0, 1.0))
        hist_b, _ = np.histogram(b_ch, bins=bins, range=(0.0, 1.0))
        hist_a = hist_a.astype(np.float64) / max(hist_a.sum(), 1)
        hist_b = hist_b.astype(np.float64) / max(hist_b.sum(), 1)
        # 直方图交叉量
        intersection = float(np.minimum(hist_a, hist_b).sum())
        similarities.append(intersection)
    return float(np.mean(similarities))


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
    hist_sim_list: list[float] = []
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
                hist_sim = _histogram_similarity(a, b)
                compared += 1
                mse_list.append(mse)
                psnr_list.append(psnr)
                hist_sim_list.append(hist_sim)
                entry.append(f"mse={mse:.6f}")
                entry.append(f"psnr={psnr:.2f}")
                entry.append(f"hist_sim={hist_sim:.4f}")
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
        lines.append(f"- hist_similarity_mean: {float(np.mean(hist_sim_list)):.4f}")
    else:
        lines.append("- mse_mean: N/A")
        lines.append("- psnr_mean: N/A")
        lines.append("- hist_similarity_mean: N/A")
        lines.append("- note: provide --ref-dir with blueprint images to enable pixel-level comparison.")

    lines.append("")
    lines.append("## Next")
    lines.append("- 生成产品图：`bash scripts/run_product_all.sh --rollout-dir \"$OUTPUT_ROOT/day4_rollout_30h\" --hours 24,30 --force`")
    lines.append("- 参考图比对：`scripts/run_gpu.sh tools/compare_plots_against_reference.py --pred-dir figures/product --ref-dir <blueprint_png_dir>`")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] wrote {out}")


if __name__ == "__main__":
    main()
