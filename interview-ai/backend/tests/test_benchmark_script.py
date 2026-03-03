from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_benchmark_dry_run_generates_results_file() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    script_path = backend_root / "scripts" / "benchmark_eval.py"
    results_path = backend_root / "docs" / "benchmark_results.md"

    if results_path.exists():
        results_path.unlink()

    process = subprocess.run(
        [sys.executable, str(script_path), "--dry-run"],
        cwd=backend_root,
        capture_output=True,
        text=True,
    )

    assert process.returncode == 0, process.stderr
    assert "PASS (dry-run)" in process.stdout
    assert results_path.exists()

    content = results_path.read_text(encoding="utf-8")
    assert "# Benchmark Results (PRD §5.2)" in content
    assert "| Date | Question ID | Type | Min | Max | Range | Status |" in content
