"""Plots page for Streamlit skeleton."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


def _collect_pngs(base: Path) -> list[str]:
    if not base.exists():
        return []
    return sorted([str(p.relative_to(base)) for p in base.rglob("*.png")])[:200]


st.title("Plots")
root_dir = Path(__file__).resolve().parents[3]
fig_root = root_dir / "figures"
output_root = Path(os.environ.get("OUTPUT_ROOT", str(root_dir / "outputs")))

st.write("Figures root:", str(fig_root))
st.write("Output root:", str(output_root))

pngs = _collect_pngs(fig_root)
if pngs:
    st.subheader("Detected PNG Files")
    st.write(pngs[:50])
else:
    st.info("No PNG files found under figures/.")

st.subheader("Product Bundle（产品图族）")
product_dir = fig_root / "product"
product_pngs = _collect_pngs(product_dir)
if product_pngs:
    st.write("figures/product 已生成文件：")
    st.write(product_pngs[:50])
else:
    st.info("figures/product 为空。")

st.code(
    "bash scripts/run_product_bundle.sh --vars z500,t2m --hours 24,30",
    language="bash",
)
