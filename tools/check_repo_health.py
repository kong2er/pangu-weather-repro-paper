#!/usr/bin/env python3
"""Repo health checks for Day8.

Goal: Validate essential files, .gitignore coverage, and doc command hygiene.
Inputs: Repository files.
Outputs: Console report and non-zero exit code on failures.
Example: uv run python tools/check_repo_health.py
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


REQUIRED_PATHS = [
    "README.md",
    "RUNBOOK.md",
    "pyproject.toml",
    "uv.lock",
    "configs/default.env",
    "scripts",
    "tools",
]

GITIGNORE_REQUIRED_PATTERNS = [
    "outputs/",
    "era5_raw/",
    "models/",
    "*.tgz",
]

DOC_FILES = [
    "README.md",
    "RUNBOOK.md",
    "Makefile",
]


def _check_required_paths(repo_root: Path) -> list[str]:
    missing = []
    for rel in REQUIRED_PATHS:
        p = repo_root / rel
        if not p.exists():
            missing.append(rel)
    return missing


def _check_gitignore(repo_root: Path) -> list[str]:
    path = repo_root / ".gitignore"
    if not path.exists():
        return ["missing .gitignore"]
    text = path.read_text()
    missing = [p for p in GITIGNORE_REQUIRED_PATTERNS if p not in text]
    return [f"pattern missing: {p}" for p in missing]


def _check_doc_commands(repo_root: Path) -> list[str]:
    issues = []
    bad_output_root = re.compile(r"\$OUTPUT_ROOT/\s+")
    bad_out_dir = re.compile(r"--out-dir\s+\"?\$OUTPUT_ROOT/\s+")
    for rel in DOC_FILES:
        path = repo_root / rel
        if not path.exists():
            continue
        for idx, line in enumerate(path.read_text().splitlines(), start=1):
            if bad_output_root.search(line) or bad_out_dir.search(line):
                issues.append(f"{rel}:{idx}: suspicious OUTPUT_ROOT spacing -> {line.strip()}")
    return issues


def main() -> int:
    p = argparse.ArgumentParser(description="Check repo health for Day8 deliverable.")
    p.add_argument("--root", default=".", help="repo root path")
    args = p.parse_args()

    repo_root = Path(args.root).resolve()
    failures = []

    missing = _check_required_paths(repo_root)
    if missing:
        failures.append("missing required paths: " + ", ".join(missing))

    gitignore_issues = _check_gitignore(repo_root)
    if gitignore_issues:
        failures.extend(gitignore_issues)

    doc_issues = _check_doc_commands(repo_root)
    if doc_issues:
        failures.extend(doc_issues)

    if failures:
        print("❌ repo health check failed")
        for item in failures:
            print("-", item)
        return 1

    print("✅ repo health check ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
