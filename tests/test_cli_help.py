import subprocess
import sys
from pathlib import Path


def _run_help(path: str) -> None:
    result = subprocess.run(
        [sys.executable, path, "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{path} --help failed: {result.stderr}"


def test_cli_help():
    repo_root = Path(__file__).resolve().parents[1]
    targets = [
        repo_root / "tools" / "day4_rollout.py",
        repo_root / "tools" / "day7_metrics.py",
        repo_root / "tools" / "day7_plot_summary.py",
        repo_root / "tools" / "run_smoke_gpu_noarena.py",
        repo_root / "scripts" / "internal" / "04_preprocess_era5_to_npy.py",
        repo_root / "scripts" / "internal" / "05_validate_inputs.py",
        repo_root / "scripts" / "internal" / "06_infer_smoke.py",
    ]
    for target in targets:
        _run_help(str(target))
