"""
Regression suite — run after every merge into main, and on Day 7.
Deliberately fast and shallow: contract tests + smoke checks.
Run:  pytest tests/regression -m regression
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]


@pytest.mark.regression
def test_contract_suite_passes():
    """The contract suite is the regression baseline — must never break."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/contract", "-q", "--no-header"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.regression
def test_no_secrets_committed():
    """Checklist gate: no credentials hardcoded. Scans the whole project."""
    banned = ("BEGIN PRIVATE KEY", "password=", "secret=")
    hits = []
    for py in ROOT.rglob("*.py"):
        if any(part in (".git", "node_modules") for part in py.parts):
            continue
        text = py.read_text(errors="ignore")
        for line_no, line in enumerate(text.splitlines(), 1):
            if any(b.lower() in line.lower() for b in banned) and "test" not in py.name:
                hits.append(f"{py}:{line_no}")
    assert not hits, f"potential secrets:\n" + "\n".join(hits)


@pytest.mark.regression
def test_full_suite_runs_under_60s():
    """Weekly checklist: CI green. A slow suite kills parallel iteration."""
    import time

    start = time.time()
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-x", "--co", "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    elapsed = time.time() - start
    assert result.returncode == 0, result.stdout + result.stderr
    assert elapsed < 60, f"collection took {elapsed:.1f}s — suite is too heavy"
