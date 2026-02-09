import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np


def _run(cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def test_plot_fields_no_rollout(tmp_path: Path):
    env = os.environ.copy()
    env["OUTPUT_ROOT"] = str(tmp_path)
    result = _run([sys.executable, "tools/plot_fields.py"], env=env)
    assert result.returncode == 2
    assert "Available" in result.stdout


def test_plot_fields_invalid_lead(tmp_path: Path):
    rollout_dir = tmp_path / "day4_rollout_30h"
    rollout_dir.mkdir(parents=True)
    pred = np.zeros((2, 2, 2), dtype=np.float32)
    gt = np.zeros((2, 2, 2), dtype=np.float32)
    npz_path = rollout_dir / "eval_z500.npz"
    np.savez(npz_path, pred_z500=pred, gt_z500=gt)
    meta = {
        "pred_path": str(npz_path),
        "steps": [24, 6],
        "date": "20230709",
        "hour": "00",
    }
    meta_path = rollout_dir / "eval_z500_meta.json"
    meta_path.write_text(json.dumps(meta))

    result = _run(
        [
            sys.executable,
            "tools/plot_fields.py",
            "--rollout-dir",
            str(rollout_dir),
            "--var",
            "z500",
            "--lead",
            "6",
        ]
    )
    assert result.returncode == 2
    assert "available leads" in result.stdout
