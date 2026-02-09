import subprocess
import sys
from pathlib import Path


def test_run_smoke_help_outside_cwd(tmp_path: Path):
    script = Path(__file__).resolve().parents[1] / "tools" / "run_smoke_gpu_noarena.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
