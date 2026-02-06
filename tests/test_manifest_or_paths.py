from pathlib import Path


def test_default_dirs_can_be_created(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts" / "day7"
    figures = tmp_path / "figures" / "day7"
    output_root = tmp_path / "outputs"
    artifacts.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    assert artifacts.is_dir()
    assert figures.is_dir()
    assert output_root.is_dir()
