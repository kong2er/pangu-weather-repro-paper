"""Streamlit app entry for alignment skeleton."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Pangu Repro App", layout="wide")
    st.title("Pangu-Weather Repro (E1 Skeleton)")
    st.markdown(
        "This is the minimal Streamlit framework aligned to the reference app structure. "
        "Business pages and product plotting will be added in E2/E3."
    )

    root_dir = Path(__file__).resolve().parents[2]
    st.write("Repository:", str(root_dir))
    st.write("Python:", os.environ.get("VIRTUAL_ENV", "system"))
    st.info("Use pages in the left sidebar: Home / Forecast / Plots.")


if __name__ == "__main__":
    main()
