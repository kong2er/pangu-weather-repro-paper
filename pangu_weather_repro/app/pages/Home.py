"""Home page for Streamlit skeleton."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st


def _list_dirs(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted([p.name for p in path.iterdir() if p.is_dir()])


st.title("Home")
root_dir = Path(__file__).resolve().parents[3]
output_root = Path(os.environ.get("OUTPUT_ROOT", str(root_dir / "outputs")))
models_root = Path(os.environ.get("MODELS_ROOT", str(root_dir / "models")))

st.write("Repo:", str(root_dir))
st.write("OUTPUT_ROOT:", str(output_root))
st.write("MODELS_ROOT:", str(models_root))
st.write("VIRTUAL_ENV:", os.environ.get("VIRTUAL_ENV", "system"))

st.subheader("Output Directories")
dirs = _list_dirs(output_root)
if dirs:
    st.write(dirs)
else:
    st.warning("No output directories found.")
